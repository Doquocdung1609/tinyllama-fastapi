"""Source-isolated answers and reconciled arithmetic for selected user PDFs."""
import re
from decimal import Decimal
from app.product.answer_composer_v2 import LABELS, UNITS, _select, display
from app.product.answer_planner_v2 import plan_question
from app.product.financial_understanding import document_profile, issuers
from app.product.independent_verifier_v2 import recompute, verify_operand
from app.product.source_cells_v2 import native_catalog


def answer(workspace, question, ids, per_document, constraints):
    docs = [{**workspace.document(doc_id),'id':doc_id} for doc_id in dict.fromkeys(ids)]
    requested_issuers = set(issuers(question))
    profiles = {doc['id']:document_profile(workspace,doc) for doc in docs}
    if requested_issuers:
        docs = [doc for doc in docs if requested_issuers.intersection(profiles[doc['id']]['identities'])]
    if len(docs)==1:
        return per_document(docs[0]['id'])
    p = plan_question(question)
    if not constraints and p.metric and len(p.years)==2 and p.operation in {'ABS_CHANGE','PERCENT_CHANGE','CHANGE_AND_GROWTH'}:
        result = compare(workspace,docs,profiles,p)
        if result:
            return result
    blocks, citations, verified_count = [], [], 0
    for doc in docs:
        try:
            response = per_document(doc['id'])
        except ValueError:
            response = {}
        refs = response.get('citations',[])
        start = len(citations)
        citations.extend(refs)
        text = response.get('answer') or 'Chưa có bằng chứng phù hợp trong PDF này.'
        text = re.sub(r'\[(\d+)\]',lambda m:f'[{start+int(m[1])}]' if 0<int(m[1])<=len(refs) else m[0],text)
        blocks.append(f"### {doc['filename']}\n{text}")
        verified_count += response.get('status')=='SUPPORTED'
    if not docs:
        return {'status':'NEEDS_CLARIFICATION','answer':'Tôi chưa xác định được doanh nghiệp trong các PDF đang chọn.',
                'values':[],'citations':[]}
    intro = ('Tôi đối chiếu từng PDF theo kỳ, đơn vị và phạm vi của chính tài liệu. '
             'Chỉ tính chênh lệch giữa các file khi xác nhận được các điều kiện so sánh.')
    return {'status':'SOURCE_EXCERPTS','answer_status':'PARTIAL_VERIFIED' if verified_count else 'REQUIRES_SOURCE_REVIEW',
            'answer':'\n\n'.join([intro,*blocks]),'citations':citations,'values':[],
            'verification_status':'PER_DOCUMENT_VERIFICATION','conversation_slots':p.public(),
            'source_document_ids':[d['id'] for d in docs]}


def compare(workspace, docs, profiles, plan):
    """Compare only source-proven observations with matching dimensions."""
    if len(docs)<2 or len(plan.metrics)>1 or plan.proposed_amount:
        return None
    identities = {(tuple(profiles[doc['id']]['identities']),profiles[doc['id']]['identity_method']) for doc in docs}
    if len(identities)!=1:
        return None
    ids, method = next(iter(identities))
    if len(ids)!=1 or method!='SOURCE_TEXT_ALIAS':
        return None
    catalogs = {doc['id']:native_catalog(workspace,[doc['id']]) for doc in docs}
    chosen = []
    for year in plan.years:
        candidates = []
        for doc in docs:
            try:
                cell = _select(catalogs[doc['id']],plan.metric,year,plan.scope,plan.basis or 'AS_REPORTED')
                if cell and (not plan.period_type or cell['period_type']==plan.period_type):
                    candidates.append(verify_operand(workspace,cell))
            except (ValueError,ArithmeticError):
                return None
        if not candidates or len({(c['value'],c['currency'],c['scale'],c['statement_scope'],c['period_type'],c['basis']) for c in candidates})!=1:
            return None
        candidates.sort(key=lambda c:(str(workspace.document(c['document_id']).get('report_period',''))[:4]!=year,c['document_id']))
        chosen.append(candidates[0])
    prior,current = chosen
    if plan.requested_unit not in {None,'%',current['unit'],current['currency']}:
        return None
    if current['statement_scope'] not in {'CONSOLIDATED','SEPARATE'}:
        return None
    try:
        delta = recompute('ABS_CHANGE',[current,prior],reconciled_documents=True)
        growth = (recompute('PERCENT_CHANGE',[current,prior],reconciled_documents=True)
                  if plan.operation!='ABS_CHANGE' and Decimal(prior['value']) else None)
    except (ValueError,ArithmeticError):
        return None
    if plan.operation in {'CHANGE_AND_GROWTH','PERCENT_CHANGE'} and growth is None:
        return None
    label = LABELS.get(plan.metric,(plan.metric,))[0]
    unit = UNITS.get(current['unit'],(current['unit'],))[0]
    if plan.requested_unit == current['currency'] and current['unit']!=current['currency']:
        return None
    d = display
    lines = [f'{label.capitalize()} của {ids[0]} được đối chiếu cùng chỉ tiêu, đơn vị, phạm vi và loại kỳ.',
             '| Kỳ | Giá trị | Tài liệu |\n| --- | ---: | --- |\n'+'\n'.join(
                f"| {c['period']} | {d(c['value'])} {unit} | {c['filename'].replace('|','/')} [{i}] |"
                for i,c in enumerate(chosen,1)),
             f"Chênh lệch = {d(current['value'])} − {d(prior['value'])} = **{d(delta)} {unit}**. [1][2]"]
    if growth is not None:
        lines.append(f"Mức thay đổi = chênh lệch ÷ {d(prior['value'])} × 100 = **{d(growth)}%**. [1][2]")
    values = [growth] if plan.operation=='PERCENT_CHANGE' else [delta,growth] if growth is not None else [delta]
    return {'status':'SUPPORTED','answer_status':'VERIFIED_ANSWER','answer':'\n\n'.join(lines),
            'citations':chosen,'operands':chosen,'values':values,'conversation_slots':plan.public(),
            'verification_status':'RECONCILED_PDF_SOURCE_CELLS_AND_DECIMAL'}

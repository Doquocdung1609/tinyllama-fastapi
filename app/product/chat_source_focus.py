"""Resolve an explicit PDF selection from source data, never client text."""
from contextlib import closing
from hashlib import sha256
import re

from app.product.ocr_candidate_answer import DEFINITIONS, describe_reread, eligible_candidate, locator, response
from app.product.pdf_extract import folded


def selected_source(workspace,payload):
    focus=payload.evidence_context
    doc_id=focus.get('document_id')
    number=focus.get('page')
    if (focus.get('intent')!='USER_SOURCE_FOCUS' or doc_id not in payload.document_ids
            or type(number) is not int):
        return None
    if any(not isinstance(focus[key],str) or len(focus[key])>220
           for key in ('row_id','column_id','chunk_id','citation_id') if focus.get(key) is not None):
        return None
    doc=workspace.document(doc_id)
    if not 1<=number<=doc['pages']:
        return None
    try:
        page=workspace.page_evidence(doc_id,number)
    except ValueError:
        return None
    if focus.get('row_id'):
        row=next((r for r in page['tables'] if r['id']==focus['row_id']),None)
        if row is None:
            if not str(focus['row_id']).startswith('date:'):
                return None
            from app.product.document_financial_cells import equity_matrix
            from app.product.pdf_ocr_financial_v3 import explicit_cover_scope
            cover=workspace.page_evidence(doc_id,1)
            candidates=[c for c in equity_matrix(doc,page,explicit_cover_scope(cover['text']))
                        if c['row_id']==focus['row_id'] and c['column_id']==focus.get('column_id')
                        and c['citation']['citation_id']==focus.get('citation_id')]
            return (candidates[0]['citation'],{},None) if len(candidates)==1 else None
        cell=None
        if focus.get('column_id'):
            cell=next((c for c in row['cells'] if c.get('cell_id')==focus['column_id'] and c.get('box')),None)
            if cell is None:
                return None
        source=locator(doc,page,row,cell)
        source['extraction_method']=page['method']
        return source,row,cell
    if str(focus.get('citation_id','')).startswith('cellv2_'):
        from app.product.source_cells_v2 import native_catalog
        from app.product.independent_verifier_v2 import verify_operand
        source=next((c for c in native_catalog(workspace,[doc_id]) if c['page']==number
                     and c['citation_id']==focus['citation_id']),None)
        if source is None:
            return None
        try:
            verify_operand(workspace,source)
        except ValueError:
            return None
        return source,{},None
    if focus.get('chunk_id'):
        with closing(workspace._connect()) as db:
            chunk=db.execute('SELECT text,text_hash FROM chunks WHERE document_id=? AND page=? AND id=?',
                             (doc_id,number,focus['chunk_id'])).fetchone()
        if chunk is None or sha256(chunk['text'].encode()).hexdigest()!=chunk['text_hash']:
            return None
        text=chunk['text'][:650]
    else:
        text=page['text'][:650]
    return {'document_id':doc_id,'page':number,'text':text,'filename':doc['filename'],
            'issuer':doc['issuer'],'source_sha256':doc['sha256'],'source_kind':'PDF',
            'chunk_id':focus.get('chunk_id'),'extraction_method':page['method']},{},None


def reference_followup(workspace,payload,history):
    q=folded(payload.question)
    if not history or not (re.match(r'^(?:co )?su khac biet .*ocr ban dau',q)
                           or re.match(r'^(?:giai thich|noi) don gian hon',q)):
        return None
    refs=history[-1]['response'].get('citations',[])
    if len(refs)!=1 or refs[0].get('extraction_method')!='OCR' or not refs[0].get('row_id'):
        return None
    source=refs[0]
    return selected_source(workspace,payload.model_copy(update={'evidence_context':{
        'intent':'USER_SOURCE_FOCUS','document_id':source.get('document_id'),'page':source.get('page'),
        'row_id':source.get('row_id'),'column_id':source.get('column_id')}}))


def explain_focus(selection,question):
    if not selection:
        return None
    q=folded(question).strip(' .?!')
    source,row,cell=selection
    if re.match(r'^(?:co )?su khac biet .*ocr ban dau',q):
        comparison=describe_reread(cell) if cell and eligible_candidate(row,cell) else None
        if comparison:
            return response(comparison+' [1]',[source],'OCR_CANDIDATE_ANSWER')
        return response('Ô nguồn chưa có hai lượt đọc nhất quán để đối chiếu. Mở ảnh gốc để kiểm tra các quan sát còn lại. [1]',[source])
    if q not in {'giai thich doan nguon nay','giai thich o nay','giai thich dong nay','noi ro hon ve doan nay'} and not re.match(
            r'^(?:giai thich|noi) don gian hon',q):
        return None
    definition=DEFINITIONS.get(row.get('metric'))
    if definition:
        text=definition+f" Bạn đang xem dòng “{source['row_label']}”"
        if cell:
            text+=f", cột {cell['column_label']}"
        return response(text+f", trang {source['page']}. [1]",[source])
    if row:
        return response(f"Dòng “{source['row_label']}” nằm ở trang {source['page']}. "
                        "Mở trích dẫn để xem dòng này cùng tiêu đề và các cột của bảng. [1]",[source])
    return response(f"Đây là đoạn nguồn ở trang {source['page']}. [1]\n\n"
                    +source['text'],[source])

"""Source-bound native operands and Decimal answers, separate from human reviews."""
from decimal import Decimal, localcontext, InvalidOperation
from hashlib import sha256
from pathlib import Path
from functools import lru_cache
import re
import json
import pymupdf
from pydantic import BaseModel, ConfigDict
from app.product.native_financial_tables import recover_retrieved_tables, recover_native_tables
from app.product.pdf_extract import folded
from app.product.financial_math import calculate,normalize_amount

VERSION='verified-native-operands/v1'

def _source_unit(cell):
    scale=Decimal(cell['scale'])
    prefix={Decimal(1):'',Decimal(1000):'THOUSAND_',Decimal(1000000):'MILLION_',Decimal(1000000000):'BILLION_'}
    if scale not in prefix:raise ValueError('UNSUPPORTED_SOURCE_SCALE')
    return prefix[scale]+cell['currency']


class FinancialCellEvidence(BaseModel):
    model_config=ConfigDict(extra='forbid')
    contract_version:str=VERSION
    document_id:str
    source_sha256:str
    source_kind:str='USER_PDF'
    issuer:str
    filing_type:str
    fiscal_year:int
    period_start:str|None=None
    period_end:str|None=None
    period_type:str='FISCAL_YEAR_DURATION'
    statement_scope:str
    statement_name:str
    table_id:str
    row_label:str
    metric_canonical_name:str
    metric_definition:str
    column_label:str
    value_raw:str
    value_decimal:Decimal
    currency:str
    scale:Decimal
    normalized_value:Decimal
    normalized_unit:str
    page:int
    row_bbox:list[float]
    cell_bbox:list[float]
    header_bbox:list[float]
    source_excerpt:str
    retrieved_chunk_ids:list[str]
    semantic_provenance:dict
    verification_status:str='CELL_VERIFIED'
    extractor_version:str=VERSION


def _digest(value):return sha256(json.dumps(value,sort_keys=True,default=str).encode()).hexdigest()


@lru_cache(maxsize=4)
def document_context(path,source_hash):
    # Caller rehashes bytes before using this immutable source/version-bound cache.
    texts=[];statement_pages=[];currency=[];segments=[];fiscal=[]
    with pymupdf.open(path) as pdf:
        if len(pdf)>250:raise ValueError('PDF_PAGE_LIMIT')
        total_chars=0
        for i,page in enumerate(pdf):
            text=' '.join(page.get_text().split());texts.append(text)
            total_chars+=len(text)
            if total_chars>2000000:raise ValueError('NATIVE_SOURCE_TEXT_BUDGET')
            if re.search(r'CONSOLIDATED STATEMENTS OF (?:OPERATIONS|INCOME)',text,re.I):statement_pages.append(i+1)
            for m in re.finditer(r'net sales and gross margins as expressed in U\.S\. dollars',text,re.I):
                currency.append({'page':i+1,'text':m[0],'method':'EXPLICIT_PRESENTATION_CURRENCY_NET_SALES'})
            for m in re.finditer(r'reportable segments consist of (?:the )?([^.;]+)',text,re.I):
                names=[s.strip() for s in re.split(r',\s*(?:and\s+)?|\s+and\s+',m[1]) if s.strip()]
                segments.append({'page':i+1,'text':m[0],'names':names})
            for m in re.finditer(r'\b(?:fiscal(?: years?)?|FY)\s*((?:20\d{2})(?:(?:\s*,\s*|\s+and\s+|\s*/\s*)20\d{2}){0,4})',text,re.I):
                fiscal.append({'page':i+1,'years':sorted(set(re.findall(r'20\d{2}',m[1]))),
                               'text':text[max(0,m.start()-30):m.end()+120]})
    cover=' '.join(texts[:3])
    from app.product.document_metadata import extract_metadata
    extracted=extract_metadata(path)['fields']['issuer']
    issuer=extracted['value'].strip() if extracted['status']=='AUTO_CONFIRMED' and extracted['value'] else None
    return {'currency':currency,'segments':segments,'fiscal':fiscal,'statement_pages':statement_pages[:4],
            'filing_type':'10-K' if re.search(r'FORM\s+10-K',cover,re.I) else 'UNKNOWN',
            'issuer':issuer,'source_sha256':source_hash}


def _metric(label):
    value=folded(label).strip(' :')
    return {'net income':'net_income','total net sales':'net_revenue','total assets':'assets',
            'operating income':'operating_income','gross profit':'gross_profit',
            'net cash provided by operating activities':'operating_cashflow'}.get(value)


def verified_bundle(workspace,document_ids,hits):
    tables=recover_retrieved_tables(workspace,document_ids,hits);cells=[];reasons=[]
    for doc_id in document_ids:
        doc=workspace.document(doc_id)
        if not doc or doc['status']!='READY':raise ValueError('PDF_DOCUMENT_NOT_READY')
        path=workspace.source_file(doc_id);context=document_context(str(path),doc['sha256'])
        if not context['issuer']:
            reasons.append('SOURCE_ISSUER_NOT_VERIFIED');continue
        selected=[t for t in tables if t['document_id']==doc_id]
        # Supplementary original-source statement headers provide comparative dates,
        # never additional retrieval hits. No ranking credit is assigned here.
        headers=recover_native_tables(path,context['statement_pages'],doc['sha256'])
        seeds=[h for h in hits if h.get('document_id')==doc_id and h.get('source_sha256')==doc['sha256']]
        for t in headers:
            # A bounded original statement lookup can verify a metric named by a
            # retrieved passage. It is explicitly supplementary, not a new hit.
            if any(any(_metric(c['row_label']) and folded(c['row_label']) in folded(h.get('text',''))
                       for c in t['cells']) for h in seeds):
                if not any(other['page']==t['page'] and other['heading']==t['heading'] for other in selected):
                    for c in t['cells']:
                        c['retrieved_chunk_ids']=list(dict.fromkeys(h['chunk_id'] for h in seeds))
                        c['supplementary_source_lookup']=True
                    selected.append(t)
        ends={}
        for t in headers:
            for c in t['cells']:
                if c.get('period_end'):ends.setdefault(c['year'],set()).add(c['period_end'])
        for table in selected:
            for c in table['cells']:
                metric=_metric(c['row_label'])
                if c['statement_scope']=='SEGMENT' and re.search(r'net sales',c['header_context'],re.I):metric='segment_net_sales'
                if not metric:continue
                if metric=='net_income' and not re.search(r'statements of (operations|income)',c['table_heading'],re.I):continue
                currency=c['currency'];currency_proof={'method':'LOCAL_TABLE_DECLARATION','text':c['header_context'],'page':c['page']}
                if currency=='UNKNOWN' and context['currency']:
                    has_sales=any(_metric(other['row_label'])=='net_revenue' for other in table['cells'])
                    if has_sales and re.search(r'\$|dollars',c['source_excerpt']+c['header_context']+' '.join(x['source_excerpt'] for x in table['cells']),re.I):
                        currency='USD';currency_proof={**context['currency'][0],'method':'EXPLICIT_NET_SALES_PRESENTATION_SAME_MONETARY_TABLE'}
                if currency=='UNKNOWN' or not c['scale']:
                    reasons.append('AMBIGUOUS_UNIT');continue
                if re.search(r'\b(?:CAD|AUD|HKD|EUR|VND|JPY|CNY|GBP)\b|Canadian dollars|Australian dollars',c['header_context'],re.I):
                    reasons.append('CONFLICTING_CURRENCY');continue
                # Avoid per-share or share-count amounts inheriting a monetary scale.
                if metric in {'assets'}:
                    reasons.append('INSTANT_PERIOD_BINDER_REQUIRED');continue
                if not context['fiscal'] or not any(str(c['year']) in f['years'] for f in context['fiscal']):
                    reasons.append('AMBIGUOUS_PERIOD');continue
                end=c.get('period_end')
                if not end and len(ends.get(c['year'],set()))==1:end=next(iter(ends[c['year']]))
                if not end:reasons.append('AMBIGUOUS_PERIOD');continue
                if c['statement_scope']=='UNKNOWN':reasons.append('AMBIGUOUS_SCOPE');continue
                source=FinancialCellEvidence(document_id=doc_id,source_sha256=doc['sha256'],
                    issuer=context['issuer'],filing_type=context['filing_type'],fiscal_year=c['year'],
                    period_end=end,statement_scope=c['statement_scope'],statement_name=c['table_heading'],
                    table_id=_digest([doc['sha256'],c['page'],c['header_context']])[:24],row_label=c['row_label'],
                    metric_canonical_name=metric,metric_definition=c['row_label'],column_label=c['column_label'],value_raw=c['raw_value'],
                    value_decimal=Decimal(c['value']),currency=currency,scale=Decimal(c['scale']),
                    normalized_value=normalize_amount(c['value'],c['scale']),normalized_unit=currency,page=c['page'],
                    row_bbox=c['row_box'],cell_bbox=c['box'],header_bbox=c['header_box'],source_excerpt=c['source_excerpt'],
                    retrieved_chunk_ids=c['retrieved_chunk_ids'],semantic_provenance={
                        'currency':currency_proof,'fiscal_period':{'method':'ANNUAL_COLUMN_AND_SAME_SOURCE_STATEMENT_DATE','end':end,
                             'supplemental_statement_pages':context['statement_pages'],
                             'fiscal_declaration':next(f for f in context['fiscal'] if str(c['year']) in f['years'])},
                        'scope':{'method':'LOCAL_TABLE_HEADING','text':c['table_heading']},
                        'retrieval_link':{'method':'SUPPLEMENTARY_STATEMENT_LOOKUP' if c.get('supplementary_source_lookup') else 'RETRIEVED_PAGE',
                                          'original_chunk_ids':c['retrieved_chunk_ids']},
                        'metric':{'method':'EXACT_ROW_DEFINITION','text':c['row_label']},
                        'scale':{'method':'LOCAL_TABLE_UNITS','text':c['header_context']}})
                cells.append(source.model_dump(mode='json'))
    return {'contract_version':VERSION,'cells':cells,'reasons':sorted(set(reasons)),
            'tables':tables,'retrieval_credit':'ORIGINAL_HITS_ONLY'}


def automatic_answer(workspace,request,result):
    q=folded(request.question)
    from app.product.query_source_context import source_company_conflict
    conflict=source_company_conflict(workspace,request.document_ids,request.question)
    if conflict:return conflict
    def refuse(reason,status='INSUFFICIENT_EVIDENCE'):
        return {'status':status,'reason':reason,'answer':'Chưa đủ bằng chứng phù hợp để xác nhận số liệu.',
                'values':[],'citations':[],'verification_status':reason}
    if len(request.document_ids)!=1:return refuse('SELECT_ONE_DOCUMENT_FOR_VERIFIED_CALCULATION')
    if re.search(r'\b(?:eur|vnd|cad|aud|hkd|jpy|cny|gbp|euros?|yen|dong)\b|in (?:thousands?|billions?)|percentage points|diem phan tram',q):
        return refuse('UNSUPPORTED_REQUESTED_CURRENCY_SCALE_OR_PERCENTAGE_POINTS')
    if re.search(r'\bquarter|\bq[1-4]\b|\bcalendar\b|(?:three|six|nine) months|quy [1-4]',q):return refuse('UNSUPPORTED_DURATION_REQUIRES_TYPED_PERIOD')
    if re.search(r'attributable|per share|eps|capex|capital expenditure|adjusted|restated|non-gaap|dieu chinh|trinh bay lai',q):return refuse('AMBIGUOUS_METRIC_DEFINITION')
    if 'basis' in request.model_fields_set and request.basis!='AS_REPORTED':return refuse('EXPLICIT_BASIS_CONFLICT','QUERY_CONTEXT_CONFLICT')
    from app.product.query_intent import metric_matches
    metrics=metric_matches(q)
    extreme=bool(re.search(r'highest|largest|maximum|lowest|minimum|lon nhat|nho nhat',q))
    if extreme and ('segment' in q or 'phan khuc' in q):
        if metrics!=['net_revenue']:return refuse('AMBIGUOUS_SEGMENT_METRIC')
        metric='segment_net_sales'
    elif len(metrics)==1:metric=metrics[0]
    elif not metrics and re.search(r'\bdoanh thu\b|\brevenue\b',q):return refuse('AMBIGUOUS_METRIC_DEFINITION')
    else:return refuse('AMBIGUOUS_METRIC')
    operation='MAX' if extreme and not re.search(r'lowest|minimum|nho nhat',q) else 'MIN' if extreme else 'PERCENT_CHANGE' if re.search(r'growth|tang truong|phan tram',q) else 'ABS_CHANGE' if re.search(r'difference|chenh lech',q) else 'EXTRACT'
    years=sorted(set(int(y) for y in re.findall(r'\b20\d{2}\b',q)))
    if len(years)!=(2 if operation in {'PERCENT_CHANGE','ABS_CHANGE'} else 1):return refuse('AMBIGUOUS_PERIOD')
    direction=re.search(r'from\s+(?:fiscal\s+)?(20\d{2})\s+to\s+(?:fiscal\s+)?(20\d{2})',q)
    if direction and direction[1]>direction[2]:return refuse('REVERSE_COMPARISON_REQUIRES_EXPLICIT_OPERAND_ORDER')
    bundle=verified_bundle(workspace,request.document_ids,result.get('results',[]))
    scope='SEGMENT' if metric=='segment_net_sales' else 'CONSOLIDATED'
    if re.search(r'\bseparate\b|parent company|\brieng\b|cong ty me',q) and scope!='SEPARATE':
        return refuse('QUESTION_SCOPE_CONFLICT','QUERY_CONTEXT_CONFLICT')
    for key,wanted in [('metric',metric),('operation',operation),('statement_scope',scope)]:
        if key in request.model_fields_set and getattr(request,key)!=wanted:return refuse('EXPLICIT_'+key.upper()+'_CONFLICT','QUERY_CONTEXT_CONFLICT')
    for key,year in [('current_period',years[-1]),('previous_period',years[0] if len(years)>1 else None)]:
        raw=re.sub(r'^FY\s*','',getattr(request,key),flags=re.I)
        if key in request.model_fields_set and raw and not re.fullmatch(r'20\d{2}(?:-\d{2}-\d{2})?',raw):return refuse('INVALID_EXPLICIT_PERIOD','QUERY_CONTEXT_CONFLICT')
        if key in request.model_fields_set and raw and (year is None or not str(raw).startswith(str(year))):return refuse('EXPLICIT_PERIOD_CONFLICT','QUERY_CONTEXT_CONFLICT')
    candidates=[c for c in bundle['cells'] if c['metric_canonical_name']==metric and c['statement_scope']==scope and c['fiscal_year'] in years]
    if not candidates and bundle['reasons'] and not any(c['metric_canonical_name']==metric for c in bundle['cells']):
        return refuse(bundle['reasons'][0])
    requested_dates=set(re.findall(r'\b20\d{2}-\d{2}-\d{2}\b',q))
    if requested_dates and not requested_dates<={c['period_end'] for c in candidates}:return refuse('QUESTION_PERIOD_CONFLICT','QUERY_CONTEXT_CONFLICT')
    for key in ('current_period','previous_period'):
        raw=getattr(request,key)
        if key in request.model_fields_set and re.fullmatch(r'20\d{2}-\d{2}-\d{2}',raw or '') and raw not in {c['period_end'] for c in candidates}:
            return refuse('EXPLICIT_PERIOD_CONFLICT','QUERY_CONTEXT_CONFLICT')
    operands=[];winner=None
    if metric=='segment_net_sales':
        context=document_context(str(workspace.source_file(request.document_ids[0])),workspace.document(request.document_ids[0])['sha256'])
        declarations={tuple(sorted(folded(n) for n in s['names'])) for s in context['segments']}
        groups={}
        for c in candidates:groups.setdefault(c['table_id'],[]).append(c)
        eligible=[]
        for group in groups.values():
            totals=[c for c in group if folded(c['row_label'])=='total net sales'];parts=[c for c in group if not folded(c['row_label']).startswith('total')]
            if len(totals)!=1 or tuple(sorted(folded(c['row_label']) for c in parts)) not in declarations:continue
            if len({(c['currency'],c['scale']) for c in group})!=1:continue
            if calculate('SUM',[c['value_decimal'] for c in parts])!=Decimal(totals[0]['value_decimal']):continue
            eligible.append(parts)
        if len(eligible)!=1:return refuse('INCOMPLETE_OR_AMBIGUOUS_SEGMENT_SET')
        operands=eligible[0];ordered=sorted(operands,key=lambda c:Decimal(c['value_decimal']),reverse=operation=='MAX')
        if len(ordered)>1 and ordered[0]['value_decimal']==ordered[1]['value_decimal']:return refuse('TIED_SEGMENT_EXTREMUM')
        winner=ordered[0];value=calculate(operation,[c['value_decimal'] for c in operands]);unit=_source_unit(winner);formula=operation+' over all declared source segments'
    else:
        for year in reversed(years):
            selected=[c for c in candidates if c['fiscal_year']==year]
            if not selected:return refuse('SOURCE_PERIOD_OR_CELL_NOT_FOUND')
            if len({(c['value_decimal'],c['currency'],c['scale'],c['period_end']) for c in selected})!=1:return refuse('CONFLICTING_EVIDENCE')
            selected.sort(key=lambda c:(not bool(re.search('statements of (operations|income)',c['statement_name'],re.I)),c['page']))
            operands.append(selected[0])
        if len({(c['currency'],c['scale']) for c in operands})!=1:return refuse('INCOMPATIBLE_UNIT')
        numbers=[Decimal(c['value_decimal']) for c in operands]
        with localcontext() as ctx:
            ctx.prec=40;value=numbers[0];formula='Source cell';unit=_source_unit(operands[0])
            if operation=='PERCENT_CHANGE':
                if not numbers[1]:return refuse('ZERO_DENOMINATOR')
                value=calculate('PERCENT_CHANGE',numbers,round_places=2)
                formula=f'({numbers[0]} - {numbers[1]}) / {numbers[1]} × 100';unit='%'
            elif operation=='ABS_CHANGE':value=calculate('ABS_CHANGE',numbers);formula=f'{numbers[0]} - {numbers[1]}'
    citations=[]
    for c in operands:
        citations.append({**c,'evidence_id':'pdfcell_'+_digest([c['source_sha256'],c['page'],c['cell_bbox'],c['header_bbox']])[:32],
            'text':c['source_excerpt'],'box':c['cell_bbox'],'header_box':c['header_bbox'],
            'row_box':c['row_bbox'],'period':c['period_end'],'unit':_source_unit(c),
            'verification':'AUTO_SOURCE_CELL_VERIFIED','chunk_id':c['retrieved_chunk_ids'][0],
            'source_display':c['value_raw']})
    display=format(value,',f').replace(',','_').replace('.',',').replace('_','.')
    label={'MILLION_USD':'triệu USD','THOUSAND_USD':'nghìn USD','BILLION_USD':'tỷ USD'}.get(unit,unit)
    return {'status':'SUPPORTED','operation':operation,'values':[str(value)],'unit':unit,'formula':formula,
        'answer':(winner['row_label']+' — ' if winner else '')+display+' '+label,
        'winner':winner['row_label'] if winner else None,'citations':citations,'operands':operands,
        'verification_status':'CELL_VERIFIED','verification':'DECIMAL_WITH_AUTOMATIC_SOURCE_CELLS',
        'effective_mode':result.get('mode'),'routing_reason':result.get('routing_reason'),
        'evidence_contract':VERSION,'retrieval_trace':{'profile':result.get('search_profile','baseline'),
            'generation':result.get('generation'),'effective_mode':result.get('mode'),
            'original_hit_ids':list(dict.fromkeys(h['chunk_id'] for h in result.get('results',[])))}}


def validate_supported_response(workspace,answer,operation=None):
    """Reject a producer's SUPPORTED label if provenance or arithmetic is absent."""
    if answer.get('status')!='SUPPORTED':return answer
    try:
        citations=answer.get('citations',[])
        if not citations or len(answer.get('values',[]))!=1:raise ValueError('MISSING_PROVENANCE')
        verified_docs=set()
        for citation in citations:
            doc_id=citation['document_id'];doc=workspace.document(doc_id)
            if doc is None or citation['source_sha256']!=doc['sha256']:raise ValueError('SOURCE_MISMATCH')
            if not citation.get('box') or not citation.get('page'):raise ValueError('MISSING_LOCATOR')
            if not 1<=int(citation['page'])<=doc.get('pages',0):raise ValueError('INVALID_SOURCE_PAGE')
            if doc_id not in verified_docs:workspace.source_file(doc_id);verified_docs.add(doc_id)
        if answer.get('evidence_contract')==VERSION:
            operands=[FinancialCellEvidence.model_validate(c) for c in answer['operands']]
            if len(operands)!=len(citations):raise ValueError('OPERAND_CITATION_MISMATCH')
            for operand in operands:
                if normalize_amount(operand.value_decimal,operand.scale)!=operand.normalized_value:raise ValueError('NORMALIZATION_MISMATCH')
                raw=operand.value_raw.strip();negative=raw.startswith('(') and raw.endswith(')')
                parsed=Decimal(raw.strip('()').replace(',',''))*(-1 if negative else 1)
                if parsed!=operand.value_decimal:raise ValueError('RAW_VALUE_MISMATCH')
            op=answer['operation'];computed=calculate(op,[c.value_decimal for c in operands],2 if op=='PERCENT_CHANGE' else None)
            if computed!=Decimal(answer['values'][0]):raise ValueError('CALCULATION_MISMATCH')
        elif not operation:raise ValueError('UNIDENTIFIED_REVIEWED_OPERATION')
        if not Decimal(answer['values'][0]).is_finite():raise ValueError('NONFINITE_CLAIM')
    except (ValueError,KeyError,TypeError,AttributeError,InvalidOperation):
        return {'status':'CONFLICTING_EVIDENCE','reason':'CLAIM_PROVENANCE_VALIDATION_FAILED',
                'answer':'Bản trả lời chưa có đủ nguồn và phép tính hợp lệ; hệ thống đã chặn số liệu.',
                'values':[],'citations':[],'verification_status':'CONFLICTING_EVIDENCE'}
    return answer

"""Independent gate: reopen source operands, then recompute the claim graph.

This module deliberately does not import the answer composer, candidate catalog
extractor, native-adjustment verifier or the producer's financial_math helper.
"""
from dataclasses import asdict, dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation, localcontext, ROUND_HALF_UP
from hashlib import sha256
from contextlib import closing
import json
import re
import pymupdf
from app.product.pdf_extract import folded

VERSION='INDEPENDENT_FINANCIAL_GATE_V2'

@dataclass
class Claim:
    claim_id:str
    type:str
    source_refs:list[str]
    source_scope:str|None
    period:list[str]
    verification_status:str
    text:str=''
    value:str|None=None
    calculation_id:str|None=None
    operand_ids:list[str]=field(default_factory=list)

@dataclass
class AnswerPlan:
    question_plan:dict
    claims:list[Claim]
    citations:list[dict]
    operands:list[dict]=field(default_factory=list)
    calculations:list[dict]=field(default_factory=list)
    version:str='VERIFIED_ANSWER_PLAN_V2'
    def public(self):return asdict(self)

def raw_decimal(raw):
    value=raw.strip().replace('−','-').rstrip('%').strip()
    neg=value.startswith('(') and value.endswith(')')
    if not re.fullmatch(r'\(?[+-]?\d{1,3}(?:,\d{3})*(?:\.\d+)?\)?|\(?[+-]?\d+(?:\.\d+)?\)?',value):raise ValueError('RAW_NUMBER_SYNTAX')
    if ('(' in value or ')' in value) and not neg:raise ValueError('NEGATIVE_SYNTAX')
    result=Decimal(value.strip('()').replace(',',''))*(-1 if neg else 1)
    if not result.is_finite():raise ValueError('NONFINITE_VALUE')
    return result

def _clip(page,box):
    if not isinstance(box,list) or len(box)!=4 or not all(isinstance(v,(int,float)) for v in box):raise ValueError('INVALID_BOX')
    r=pymupdf.Rect(box)
    if r.is_empty or r.x0<-.1 or r.y0<-.1 or r.x1>page.rect.width+.1 or r.y1>page.rect.height+.1:raise ValueError('BOX_OUTSIDE_PAGE')
    r.x0-=.5;r.y0-=.5;r.x1+=.5;r.y1+=.5
    return page.get_text(clip=r)

def _identity(c):
    keys=('document_id','source_sha256','page','box','header_box','row_label','metric','period','value_raw','unit','statement_scope','basis')
    return 'cellv2_'+sha256(json.dumps({k:c.get(k) for k in keys},sort_keys=True).encode()).hexdigest()[:28]

def verify_operand(w,c):
    """Stage A: no producer eligibility flag is trusted."""
    if c.get('extraction_method')!='NATIVE':raise ValueError('OCR_CELL_REQUIRES_IMAGE_REVIEW')
    doc=w.document(c['document_id'])
    if not doc or doc['sha256']!=c['source_sha256']:raise ValueError('SOURCE_HASH_MISMATCH')
    path=w.source_file(c['document_id'])
    if sha256(path.read_bytes()).hexdigest()!=c['source_sha256']:raise ValueError('SOURCE_BYTES_CHANGED')
    if c.get('citation_id')!=_identity(c):raise ValueError('CITATION_ID_MISMATCH')
    with pymupdf.open(path) as pdf:
        page_no=c['page']
        if not isinstance(page_no,int) or not 1<=page_no<=len(pdf):raise ValueError('PAGE_OUT_OF_RANGE')
        page=pdf[page_no-1]
        if page.rotation:raise ValueError('UNSUPPORTED_NATIVE_ROTATION')
        raw=''.join(_clip(page,c['box']).split())
        if raw!=''.join(c['value_raw'].split()):raise ValueError('ORIGINAL_CELL_VALUE_MISMATCH')
        row=folded(' '.join(_clip(page,c['row_box']).split()))
        if folded(c['row_label']) not in row:raise ValueError('ORIGINAL_ROW_LABEL_MISMATCH')
        box=c['box'];rb=c['row_box']
        if box[0]<rb[0]-.6 or box[2]>rb[2]+.6 or box[1]<rb[1]-.6 or box[3]>rb[3]+.6:raise ValueError('CELL_OUTSIDE_DECLARED_ROW')
        header=folded(' '.join(_clip(page,c['header_box']).split()))
        year=str(c['period'])
        if c.get('basis') in {'ORIGINAL','ADJUSTMENT','RESTATED'}:
            if c.get('metric')=='retained_earnings' and 'loi nhuan sau thue chua phan phoi' not in row:raise ValueError('ADJUSTMENT_METRIC_MISMATCH')
            if c.get('basis')=='ADJUSTMENT' and 'chinh' not in header:raise ValueError('ADJUSTMENT_HEADER_MISMATCH')
            if c.get('basis')=='ORIGINAL' and 'cong bo' not in header:raise ValueError('ORIGINAL_HEADER_MISMATCH')
            if c.get('basis')=='RESTATED' and 'trinh bay lai' not in header:raise ValueError('RESTATED_HEADER_MISMATCH')
            context_no=c['scope_source_page']
            if context_no not in {page_no,page_no-1}:raise ValueError('CONTINUATION_SCOPE_MISMATCH')
            context=folded(pdf[context_no-1].get_text())
            if not re.search(r'31/12/'+year,context):raise ValueError('ADJUSTMENT_PERIOD_UNPROVEN')
            scope='CONSOLIDATED' if 'hop nhat' in context[:1600] else 'SEPARATE' if 'rieng' in context[:1600] else None
            if scope!=c['statement_scope'] or 'trieu dong' not in context:raise ValueError('ADJUSTMENT_SCOPE_UNIT_MISMATCH')
            if (c['currency'],c['scale'],c['unit'])!=('VND','1000000','TRIEU_VND'):raise ValueError('ADJUSTMENT_UNIT_MISMATCH')
            markers=[]
            for token in ('đã','chỉnh','trình'):
                words=[w for w in page.get_text('words') if w[3]<min(box[1]-4,150) and w[4].casefold().strip('():.')==token]
                if len(words)!=1:raise ValueError('AMBIGUOUS_ADJUSTMENT_HEADERS')
                markers.append((words[0][0]+words[0][2])/2)
            bounds=[(markers[i]+markers[i+1])/2 for i in range(2)];x=(box[0]+box[2])/2
            actual=0 if x<bounds[0] else 1 if x<bounds[1] else 2
            if c['basis']!=('ORIGINAL','ADJUSTMENT','RESTATED')[actual]:raise ValueError('ADJUSTMENT_COLUMN_SWAPPED')
        else:
            if year not in header:raise ValueError('COLUMN_PERIOD_MISMATCH')
            yw=[w for w in page.get_text('words') if abs(w[1]-c['header_box'][1])<2 and re.fullmatch('20[0-9]{2}',w[4])]
            if len(yw)<2:raise ValueError('UNPROVEN_ANNUAL_COLUMN_SET')
            nearest=min(yw,key=lambda w:abs(box[2]-(w[0]+w[2])/2))
            if nearest[4]!=year:raise ValueError('YEAR_COLUMN_SWAPPED')
            context=folded(_clip(page,c['section_box'])) if c.get('section_box') else ''
            label=folded(re.sub(r'\s*\(\d+\)\s*$','',c['row_label'])).strip(' :')
            metric=c['metric']
            if metric.startswith(('products_','services_')):
                category=metric.split('_',1)[0]
                if label!=category:raise ValueError('PRODUCT_CATEGORY_MISMATCH')
                suffix=metric[len(category)+1:]
                required={'net_sales':'net sales','cost_of_sales':'cost of sales','gross_margin':'gross margin','gross_margin_percentage':'gross margin percentage'}.get(suffix)
                if not required or required not in context:raise ValueError('METRIC_SECTION_MISMATCH')
                grouped={}
                for word in page.get_text('words'):
                    if c['header_box'][3]<word[1]<box[1]-2:grouped.setdefault(round(word[1]),[]).append(word)
                headings=[]
                for y,words in grouped.items():
                    text=folded(' '.join(w[4] for w in sorted(words,key=lambda w:w[0])))
                    if re.search(r'^(?:net sales|cost of sales|gross margin(?: percentage)?|long-lived assets):$',text):headings.append((y,text))
                if headings and required!=max(headings)[1].strip(':'):raise ValueError('INTERVENING_ACCOUNTING_SECTION')
            elif metric=='us_net_sales':
                if label!='u.s.' or 'net sales' not in context or 'long-lived assets' in context:raise ValueError('GEOGRAPHY_METRIC_MISMATCH')
            elif metric in {'americas_net_sales','europe_net_sales','greater_china_net_sales','japan_net_sales','rest_of_asia_pacific_net_sales'}:
                expected=metric.removesuffix('_net_sales').replace('_',' ')
                if label!=expected or 'net sales' not in context:raise ValueError('SEGMENT_METRIC_MISMATCH')
            elif metric=='effective_tax_rate':
                if label!='effective tax rate' or not c['value_raw'].endswith('%'):raise ValueError('EFFECTIVE_TAX_RATE_MISMATCH')
            elif metric in {'net_revenue','net_income','gross_profit','operating_income','assets','gross_margin_percentage'}:
                allowed={'net_revenue':{'total net sales'},'net_income':{'net income'},'gross_profit':{'gross margin','total gross margin'},
                    'operating_income':{'operating income'},'assets':{'total assets'},'gross_margin_percentage':{'total gross margin percentage'}}
                if label not in allowed[metric]:raise ValueError('METRIC_DEFINITION_MISMATCH')
            else:raise ValueError('UNSUPPORTED_CELL_METRIC')
            scope_page=pdf[c['scope_source_page']-1].get_text()
            if c['statement_scope']!='CONSOLIDATED' or not re.search('CONSOLIDATED STATEMENTS',scope_page):raise ValueError('CONSOLIDATED_SCOPE_UNPROVEN')
            if year not in scope_page:raise ValueError('FISCAL_PERIOD_UNPROVEN')
            exact_dates=[]
            for month,day,yr in re.findall(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s*(20\d{2})',scope_page[:1200]):
                if yr==year:exact_dates.append(datetime.strptime(f'{month} {day} {yr}','%B %d %Y').date().isoformat())
            # Independently reconstruct split month/day and year column headers.
            scope_original=pdf[c['scope_source_page']-1]
            for yearword in scope_original.get_text('words'):
                if yearword[4]!=year:continue
                siblings=[v for v in scope_original.get_text('words') if abs(v[1]-yearword[1])<2 and re.fullmatch(r'20\d{2}',v[4])]
                if len(siblings)<2:continue
                center=(yearword[0]+yearword[2])/2;gap=min(abs(center-(v[0]+v[2])/2) for v in siblings if v!=yearword)
                fragment=scope_original.get_text(clip=pymupdf.Rect(center-gap/2,max(0,yearword[1]-40),center+gap/2,yearword[3]+1))
                found=re.findall(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?',fragment)
                if len(found)==1:exact_dates=[datetime.strptime(f'{found[0][0]} {found[0][1]} {year}','%B %d %Y').date().isoformat()];break
            if exact_dates!=[c['period_end']]:raise ValueError('EXACT_PERIOD_END_MISMATCH')
            if c['period_type']!='FY':raise ValueError('NONANNUAL_PERIOD_REQUIRES_EXACT_DATE_BINDER')
            local=page.get_text(clip=pymupdf.Rect(0,max(0,c['header_box'][1]-150),page.rect.width,c['header_box'][3]+1))
            if re.search(r'(?:three|six|nine) months (?:ended|ending)|(?:quarter|quarterly) (?:ended|results)|quy\s*(?:iv|iii|ii|i|[1-4])',folded(local)):raise ValueError('LOCAL_TABLE_IS_NOT_ANNUAL')
            if c['unit']=='%':
                if not raw.endswith('%') or c['currency']!='PERCENT' or c['scale']!='1':raise ValueError('PERCENT_UNIT_MISMATCH')
            else:
                proof=pdf[c['currency_source_page']-1].get_text()
                if not re.search(r'U\.S\. dollars|\bUSD\b',proof,re.I):raise ValueError('PRESENTATION_CURRENCY_UNPROVEN')
                if not re.search(r'\bmillions\b',local,re.I) or (c['unit'],c['currency'],c['scale'])!=('MILLION_USD','USD','1000000'):raise ValueError('AMOUNT_SCALE_MISMATCH')
        value=raw_decimal(c['value_raw'])
        if 'value' in c and value!=Decimal(c['value']):raise ValueError('PROPOSED_OPERAND_VALUE_MISMATCH')
        return {**c,'value':str(value),'verification_status':'INDEPENDENT_SOURCE_CELL_VERIFIED','normalized_value':str(value*Decimal(c['scale']))}

def recompute(operation,operands,places=2,target_unit=None,proposed_amount=None,*,reconciled_documents=False):
    """Stage B: separate implementation; values are Stage-A records only."""
    if not operands:raise ValueError('NO_VERIFIED_OPERANDS')
    values=[Decimal(c['value']) for c in operands]
    if any(not v.is_finite() for v in values):raise ValueError('NONFINITE_OPERAND')
    if len({(c['currency'],c['scale'],c['unit']) for c in operands})!=1:raise ValueError('DIMENSIONAL_UNIT_MISMATCH')
    if len({c['document_id'] for c in operands})!=1 and not (
            reconciled_documents and operation in {'ABS_CHANGE','PERCENT_CHANGE'} and
            all(c.get('verification_status')=='INDEPENDENT_SOURCE_CELL_VERIFIED' for c in operands)):
        raise ValueError('CROSS_DOCUMENT_CALCULATION_REQUIRES_RECONCILIATION')
    if len({c['period_type'] for c in operands})!=1:raise ValueError('PERIOD_TYPE_MISMATCH')
    metrics={c['metric'] for c in operands};scopes={c['statement_scope'] for c in operands};years={c['period'] for c in operands}
    if operation!='SCOPE_DIFFERENCE' and len(scopes)!=1:raise ValueError('SCOPE_MISMATCH')
    if operation=='SCOPE_DIFFERENCE' and (scopes!={'SEPARATE','CONSOLIDATED'} or len(years)!=1 or len(metrics)!=1 or any(c['basis']!='ADJUSTMENT' for c in operands)):raise ValueError('INCOMPATIBLE_SCOPE_DIFFERENCE')
    if operation in {'ABS_CHANGE','PERCENT_CHANGE'} and (len(metrics)!=1 or len(years)!=2):raise ValueError('INCOMPATIBLE_PERIOD_COMPARISON')
    if operation in {'SHARE_PERCENT','PER_100','RELATIVE_DIFFERENCE','GEOGRAPHY_DIFFERENCE','PERCENTAGE_POINT_DIFFERENCE','RESTATEMENT_GROWTH','RESTATEMENT_IDENTITY','SUM','PART_WHOLE_CHECK'} and len(years)!=1:raise ValueError('SAME_PERIOD_REQUIRED')
    if operation in {'SHARE_PERCENT','PER_100'} and (operands[1]['metric']!='net_revenue' or operands[0]['metric'] not in {'services_net_sales','products_net_sales','net_income','gross_profit'}):raise ValueError('DENOMINATOR_SEMANTICS_MISMATCH')
    if operation in {'PERCENTAGE_POINT_DIFFERENCE','RELATIVE_DIFFERENCE'} and (operands[0]['unit']!='%' or not all('gross_margin_percentage' in c['metric'] for c in operands)):raise ValueError('PERCENTAGE_POINT_DIMENSION_MISMATCH')
    if operation in {'ABS_CHANGE','PERCENT_CHANGE'} and len({c['basis'] for c in operands})!=1:raise ValueError('REPORTING_BASIS_MISMATCH')
    if operation=='RESTATEMENT_IDENTITY' and len(metrics)!=1:raise ValueError('RESTATEMENT_METRIC_MISMATCH')
    if operation=='RESTATEMENT_GROWTH' and ([c['basis'] for c in operands]!=['ADJUSTMENT','ORIGINAL'] or len(metrics)!=1):raise ValueError('RESTATEMENT_BASIS_MISMATCH')
    if operation in {'ABS_CHANGE','PERCENT_CHANGE'} and operands[0]['period']<=operands[1]['period']:raise ValueError('PERIOD_DIRECTION_MISMATCH')
    if operation=='SCOPE_DIFFERENCE' and [c['statement_scope'] for c in operands]!=['CONSOLIDATED','SEPARATE']:raise ValueError('SCOPE_DIRECTION_MISMATCH')
    if operation in {'PERCENTAGE_POINT_DIFFERENCE','RELATIVE_DIFFERENCE'} and [c['metric'] for c in operands]!=['services_gross_margin_percentage','products_gross_margin_percentage']:raise ValueError('MARGIN_DIRECTION_MISMATCH')
    if operation=='GEOGRAPHY_DIFFERENCE' and [c['metric'] for c in operands]!=['americas_net_sales','us_net_sales']:raise ValueError('GEOGRAPHY_DIRECTION_MISMATCH')
    if operation=='RATE_POINT_CHANGE' and (len(operands)!=2 or metrics!={'effective_tax_rate'} or operands[0]['unit']!='%' or operands[0]['period']<=operands[1]['period']):raise ValueError('RATE_PERIOD_DIMENSION_MISMATCH')
    with localcontext() as ctx:
        ctx.prec=50
        if operation=='PROPOSAL_DIFFERENCE' and len(values)==1 and proposed_amount is not None:
            result=Decimal(proposed_amount)-values[0]
        elif operation=='EXTRACT' and len(values)==1:
            result=values[0]
            if target_unit and target_unit!=operands[0]['unit']:
                units={'VND':('VND','1'),'TRIEU_VND':('VND','1000000'),'TY_VND':('VND','1000000000'),
                    'USD':('USD','1'),'MILLION_USD':('USD','1000000')}
                if target_unit not in units or units[target_unit][0]!=operands[0]['currency']:raise ValueError('FX_CONVERSION_NOT_AUTHORIZED')
                result=result*Decimal(operands[0]['scale'])/Decimal(units[target_unit][1])
        elif operation in {'ABS_CHANGE','SCOPE_DIFFERENCE','GEOGRAPHY_DIFFERENCE','PERCENTAGE_POINT_DIFFERENCE','RATE_POINT_CHANGE'} and len(values)==2:result=values[0]-values[1]
        elif operation in {'PERCENT_CHANGE','SHARE_PERCENT','PER_100','RELATIVE_DIFFERENCE','RESTATEMENT_GROWTH'} and len(values)==2:
            if not values[1]:raise ValueError('ZERO_DENOMINATOR')
            if operands[0]['unit']=='%' and operation!='RELATIVE_DIFFERENCE':raise ValueError('PERCENT_AS_MONETARY_AMOUNT')
            result=((values[0]-values[1]) if operation in {'PERCENT_CHANGE','RELATIVE_DIFFERENCE'} else values[0])/values[1]*Decimal(100)
        elif operation=='RESTATEMENT_IDENTITY' and len(values)==3:
            if [c['basis'] for c in operands]!=['ORIGINAL','ADJUSTMENT','RESTATED']:raise ValueError('RESTATEMENT_COLUMN_ORDER')
            result=values[0]+values[1]-values[2]
        elif operation=='SUM' and len(values)==2:
            if [c['metric'] for c in operands]!=['products_net_sales','services_net_sales']:raise ValueError('PART_WHOLE_SEMANTICS')
            result=values[0]+values[1]
        elif operation=='PART_WHOLE_CHECK' and len(values)==3:
            if [c['metric'] for c in operands]!=['products_net_sales','services_net_sales','net_revenue']:raise ValueError('PART_WHOLE_SEMANTICS')
            result=values[0]+values[1]-values[2]
        else:raise ValueError('OPERATION_OR_OPERAND_COUNT')
        if operation in {'PERCENT_CHANGE','SHARE_PERCENT','PER_100','RELATIVE_DIFFERENCE','RESTATEMENT_GROWTH','PERCENTAGE_POINT_DIFFERENCE','RATE_POINT_CHANGE'}:
            result=result.quantize(Decimal(1).scaleb(-places),rounding=ROUND_HALF_UP)
        return str(result)

def verify_plan(w,plan):
    audit={'version':VERSION,'stage_a':[],'stage_b':[],'status':'REJECTED'}
    try:
        ids=[c['citation_id'] for c in plan.citations]
        if len(ids)!=len(set(ids)):raise ValueError('DUPLICATE_CITATION_ID')
        operand_citations={c['citation_id'] for c in plan.operands}
        for citation in plan.citations:
            doc=w.document(citation['document_id'])
            if not doc or doc['sha256']!=citation['source_sha256']:raise ValueError('CITATION_SOURCE_MISMATCH')
            w.source_file(citation['document_id'])
            if not 1<=citation['page']<=doc['pages']:raise ValueError('CITATION_PAGE_MISMATCH')
            if citation['citation_id'] in operand_citations:continue
            if citation['citation_id'].startswith('cellv2_'):
                if citation['citation_id']!=_identity(citation):raise ValueError('SOURCE_CELL_LOCATOR_FORGED')
                with pymupdf.open(w.source_file(citation['document_id'])) as original:
                    source_page=original[citation['page']-1]
                    if ''.join(_clip(source_page,citation['box']).split())!=''.join(citation['value_raw'].split()):raise ValueError('SOURCE_ONLY_CELL_BYTES_MISMATCH')
                    if folded(citation['row_label']) not in folded(_clip(source_page,citation['row_box'])):raise ValueError('SOURCE_ONLY_ROW_MISMATCH')
                continue
            evidence=w.page_evidence(citation['document_id'],citation['page'])
            if citation['citation_id'].startswith('heading_'):
                expected='heading_'+sha256(json.dumps([doc['sha256'],citation['page'],citation.get('box'),citation['text']]).encode()).hexdigest()[:24]
                if expected!=citation['citation_id'] or not any(line['text']==citation['text'] and line.get('box')==citation.get('box') for line in evidence.get('lines',[])):raise ValueError('HEADING_CITATION_FORGED')
            elif citation.get('row_id'):
                row=next((r for r in evidence.get('tables',[]) if r['id']==citation['row_id']),None)
                expected=sha256(f"{doc['sha256']}:{citation['page']}:{citation['row_id']}:{evidence['evidence_sha256']}".encode()).hexdigest()[:24]
                if row is None:
                    raise ValueError('ROW_CITATION_FORGED')
                if citation.get('column_id') and evidence.get('version')=='studio-vietnamese-financial-ocr-v3':
                    cell=next((c for c in row['cells'] if c.get('cell_id')==citation['column_id']),None)
                    expected=sha256(f"{expected}:{citation['column_id']}".encode()).hexdigest()[:24]
                    if (cell is None or not cell.get('box') or cell['box']!=citation.get('box')
                            or cell.get('source_sha256')!=doc['sha256'] or citation.get('numeric_status')!='UNVERIFIED'):
                        raise ValueError('OCR_CANDIDATE_LOCATOR_FORGED')
                if expected!=citation['citation_id']:
                    raise ValueError('ROW_CITATION_FORGED')
            elif citation.get('chunk_id') and hasattr(w,'_connect'):
                with closing(w._connect()) as db:row=db.execute('SELECT document_id,page,text FROM chunks WHERE id=?',(citation['chunk_id'],)).fetchone()
                if row is None or row['document_id']!=doc['id'] or row['page']!=citation['page'] or not row['text'].startswith(citation['text']):raise ValueError('CHUNK_CITATION_FORGED')
            else:raise ValueError('CITATION_WITHOUT_SOURCE_LOCATOR')
        verified={}
        for operand in plan.operands:
            c=verify_operand(w,operand);verified[c['operand_id']]=c
            if c['citation_id'] not in ids:raise ValueError('OPERAND_CITATION_NOT_IN_PLAN')
            audit['stage_a'].append({'operand_id':c['operand_id'],'citation_id':c['citation_id'],'value':c['value'],'status':'VERIFIED'})
        calculations={}
        calculation_inputs={}
        for calc in plan.calculations:
            if calc['operation'] in {'PERCENT_CHANGE','SHARE_PERCENT','PER_100','RELATIVE_DIFFERENCE','RESTATEMENT_GROWTH','PERCENTAGE_POINT_DIFFERENCE','RATE_POINT_CHANGE'} and calc.get('round_places',2)!=2:raise ValueError('ROUNDING_POLICY_MISMATCH')
            inputs=[verified[i] for i in calc['operand_ids']]
            proposed=None
            if calc['operation']=='PROPOSAL_DIFFERENCE':
                raw=plan.question_plan.get('raw_text','')
                match=re.search(r'(\d[\d.,]*\d|\d)\s*(?:million|triệu)',raw,re.I)
                if not match:raise ValueError('USER_PROPOSAL_NOT_IN_QUESTION')
                number=match[1]
                if '.' in number and ',' in number:
                    dec=max(number.rfind('.'),number.rfind(','));proposed=re.sub(r'[.,]','',number[:dec])+'.'+number[dec+1:]
                elif re.fullmatch(r'\d{1,3}(?:[.,]\d{3})+',number):proposed=re.sub(r'[.,]','',number)
                else:proposed=number.replace(',','.')
                if proposed!=plan.question_plan.get('proposed_amount') or inputs[0]['unit']!=plan.question_plan.get('requested_unit'):raise ValueError('USER_PROPOSAL_BINDING_MISMATCH')
            result=recompute(calc['operation'],inputs,calc.get('round_places',2),calc.get('result_unit'),proposed)
            expected_unit='%' if calc['operation'] in {'PERCENT_CHANGE','SHARE_PERCENT','PER_100','RELATIVE_DIFFERENCE','RESTATEMENT_GROWTH'} else 'PERCENTAGE_POINTS' if calc['operation'] in {'PERCENTAGE_POINT_DIFFERENCE','RATE_POINT_CHANGE'} else inputs[0]['unit']
            if calc['operation']!='EXTRACT' and calc['result_unit']!=expected_unit:raise ValueError('RESULT_UNIT_DIMENSION_MISMATCH')
            if Decimal(result)!=Decimal(calc['proposed_result']):raise ValueError('INDEPENDENT_ARITHMETIC_MISMATCH')
            calculations[calc['calculation_id']]=result
            calculation_inputs[calc['calculation_id']]=calc['operand_ids']
            audit['stage_b'].append({'calculation_id':calc['calculation_id'],'operation':calc['operation'],'recomputed_result':result,'status':'VERIFIED','operand_metrics':[c['metric'] for c in inputs]})
        for claim in plan.claims:
            if not claim.source_refs or not set(claim.source_refs)<=set(ids):raise ValueError('CLAIM_CITATION_OUTSIDE_PLAN')
            if claim.type=='SOURCE_FACT':
                if not verify_rendered_numerals(claim.text,plan):raise ValueError('SOURCE_FACT_UNBOUND_NUMERAL')
                refs=[c for c in plan.citations if c['citation_id'] in claim.source_refs]
                literal=' '.join(folded(c['text']) for c in refs)
                if claim.source_scope=='SEPARATE' and not re.search(r'rieng|cong ty me|parent company|separate',literal):raise ValueError('SOURCE_FACT_SCOPE_UNPROVEN')
                if claim.source_scope=='CONSOLIDATED' and not re.search(r'hop nhat|consolidated',literal):raise ValueError('SOURCE_FACT_SCOPE_UNPROVEN')
                if re.search(r'north and south america|bac my va nam my',folded(claim.text)) and 'includes both north and south america' not in literal:raise ValueError('SOURCE_FACT_GEOGRAPHY_UNPROVEN')
            if claim.type=='NUMERIC':
                if claim.calculation_id not in calculations or Decimal(claim.value)!=Decimal(calculations[claim.calculation_id]):raise ValueError('CLAIM_RESULT_NOT_AUTHORIZED')
                if claim.operand_ids!=calculation_inputs[claim.calculation_id]:raise ValueError('CLAIM_CALCULATION_OPERANDS_MISMATCH')
                inputs=[verified[i] for i in claim.operand_ids]
                scopes={c['statement_scope'] for c in inputs}
                if claim.source_scope!=(next(iter(scopes)) if len(scopes)==1 else None):raise ValueError('CLAIM_SCOPE_MISMATCH')
                qp=plan.question_plan
                requested_operation=qp.get('operation')
                actual_operation=next(c['operation'] for c in plan.calculations if c['calculation_id']==claim.calculation_id)
                if requested_operation and requested_operation not in {'CHANGE_AND_GROWTH',actual_operation} and not (actual_operation=='PROPOSAL_DIFFERENCE' and qp.get('proposed_amount')) and qp.get('intent') not in {'RESTATEMENT_LIST','EXPLAIN'}:raise ValueError('QUESTION_OPERATION_MISMATCH')
                if requested_operation=='CHANGE_AND_GROWTH' and actual_operation not in {'ABS_CHANGE','PERCENT_CHANGE'}:raise ValueError('QUESTION_OPERATION_MISMATCH')
                requested_unit=qp.get('requested_unit')
                if requested_unit and requested_unit not in {'%','USD','VND','MILLION_USD','TRIEU_VND','TY_VND'}:raise ValueError('UNSUPPORTED_REQUESTED_UNIT')
                if requested_unit=='%' and actual_operation=='EXTRACT' and inputs[0]['unit']!='%':raise ValueError('REQUESTED_PERCENT_REQUIRES_DEFINED_RATIO')
                if requested_unit and requested_unit!='%' and requested_unit in {'USD','VND','MILLION_USD','TRIEU_VND','TY_VND'}:
                    result_unit=next(c['result_unit'] for c in plan.calculations if c['calculation_id']==claim.calculation_id)
                    if actual_operation=='EXTRACT' and result_unit!=requested_unit:raise ValueError('QUESTION_REQUESTED_SCALE_MISMATCH')
                    expected_currency='USD' if 'USD' in requested_unit else 'VND'
                    if any(c['currency']!=expected_currency for c in inputs):raise ValueError('QUESTION_CURRENCY_MISMATCH')
                if qp.get('years') and not set(qp['years'])>=set(claim.period):raise ValueError('QUESTION_PERIOD_MISMATCH')
                if qp.get('scope') and any(c['statement_scope']!=qp['scope'] for c in inputs) and qp.get('operation')!='SCOPE_DIFFERENCE':raise ValueError('QUESTION_SCOPE_MISMATCH')
                if qp.get('period_type') and any(c['period_type']!=qp['period_type'] for c in inputs):raise ValueError('QUESTION_PERIOD_TYPE_MISMATCH')
                if qp.get('metrics') and qp.get('metric')!='geography_definition' and not {c['metric'] for c in inputs}<=set(qp['metrics']):raise ValueError('QUESTION_METRIC_MISMATCH')
                if set(claim.source_refs)!={c['citation_id'] for c in inputs}:raise ValueError('CLAIM_SOURCE_BINDING_MISMATCH')
                if set(claim.period)!={c['period'] for c in inputs}:raise ValueError('CLAIM_PERIOD_MISMATCH')
        audit['status']='VERIFIED' if verified else 'SOURCE_SUPPORTED_NON_NUMERIC'
    except (ValueError,KeyError,TypeError,IndexError,InvalidOperation,AttributeError) as exc:audit['reason']=str(exc)
    return audit



def verify_rendered_numerals(answer,plan):
    """Authorize financial numerals in deterministic prose from the audited graph.

    Dates/pages/citation ordinals are metadata; amount literals require a source
    operand or calculated claim. Both en/vi display separators are accepted.
    """
    allowed=set()
    for c in plan.operands:
        allowed.add(raw_decimal(c['value_raw']));allowed.add(Decimal(c['period']));allowed.add(Decimal(c['page']))
    for c in plan.calculations:allowed.add(Decimal(c['proposed_result']))
    # A percentage/per-100 formula has an authenticated fixed multiplier.
    if any(c['operation'] in {'PER_100','RELATIVE_DIFFERENCE'} for c in plan.calculations):allowed.add(Decimal(100))
    for i,c in enumerate(plan.citations,1):
        allowed.add(Decimal(i));allowed.add(Decimal(c['page']))
    for year in plan.question_plan.get('years',[]):allowed.add(Decimal(year))
    for token in re.findall(r'(?<![\w])(?:FY)?([+-]?\d[\d.,]*)(?![\w])',answer):
        token=token.rstrip('.,')
        candidates=[]
        for normalized in (token.replace(',',''),token.replace('.','').replace(',','.')):
            try:candidates.append(Decimal(normalized))
            except InvalidOperation:pass
        if not any(v in allowed for v in candidates):return False
    return True



def verify_paragraph(w,c):
    """Reopen a literal native paragraph; no producer relevance flag is trusted."""
    d=w.document(c['document_id']);path=w.source_file(c['document_id'])
    if d['sha256']!=c['source_sha256'] or sha256(path.read_bytes()).hexdigest()!=d['sha256']:return False
    expected='paragraph_'+sha256(json.dumps([d['sha256'],c['page'],c['box'],c['text']]).encode()).hexdigest()[:28]
    if c['citation_id']!=expected:return False
    with pymupdf.open(path) as pdf:
        if not 1<=c['page']<=len(pdf):return False
        return ' '.join(_clip(pdf[c['page']-1],c['box']).split())==c['text']

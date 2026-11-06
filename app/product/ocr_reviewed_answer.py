"""Direct OCR answers draw only on the image-review ledger."""
from datetime import date
import re

from app.product.pdf_extract import folded
from app.product.pdf_ocr_financial_v3 import HUMAN


def requested_periods(question, metric):
    q=folded(question)
    dates=re.findall(r'\b(\d{1,2})/(\d{1,2})/(20\d{2})\b',q)
    if metric in {'assets','liabilities','equity'}:
        if len(set(dates))!=1:
            return []
        day,month,year=map(int,dates[0])
        try:
            return [(date(year,month,day).isoformat(),'INSTANT')]
        except ValueError:
            return []
    if metric not in {'net_revenue','net_income','operating_cashflow'}:
        return []
    if dates or re.search(r'\bthang\s+\d',q):
        return []
    years=set(re.findall(r'\b20\d{2}\b',q))
    if len(years)!=1 or re.search(r'\b(?:q[123]|quy\s+(?:iii|ii|i|[123]))\b|luy ke|ytd',q):
        return []
    end=next(iter(years))+'-12-31'
    quarter=bool(re.search(r'\b(?:q4|quy\s+(?:iv|4))\b',q))
    annual=bool(re.search(r'\b(?:ca nam|fy\s*20\d{2}|nam tai chinh)\b',q)) or not quarter
    return ([(end,'3M_Q4')] if quarter else [])+([(end,'FY')] if annual else [])


def requested_note_column(question):
    q=folded(question)
    if found:=re.search(r'\b(dau|cuoi) nam (20\d{2})\b',q):
        position, year=found.groups()
        end=f'{year}-01-01' if position=='dau' else f'{year}-12-31'
        basis='du phong' if 'du phong' in q else 'gia goc' if 'gia goc' in q else None
        return end,basis
    return None,None


def period_label(kind, end, column=None):
    if kind=='3M_Q4':
        return 'quý IV/'+end[:4]
    if kind=='FY':
        return 'cả năm '+end[:4]
    return 'ngày '+(column or date.fromisoformat(end).strftime('%d/%m/%Y'))


UNIT_LABELS={'VND':'đồng','NGHIN_VND':'nghìn đồng','TRIEU_VND':'triệu đồng','TY_VND':'tỷ đồng',
             'USD':'USD','MILLION_USD':'triệu USD'}
SCOPE_LABELS={'SEPARATE':'báo cáo riêng','CONSOLIDATED':'báo cáo hợp nhất'}


def answer(workspace, request):
    from app.product.analysis import METRICS, eligible_facts
    from app.product.answer_composer_v2 import display
    from app.product.verified_financial import validate_supported_response
    from app.product.financial_math import calculate
    from app.product.financial_understanding import requested_unit
    from decimal import Decimal
    q=folded(request.question)
    if len(request.document_ids)!=1 or not re.search(r'bao nhieu|trich gia tri|doc (?:dung|gia tri)|kiem duyet|da (?:duoc )?xac minh',q):
        return None
    if re.search(r'so voi|chenh lech|ty le|ty trong|ocr ban dau|doc lai|tang|giam|vi sao|giai thich|tong hop|don vi khac|doi sang|\b(?:usd|eur)\b',q):
        return None
    metrics=[m for m,aliases in METRICS.items() if any(a in q for a in aliases)]
    if len(metrics)!=1 or 'chua phan phoi' in q or 'ngan han' in q or 'dai han' in q:
        return None
    metric=metrics[0]
    wanted=requested_periods(request.question,metric)
    if not wanted:
        return None
    scope='CONSOLIDATED' if 'hop nhat' in q else 'SEPARATE' if 'cong ty me' in q or 'rieng' in q else None
    facts=[f for f in eligible_facts(workspace,request.document_ids) if f.get('review_status')==HUMAN
           and f['metric']==metric and f['basis']=='AS_REPORTED' and (not scope or f['statement_scope']==scope)]
    picked=[]
    for period,kind in wanted:
        match=[f for f in facts if f['period']==period and f['period_type']==kind]
        if len(match)!=1:
            return None
        picked.append(match[0])
    unit=requested_unit(request.question)
    if len({(f['unit'],f['statement_scope']) for f in picked})!=1 or (unit and unit!=picked[0]['unit']):
        return None
    citations=[];values=[];parts=[]
    for i,fact in enumerate(picked,1):
        value=str(calculate('EXTRACT',[Decimal(fact['value'])]))
        citation={**fact,'citation_id':fact['id'],'evidence_id':fact['id'],'text':fact['row_label']+' | '+fact['source_display'],
                  'source_kind':'PDF','period':fact['period'],'extraction_method':'OCR','column_id':fact.get('cell_id')}
        if validate_supported_response(workspace,{'status':'SUPPORTED','values':[value],'citations':[citation]},'EXTRACT')['status']!='SUPPORTED':
            return None
        citations.append(citation)
        values.append(value)
        kind=period_label(fact['period_type'],fact['period'],fact['column_label'])
        unit_text=UNIT_LABELS[fact['unit']]
        if len(picked)==1:
            from app.product.financial_understanding import issuers
            document=workspace.document(fact['document_id'])
            identities=issuers(document.get('filename',''))
            issuer=fact.get('issuer') or (identities[0] if len(identities)==1 else '')
            issuer={'HPG':'Hòa Phát'}.get(issuer,issuer)
            entity=(' của công ty mẹ '+issuer if fact['statement_scope']=='SEPARATE' else ' của '+issuer) if issuer else ''
            parts.append(f"{fact['row_label']}{entity} tại {kind} là {display(value)} {unit_text}. "
                         f"Giá trị đã được người dùng đối chiếu với ảnh gốc, {SCOPE_LABELS[fact['statement_scope']]}, trang {fact['page']}. [{i}]")
        else:
            parts.append(f"{fact['row_label']} {kind} là {display(value)} {unit_text}. "
                         f"Người dùng đã đối chiếu ô này trong {SCOPE_LABELS[fact['statement_scope']]}, trang {fact['page']}. [{i}]")
    return {'status':'SUPPORTED','answer_status':'VERIFIED_ANSWER','answer':' '.join(parts),
            'values':values,'unit':picked[0]['unit'],'citations':citations,'formula':'Đọc giá trị trực tiếp từ ô nguồn',
            'verification_status':HUMAN,'source_numeric_verification':HUMAN}


def calculation(workspace, request):
    from decimal import Decimal, localcontext, ROUND_HALF_UP
    from app.product.analysis import eligible_facts, numeric_answer
    from app.product.answer_composer_v2 import display
    from app.product.verified_financial import validate_supported_response

    q=folded(request.question)
    if len(request.document_ids)!=1 or not re.search(r'\b(?:ty le|ty trong)\s+no phai tra\s+(?:tren|chia cho)\s+tong (?:cong )?tai san',q):
        return None
    if 'so voi' in q or ('hop nhat' in q and ('cong ty me' in q or 'bao cao rieng' in q)):
        return None
    wanted=requested_periods(request.question,'assets')
    if not wanted:
        return None
    end,_=wanted[0]
    scope='CONSOLIDATED' if 'hop nhat' in q else 'SEPARATE' if 'cong ty me' in q or 'bao cao rieng' in q else None
    facts=[f for f in eligible_facts(workspace,request.document_ids)
           if f.get('review_status')==HUMAN and f['period']==end and f['period_type']=='INSTANT'
           and f['basis']=='AS_REPORTED' and f['metric'] in {'liabilities','assets'}
           and (not scope or f['statement_scope']==scope)]
    if len(facts)!=2 or {f['metric'] for f in facts}!={'liabilities','assets'} or len({f['statement_scope'] for f in facts})!=1:
        return None
    payload=request.model_copy(update={'mode':'numeric','operation':'DEBT_TO_ASSETS','current_period':end,
                                       'statement_scope':facts[0]['statement_scope']})
    answer=validate_supported_response(workspace,numeric_answer(workspace,payload),'DEBT_TO_ASSETS')
    if answer['status']!='SUPPORTED':
        return None
    with localcontext() as context:
        context.prec=40
        debt,assets=(Decimal(f['base_value']) for f in answer['citations'])
        if not assets:
            return None
        expected=debt/assets*100
        if abs(expected-Decimal(answer['values'][0]))>Decimal('1e-26'):
            return None
        rounded=expected.quantize(Decimal('0.01'),rounding=ROUND_HALF_UP)
    citations=[]
    for fact in answer['citations']:
        citations.append({**fact,'citation_id':fact['id'],'column_id':fact.get('cell_id'),
                          'source_kind':'PDF','text':fact['row_label']+' | '+fact['source_display']})
    return {**answer,'answer':f"Tỷ lệ nợ phải trả trên tổng tài sản tại {period_label('INSTANT',end)} "
            f"là {display(str(rounded))}%. Tôi chia nợ phải trả [1] cho tổng tài sản [2] rồi nhân 100. "
            "Cả hai ô đã được người dùng đối chiếu trên ảnh gốc.",
            'citations':citations,'answer_status':'VERIFIED_ANSWER','verification_status':HUMAN}


def readable_history(reply):
    """Project legacy replies without editing the saved conversation."""
    if reply.get('verification_status')!=HUMAN or "{'INSTANT':" not in (reply.get('answer') or ''):
        return reply
    from app.product.answer_composer_v2 import display
    sentences=[]
    for index,(fact,value) in enumerate(zip(reply.get('citations',[]),reply.get('values',[])),1):
        if not all(fact.get(key) for key in ('period','page','unit','row_label')):
            continue
        try:
            period=period_label(fact.get('period_type','INSTANT'),fact['period'],fact.get('column_label'))
            unit=UNIT_LABELS[fact['unit']]
        except (KeyError,ValueError):
            continue
        sentences.append(f"{fact['row_label']} tại {period} là {display(value)} {unit}. "
                         f"Người dùng đã đối chiếu ảnh gốc, trang {fact['page']}. [{index}]")
    return {**reply,'answer':' '.join(sentences) or 'Giá trị đã được đối chiếu. Mở trích dẫn để đọc ô nguồn.'}

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


def answer(workspace, request):
    from app.product.analysis import METRICS, eligible_facts
    from app.product.answer_composer_v2 import display
    from app.product.verified_financial import validate_supported_response
    from app.product.financial_math import calculate
    from app.product.financial_understanding import requested_unit
    from decimal import Decimal
    q=folded(request.question)
    if len(request.document_ids)!=1 or not re.search(r'bao nhieu|trich gia tri|doc (?:dung|gia tri)',q):
        return None
    if re.search(r'so voi|chenh lech|ty le|ty trong|tang|giam|vi sao|giai thich|tong hop|don vi khac|doi sang|\b(?:usd|eur)\b',q):
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
                  'source_kind':'PDF','period':fact['period'],'extraction_method':'OCR'}
        if validate_supported_response(workspace,{'status':'SUPPORTED','values':[value],'citations':[citation]},'EXTRACT')['status']!='SUPPORTED':
            return None
        citations.append(citation)
        values.append(value)
        kind={'INSTANT':fact['column_label'],'3M_Q4':'Quý IV '+fact['period'][:4],'FY':'Cả năm '+fact['period'][:4]}
        parts.append(f"{kind}: {display(value)} {fact['unit']} [{i}]")
    return {'status':'SUPPORTED','answer_status':'VERIFIED_ANSWER','answer':picked[0]['row_label']+' · '+'; '.join(parts)+'.',
            'values':values,'unit':picked[0]['unit'],'citations':citations,'formula':'Đọc giá trị trực tiếp từ ô nguồn',
            'verification_status':HUMAN,'source_numeric_verification':HUMAN}

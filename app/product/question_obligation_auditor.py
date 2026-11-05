"""Raw-utterance auditor. Does not import the planner or trust requested_claims.

This bounded financial grammar discovers independently recognizable obligations.
An unknown construction is not proof of exhaustive natural-language understanding.
"""
import re
from decimal import Decimal,InvalidOperation
from app.product.pdf_extract import folded

VERSION='RAW_QUESTION_OBLIGATION_AUDITOR_V3'

def discover(raw):
    q=folded(raw);requirements=[]
    def add(key,operations,render=None):
        requirements.append({'id':key,'operations':operations,'render_pattern':render})
    if re.search(r'services|dich vu',q) and re.search(r'(?:trong|cu).*100|per 100|out of (?:every )?100',q):
        add('PER_100',['PER_100'],r'100.*(?:usd|dong|dollar)|(?:usd|dollar).*100')
    elif re.search(r'services|dich vu',q) and re.search(r'ty trong|chiem.*(?:%|phan tram)|share|what percentage|dong gop.*tong',q):
        add('PART_OF_TOTAL',['SHARE_PERCENT'])
    if re.search(r'tuong doi|relative',q) and (re.search(r'margin|bien loi nhuan',q) or ('services' in q and 'products' in q and re.search(r'diem phan tram|percentage point',q))):
        add('RELATIVE_COMPARISON',['RELATIVE_DIFFERENCE'],r'tuong doi|relative')
    if re.search(r'diem phan tram|percentage points?',q):
        add('POINT_COMPARISON',['PERCENTAGE_POINT_DIFFERENCE','RATE_POINT_CHANGE'],r'diem phan tram|percentage points?')
    if re.search(r'\d[\d.,]*\s*(?:trieu|million)',q) and re.search(r'dung|correct|confirm|kiem tra phat bieu',q):
        add('EXPLICIT_CONFIRMATION',['EXTRACT'],r'khong dung|^dung\b|incorrect|^yes\b|^no\b')
    if re.search(r'hoa ky|u\.s\.|united states',q) and 'americas' in q and re.search(r'khac|difference|bang|same',q):
        add('GEOGRAPHY_AMOUNT_DIFFERENCE',['GEOGRAPHY_DIFFERENCE'],r'chenh lech|difference')
    return requirements

def audit(raw,outputs,rendered=None):
    requirements=discover(raw);audits=[]
    for r in requirements:
        candidates=[o for o in outputs if o.get('status')=='VERIFIED' and o.get('numeric_verification')=='VERIFIED']
        executed={op for o in candidates for op in o.get('calculation_operations',[])}
        executed.update(c['operation'] for o in candidates for c in o.get('calculation_results',[]))
        # Only actual independently recomputed operations satisfy an obligation.
        ok=bool(executed.intersection(r['operations']))
        reason=None if ok else 'RAW_QUESTION_OPERATION_MISSING'
        if ok and rendered is not None and r['render_pattern'] and not re.search(r['render_pattern'],folded(rendered)):
            ok=False;reason='RAW_QUESTION_ANSWER_NOT_RENDERED'
        calculations=[c for o in candidates for c in o.get('calculation_results',[]) if c.get('operation') in r['operations']]
        if ok and rendered is not None:
            numbers=set()
            for token in re.findall(r'(?<!\w)[+-]?\d[\d.,]*(?!\w)',rendered):
                token=token.rstrip('.,')
                for normalized in (token.replace(',',''),token.replace('.','').replace(',','.')):
                    try:numbers.add(Decimal(normalized))
                    except InvalidOperation:pass
            if not calculations or any(Decimal(c['recomputed_result']) not in numbers for c in calculations):
                ok=False;reason='AUDITED_RESULT_NOT_RENDERED'
        if ok and r['id'] in {'RELATIVE_COMPARISON','POINT_COMPARISON'} and re.search(r'products.*(?:cao hon|higher than|relative to|so voi).*services',folded(raw)):
            if any(c.get('operand_metrics')!=['products_gross_margin_percentage','services_gross_margin_percentage'] for c in calculations):
                ok=False;reason='ORIGINAL_COMPARISON_BASE_MISMATCH'
        if ok and rendered is not None and r['id']=='EXPLICIT_CONFIRMATION':
            text=folded(rendered).strip()
            observed=False if re.match(r'khong\b|no\b',text) else True if re.match(r'dung\b|yes\b',text) else None
            expected={o['confirmation'] for o in candidates if o.get('confirmation') is not None}
            if len(expected)!=1 or observed is None or observed not in expected:
                ok=False;reason='INCORRECT_RENDERED_CONFIRMATION'
        audits.append({**r,'verdict':'ANSWERED' if ok else 'MISSING','reason':reason})
    return {'version':VERSION,'original_question':raw,'DISCOVERED_REQUIREMENTS':audits,
            'ANSWERED':[r['id'] for r in audits if r['verdict']=='ANSWERED'],
            'MISSING':[r['id'] for r in audits if r['verdict']=='MISSING'],'UNSUPPORTED':[]}

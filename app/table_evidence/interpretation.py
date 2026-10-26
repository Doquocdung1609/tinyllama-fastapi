"""Small explicit financial cell grammar; unknown interpretations stay unknown."""
import re
from decimal import Decimal, localcontext
from app.financial_query.period_resolver import extract_periods
from app.table_evidence.contracts import PeriodContextV1


def period_context(labels):
    periods=[]
    for label in labels:
        # Header separators have no effect on coordinates, only parse clauses.
        try:
            parsed,_,unresolved=extract_periods(label.casefold())
        except ValueError:
            return None,'UNRESOLVED_HEADER_PERIOD'
        if unresolved:
            return None, 'UNRESOLVED_HEADER_PERIOD'
        periods.extend(parsed)
    unique={(p.kind,p.year,p.quarter,str(p.end) if p.end else None,p.months) for p in periods}
    if not unique:
        return None,'MISSING_COLUMN_PERIOD'
    if len(unique)!=1:
        return None,'CONFLICTING_HEADER_PERIODS'
    kind,year,quarter,end,months=next(iter(unique))
    return PeriodContextV1(kind=kind,year=year,quarter=quarter,end=end,months=months,raw_labels=tuple(labels)),None


def parse_number(raw):
    """Whole-cell decimal only, never a nearby number or a partial match."""
    text=raw.strip()
    if not text:
        return None,'NONE','BLANK',None
    if text in {'-','–','—','−'}:
        return None,'NONE','DASH',None
    if text.casefold() in {'n/a','na','not available'}:
        return None,'NONE','NOT_AVAILABLE',None
    pattern=r'(?:USD\s*|\$\s*)?(?P<n>\([+−\-]?(?:[0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)(?:\.[0-9]+)?\)|[+−\-]?(?:[0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)(?:\.[0-9]+)?)(?P<p>%)?'
    m=re.fullmatch(pattern,text)
    if not m:
        return None,'NONE','TEXT','UNSUPPORTED_NUMERIC_CELL' if any(c.isdecimal() for c in text) else None
    token=m['n'].replace('−','-')
    if len(token)>150:
        return None,'NONE','TEXT','NUMERIC_DIGIT_BUDGET'
    paren=token.startswith('('); inner=token.strip('()')
    if paren and inner.startswith(('+','-')):
        return None,'NONE','TEXT','CONFLICTING_DISPLAY_SIGNS'
    value=Decimal(inner.replace(',',''))
    if paren:
        value=value.copy_negate()
    sign='PARENTHESES' if paren else 'MINUS' if inner.startswith('-') else 'PLUS' if inner.startswith('+') else 'NONE'
    return value,sign,'NUMBER',None


def measurement(row,headers):
    text=' / '.join(headers).casefold(); r=row.casefold()
    if 'carrying' in text and 'fair value' in text:
        return 'CONFLICTED'
    if 'carrying' in text:
        return 'CARRYING_VALUE'
    if 'fair value' in text:
        return 'FAIR_VALUE'
    if re.search(r'\bbasic\b',r) and re.search(r'\bdiluted\b',text) or re.search(r'\bdiluted\b',r) and re.search(r'\bbasic\b',text):
        return 'CONFLICTED'
    if 'basic' in r and ('eps' in r or 'per share' in r):
        return 'BASIC_EPS'
    if 'diluted' in r and ('eps' in r or 'per share' in r):
        return 'DILUTED_EPS'
    if 'percentage point' in text:
        return 'PERCENTAGE_POINT_CHANGE'
    if re.search(r'percent|%',text):
        return 'PERCENT_CHANGE' if 'change' in text else 'PERCENT'
    if 'change' in text:
        return 'AMOUNT_CHANGE'
    return 'AMOUNT'


def units(raw,row,headers,unit_context):
    local=' / '.join(headers).casefold()
    table=(unit_context or '').casefold()
    if re.match(r'\s*(?:USD|\$)',raw,re.I) and raw.strip().endswith('%'):
        return 'UNKNOWN',None,'CONFLICTING_NUMERIC_UNITS'
    if re.match(r'\s*(?:USD|\$)',raw,re.I) and re.search(r'\bshares\b',local):
        return 'UNKNOWN',None,'CONFLICTING_DISPLAY_CURRENCY_AND_SHARES'
    if re.search(r'\beur\b|\bgbp\b|\bjpy\b|\bcad\b|\bcny\b|[€£¥]',local+' '+table):
        return 'UNKNOWN',None,'CONFLICTING_CURRENCY_CONTEXT' if re.search(r'\busd\b|\$',local+' '+table) else 'UNSUPPORTED_CURRENCY'
    if raw.strip().endswith('%') or 'percent' in local or '%' in local:
        return ('PERCENTAGE_POINTS' if 'percentage point' in local else 'PERCENT'),Decimal(1),None
    eps=bool(re.search(r'\beps\b|per share',row,re.I))
    per_share=bool(re.search(r'per[ -]share|usd/share',local))
    if per_share or eps and 'except per share' in table:
        return ('USD_PER_SHARE',Decimal(1),None) if 'usd' in table+' '+local else ('UNKNOWN',None,'UNRESOLVED_CURRENCY')
    if re.search(r'except|mixed',table) and not eps:
        return 'UNKNOWN',None,'UNRESOLVED_UNIT_EXCEPTION'
    text=local+' / '+table
    currency=bool(re.search(r'\busd\b|\$',text))
    shares=bool(re.search(r'\bshares\b',local))
    if currency and shares:
        return 'UNKNOWN',None,'CONFLICTING_UNIT_CONTEXT'
    if not currency and not shares:
        return 'UNKNOWN',None,'MISSING_UNIT'
    scales=[v for k,v in [('thousand','1000'),('million','1000000'),('billion','1000000000')] if k in text]
    if len(scales)>1:
        return 'UNKNOWN',None,'CONFLICTING_SCALE_CONTEXT'
    return 'USD' if currency else 'SHARES',Decimal(scales[0] if scales else '1'),None


def exact_effective(value,multiplier):
    if value is None or multiplier is None:
        return None
    with localcontext() as context:
        context.prec=max(200,len(value.as_tuple().digits)+len(multiplier.as_tuple().digits)+10)
        return value*multiplier

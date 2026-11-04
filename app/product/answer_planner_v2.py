"""Source-bound question plans; no financial values or document-specific answers."""
from dataclasses import asdict, dataclass, field
import re
from app.product.pdf_extract import folded
from app.product.financial_understanding import understand

VERSION='FINANCIAL_QUESTION_PLAN_V2'

@dataclass
class QuestionPlan:
    raw_text:str
    intent:str
    metric:str|None=None
    years:list[str]=field(default_factory=list)
    scope:str|None=None
    period_type:str|None=None
    basis:str|None=None
    operation:str='EXTRACT'
    metrics:list[str]=field(default_factory=list)
    requested_unit:str|None=None
    section:str|None=None
    language:str='vi'
    inherited_slots:list[str]=field(default_factory=list)
    version:str=VERSION
    def public(self):return asdict(self)

def plan_question(text):
    q=folded(text);base=understand(text)
    p=QuestionPlan(text,'FIND_EVIDENCE',base.metric,sorted(set(re.findall(r'(?<!\d)(?:FY\s*)?(20\d{2})(?!\d)',text,re.I))),base.scope,base.period_type,base.basis,
        requested_unit=base.requested_unit,language='vi' if re.search(r'bao cao|tai lieu|nam |loi nhuan|doanh thu|bao nhieu|dong |hop nhat|rieng|quy|nguon|don vi',q) else 'en')
    if re.search(r'million[s]? (?:usd|dollars)|trieu usd',q):p.requested_unit='MILLION_USD'
    if re.search(r'sau dieu chinh|sau khi dieu chinh|restated|trinh bay lai',q):p.basis='RESTATED'
    if re.search(r'quy\s*(?:iv|4)|\bq4\b',q):p.period_type='3M_Q4'
    elif re.search(r'quy\s*(?:iii|3)|\bq3\b',q):p.period_type='3M_Q3'
    elif re.search(r'quy\s*(?:ii|2)|\bq2\b',q):p.period_type='3M_Q2'
    elif re.search(r'\bfy\s*20|fiscal|ca nam|annual',q):p.period_type='FY'
    if re.search(r'services|dich vu',q):
        p.metric='services_net_sales'
        if re.search(r'gross margin|bien loi nhuan gop',q):p.metric='services_gross_margin_percentage' if re.search(r'percentage|percent|%|bien|points|ty suat',q) else 'services_gross_margin'
    if re.search(r'products|san pham',q) and not re.search(r'services|dich vu',q):
        p.metric='products_net_sales'
        if re.search(r'gross margin|bien loi nhuan gop',q):p.metric='products_gross_margin_percentage' if re.search(r'percentage|percent|%|bien|points|ty suat',q) else 'products_gross_margin'
    if re.search(r'americas',q) and not re.search(r'\bu\.s\.|united states|hoa ky',q):p.metric='americas_net_sales'
    if re.search(r'net margin|bien loi nhuan rong',q):p.metric='net_income';p.metrics=['net_income','net_revenue'];p.operation='SHARE_PERCENT'
    if re.search(r'day la.*(?:rieng|hop nhat)|bao cao.*hay.*hop nhat|report.*(?:separate|consolidated).*\?|what (?:type|kind).*report|loai bao cao',q):p.intent='DOCUMENT_IDENTITY'
    elif re.search(r'\bu\.s\.|united states|hoa ky',q) and 'americas' in q:p.intent='EXPLAIN';p.metric='geography_definition'
    elif re.search(r'tim (?:bang|bao cao)|find.*(?:balance sheet|income statement)|locate.*(?:statement|section)',q):
        p.intent='FIND_SECTION';p.section='BALANCE_SHEET' if re.search(r'can doi|balance sheet',q) else 'INCOME_STATEMENT'
    elif re.search(r'nhung so lieu|liet ke.*dieu chinh|list.*adjust|all.*adjust',q):p.intent='RESTATEMENT_LIST'
    elif re.search(r'nguon o dau|trang nao|what page|where.*source|don vi gi|unit\??$',q):p.intent='FOLLOW_UP'
    elif re.search(r'tom tat|summari[sz]e|overview|tong quan',q):p.intent='SUMMARIZE'
    elif re.search(r'tim dong|find.*(?:row|table)|locate|tim.*nguon',q):p.intent='TABLE_LOOKUP'
    elif re.search(r'giai thich|tai sao|why|explain',q):p.intent='EXPLAIN'
    else:p.intent='EXTRACT_VALUE' if p.metric else 'CLARIFY'
    if p.metric=='retained_earnings' and re.search(r'identity|kiem tra.*(?:dieu chinh|trinh bay lai)|da cong bo.*dieu chinh.*trinh bay lai',q):p.intent='ARITHMETIC';p.operation='RESTATEMENT_IDENTITY'
    elif 'retained_earnings'==p.metric and re.search(r'chenh lech|khac nhau|difference|gap',q):p.intent='RESTATEMENT_COMPARE';p.operation='SCOPE_DIFFERENCE'
    elif p.metric=='retained_earnings' and re.search(r'tang.*%|phan tram|percent|growth',q):p.intent='ARITHMETIC';p.operation='RESTATEMENT_GROWTH'
    elif re.search(r'(?:services|dich vu).*(?:products|san pham)|(?:products|san pham).*(?:services|dich vu)',q) and re.search(r'margin|bien loi nhuan',q):
        p.intent='ARITHMETIC';p.operation='PERCENTAGE_POINT_DIFFERENCE';p.metrics=['services_gross_margin_percentage','products_gross_margin_percentage'];p.metric=p.metrics[0]
    elif re.search(r'(?:services|dich vu)',q) and re.search(r'what percentage|share|ty trong|chiem.*%|chiem.*phan tram',q):
        p.intent='ARITHMETIC';p.operation='SHARE_PERCENT';p.metrics=['services_net_sales','net_revenue'];p.metric=p.metrics[0]
    elif re.search(r'products.*services|services.*products',q) and re.search(r'sum|add|tong|equals|equal|bang',q):
        p.intent='ARITHMETIC';p.operation='PART_WHOLE_CHECK' if re.search(r'equals|equal|bang|total net sales',q) else 'SUM';p.metrics=['products_net_sales','services_net_sales']+(['net_revenue'] if p.operation=='PART_WHOLE_CHECK' else []);p.metric=p.metrics[0]
    elif p.operation=='SHARE_PERCENT':p.intent='ARITHMETIC'
    elif re.search(r'growth|grow|tang truong|tang.*phan tram|tang.*%',q):
        p.intent='PERIOD_COMPARISON';p.operation='CHANGE_AND_GROWTH' if re.search(r'dollars and percent|tien va|ca.*(?:tuyet doi|phan tram)',q) else 'PERCENT_CHANGE'
    elif re.search(r'difference|delta|chenh lech|tang bao nhieu|so voi|compared with',q) and p.metric:
        p.intent='PERIOD_COMPARISON';p.operation='ABS_CHANGE'
    if p.metric in {'retained_earnings','assets'} and p.period_type in {None,'FY'}:p.period_type='INSTANT'
    if not p.metrics and p.metric:p.metrics=[p.metric]
    return p

def resolve_followup(text,history):
    """Only caller-approved same-source history may enter this function."""
    p=plan_question(text);q=folded(text)
    if not history:return text,p
    last=history[-1];response=last.get('response',{})
    if response.get('status') in {'QUERY_CONTEXT_CONFLICT','SOURCE_UNAVAILABLE'}:return text,p
    previous=response.get('conversation_slots') or plan_question(last.get('resolved_question',last['question'])).public()
    explicit_metric=p.metric is not None
    follow=bool(re.search(r'^so voi |^con |^vay |^and |^what about|hai (?:bang|muc)|nguon o dau|don vi gi|tinh tang truong|tai sao khac|how much did it grow',q))
    if not follow:return text,p
    metric=p.metric or previous.get('metric')
    if not metric:return text,p
    parts=[text]
    names={'net_revenue':'total net sales','net_income':'net income','retained_earnings':'lợi nhuận sau thuế chưa phân phối',
        'assets':'tổng cộng tài sản','services_net_sales':'Services net sales','products_net_sales':'Products net sales'}
    if not explicit_metric:parts.insert(0,names.get(metric,metric.replace('_',' ')));p.inherited_slots.append('metric')
    old_years=previous.get('years') or []
    comparison=bool(re.search(r'grow|growth|tang truong|so voi|chenh lech',q))
    if not p.years or comparison:
        years=sorted(set(p.years+old_years))
        parts.append(' FY '+' '.join(years));p.inherited_slots.append('years')
    if not p.scope and previous.get('scope') and not re.search(r'rieng.*hop nhat|hop nhat.*rieng',q):
        parts.append(' consolidated' if previous['scope']=='CONSOLIDATED' else ' riêng công ty mẹ');p.inherited_slots.append('scope')
    if re.fullmatch(r'(?:and in|what about|con nam)\s*(?:fy\s*)?20\d{2}[?. ]*',q) and previous.get('operation')=='SHARE_PERCENT':
        parts.append('what percentage of total net sales');p.inherited_slots.append('operation')
    resolved=' '.join(parts);updated=plan_question(resolved);updated.inherited_slots=p.inherited_slots
    return resolved,updated


def constraint_conflicts(request,answer):
    """Advanced controls are explicit assertions; they cannot override source facts."""
    p=answer.get('query_plan',{});operands=answer.get('operands',[]);bad=[]
    fields=request.model_fields_set
    expected={'metric':p.get('metric'),'operation':p.get('operation'),'statement_scope':p.get('scope'),'basis':p.get('basis')}
    for field in ('metric','operation','statement_scope','basis'):
        if field not in fields:continue
        value=getattr(request,field)
        observed={c.get(field) for c in operands} if field in {'statement_scope','basis','metric'} else {expected[field]}
        if expected[field] and expected[field]!=value:bad.append(field)
        elif operands and value not in observed:bad.append(field)
        elif not operands and not expected[field]:bad.append(field)
    years=sorted({c['period'] for c in operands} or p.get('years',[]))
    for field,index in [('current_period',-1),('previous_period',0)]:
        if field not in fields:continue
        value=getattr(request,field)
        if not value or not re.fullmatch(r'20\d{2}(?:-\d{2}-\d{2})?',value):bad.append(field);continue
        if not years or value[:4]!=years[index]:bad.append(field);continue
        if len(value)>4 and not any(c['period']==value[:4] and c['period_end']==value for c in operands):bad.append(field)
    return sorted(set(bad))

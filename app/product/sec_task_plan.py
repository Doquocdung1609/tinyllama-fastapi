"""Deterministic, source-bound obligations for SEC financial chat.

The plan contains no financial values.  Every issuer is checked against the
actual UI-selected catalog before an obligation may execute.
"""
from dataclasses import asdict, dataclass, field
import re

from app.product.pdf_extract import folded
from app.product.sec_ontology_v8 import ISSUERS


@dataclass(frozen=True)
class SecTask:
    task_id: str
    issuer: str
    metric: str
    operation: str
    period: str | None = None
    duration: str | None = None
    relation: str | None = None
    unit: str | None = None
    filing_ids: tuple[str, ...] = ()
    filing_form: str | None = None
    accession: str | None = None
    reporting_scope: str | None = None
    currency: str | None = None
    output_obligations: tuple[str, ...] = ()
    missing_evidence: str | None = None
    denominator: str | None = None


@dataclass
class SecQuestionPlan:
    original_question: str
    selected_filing_ids: list[str]
    named_entities: list[str]
    context_only_entities: list[str]
    focused_entities: list[str]
    comparison_entities: list[str]
    excluded_entities: list[str]
    unselected_entities: list[str]
    eligible_entities: list[str]
    tasks: list[SecTask] = field(default_factory=list)
    intent: str = "UNKNOWN"
    error: str | None = None

    def public(self):
        return asdict(self)


def _entity_mentions(text, catalog):
    aliases = {ticker: set(names) | {ticker} for ticker, names in ISSUERS.items()}
    for ticker, rows in catalog.items():
        for filing, _ in rows:
            name = filing.get('issuer', '')
            aliases.setdefault(ticker, set()).add(name)
            short = re.sub(r'\s+(?:(?:inc|corp|co|company|corporation|ltd|plc|limited)\.?\s*)+$',
                           '', name.replace(',', ''), flags=re.I).strip()
            if len(short) >= 4:
                aliases[ticker].add(short)
    found = set()
    for ticker, names in aliases.items():
        for name in names:
            term = folded(name)
            if term and re.search(r'(?<!\w)' + re.escape(term) + r'(?!\w)', text):
                found.add(ticker)
                break
    found.update(x.upper() for x in re.findall(r'\b(?:ticker|ma chung khoan)\s+([a-z]{1,5})\b', text))
    return found


def _clause_entities(q, catalog, markers):
    result = set()
    for marker in markers:
        for match in re.finditer(marker, q):
            clause = re.split(r'[.;!?]|\b(?:nhung|but|however)\b', q[match.end():], maxsplit=1)[0]
            result.update(_entity_mentions(clause, catalog))
    return result


def plan_sec_question(question, catalog, ticker=None, metrics=(), margin=None, topics=()):
    q = folded(question)
    named = _entity_mentions(q, catalog)
    excluded = _clause_entities(q, catalog, (
        r'\b(?:bo qua|ngoai tru|khong dung|khong lay|khong tinh|exclude|except|ignore)\b',))
    focused = _clause_entities(q, catalog, (
        r'\b(?:chi su dung|chi dung|chi lay|chi chon|chi hoi|chi phan tich|only use|use only|focus on|only analyze|only for)\b',))
    focused -= excluded
    comparison = bool(re.search(r'\b(?:so sanh|doi chieu|compare|comparison|versus|vs|tung doanh nghiep|each company|ca ba|ca hai)\b', q))
    if focused:
        requested = focused
    elif comparison and named:
        requested = named - excluded
    elif len(named - excluded) == 1:
        requested = named - excluded
    elif not named and ticker:
        requested = {ticker.upper()}
    elif not named and comparison:
        requested = set(catalog) - excluded
    else:
        requested = named - excluded
    conflict = bool(ticker and requested and ticker.upper() not in requested)
    unselected = requested - set(catalog)
    # A comparison may complete the selected companies while marking a
    # missing issuer explicitly. A focused request to an unselected company
    # must never be redirected to other selected companies.
    eligible = (requested & set(catalog)) if not unselected or comparison and not focused else set()
    ambiguous = len(eligible) > 1 and not comparison and not focused
    if conflict:
        error = 'SEC_COMPANY_SCOPE_CONFLICT'
    elif unselected and not (comparison and eligible and not focused):
        error = 'SEC_ISSUER_NOT_SELECTED'
    elif ambiguous:
        error = 'SEC_COMPANY_SCOPE_AMBIGUOUS'
    elif not eligible:
        error = 'SEC_ISSUER_NOT_SELECTED' if requested else 'SEC_COMPANY_SCOPE_AMBIGUOUS'
    else:
        error = None
    from app.product.sec_ratio import PRIOR, ratio_variants
    margin_prior=bool(margin and PRIOR.search(q))
    operation = ('MARGIN_YEAR_OVER_YEAR' if margin_prior else 'MARGIN_PERCENT' if margin else 'YEAR_OVER_YEAR' if re.search(
        r'\b(?:cung ky nam truoc|same period last year|year.over.year|yoy)\b', q)
                 else 'EXTRACT')
    intent = 'MARGIN' if margin else 'NARRATIVE' if topics else 'NUMERIC' if metrics else 'UNKNOWN'
    iso_date=re.search(r'\b(20\d{2}-\d{2}-\d{2})\b',q)
    vn_date=re.search(r'\b(\d{1,2})/(\d{1,2})/(20\d{2})\b',q)
    period=iso_date[1] if iso_date else f'{vn_date[3]}-{int(vn_date[2]):02d}-{int(vn_date[1]):02d}' if vn_date else None
    weeks=re.findall(r'\b(\d+)\s*(?:tuan|weeks?)\b',q)
    duration=(weeks[0]+'W') if len(set(weeks))==1 else 'SHORTEST_REPORTED' if re.search(
        r'\b(?:ky ngan nhat|shortest period)\b',q) else None
    form_match=re.search(r'\b(10-k|10-q|20-f)(?:/a)?\b',q)
    form=form_match[0].upper() if form_match else None
    accession_match=re.search(r'\b\d{10}-\d{2}-\d{6}\b',q)
    scope='CONSOLIDATED' if re.search(r'\b(?:hop nhat|consolidated)\b',q) else None
    currency='USD' if re.search(r'\b(?:usd|dollars?)\b',q) else None
    tasks = []
    if not error:
        for issuer in sorted(eligible):
            filing_ids = tuple(sorted(f['filing_id'] for f, _ in catalog[issuer]))
            for metric in ([margin] if margin else list(topics) if topics else list(metrics)):
                for denominator in (ratio_variants(q) if margin else [None]):
                    task_id = f'SEC-{len(tasks) + 1:03d}'
                    tasks.append(SecTask(task_id, issuer, metric, operation if not topics else 'SUMMARIZE',
                                     denominator=denominator,
                                     period=period, duration=duration, filing_ids=filing_ids,
                                     filing_form=form, accession=accession_match[0] if accession_match else None,
                                     reporting_scope=scope, currency=currency,
                                     relation='PRIOR_YEAR' if operation in {'YEAR_OVER_YEAR','MARGIN_YEAR_OVER_YEAR'} else None,
                                     unit='PERCENT' if margin else 'SOURCE_UNIT',
                                     output_obligations=('current_margin','prior_year_margin','margin_change','citations') if margin_prior else
                                     ('source_cells', 'period', 'unit', 'calculation', 'citations')
                                     if not topics else ('disclosure', 'citation', 'interpretation_boundary')))
    return SecQuestionPlan(question,
                           sorted(f['filing_id'] for rows in catalog.values() for f, _ in rows),
                           sorted(named), sorted(named - requested - excluded), sorted(focused),
                           sorted(requested) if comparison else [], sorted(excluded),
                           sorted(unselected), sorted(eligible), tasks, intent, error)


FOLLOWUP = re.compile(r'^(?:so voi\b|compared with\b|con\b|the\b|vay\b|what about\b|how about\b|and\b|cung ky\b|(?:ky|quy|nam) (?:truoc|ngan nhat)\b|shortest\b|same (?:quarter|period)\b)')


def resolve_typed_followup(index, question, previous):
    """Apply only explicit slot overrides to a previously executed task."""
    from app.product.sec_a5 import plan_query
    from app.product.sec_library import partitions
    from app.product.sec_multi_qa import period_for, requested_metrics
    from app.product.sec_ratio import CURRENT, PRIOR, SHORTEST, TOTAL, SALES
    from app.product.sec_question import MARGIN, RISK
    q=folded(question).strip()
    context=previous.get('sec_task_context')
    prior_plan=previous.get('sec_question_plan') or {}
    if not context or not FOLLOWUP.search(q) or MARGIN.search(q) or requested_metrics(q) or RISK.search(q):
        return None
    catalog={}
    for part in partitions(index):
        for row in part.catalog_rows:
            catalog.setdefault(row['ticker'],[]).append((row,part))
    issuers=_entity_mentions(q,catalog)
    if len(issuers)>1:
        return {'clarification':'Bạn muốn tiếp tục phép tính cho doanh nghiệp nào trong số đã nêu?'}
    issuer=next(iter(issuers),context['issuer'])
    period=plan_query(question)
    if issuer not in catalog:
        return {'clarification':f'Filing của {issuer} chưa nằm trong bộ nguồn đã chọn.',
                'reason':'SEC_ISSUER_NOT_SELECTED'}
    explicit_duration=period_for(q,catalog[issuer],context['metric']) if re.search(
        r'\b(?:tuan|weeks?|thang|months?|quy|quarter|luy ke|ytd|ca nam|annual)\b',q) and not PRIOR.search(q) else None
    shortest=bool(SHORTEST.search(q))
    explicit_prior=bool(PRIOR.search(q))
    if not (issuers or period.period_end or explicit_duration or shortest or explicit_prior or CURRENT.search(q)):
        return {'clarification':'Bạn muốn đổi doanh nghiệp hay kỳ nào cho phép tính vừa hỏi?'}
    overrides={}
    if issuers:
        overrides['issuer']=issuer
    duration=context.get('duration')
    report_end=context.get('report_end')
    if issuer!=context['issuer']:
        report_end=None
    if shortest:
        duration='SHORTEST_REPORTED'
        overrides['duration']=duration
    elif explicit_duration is not None:
        duration=explicit_duration
        overrides['duration']=duration
    if period.period_end:
        report_end=period.period_end
        overrides['report_end']=report_end
    elif CURRENT.search(q):
        report_end=None
        overrides['report_end']='CURRENT'
    duration_text= ('kỳ ngắn nhất' if duration=='SHORTEST_REPORTED' else
                    ' và '.join(f'{w} tuần' for w in duration) if isinstance(duration,(list,tuple)) else
                    {3:'ba tháng',6:'sáu tháng',9:'chín tháng',12:'cả năm','YTD':'lũy kế'}.get(duration,''))
    metric=context['metric']
    label={'operating_income':'biên lợi nhuận hoạt động','gross_profit':'biên lợi nhuận gộp',
           'income':'biên lợi nhuận ròng'}.get(metric,metric.replace('_',' '))
    variants=context.get('denominators',[])
    if TOTAL.search(q) or SALES.search(q):
        from app.product.sec_ratio import ratio_variants
        variants=ratio_variants(q)
        overrides['denominators']=variants
    terms={'TOTAL_REVENUE':'tổng doanh thu','NET_SALES':'doanh thu thuần','PRODUCT_NET_SALES':'doanh thu thuần bán hàng'}
    denominator_text=' và '.join(terms[k] for k in variants if k in terms)
    relation='cùng kỳ năm trước' if explicit_prior or context.get('relation')=='PRIOR_YEAR' else ''
    if explicit_prior:
        overrides['relation']='PRIOR_YEAR'
    resolved=' '.join(filter(None,[issuer,label,duration_text,report_end,denominator_text,relation,
                                    'kỳ hiện tại' if overrides.get('report_end')=='CURRENT' else '']))
    return {'question':resolved,'inherited':{k:v for k,v in context.items() if k not in overrides
                                             and (k!='report_end' or report_end)},
            'overrides':overrides,'previous_intent':prior_plan.get('intent')}

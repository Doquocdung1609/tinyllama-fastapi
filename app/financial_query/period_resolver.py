"""Parse explicit periods and match supplied column metadata, never filing-year guesses."""
import calendar
from datetime import date
import re
from app.financial_query.contracts import DateRangeV1, PeriodV1

MONTHS = {name.lower(): i for i, name in enumerate(calendar.month_name) if name}
MONTH_PATTERN = '|'.join(MONTHS)
DATE_PATTERN = rf"(?:{MONTH_PATTERN}) [0-9]{{1,2}},? [0-9]{{4}}|[0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}}"


def parse_date(text):
    if re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", text):
        return date.fromisoformat(text)
    month, day, year = text.replace(',', '').split()
    return date(int(year), MONTHS[month], int(day))


def extract_periods(text: str):
    periods, unresolved, consumed, ranges = [], [], set(), []
    def consume(m):
        consumed.update(range(*m.span()))
    # Filing dates are disjoint from requested statement periods.
    for m in re.finditer(rf"\bfiled (?:in|during) (?:(?P<month>{MONTH_PATTERN}) )?(?P<year>[0-9]{{4}})\b", text):
        year = int(m['year']); month = MONTHS.get(m['month'])
        ranges.append(DateRangeV1(start=date(year, month or 1, 1),
            end=date(year, month or 12, calendar.monthrange(year, month)[1] if month else 31)))
        consume(m)
    for m in re.finditer(rf"\bfiled on (?P<date>{DATE_PATTERN})\b", text):
        d = parse_date(m['date']); ranges.append(DateRangeV1(start=d, end=d)); consume(m)
    for m in re.finditer(r"\b(?:(?:q(?P<q>[1-4]))\s+)?(?:fy\s*|fiscal (?:year )?)(?P<y>[0-9]{4})\b", text):
        periods.append(PeriodV1(kind="FISCAL_QUARTER" if m['q'] else "FISCAL_YEAR", year=int(m['y']),
                                quarter=int(m['q']) if m['q'] else None, raw=m.group())); consume(m)
    for m in re.finditer(r"\bcalendar (?:year )?(?P<y>[0-9]{4})\b", text):
        periods.append(PeriodV1(kind="CALENDAR_YEAR", year=int(m['y']), raw=m.group())); consume(m)
    for m in re.finditer(rf"\b(?P<kind>year ended|quarter ended|as of) (?P<date>{DATE_PATTERN})\b", text):
        periods.append(PeriodV1(kind="INSTANT" if m['kind'] == 'as of' else "DURATION", end=parse_date(m['date']),
             months=None if m['kind'] == 'as of' else 12 if m['kind'] == 'year ended' else 3, raw=m.group())); consume(m)
    if re.search(r"\b(last year|this year|last quarter|latest|recent|previous year|yesterday|today)\b", text):
        unresolved.append("RELATIVE_PERIOD_REQUIRES_REFERENCE")
    # Any unconsumed date/year/quarter is unresolved, never assigned the filing period.
    for m in re.finditer(r"\b(?:19|20|21|22)[0-9]{2}\b|\bq[0-9]+\b", text):
        if not all(i in consumed for i in range(*m.span())):
            # Ignore the middle year digits in an explicitly formatted accession.
            unresolved.append("UNQUALIFIED_PERIOD")
    for m in re.finditer(r'(?<![\w-])(?:fy|q|fiscal\s*(?:year\s*)?|calendar\s*(?:year\s*)?)\s*[0-9][a-z0-9]*(?!\w)', text):
        if not all(i in consumed for i in range(*m.span())):
            unresolved.append('UNSUPPORTED_PERIOD_SYNTAX')
    if len({(r.start, r.end) for r in ranges}) > 1:
        unresolved.append("CONFLICTING_FILING_DATES")
    distinct = {}
    for p in periods:
        distinct.setdefault(period_key(p), p)
    return list(distinct.values()), ranges[0] if ranges else None, sorted(set(unresolved))


def period_key(period):
    return period.kind, period.year, period.quarter, period.end, period.months


def match_periods(filings, requested):
    """Return eligible union, per-filing refs, missing periods and uncertain membership.

    Comparison operands may live in different filings. A filing with incomplete
    column metadata is retained as uncertain, never excluded solely by fiscal_year.
    """
    if not requested:
        return filings, {}, [], False
    eligible, refs, covered, uncertain = [], {}, set(), False
    for filing in filings:
        matches = [c for c in filing.column_periods if any(period_key(c.period) == period_key(p) for p in requested)]
        for c in matches:
            covered.add(period_key(c.period))
        if matches or not filing.column_periods_complete:
            eligible.append(filing)
            refs[filing.filing_id] = sorted({c.source_ref for c in matches})
            if not filing.column_periods_complete:
                uncertain = True
    missing = [p for p in requested if period_key(p) not in covered]
    return eligible, refs, missing, uncertain

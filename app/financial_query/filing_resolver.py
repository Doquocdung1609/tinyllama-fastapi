"""Filing membership and version selection, without synthesized amended tables."""
from app.financial_query.contracts import Status


def resolve_filings(intent, filters, catalog, cik):
    filings = sorted((f for f in catalog.filings if f.cik == cik), key=lambda f: f.filing_id)
    if filters.form_type and intent.forms and intent.forms != [filters.form_type]:
        return [], Status.NEEDS_CLARIFICATION, ["FORM_FILTER_CONFLICT"], None, "UNSPECIFIED"
    form = filters.form_type or (intent.forms[0] if len(intent.forms) == 1 else None)
    dates = filters.filing_dates or intent.filing_dates
    if filters.filing_dates and intent.filing_dates and filters.filing_dates != intent.filing_dates:
        # Conservative: do not silently intersect or relax a user's date predicates.
        return [], Status.NEEDS_CLARIFICATION, ["FILING_DATE_FILTER_CONFLICT"], dates, "UNSPECIFIED"
    pref = filters.amendment_preference
    if pref != 'UNSPECIFIED' and intent.amendment_preference not in {pref, 'UNSPECIFIED'}:
        return [], Status.NEEDS_CLARIFICATION, ["AMENDMENT_FILTER_CONFLICT"], dates, pref
    if pref == 'UNSPECIFIED':
        pref = intent.amendment_preference
    if form and ((pref == 'ORIGINAL' and form.endswith('/A')) or (pref == 'AMENDED' and not form.endswith('/A'))):
        return [], Status.NEEDS_CLARIFICATION, ["FORM_VERSION_CONFLICT"], dates, pref
    if filters.filing_ids:
        filings = [f for f in filings if f.filing_id in filters.filing_ids]
    if intent.accessions:
        if filters.filing_ids and not any(f.accession in intent.accessions for f in filings):
            return [], Status.NEEDS_CLARIFICATION, ['ACCESSION_FILTER_CONFLICT'], dates, pref
        filings = [f for f in filings if f.accession in intent.accessions]
    if form:
        if (intent.accessions or filters.filing_ids) and filings and not any(f.form == form for f in filings):
            return [], Status.NEEDS_CLARIFICATION, ['EXPLICIT_FILING_FORM_CONFLICT'], dates, pref
        filings = [f for f in filings if f.form == form]
    reasons = []
    if dates:
        if any(f.filing_date is None for f in filings):
            reasons.append("FILING_DATE_METADATA_MISSING")
        filings = [f for f in filings if f.filing_date is None or dates.start <= f.filing_date <= dates.end]
    if pref == 'ORIGINAL':
        filings = [f for f in filings if not f.form.endswith('/A')]
    elif pref == 'AMENDED':
        filings = [f for f in filings if f.form.endswith('/A')]
    if any(f.form.endswith('/A') and f.amendment_of is None for f in filings):
        reasons.append("AMENDMENT_LINKAGE_MISSING")
    # Explicit original form/accession is a document selection, not a request to
    # silently replace it with any amendment outside that exact selection.
    if pref == 'UNSPECIFIED' and not form and not intent.accessions and not filters.filing_ids:
        ids = {f.filing_id for f in filings}
        if any(f.form.endswith('/A') and (f.amendment_of in ids or f.amendment_of is None) for f in filings):
            reasons.append("AMENDMENT_SELECTION_REQUIRED")
    status = Status.NEEDS_CLARIFICATION if reasons else Status.RESOLVED if filings else Status.NO_ELIGIBLE_EVIDENCE
    return filings, status, sorted(set(reasons)) or ["EXPLICIT_FILING_CONSTRAINTS_APPLIED"], dates, pref

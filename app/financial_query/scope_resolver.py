"""Opt-in orchestration: parse → entity lookup → filing lookup → period validation.

No services, databases or filesystem operations. Determinism is relative to the
complete supplied catalog, filters and generation identity, not current time.
"""
from pydantic import ValidationError
from app.financial_query.contracts import (
    CorpusCatalogV1, ExplicitFiltersV1, IntentCategory, PeriodV1, ResolvedScopeV1,
    ScopeResolutionResultV1, Status, TraceStepV1, validate_input_budget,
)
from app.financial_query.filing_resolver import resolve_filings
from app.financial_query.intent_classifier import parse_query
from app.financial_query.issuer_resolver import extract_issuers, resolve_issuer
from app.financial_query.period_resolver import match_periods, period_key


def resolve_financial_query(question, explicit_filters, corpus_catalog, generation_identity=None):
    trace, intent = [], None
    def step(stage, rule, detail):
        trace.append(TraceStepV1(stage=stage, rule_id=rule, detail=detail))
    def result(status, reasons, scope=None, warnings=None):
        step('result', status.value, ','.join(reasons))
        return ScopeResolutionResultV1(query_intent=intent, resolved_scope=scope, status=status,
            clarification_questions=[f"Please clarify: {r}." for r in reasons] if status == Status.NEEDS_CLARIFICATION else [],
            warnings=sorted(set(warnings or [])), trace=trace)
    try:
        intent = parse_query(question)
        validate_input_budget(explicit_filters)
        validate_input_budget(corpus_catalog)
        filter_data = explicit_filters.model_dump(warnings=False) if isinstance(explicit_filters, ExplicitFiltersV1) else explicit_filters
        filters = ExplicitFiltersV1.model_validate(filter_data if filter_data is not None else {})
        # Revalidate copies; mutable containers inside frozen Pydantic objects are
        # not trusted as immutable after construction by a caller.
        catalog = CorpusCatalogV1.model_validate(corpus_catalog.model_dump(warnings=False) if isinstance(corpus_catalog, CorpusCatalogV1) else corpus_catalog)
        step('input', 'VALIDATED_V1', 'Bounded question and strict catalog/filter schemas')
        if generation_identity is not None and generation_identity != catalog.generation_id:
            return result(Status.INVALID_INPUT, ['GENERATION_IDENTITY_MISMATCH'])
        mentions = extract_issuers(intent.original_question, catalog)
        intent = intent.model_copy(update={'issuer_mentions': mentions})
        step('parse', 'RULES_V1', ','.join(intent.matched_rule_ids))
    except (ValueError, TypeError, ValidationError):
        # Never echo malformed input, secrets or local paths in diagnostic text.
        return result(Status.INVALID_INPUT, ['INVALID_QUESTION_FILTER_OR_CATALOG'])
    if intent.category == IntentCategory.UNSUPPORTED:
        return result(Status.UNSUPPORTED, ['NO_SUPPORTED_FINANCIAL_INTENT'])
    if intent.unresolved_slots:
        return result(Status.NEEDS_CLARIFICATION, intent.unresolved_slots)
    issuer, status, reasons = resolve_issuer(mentions, filters, catalog, intent.accessions)
    step('issuer', status.value, ','.join(reasons))
    if issuer is None:
        return result(status, reasons)
    filings, status, reasons, dates, amendment = resolve_filings(intent, filters, catalog, issuer.cik)
    step('filing', status.value, ','.join(reasons))
    if status == Status.NEEDS_CLARIFICATION and not filings:
        return result(status, reasons)
    periods = list(intent.reporting_periods)
    if filters.fiscal_period and not filters.fiscal_year:
        return result(Status.NEEDS_CLARIFICATION, ['FISCAL_YEAR_REQUIRED_FOR_QUARTER_FILTER'])
    if filters.fiscal_year:
        period = PeriodV1(kind='FISCAL_QUARTER' if filters.fiscal_period and filters.fiscal_period != 'FY' else 'FISCAL_YEAR',
            year=filters.fiscal_year, quarter=int(filters.fiscal_period[1:]) if filters.fiscal_period and filters.fiscal_period != 'FY' else None,
            raw='explicit fiscal filter')
        if periods and any(period_key(p) != period_key(period) for p in periods):
            return result(Status.NEEDS_CLARIFICATION, ['PERIOD_FILTER_CONFLICT'])
        periods = [period]
    # Filing problems cannot be erased by a period filter. Preserve candidate
    # scope for audit, but never call it resolved on metadata uncertainty.
    if status == Status.NO_ELIGIBLE_EVIDENCE:
        return result(status, ['NO_MATCHING_FILING'])
    eligible, refs, missing, uncertain = match_periods(filings, periods)
    period_reasons = []
    if missing or uncertain:
        if uncertain:
            period_reasons.append('COLUMN_PERIOD_METADATA_INCOMPLETE')
            status = Status.NEEDS_CLARIFICATION
        elif missing:
            if status != Status.NEEDS_CLARIFICATION:
                status = Status.NO_ELIGIBLE_EVIDENCE
            period_reasons.append('REQUESTED_PERIOD_NOT_IN_CATALOG')
    if not eligible and status == Status.RESOLVED:
        status = Status.NO_ELIGIBLE_EVIDENCE
    step('period', status.value, ','.join(period_reasons) or 'Explicit column metadata matched; no filing-year exclusion')
    warnings = ['PARTIAL_EXTRACTION:' + f.filing_id for f in eligible if f.extraction_status == 'PARTIAL_EXTRACTION']
    if intent.metric_mentions or intent.numerical_constraints or intent.unit_mentions:
        warnings.append('METRIC_AND_UNIT_EVIDENCE_NOT_VERIFIED_BY_D1')
    if len(eligible) > 1:
        warnings.append('MULTIPLE_ELIGIBLE_FILINGS_NO_LATEST_SELECTION')
    if any(f.form.endswith('/A') for f in eligible):
        warnings.append('AMENDMENT_IS_NOT_A_MERGED_STATEMENT')
    all_reasons = sorted(set(reasons + period_reasons))
    scope = ResolvedScopeV1(dataset_id=catalog.dataset_id, manifest_hash=catalog.manifest_hash,
        generation_id=catalog.generation_id, cik=issuer.cik,
        issuer_aliases=sorted(set([issuer.company_name] + issuer.tickers + issuer.verified_aliases)),
        eligible_filing_ids=[f.filing_id for f in eligible], forms=sorted({f.form for f in eligible}),
        filing_dates=dates, requested_periods=periods, comparative_column_requirements=periods,
        matched_column_refs=refs, amendment_selection=amendment, warnings=warnings,
        resolution_reasons=all_reasons, status=status)
    return result(status, all_reasons, scope, warnings)

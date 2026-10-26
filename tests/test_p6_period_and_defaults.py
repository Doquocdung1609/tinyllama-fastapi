"""P6 fail-first regression for D1 wording and RAG configuration isolation."""
from app.financial_query.period_resolver import extract_periods
from app.config import get_settings
from app.models import RAGRequest


def test_three_months_ended_is_typed_duration():
    periods, filing_date, unresolved = extract_periods('three months ended september 30, 2026')
    assert not unresolved and filing_date is None
    assert len(periods) == 1
    assert periods[0].kind == 'DURATION' and periods[0].months == 3
    assert str(periods[0].end) == '2026-09-30'


def test_rag_request_respects_configured_default_and_explicit_override():
    assert RAGRequest(question='Where?').score_threshold == get_settings().score_threshold
    assert RAGRequest(question='Where?', score_threshold=.55).score_threshold == .55

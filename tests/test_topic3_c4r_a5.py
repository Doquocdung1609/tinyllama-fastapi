"""C4R reproductions: new A5 must keep financial scope and run provenance."""

import csv
from pathlib import Path

import pytest

from app.research_retrieval.faith_r_a5 import plan_query, retrieval_filters, execute_a5
from app.research_retrieval.financial_answer_v8 import SourceArchiveAnswererV8


CASES = Path(__file__).resolve().parents[1] / "docs/topic3_c4r_recovery/C4R_QUERY_PARSER_VI_EN_TEST_CASES.csv"


def test_quarter_and_foreign_fiscal_metadata_never_hard_exclude():
    q = plan_query("What was Apple net sales for the three months ended June 28, 2025 in its 10-Q?")
    f = retrieval_filters(q)
    assert q.issuer == "AAPL" and q.form == "10-Q" and q.duration_months == 3
    assert f.tickers == ["AAPL"] and f.document_types == ["10-Q"]
    assert f.fiscal_periods is None
    tsm = plan_query("What was TSMC net revenue for FY2022 in its 20-F?")
    assert retrieval_filters(tsm).fiscal_periods is None


def test_bilingual_contrastive_metrics_and_scope():
    parent = plan_query("Lợi nhuận sau thuế công ty mẹ Hòa Phát quý 4 năm 2025 là bao nhiêu?")
    assert parent.metric == "NET_INCOME" and parent.scope == "PARENT"
    assert parent.quarter == 4 and parent.fiscal_year == 2025
    assert plan_query("Doanh thu thuần của Apple năm tài chính 2024?").metric == "NET_REVENUE"
    assert plan_query("Giá vốn hàng bán của Apple năm tài chính 2024?").metric == "COST_OF_SALES"
    assert plan_query("Lợi nhuận gộp của Apple năm tài chính 2024?").metric == "GROSS_PROFIT"
    assert plan_query("Biên lợi nhuận gộp của Apple năm tài chính 2024?").metric == "GROSS_MARGIN_PERCENT"
    assert plan_query("Apple capital expenditures in 2024?").metric == "CAPEX"


def test_every_attempt_records_empty_and_no_cross_issuer_leak():
    class EmptyEngine:
        def search(self, query, method, k, filters, prefetch_k):
            assert filters.tickers == ["AAPL"]
            return []

    result = execute_a5(EmptyEngine(), "Apple net sales for fiscal 2024 in its 10-K", budget=5)
    assert result.status == "COMPLETED_EMPTY"
    assert result.hits == []
    assert len(result.attempts) >= 1
    assert all(a["status"] in {"COMPLETED_EMPTY", "COMPLETED_WITH_HITS"} for a in result.attempts)


@pytest.mark.parametrize("case", list(csv.DictReader(CASES.open(encoding="utf-8", newline=""))),
                         ids=lambda x: x["id"])
def test_forty_bilingual_accounting_contrasts(case):
    plan = plan_query(case["question"])
    assert plan.original == case["question"]
    assert (plan.metric or "") == case["expected_metric"]
    assert (plan.scope or "") == case["expected_scope"]
    assert (str(plan.duration_months) if plan.duration_months else "") == case["expected_duration"]
    if case["expected_flag"]:
        assert any(x.startswith(case["expected_flag"]) for x in plan.unresolved)


def test_form_duration_instant_and_fiscal_shift():
    assert plan_query("TSMC net income FY2022 in its 20-F").form == "20-F"
    assert retrieval_filters(plan_query("TSMC net income FY2022 in its 20-F")).fiscal_periods is None
    assert plan_query("TSMC corporate changes in its 6-K in 2025").form == "6-K"
    assert plan_query("Apple total assets as of 2025-06-28 in its 10-Q").statement == "BALANCE"
    assert plan_query("Apple operating income for six months ended 2025-06-28").duration_months == 6
    assert plan_query("Apple cash and cash equivalents at ngày 28/09/2024").period_end == "2024-09-28"


def test_source_enriched_answer_requires_retrieved_filing_and_scope(tmp_path):
    # SYNTHETIC fixture: this is a contract test, never benchmark evidence.
    source = {"accession": "a1", "ticker": "AAPL", "form": "10-K",
              "report_date": "2024-09-28", "source_url": "https://example.test/a1",
              "sha256": "synthetic-source"}
    path = tmp_path / "sources.json"
    path.write_text(__import__("json").dumps({"verified": 47, "sources": [source]}))
    answerer = SourceArchiveAnswererV8(path)
    answerer._facts["a1"] = [{"metric": "TOTAL_ASSETS", "period_start": None,
                              "period_end": "2024-09-28", "duration_type": "INSTANT",
                              "value_decimal": "42", "value_literal": "42", "unit": "USD_MILLIONS",
                              "currency": "USD", "source_element_id": "f-1"}]
    question = "Apple total assets as of 2024-09-28 in its 10-K"
    hit = {"accession_number": "a1", "chunk_id": "original-1"}
    assert answerer.answer(question, [], "SOURCE_ENRICHED_V1").status == "ABSTAIN"
    assert answerer.answer(question, [hit], "ORIGINAL_CHUNK_ONLY").status == "ABSTAIN"
    got = answerer.answer(question, [hit], "SOURCE_ENRICHED_V1")
    assert got.status == "VERIFIED_SOURCE_CELL" and got.value_decimal == "42"
    assert answerer.answer("Apple parent company total assets as of 2024-09-28 in its 10-K",
                           [hit], "SOURCE_ENRICHED_V1").status == "ABSTAIN"


def test_sidecar_reservation_is_not_truncated_after_full_base_pool():
    class Hit:
        def __init__(self, i):
            self.chunk_id = f"base-{i}"
            self.ticker = "AAPL"
            self.document_type = "10-K"
            self.fiscal_period = "FY2024"
            self.filing_date = "2024-11-01"
            self.section = "Item 8. Financial Statements"
            self.score = 1.0
            self.text = "Total assets | 1,000"
            self.source_url = "https://example.test"

        def model_dump(self):
            return {"document_id": "AAPL_acc"}

    class Engine:
        def search(self, query, method, k, filters, prefetch_k):
            return [Hit(i) for i in range(60)]

    class Sidecar:
        def find(self, plan, quota, report_dates):
            return [{"chunk_id": "sidecar-original", "ticker": "AAPL",
                     "document_type": "10-K", "fiscal_period": "FY2024",
                     "section": "Item 8. Financial Statements", "text": "Total assets | 2,000",
                     "score": 0.0, "accession_number": "acc", "source_url": "https://example.test"}], 8670

    result = execute_a5(Engine(), "Apple total assets fiscal year 2024 in its 10-K",
                        budget=20, sidecar=Sidecar())
    assert "sidecar-original" in result.candidate_pool_ids
    assert len(result.candidate_pool_ids) == 60
    assert result.candidate_scanned == 8670


def test_explicit_issuer_never_accepts_foreign_hit_even_if_engine_misbehaves():
    class Foreign:
        chunk_id = "foreign"
        ticker = "MSFT"
        document_type = "10-K"
        fiscal_period = "FY2024"
        filing_date = "2024-11-01"
        section = "Item 8"
        score = 2
        text = "Total assets | 1,000"
        source_url = "https://example.test"

        def model_dump(self):
            return {"document_id": "MSFT_foreign"}

    class BadEngine:
        def search(self, query, method, k, filters, prefetch_k):
            return [Foreign()]

    got = execute_a5(BadEngine(), "Apple total assets fiscal year 2024 in its 10-K", 5)
    assert got.status == "COMPLETED_EMPTY" and got.hits == []
    assert len(got.attempts) == 2

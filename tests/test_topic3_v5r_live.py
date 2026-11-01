from types import SimpleNamespace

from app.research_retrieval import faith_r_live


class Engine:
    def __init__(self):
        self.filters = []

    def search(self, question, method, k, filters, prefetch_k):
        self.filters.append(filters)
        return [SimpleNamespace(chunk_id="wrong", ticker="AMD", fiscal_period="FY2022", score=9,
                                text="[AMD total revenue FY2022]\n\nUnrelated exhibit text.",
                                source_url="https://www.sec.gov/test", document_id="cik_acc")]


def test_live_arms_use_real_engine_and_same_budget(monkeypatch):
    monkeypatch.setattr(faith_r_live, "safe_filters", lambda question: {"validated": True})
    engine = Engine()
    sidecar = faith_r_live.EvidenceSidecar.__new__(faith_r_live.EvidenceSidecar)
    sidecar.payloads = [{"chunk_id": "row", "ticker": "AMD", "fiscal_period": "FY2022",
                         "text": "[AMD FY2023]\n\nTotal net revenue | $ | 23,601 | 16,434",
                         "source_url": "https://www.sec.gov/test", "accession_number": "acc"}]
    question = "What was AMD total revenue in fiscal 2022?"
    a2 = faith_r_live.live_retrieve(engine, question, "A2", 2)
    a3 = faith_r_live.live_retrieve(engine, question, "A3", 2, sidecar)
    a4 = faith_r_live.live_retrieve(engine, question, "A4", 2, sidecar)
    assert [h["chunk_id"] for h in a2.hits] == ["wrong"]
    assert set(a3.candidate_pool_ids) == {"wrong", "row"}
    assert [h["chunk_id"] for h in a4.hits] == ["row", "wrong"]
    assert all(h["verification_status"] == "UNVERIFIED" for h in a4.hits)
    assert all(f == {"validated": True} for f in engine.filters)


def test_comparative_year_does_not_become_hard_filter():
    from app.research_retrieval.faith_r import parse_query
    slots = parse_query("Compare AMD revenue in 2022 versus 2023")
    assert slots.comparative_intent
    assert slots.fiscal_year is None
    apple = parse_query("Compare Apple's FY2023 and FY2024 net sales")
    assert apple.issuer == "AAPL" and apple.metric == "TOTAL_REVENUE"
    assert apple.comparative_intent and apple.fiscal_year is None
    assert apple.requested_years == (2023, 2024)
    assert parse_query("What were Apple's FY2024 net sales?").fiscal_year == 2024


def test_posthoc_financial_alignment_uses_row_boundary_and_phrase_year():
    from app.research_retrieval.faith_r import parse_query
    slots = parse_query("What was AMD total revenue in fiscal 2022?")
    row = {"chunk_id": "a", "ticker": "AMD", "fiscal_period": "FY2022", "score": 1,
           "text": "[header]\n\n| Total revenues | $ | 23,601 |"}
    prose = {"chunk_id": "b", "ticker": "AMD", "fiscal_period": "FY2022", "score": 1,
             "text": "[header]\n\nRevenue increased as a percentage of total revenues in 2023."}
    assert faith_r_live.financial_alignment(row, slots) > faith_r_live.financial_alignment(prose, slots)
    capex = parse_query("What was Meta capital expenditure in fiscal 2024?")
    right = {"chunk_id": "c", "ticker": "META", "fiscal_period": "FY2024", "score": 1,
             "text": "[header]\n\nCapital expenditures, including finance leases, were $39 billion in 2024."}
    wrong_year = {"chunk_id": "d", "ticker": "META", "fiscal_period": "FY2024", "score": 1,
                  "text": "[header]\n\nCapital expenditures will be $60 billion in 2025."}
    assert faith_r_live.financial_alignment(right, capex) > faith_r_live.financial_alignment(wrong_year, capex)


def test_live_api_requires_explicit_feature_flag(monkeypatch):
    from fastapi import HTTPException
    from app.product.frontend_api import FaithRLiveRequest, faith_r_live_lab, faith_r_live_status
    monkeypatch.delenv("FAITH_R_LIVE_ENABLED", raising=False)
    assert faith_r_live_status()["status"] == "NOT_AVAILABLE"
    try:
        faith_r_live_lab(FaithRLiveRequest(query="AMD total revenue FY2022", arm="A4R"))
    except HTTPException as exc:
        assert exc.status_code == 503 and exc.detail["code"] == "RESEARCH_INDEX_NOT_ENABLED"
    else:
        raise AssertionError("live research ran without feature flag")


def test_recorded_live_summary_is_explicitly_unreviewed():
    from app.product.frontend_api import faith_r_live_summary

    result = faith_r_live_summary()
    assert result["status"] == "RECORDED_LIVE_RUN_EXPOSED_DEVELOPMENT"
    assert result["human_gold"] is False and result["numeric_cells_verified"] == 0
    assert result["arms"]["A4R"]["known_positive_hit"]["1"] == 13

from app.research_retrieval.faith_r import parse_query, rank_recorded_top10
from app.research_retrieval.independent_qrels import Judgment, validate_independent_gold, judged_hit_bounds
from app.product.topic3_lab import faith_r_recorded_experiment


def test_explicit_slots_and_ambiguity():
    slots = parse_query("What was AMD total revenue in fiscal 2022?")
    assert (slots.issuer, slots.fiscal_year, slots.metric) == ("AMD", 2022, "TOTAL_REVENUE")
    assert not slots.unresolved
    assert parse_query("What was revenue?").unresolved


def test_same_pool_and_stale_header_excluded():
    slots = parse_query("What was AMD total revenue in fiscal 2022?")
    hits = [
        {"chunk_id": "stale", "ticker": "AMD", "fiscal_period": "FY2022", "score": 9,
         "text": "[AMD total revenue FY2022]\n\nThe filing has an exhibit list."},
        {"chunk_id": "row", "ticker": "AMD", "fiscal_period": "FY2022", "score": 2,
         "text": "[AMD FY2023]\n\nTotal net revenue | $ | 23,601 | 16,434"},
    ]
    ranked = rank_recorded_top10(hits, slots)
    assert [c.chunk_id for c in ranked] == ["row", "stale"]
    assert ranked[0].table_row_candidate
    assert ranked[0].verification_status == "UNVERIFIED"
    assert ranked[0].unit is None and ranked[0].value is None
    assert ranked[1].metric_relation == "UNKNOWN"


def test_budget_and_duplicate_guard():
    slots = parse_query("AMD total revenue 2022")
    hit = {"chunk_id": "same", "text": "none"}
    try:
        rank_recorded_top10([hit, hit], slots)
    except ValueError as exc:
        assert "DUPLICATE" in str(exc)
    else:
        raise AssertionError("duplicate accepted")


def test_independent_qrel_gate_and_unknown_bounds():
    assert validate_independent_gold([])["status"] == "NO_INDEPENDENT_GOLD"
    machine = Judgment("q", "c", "YES", "acc", "table 1 row 2", "revenue", "FY2024", "USD", "bot", "MACHINE")
    try:
        validate_independent_gold([machine])
    except ValueError as exc:
        assert "HUMAN" in str(exc)
    else:
        raise AssertionError("machine label accepted as independent gold")
    assert judged_hit_bounds(["unknown"], {}, 1) == {
        "known_positive_hit": 0, "possible_positive_hit": 1, "unknown_count": 1, "recall": None}


def test_recorded_ui_projection_is_explicitly_unreviewed():
    result = faith_r_recorded_experiment()
    assert result["status"] == "RECORDED_EXPERIMENT"
    assert result["review_status"] == "UNREVIEWED"
    assert len(result["cases"]) == 15
    assert all(c["a4_top1"]["verification_status"] == "UNVERIFIED" for c in result["cases"])

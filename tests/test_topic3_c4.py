"""C4 gates reject unsupported scores and keep the public proxy arithmetic honest."""

import json
from pathlib import Path

import pytest

from scripts.topic3_c4_score_proxy import score, quantile


ROOT = Path(__file__).resolve().parents[1] / "docs" / "topic3_c4"


def test_quantile_is_observed_not_fabricated():
    assert quantile([], .5) is None
    assert quantile([10.0], .95) == 10.0
    assert quantile([1.0, 2.0, 3.0], .5) == 2.0


def test_score_gate_fails_before_reading_ranked_data(tmp_path):
    lock = tmp_path / "lock.json"
    eligibility = tmp_path / "eligible.json"
    lock.write_text(json.dumps({
        "metric_scope": "TRACK_B_OBJECTIVE_TARGET_FILING_PROXY_ONLY",
        "original_single_chunk_exact_qrels": 0,
        "private_eligibility_sha256": "wrong",
    }))
    eligibility.write_text("{}")
    with pytest.raises(ValueError, match="Pre-scoring eligibility"):
        score(lock, eligibility, tmp_path / "absent_pool", tmp_path / "absent_qrel",
              tmp_path / "results", tmp_path / "summary", tmp_path / "public")


def test_real_public_proxy_denominators_and_limits():
    data = json.loads((ROOT / "C4_OBJECTIVE_PROXY_SCORECARD_V1.json").read_text())
    assert data["frozen_questions"] == 94
    assert data["objective_proxy_eligible"] == 93
    assert data["excluded"] == 1
    assert data["expected_arm_question_index_runs"] == 94 * 18
    assert data["observed_hit_row_runs"] + data["no_hit_rows_provenance_unknown"] == 94 * 18
    assert data["no_hit_rows_provenance_unknown"] == 104
    assert len(data["arms"]) == 18
    assert sum(a["unknown_zero_or_omitted"] for a in data["arms"]) == 104
    for arm in data["arms"]:
        assert arm["observed_runs"] + arm["unknown_zero_or_omitted"] == 93
        assert (0 <= arm["hit_at_1_numerator"] <=
                arm["hit_at_5_numerator"] <= arm["hit_at_10_numerator"] <=
                arm["observed_runs"])
    for pair in data["paired"]:
        assert (pair["right_win"] + pair["tie"] + pair["right_loss"] ==
                pair["paired_denominator"])
    assert data["original_chunk_exact_at_k"].startswith("NOT_REPORTABLE")
    assert data["final_G2_relevance_metrics"] == "NOT_RUN"


def test_failure_diagnosis_is_a_post_score_read_only_audit():
    data = json.loads((ROOT / "C4_FAILURE_DIAGNOSIS_V1.json").read_text())
    assert data["read_only_index_b_points"] == 8670
    assert data["read_only_index_b_accessions"] == 47
    assert (data["target_filing_hit_and_filter_match"] +
            data["no_ranked_hit_rows_with_target_filter_mismatch"] +
            data["wrong_filing_all_top20_with_target_filter_mismatch"]) == 93
    assert data["no_ranked_hit_rows_by_form"] == {"10-Q": 24, "20-F": 2}
    assert "NO_G2_RERUN" in data["post_score_action"]


def test_provisional_qrel_coverage_does_not_become_gold():
    data = json.loads((ROOT / "C4_QREL_COVERAGE_AT_K_V1.json").read_text())
    assert data["qrel_scope"] == "AI_PROVISIONAL_ONLY_NOT_HUMAN_GOLD"
    assert len(data["arms"]) == 18
    for arm in data["arms"]:
        for k in (1, 5, 10):
            cell = arm[f"at_{k}"]
            assert cell["candidate_slots"] == (
                cell["ai_provisional_partial"] + cell["unjudged"])
            assert cell["exact"] == cell["human_judged"] == 0
    assert data["exact_relevance_metrics"] == "NOT_REPORTABLE"

from scripts.financial_retrieval_benchmark import evaluate, _p95
import pytest


def test_retrieval_metrics_are_hand_checkable():
    score = evaluate(["bad", "a", "b", "bad2"], {"a", "b"}, 4)
    assert score["recall"] == 1
    assert score["precision"] == .5
    assert score["mrr"] == .5
    assert 0 < score["ndcg"] < 1


def test_no_gold_labels_is_rejected_not_reported_as_perfect():
    with pytest.raises(ValueError, match="independently"):
        evaluate(["anything"], set(), 5)


def test_p95_small_n():
    assert _p95([10, 30, 20]) == 30

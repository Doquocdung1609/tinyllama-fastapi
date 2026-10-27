"""Offline P11 partition, source-lineage and provisional-label invariants."""
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / "docs/topic3/milestone_d/recovery/p11"


def read(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def test_issuer_partitions_are_disjoint_and_exclude_consumed_corpus():
    data = read("p11_partition_manifest.json")
    parts = [{row["cik"] for row in items} for items in data["partitions"].values()]
    assert len(set.union(*parts)) == sum(map(len, parts)) == 9
    assert not set.union(*parts).intersection(data["excluded_ciks"])
    assert data["status"] == "PRESELECTED_BEFORE_ACQUISITION"


def test_acquired_sources_match_fixed_partition_and_official_url():
    plan = read("p11_partition_manifest.json")
    expected = {row["ticker"]: (part, row["cik"], row["requested_form"])
                for part, items in plan["partitions"].items() for row in items}
    source = read("p11_source_registry.json")
    assert len(source["records"]) == 9
    assert source["contact_identity_recorded"] is False
    for row in source["records"]:
        assert (row["partition"], row["cik"], row["requested_form"]) == expected[row["ticker"]]
        if row["status"] == "ACQUIRED_OFFICIAL_SOURCE":
            assert len(row["raw_sha256"]) == 64
            assert 0 < row["source_bytes"] <= plan["limits"]["max_bytes_per_filing"]
            assert row["metadata"]["source_url"].startswith(
                "https://www.sec.gov/Archives/edgar/data/")
        else:
            assert row["status"] == "OFFICIAL_SOURCE_REQUEST_FAILED"
            assert row["reason"] == "SOURCE_BYTES_BUDGET_EXCEEDED"


def test_heldout_bytes_are_not_parsed_or_labeled():
    parsed = read("p11_parsed_sources.json")
    assert parsed["heldout_parsed"] is False
    assert {r["ticker"] for r in parsed["records"]} == {"MCD", "CAT", "SBUX", "UPS", "TXN"}
    labels = read("p11_query_registry.json")
    assert {r.get("issuer") for r in labels["queries"] if r.get("issuer")} <= {"MCD", "CAT"}


def test_qrels_are_provisional_and_refer_only_to_positive_dev_questions():
    questions = read("p11_query_registry.json")
    qrels = read("p11_qrels.json")
    review = read("p11_label_review_queue.json")
    positives = {q["query_id"]: q for q in questions["queries"]
                 if q.get("eligible_parent_ids")}
    assert len(positives) == len(qrels["qrels"]) == len(review["items"]) == 10
    assert len(questions["queries"]) == 14
    assert qrels["human_reviewers"] == review["human_reviewers"] == 0
    assert qrels["rankings_used_for_labels"] is False
    for row in qrels["qrels"]:
        assert row["query_id"] in positives
        assert row["parent_id"] in positives[row["query_id"]]["eligible_parent_ids"]
        assert row["status"] == "PROVISIONAL_SOURCE_ROW_LABEL"
    for row in questions["queries"]:
        if not row.get("eligible_parent_ids"):
            assert row["qrel_status"] == "NOT_A_NEGATIVE_QREL"

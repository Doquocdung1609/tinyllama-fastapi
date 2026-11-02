"""Guard scientific labels and provenance in tracked V6 review artifacts."""

import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V6 = ROOT / "docs/topic3_v6"


def test_fresh_holdout_is_unjudged_and_has_no_exact_pilot_overlap():
    fresh_path = V6 / "V6_FRESH_HOLDOUT_30_UNJUDGED.csv"
    pilot_path = ROOT / "docs/topic3_v5/recovery_live/holdout_30_review_queue.csv"
    fresh = list(csv.DictReader(fresh_path.open(encoding="utf-8", newline="")))
    pilot = list(csv.DictReader(pilot_path.open(encoding="utf-8", newline="")))
    manifest = json.loads((V6 / "V6_FRESH_HOLDOUT_MANIFEST.json").read_text(encoding="utf-8"))
    assert len(fresh) == 30 and len({r["question_id"] for r in fresh}) == 30
    assert all(r["label"] == "UNJUDGED" and not r["adjudicator"] and not r["value"] for r in fresh)
    assert not ({r["question"].casefold().strip() for r in fresh} &
                {r["question"].casefold().strip() for r in pilot})
    assert manifest["sha256"] == hashlib.sha256(fresh_path.read_bytes()).hexdigest()


def test_review_packets_do_not_masquerade_as_human_gold():
    for directory in (V6 / "V6_SOURCE_FIRST_REVIEW_PACKETS", V6 / "V6_FRESH_HOLDOUT_REVIEW_PACKETS"):
        manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["status"] == "MACHINE_PREPARED_UNJUDGED"
        assert manifest["independently_reviewed"] == 0
        assert len(manifest["packets"]) == 30
        for item in manifest["packets"]:
            packet = json.loads((directory / f"{item['id']}.json").read_text(encoding="utf-8"))
            assert packet["label"] == "UNJUDGED" and packet["machine_prepared_only"] is True
            assert all(value is None for value in packet["review_fields"].values())
            assert packet["source_url"].startswith("https://www.sec.gov/Archives/edgar/data/")
            assert (directory / f"{item['id']}.html").is_file()


def test_pilot_is_exploratory_and_final_ranking_unrun():
    pilot = json.loads((V6 / "V6_PILOT_SUMMARY.json").read_text(encoding="utf-8"))
    assert pilot["status"] == "EXPLORATORY_PILOT_UNJUDGED_NOT_INDEPENDENT"
    assert pilot["questions"] == 30 and pilot["runs"] == 300
    assert pilot["relevance_labels"] == 0 and pilot["numeric_cells_verified"] == 0
    assert set(pilot["methods"]) == {"bm25", "dense", "sparse", "bm25_dense", "sparse_dense",
                                     "rerank", "A2", "A3", "A4", "A4R"}

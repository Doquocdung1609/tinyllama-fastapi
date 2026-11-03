"""Freeze C4 objective-proxy eligibility before inspecting sealed G3U rankings."""

from __future__ import annotations

import argparse
from collections import Counter
import csv
from hashlib import sha256
import json
from pathlib import Path
import zipfile

from scripts.topic3_v7a_g3s_review_tool import release_preview, verify_events

EXPECTED_EVENT_SHA = "be9cd71e6731aa48287c63078737a6f10e1c4fb00c30c191f8a41f72effa3991"
EXPECTED_HANDOFF_SHA = "2392027056f713bc465eaf0bba25461dec813ce7e0b080717018ad90c5f3485b"
EXPECTED_RANKED_SHA = "93c9dcf09112dc106f1d79aa63f232c03752c5d7c4ba0127221f10e300759a21"
EXPECTED_G2_QUESTION_SHA = "a92cdfb6a00744c3ea8bdae93b337d60919be52e65019b4f541b40235f4aa4ef"


def sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def freeze(events_path: Path, handoff_path: Path, status_csv: Path,
           ranked_path: Path, private_out: Path, public_out: Path) -> dict:
    if private_out.exists() or public_out.exists():
        raise FileExistsError("C4 eligibility freeze already exists")
    if (sha(events_path) != EXPECTED_EVENT_SHA or
            sha(handoff_path) != EXPECTED_HANDOFF_SHA or
            sha(ranked_path) != EXPECTED_RANKED_SHA):
        raise ValueError("Pinned event/handoff/ranked bytes changed")
    events = verify_events(events_path)
    if len(events) != 102 or len({event["event_id"] for event in events}) != 102:
        raise ValueError("Expected 102 distinct hash-chained events")
    with zipfile.ZipFile(handoff_path) as archive:
        if archive.testzip() is not None:
            raise ValueError("G3T handoff ZIP CRC failure")
        dataset_bytes = archive.read("G3T_HUMAN_REVIEW_INPUT_20261103_V2.json")
        dataset = json.loads(dataset_bytes)
    evidence_sha = sha256(dataset_bytes).hexdigest()
    if evidence_sha != "694e55134cc20dc204df02c16bb5397af50e2f4a62088ec04213a0ec026de6e2":
        raise ValueError("G3T review input V2 hash changed")
    if any(event["evidence_sha256"] != evidence_sha for event in events):
        raise ValueError("Human event refers to a different review input")
    records = {row["question_id"]: row for row in dataset["records"]}
    latest = {event["question_id"]: event for event in events}
    if not (len(records) == len(latest) == 94 and set(records) == set(latest)):
        raise ValueError("Human log / frozen question identity mismatch")
    decisions = Counter(event["decision"] for event in latest.values())
    if decisions != {"APPROVE": 86, "REQUEST_CORRECTION": 7, "EXCLUDE": 1}:
        raise ValueError("Latest human decision distribution changed")
    if [(event["question_id"], event["decision"]) for event in events[98:]] != [
            ("V7A_G2_11_02", "APPROVE"),
            ("V7A_G2_12_01", "APPROVE"),
            ("V7A_G2_14_02", "REQUEST_CORRECTION"),
            ("V7A_G2_25_02", "REQUEST_CORRECTION")]:
        raise ValueError("Four correction events differ from owner handoff")
    dataset["evidence_sha256"] = evidence_sha
    preview = release_preview(dataset, events_path)
    if (preview["approved_count"], preview["blocked_count"],
            preview["excluded_count"], preview["pending_count"]) != (67, 26, 1, 0):
        raise ValueError("Release preview denominator changed")
    blocked = Counter(item["reason"] for item in preview["blocked"])
    if blocked != {"STRUCTURED_SOURCE_EVIDENCE_REQUIRED": 19,
                   "REQUEST_CORRECTION": 7}:
        raise ValueError("Blocked category changed")
    with status_csv.open(encoding="utf-8-sig", newline="") as stream:
        supplied_status = {row["question_id"]: row for row in csv.DictReader(stream)}
    if len(supplied_status) != 94 or set(supplied_status) != set(latest):
        raise ValueError("Supplied status CSV has wrong question set")
    stale = sorted(qid for qid in latest if
                   supplied_status[qid]["last_event_hash"] !=
                   latest[qid]["event_sha256"])
    if stale != ["V7A_G2_25_02"]:
        raise ValueError("Supplied status CSV staleness changed")
    block_by_id = {item["question_id"]: item["reason"]
                   for item in preview["blocked"]}
    excluded = {item["question_id"] for item in preview["excluded"]}
    eligible = []
    for qid in sorted(records):
        source = records[qid]
        event = latest[qid]
        eligible.append({
            "question_id": qid,
            "target_accession": source["accession"],
            "ticker": source["ticker"],
            "form": source["form"],
            "source_sha256": source["source_sha256"],
            "latest_event_sha256": event["event_sha256"],
            "latest_decision": event["decision"],
            "release_preview": ("EXCLUDED" if qid in excluded else
                                block_by_id.get(qid, "PREVIEW_APPROVED_NOT_GOLD_CERTIFIED")),
            "target_filing_proxy_eligible": qid not in excluded,
            "original_chunk_exact_qrel_eligible": False,
        })
    private = {
        "schema": "c4_judged_eligibility/v1",
        "lock_timing": "BEFORE_ANY_C4_RANKED_RESULT_INSPECTION_OR_SCORING",
        "event_log_sha256": sha(events_path),
        "review_input_sha256": evidence_sha,
        "ranked_pool_sha256": sha(ranked_path),
        "frozen_question_sha256": EXPECTED_G2_QUESTION_SHA,
        "source_review_identity_assurance": "SELF_DECLARED_REVIEWER_SHA_CHAIN_DOES_NOT_AUTHENTICATE_PERSON",
        "target_filing_proxy_rule": "All 94 frozen questions except the one prior EXCLUDE; target accession fixed by G3T input; no relevance or answer correctness claim",
        "target_filing_proxy_denominator": 93,
        "source_answer_release_preview": 67,
        "source_structure_blocked": 19,
        "review_correction_blocked": 7,
        "excluded": 1,
        "original_single_chunk_exact_qrels": 0,
        "exact_evidence_scoring": "NOT_REPORTABLE",
        "stale_supplied_status_csv_ids": stale,
        "all_94": eligible,
    }
    private_out.parent.mkdir(parents=True, exist_ok=True)
    private_out.write_text(json.dumps(private, indent=2, ensure_ascii=False) + "\n",
                           encoding="utf-8")
    public = {
        "schema": "c4_pre_scoring_eligibility_lock/v1",
        "private_eligibility_sha256": sha(private_out),
        "event_log_sha256": sha(events_path),
        "ranked_pool_sha256": sha(ranked_path),
        "review_input_sha256": evidence_sha,
        "question_count": 94,
        "objective_target_filing_eligible": 93,
        "prior_excluded": 1,
        "human_source_release_preview_only": 67,
        "source_structure_blocked": 19,
        "review_correction_blocked": 7,
        "original_single_chunk_exact_qrels": 0,
        "metric_scope": "TRACK_B_OBJECTIVE_TARGET_FILING_PROXY_ONLY",
        "top_k": [1, 5, 10],
        "no_hit_policy": "NO_HIT_IS_PROXY_MISS_IF_RUN_LOG_PROVES_EXECUTION; OTHERWISE_UNKNOWN",
        "author_rrf": "NATIVE_DEFAULT_K2_V2_POOL; EXPLICIT_K60_NOT_RUN",
        "stage2": "NATIVE_INTERNAL_60_FOR_TOP20_POOL_OUTPUT",
        "frozen_status_csv_warning": "V7A_G2_25_02_LAST_EVENT_HASH_STALE_USE_102_EVENT_LOG",
        "not_authorized_by_this_lock": [
            "original_chunk EXACT/MRR/nDCG/Recall scoring",
            "financial answer correctness scoring",
            "human gold certification",
            "rerun or expansion of the G3U one-shot pool",
        ],
    }
    public_out.parent.mkdir(parents=True, exist_ok=True)
    public_out.write_text(json.dumps(public, indent=2) + "\n", encoding="utf-8")
    return public


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("events_path", "handoff_path", "status_csv", "ranked_path",
                 "private_out", "public_out"):
        parser.add_argument("--" + name.replace("_", "-"), type=Path, required=True)
    print(json.dumps(freeze(**vars(parser.parse_args())), indent=2))

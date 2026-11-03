"""Audit exported G3T double-check tables without treating them as signed human events."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from hashlib import sha256
import json
from pathlib import Path
import re
import zipfile


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def zip_json_lines(archive: zipfile.ZipFile, member: str) -> list[dict]:
    return [json.loads(line) for line in archive.read(member).splitlines() if line]


def audit(latest_path: Path, history_path: Path, memo_path: Path,
          handoff_path: Path) -> dict:
    latest = csv_rows(latest_path)
    history = csv_rows(history_path)
    if len(latest) != 94 or len(history) != 98:
        raise ValueError("Expected exactly 94 latest rows and 98 historical rows")
    by_id: dict[str, list[dict[str, str]]] = defaultdict(list)
    for order, event in enumerate(history, 1):
        if (int(event["event_order"]) != order or
                not re.fullmatch(r"[0-9a-f]{64}", event["event_sha256"])):
            raise ValueError(f"Invalid exported event order/hash at {order}")
        by_id[event["question_id"]].append(event)
    if len({event["event_sha256"] for event in history}) != 98:
        raise ValueError("Duplicate exported event SHA")
    latest_map = {row["question_id"]: row for row in latest}
    if len(latest_map) != 94 or set(latest_map) != set(by_id):
        raise ValueError("Question IDs do not form the same 94-ID set")
    for qid, row in latest_map.items():
        events = by_id[qid]
        last = events[-1]
        if (int(row["latest_event_index"]) != int(last["event_order"]) or
                int(row["events_for_question"]) != len(events) or
                row["latest_decision"] != last["decision"] or
                row["latest_review_event_sha256"] != last["event_sha256"] or
                last["current_for_id"] != "True" or
                sum(event["current_for_id"] == "True" for event in events) != 1):
            raise ValueError(f"Latest/event-history mismatch: {qid}")

    if digest(handoff_path) != (
            "2392027056f713bc465eaf0bba25461dec813ce7e0b080717018ad90c5f3485b"):
        raise ValueError("Frozen G3T private handoff ZIP changed")
    with zipfile.ZipFile(handoff_path) as archive:
        if archive.testzip() is not None:
            raise ValueError("G3T handoff ZIP CRC failure")
        dataset = json.loads(archive.read("G3T_HUMAN_REVIEW_INPUT_20261103_V2.json"))
        c1 = zip_json_lines(archive,
                            "G3T_C1_PRIVATE_20261103_V7/G3T_C1_94_EVIDENCE_LEDGER.jsonl")
        c2 = zip_json_lines(archive,
                            "G3T_C2_PRIVATE_20261103_V3/G3T_C2_AI_ADJUDICATION_94.jsonl")
    records = {row["question_id"]: row for row in dataset["records"]}
    c1_map = {row["question_id"]: row for row in c1}
    c2_map = {row["question_id"]: row for row in c2}
    if not (len(records) == len(c1_map) == len(c2_map) == 94 and
            set(records) == set(c1_map) == set(c2_map) == set(latest_map)):
        raise ValueError("Exported IDs differ from frozen G3T input/C1/C2")
    for qid, row in latest_map.items():
        record, fact, ai = records[qid], c1_map[qid], c2_map[qid]
        numeric = sum(cell.get("value_decimal") is not None
                      for cell in fact["source_cells"])
        if (row["question"] != record["question"] or
                row["ticker"] != record["ticker"] or
                row["source_url"] != record["source_url"] or
                fact["source_url"] != record["source_url"] or
                fact["accession"] != record["accession"] or
                row["ai_prior_label"] != ai["technical_label"] or
                int(row["c1_numeric_cells"]) != numeric or
                (row["source_url_matches"] == "True") !=
                (by_id[qid][-1]["source_url_matches"] == "True")):
            raise ValueError(f"Export/frozen source or AI mismatch: {qid}")
    if sum(int(row["c1_numeric_cells"]) for row in latest) != 116:
        raise ValueError("Expected 116 frozen C1 numeric cells")
    issue_orders = [int(row["event_order"]) for row in history if row["issue"]]
    if issue_orders != [4, 8, 10, 13]:
        raise ValueError("Historical issue markers differ")
    flags = Counter(row["audit_flag"] for row in latest)
    if flags != {"NO_DETECTED_MIXUP": 89, "CRITICAL_ACTIVE": 3,
                 "POLICY_CONFLICT": 1, "HISTORY_CORRECTED": 1}:
        raise ValueError("Latest issue distribution differs")
    if Counter(row["latest_decision"] for row in latest) != {
            "APPROVE": 85, "REQUEST_CORRECTION": 7,
            "AMBIGUOUS": 1, "EXCLUDE": 1}:
        raise ValueError("Latest decision distribution differs")
    expected_flags = {
        "V7A_G2_11_02": "POLICY_CONFLICT",
        "V7A_G2_12_01": "CRITICAL_ACTIVE",
        "V7A_G2_14_02": "CRITICAL_ACTIVE",
        "V7A_G2_24_01": "HISTORY_CORRECTED",
        "V7A_G2_25_02": "CRITICAL_ACTIVE",
    }
    if {qid: row["audit_flag"] for qid, row in latest_map.items()
            if row["audit_flag"] != "NO_DETECTED_MIXUP"} != expected_flags:
        raise ValueError("Affected question IDs differ")
    if "98/98 PASS" not in memo_path.read_text(encoding="utf-8"):
        raise ValueError("Memo is not the expected double-check report")
    return {
        "schema": "g3u_g3t_double_check_export_intake/v1",
        "input_sha256": {
            "latest_csv": digest(latest_path),
            "history_csv": digest(history_path),
            "memo_md": digest(memo_path),
            "frozen_g3t_zip": digest(handoff_path),
        },
        "verified_from_supplied_exports": {
            "latest_rows": 94, "history_rows": 98,
            "unique_question_ids": 94, "frozen_id_question_source_ai_alignment": "PASS",
            "c1_numeric_cell_count": 116,
            "latest_history_sha_string_alignment": "PASS",
            "latest_decisions": dict(Counter(row["latest_decision"] for row in latest)),
            "audit_flags": dict(flags),
            "four_historical_issue_orders": issue_orders,
            "active_critical_ids": [
                "V7A_G2_12_01", "V7A_G2_14_02", "V7A_G2_25_02"],
            "policy_conflict_id": "V7A_G2_11_02",
            "history_corrected_id": "V7A_G2_24_01",
        },
        "not_independently_verified": [
            "98/98 canonical original-event SHA calculations and previous-event chain",
            "98/98 original evidence SHA matches",
            "complete rationale prose and 112/116 value-presence claim",
            "reviewer identity or authenticity",
            "independent SEC HTML truth for every rationale",
        ],
        "reason": "The original G3T_HUMAN_REVIEW_EVENTS.jsonl is absent; the CSVs contain only exported SHA strings and explanation excerpts.",
        "release_gate": "HUMAN_EVENT_ORIGINAL_REQUIRED; ERRATA_REVIEW_PENDING",
        "new_human_events_written": 0,
        "gold_or_qrel_promotion": "NONE",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("latest_path", "history_path", "memo_path", "handoff_path",
                 "out_path"):
        parser.add_argument("--" + name.replace("_", "-"), type=Path, required=True)
    args = parser.parse_args()
    if args.out_path.exists():
        raise FileExistsError(args.out_path)
    report = audit(args.latest_path, args.history_path, args.memo_path,
                   args.handoff_path)
    args.out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False)
                             + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))

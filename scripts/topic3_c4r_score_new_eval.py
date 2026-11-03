"""Score completed raw method outputs against a private source-first reference.

Run only after the raw output file is closed. This evaluator is never imported
by the retrieval runner or answerer.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import statistics

from scripts.topic3_c4r_run_new_eval import METHODS


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def score(private_reference: Path, public_lock: Path, raw_output: Path,
          split: str, comparison: Path, summary_csv: Path,
          public_summary: Path) -> dict:
    if any(p.exists() for p in (comparison, summary_csv, public_summary)):
        raise FileExistsError("Evaluation score exists; no overwrite")
    lock = json.loads(public_lock.read_text(encoding="utf-8"))
    if sha(private_reference) != lock["private_manifest_sha256"]:
        raise ValueError("Private source-first reference hash changed")
    source_split = "HOLDOUT" if split == "VN_PAIRED" else split
    gold = {f["question_id"]: f for f in json.loads(private_reference.read_text(encoding="utf-8"))["facts"]
            if f["split"] == source_split}
    if len(gold) != (4 if split == "DEV" else 12):
        raise ValueError("Split changed")
    rows = [json.loads(line) for line in raw_output.read_text(encoding="utf-8").splitlines()]
    if len(rows) != len(gold) * len(METHODS):
        raise ValueError("Question×method run row missing")
    keys = [(r["query_id"], r["method"]) for r in rows]
    if len(set(keys)) != len(keys) or set(keys) != {(qid, method) for qid in gold for method in METHODS}:
        raise ValueError("Duplicate or missing method outcomes")
    details = []
    for row in rows:
        g = gold[row["query_id"]]
        candidates = row["candidate_ids_and_ranks"]
        ranks = [hit["rank"] for hit in candidates if hit["accession"] == g["accession"]]
        first_target = min(ranks) if ranks else None
        for track in ("ORIGINAL_CHUNK_ONLY", "SOURCE_ENRICHED_V1"):
            answer = row["answers"].get(track, {})
            answered = answer.get("status") == "VERIFIED_SOURCE_CELL"
            try:
                numeric_match = answered and Decimal(answer["value_decimal"]) == Decimal(g["value_decimal"])
            except (InvalidOperation, KeyError, TypeError):
                numeric_match = False
            period_match = answered and (answer.get("period_end") == g["period_end"] and
                                         answer.get("period_start") == g["period_start"] and
                                         answer.get("duration_type") == g["duration_type"])
            unit_match = answered and answer.get("unit") == g["unit"] and answer.get("currency") == g["currency"]
            scope_match = answered and answer.get("scope") == g["scope"]
            source_match = answered and answer.get("source_sha256") == g["source_sha256"]
            filing_match = answered and answer.get("accession") == g["accession"]
            correct = bool(numeric_match and period_match and unit_match and scope_match and source_match and filing_match)
            error = ("RUN_ERROR" if row["status"] == "ERROR" else
                     "CORRECT" if correct else
                     "WRONG_VALUE_OR_CONTEXT" if answered else
                     answer.get("error_code") or "NO_ANSWER")
            details.append({
                "schema": "c4r_answer_comparison_question_level/v1", "run_id": row["run_id"],
                "method": row["method"], "arm_version": row["method"],
                "query_id": row["query_id"], "query_original": row["query_original"],
                "language": "VI" if split == "VN_PAIRED" else "EN", "track": track, "query_plan": row["query_plan"],
                "candidate_ids_and_ranks": candidates,
                "retrieved_accession": answer.get("accession"),
                "retrieved_original_chunk_ids": [x["chunk_id"] for x in candidates],
                "retrieved_source_locators": [answer.get("source_locator")] if answer.get("source_locator") else [],
                "final_answer_literal": answer.get("final_answer_literal"),
                "answer_value_decimal": answer.get("value_decimal"),
                "answer_unit": answer.get("unit"), "answer_currency": answer.get("currency"),
                "answer_period": [answer.get("period_start"), answer.get("period_end")],
                "answer_scope": answer.get("scope"), "answer_status": answer.get("status", "ERROR"),
                "confidence": answer.get("confidence", 0),
                "gold_value": g["value_decimal"], "gold_unit": g["unit"],
                "gold_period": [g["period_start"], g["period_end"]], "gold_scope": g["scope"],
                "gold_source_sha": g["source_sha256"], "gold_locator": g["source_locator"],
                "gold_accession": g["accession"], "gold_status": g["reference_status"],
                "numerical_match": bool(numeric_match), "period_match": bool(period_match),
                "unit_match": bool(unit_match), "scope_match": bool(scope_match),
                "support_complete": bool(correct), "correct_or_abstain": bool(correct or not answered),
                "correct": correct, "error_code": error,
                "first_target_filing_rank": first_target,
                "hit_at_1": bool(first_target and first_target <= 1),
                "hit_at_5": bool(first_target and first_target <= 5),
                "hit_at_10": bool(first_target and first_target <= 10),
                "latency_ms": row["latency_ms"], "peak_rss_mb": row["rss_mb"],
                "index_id": row["index_id"], "environment_commit": row["environment_commit"],
                "question_gold_version": "C4R_NEW_V1_SOURCE_XBRL_MACHINE_UNREVIEWED",
                "run_timestamp": row["run_timestamp"],
                "source_hashes": [g["source_sha256"]],
            })
    comparison.parent.mkdir(parents=True, exist_ok=True)
    with comparison.open("x", encoding="utf-8", newline="\n") as stream:
        for row in details:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
    groups = defaultdict(list)
    for row in details:
        groups[row["method"], row["track"]].append(row)
    summary = []
    for (method, track), group in sorted(groups.items()):
        n = len(group)
        summary.append({"method": method, "track": track, "questions": n,
                        "hit_at_1": sum(x["hit_at_1"] for x in group),
                        "hit_at_5": sum(x["hit_at_5"] for x in group),
                        "hit_at_10": sum(x["hit_at_10"] for x in group),
                        "correct_answer": sum(x["correct"] for x in group),
                        "wrong_answer": sum(x["answer_status"] == "VERIFIED_SOURCE_CELL" and not x["correct"] for x in group),
                        "abstained": sum(x["answer_status"] == "ABSTAIN" for x in group),
                        "errors": sum(x["error_code"] == "RUN_ERROR" for x in group),
                        "latency_p50_ms": round(statistics.median(x["latency_ms"] for x in group), 3),
                        "latency_p95_ms": round(sorted(x["latency_ms"] for x in group)[int(.95*(n-1))], 3)})
    import csv
    with summary_csv.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(summary[0]))
        writer.writeheader()
        writer.writerows(summary)
    public = {"schema": "c4r_new_eval_scorecard/v1", "split": split,
              "reference": "SOURCE_XBRL_MACHINE_VERIFIED_UNREVIEWED",
              "not_original_chunk_qrels": True, "questions": len(gold),
              "method_rows": len(rows), "comparison_rows": len(details),
              "raw_output_sha256": sha(raw_output), "comparison_sha256": sha(comparison),
              "summary_csv_sha256": sha(summary_csv), "methods": summary}
    public_summary.write_text(json.dumps(public, indent=2) + "\n", encoding="utf-8")
    return public


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("private_reference", "public_lock", "raw_output", "comparison",
                 "summary_csv", "public_summary"):
        p.add_argument("--" + name.replace("_", "-"), type=Path, required=True)
    p.add_argument("--split", choices=("DEV", "HOLDOUT", "VN_PAIRED"), required=True)
    print(json.dumps(score(**vars(p.parse_args())), indent=2))

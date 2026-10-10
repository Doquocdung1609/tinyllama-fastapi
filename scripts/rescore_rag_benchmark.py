"""Merge targeted reruns and deterministically rescore a live RAG benchmark."""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.rag_live_benchmark import element_matches, near_expected, refusal_detected


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--patch", type=Path, action="append", default=[])
    parser.add_argument("--cases", type=Path, default=Path("reports/rag_eval_cases.json"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = read_csv(args.input)
    patches = {row["question_id"]: row for path in args.patch for row in read_csv(path)}
    rows = [patches.get(row["question_id"], row) for row in rows]
    cases = {case["id"]: case for case in json.loads(args.cases.read_text(encoding="utf-8"))}
    for row in rows:
        case = cases[row["question_id"]]; answer = row.get("answer", "")
        matched = [element for element in case["expected_elements"] if element_matches(answer, element)]
        recall = len(matched) / len(case["expected_elements"]) if case["expected_elements"] else 1.0
        refused = refusal_detected(answer)
        row["matched_elements"] = " | ".join(matched)
        row["element_recall"] = str(round(recall, 4))
        row["refused"] = str(refused)
        row["answer_correct"] = str((case["refusal"] and refused) or
                                    (not case["refusal"] and not refused and recall >= .60))
        cited = [int(value) for value in re.findall(r"trang\s+(\d+)", answer, re.I)]
        correct = (bool(cited) and all(near_expected(page, case["pages"]) for page in cited)
                   if case["pages"] else not cited)
        row["cited_pages"] = ",".join(map(str, cited)); row["citation_correct"] = str(correct)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    supported = [row for row in rows if row["expected_refusal"] != "True"]
    expected_refusals = [row for row in rows if row["expected_refusal"] == "True"]
    predicted_refusals = [row for row in rows if row["refused"] == "True"]
    summary = {"cases": len(rows),
        "recall_at_k": sum(row["retrieval_hit"] == "True" for row in rows) / len(rows),
        "mrr": sum(float(row["reciprocal_rank"]) for row in supported) / len(supported),
        "evidence_precision": sum(float(row["evidence_precision"]) for row in rows) / len(rows),
        "evidence_in_prompt_coverage": sum(float(row["evidence_in_prompt"]) for row in rows) / len(rows),
        "answer_correctness": sum(row["answer_correct"] == "True" for row in rows) / len(rows),
        "citation_accuracy_supported": sum(row["citation_correct"] == "True" for row in supported) / len(supported),
        "refusal_recall": sum(row["refused"] == "True" for row in expected_refusals) / max(1, len(expected_refusals)),
        "refusal_precision": sum(row["expected_refusal"] == "True" for row in predicted_refusals) / max(1, len(predicted_refusals)),
        "avg_total_ms": sum(float(row["total_ms"]) for row in rows) / len(rows)}
    args.output.with_suffix(".summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Compare live restored-index rankings with immutable historical P5/P7L rows."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import zipfile
from collections import Counter
from pathlib import Path

from topic3_v5r_restore import REPO, SOURCE


LIVE = REPO / "tmp/topic3_v5r/live"
OUT = REPO / "docs/topic3_v5/recovery_live"


def main() -> None:
    with zipfile.ZipFile(SOURCE) as z:
        historical_p5 = {(r["query_id"], r["method"]): r for r in
                         (json.loads(line) for line in z.read("baseline/p5_query_results.jsonl").splitlines())}
        historical_p7l = {(r["case"], r["method"], r["variant"][0]): r for r in
                           (json.loads(line) for line in z.read("audit/p7l_full_raw_top10.jsonl").splitlines())}
        label_rows = csv.DictReader(io.StringIO(z.read("research/f10_closeout/f10_current_900_rank_checkpoint.csv").decode("utf-8-sig")))
        labels = {}
        for row in label_rows:
            key = (row["case"], row["chunk_id"])
            value = row["final_review_label"]
            if key in labels and labels[key] != value:
                raise ValueError(f"Conflicting label: {key}")
            labels[key] = value
    output = []
    for arm in ("A", "B"):
        for dataset in ("p5", "p7l"):
            path = LIVE / f"{dataset}_{arm}.jsonl"
            if not path.is_file():
                raise ValueError(f"Missing live run: {path}")
            for row in (json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()):
                historical = historical_p5.get((row["id"], row["method"])) if dataset == "p5" and arm == "A" else (
                    historical_p7l.get((row["id"], row["method"], arm)) if dataset == "p7l" else None)
                ids = [r["chunk_id"] for r in row["results"]]
                old = [r["chunk_id"] for r in historical["results"]] if historical else None
                output.append({"dataset": dataset, "index": arm, "id": row["id"], "method": row["method"],
                               "historical_available": old is not None, "exact_top10": ids == old if old is not None else None,
                               "same_top1": ids[:1] == old[:1] if old is not None else None,
                               "target_filing_h1": int(bool(ids and row["target_accession"] in ids[0])) if dataset == "p7l" else None,
                               "target_filing_h10": int(any(row["target_accession"] in x for x in ids)) if dataset == "p7l" else None,
                               "known_positive_h1": int(bool(ids and labels.get((row["id"], ids[0])) == "YES")) if dataset == "p7l" else None,
                               "known_positive_h10": int(any(labels.get((row["id"], x)) == "YES" for x in ids)) if dataset == "p7l" else None,
                               "top1_label": (labels.get((row["id"], ids[0]), "UNJUDGED") if ids else "NO_RESULT") if dataset == "p7l" else "NOT_JUDGED"})
    csv_path = OUT / "historical_reconciliation.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(output[0]))
        writer.writeheader()
        writer.writerows(output)
    summary = {}
    for dataset in ("p5", "p7l"):
        for arm in ("A", "B"):
            subset = [r for r in output if r["dataset"] == dataset and r["index"] == arm]
            summary[f"{dataset}_{arm}"] = {"runs": len(subset), "historical_comparable": sum(r["historical_available"] for r in subset),
                                            "exact_top10": sum(r["exact_top10"] is True for r in subset),
                                            "same_top1": sum(r["same_top1"] is True for r in subset),
                                            "target_filing_h10": sum(r["target_filing_h10"] for r in subset) if dataset == "p7l" else None,
                                            "methods": {m: {"runs": sum(r["method"] == m for r in subset),
                                                            "known_positive_h1": sum(r["known_positive_h1"] for r in subset if r["method"] == m) if dataset == "p7l" else None,
                                                            "known_positive_h10": sum(r["known_positive_h10"] for r in subset if r["method"] == m) if dataset == "p7l" else None}
                                                        for m in sorted({r["method"] for r in subset})}}
    result = {"status": "LIVE_VS_HISTORICAL_RECONCILED", "summary": summary,
              "csv_sha256": hashlib.sha256(csv_path.read_bytes()).hexdigest(),
              "limits": ["Historical P5 is for Index A only", "Index A P3D equivalence to P3C unproven",
                         "F10 labels are exposed/incomplete; known-positive Hit is not independent Recall"]}
    (OUT / "historical_reconciliation.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

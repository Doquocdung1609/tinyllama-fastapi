"""Evaluate post-hoc source-row repair on exposed F10 development labels."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import statistics
import zipfile
from collections import Counter

from topic3_v5r_restore import REPO, SOURCE


def main() -> None:
    old_path = REPO / "tmp/topic3_v5r/live/ablation_B.jsonl"
    new_path = REPO / "tmp/topic3_v5r/live/ablation_B_repair.jsonl"
    with zipfile.ZipFile(SOURCE) as z:
        labels = {(r["case"], r["chunk_id"]): r["final_review_label"] for r in
                  csv.DictReader(io.StringIO(z.read("research/f10_closeout/f10_current_900_rank_checkpoint.csv").decode("utf-8-sig")))}
    old = {r["id"]: r for r in (json.loads(line) for line in old_path.read_text(encoding="utf-8").splitlines()) if r["arm"] == "A4"}
    new = {r["id"]: r for r in (json.loads(line) for line in new_path.read_text(encoding="utf-8").splitlines())}
    if set(old) != set(new) or len(old) != 15:
        raise ValueError("Repair paired cases incomplete")
    cases = []
    for case in sorted(old):
        prev, after = old[case], new[case]
        if set(prev["candidate_pool_ids"]) != set(after["candidate_pool_ids"]):
            raise ValueError(f"Repair candidate set changed: {case}")
        ids_old = [h["chunk_id"] for h in prev["hits"]]
        ids_new = [h["chunk_id"] for h in after["hits"]]
        cases.append({"case": case, "same_candidate_pool": True,
                      "a4_top1": {"id": ids_old[0], "label": labels.get((case, ids_old[0]), "UNJUDGED")},
                      "a4r_top1": {"id": ids_new[0], "label": labels.get((case, ids_new[0]), "UNJUDGED")},
                      "a4r_known_positive_h3": int(any(labels.get((case, x)) == "YES" for x in ids_new[:3])),
                      "a4r_known_positive_h10": int(any(labels.get((case, x)) == "YES" for x in ids_new)),
                      "a4_ms": prev["elapsed_ms"], "a4r_ms": after["elapsed_ms"]})
    result = {"status": "POST_HOC_EXPOSED_DEVELOPMENT_ONLY", "case_count": len(cases),
              "inputs_sha256": {"a4": hashlib.sha256(old_path.read_bytes()).hexdigest(),
                                "a4r": hashlib.sha256(new_path.read_bytes()).hexdigest()},
              "same_candidate_pool_all": True,
              "a4_top1_labels": dict(Counter(c["a4_top1"]["label"] for c in cases)),
              "a4r_top1_labels": dict(Counter(c["a4r_top1"]["label"] for c in cases)),
              "a4r_known_positive_h3": sum(c["a4r_known_positive_h3"] for c in cases),
              "a4r_known_positive_h10": sum(c["a4r_known_positive_h10"] for c in cases),
              "a4_p50_ms": statistics.median(c["a4_ms"] for c in cases),
              "a4r_p50_ms": statistics.median(c["a4r_ms"] for c in cases),
              "cases": cases,
              "qualification": "Repair designed after inspecting exposed failures; no independent superiority or cell accuracy claim"}
    out = REPO / "docs/topic3_v5/recovery_live/posthoc_repair.json"
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k not in ("cases", "inputs_sha256")}, indent=2))


if __name__ == "__main__":
    main()

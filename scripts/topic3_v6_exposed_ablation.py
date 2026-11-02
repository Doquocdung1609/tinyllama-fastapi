"""Counterfactual A4 feature removal on saved exposed development pools."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import sys
import zipfile
from collections import Counter
from pathlib import Path

from topic3_v5r_restore import REPO, SOURCE

sys.path.insert(0, str(REPO))
from app.research_retrieval.faith_r import candidate, parse_query

RAW = REPO / "tmp/topic3_v5r/live/ablation_B.jsonl"
OUT = REPO / "docs/topic3_v6/V6_EXPOSED_FEATURE_ABLATION.json"


def main() -> None:
    with zipfile.ZipFile(SOURCE) as archive:
        labels = {(r["case"], r["chunk_id"]): r["final_review_label"] for r in
                  csv.DictReader(io.StringIO(archive.read("research/f10_closeout/f10_current_900_rank_checkpoint.csv").decode("utf-8-sig")))}
    a3 = {r["id"]: r for r in map(json.loads, RAW.read_text(encoding="utf-8").splitlines()) if r["arm"] == "A3"}
    assert len(a3) == 15
    masks = {
        "A4_FULL": (), "NO_ISSUER_FEATURE": (0,), "NO_FISCAL_FEATURE": (1,),
        "NO_TABLE_ROW_FEATURE": (2,), "NO_METRIC_RELATION_FEATURES": (2, 3, 4),
        "NO_YEAR_IN_BODY_FEATURE": (5,),
    }
    output = {}
    for name, removed in masks.items():
        per_case = []
        for case_id, row in sorted(a3.items()):
            slots = parse_query(row["question"])
            candidates = [candidate(hit, rank, slots) for rank, hit in enumerate(row["hits"], 1)]
            ranked = sorted(candidates, key=lambda item: (
                tuple(-score if index not in removed else 0 for index, score in enumerate(item.ordering())),
                item.original_rank, item.chunk_id))
            ids = [item.chunk_id for item in ranked]
            relevance = [labels.get((case_id, chunk_id), "UNJUDGED") for chunk_id in ids]
            per_case.append({"case": case_id, "ids": ids,
                             "labels": relevance, "top1_label": relevance[0] if relevance else "NO_RESULT"})
        output[name] = {"case_count": len(per_case),
                        "known_positive_h1": sum(r["labels"][0] == "YES" for r in per_case),
                        "known_positive_h3": sum("YES" in r["labels"][:3] for r in per_case),
                        "known_positive_h10": sum("YES" in r["labels"][:10] for r in per_case),
                        "top1_labels": dict(Counter(r["top1_label"] for r in per_case)),
                        "cases": per_case}
    original = {r["id"]: [h["chunk_id"] for h in r["hits"]]
                for r in map(json.loads, RAW.read_text(encoding="utf-8").splitlines()) if r["arm"] == "A4"}
    full = {r["case"]: r["ids"] for r in output["A4_FULL"]["cases"]}
    if full != original:
        raise ValueError("Feature ablation does not reproduce frozen A4")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"status": "EXPOSED_DEVELOPMENT_COUNTERFACTUAL_NO_NEW_SEARCH",
                               "input_sha256": hashlib.sha256(RAW.read_bytes()).hexdigest(),
                               "frozen_a4_reproduced": True, "budget": 10, "variants": output,
                               "unmeasurable_features": {
                                   "COLUMN_YEAR": "A4 only checks year anywhere in chunk body; no column-year feature",
                                   "UNIT": "A4 does not extract or score units"},
                               "qualification": "15 exposed, incompletely judged F10 cases; not independent validation"},
                              indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: {"h1": v["known_positive_h1"], "h3": v["known_positive_h3"]}
                      for k, v in output.items()}))


if __name__ == "__main__":
    main()

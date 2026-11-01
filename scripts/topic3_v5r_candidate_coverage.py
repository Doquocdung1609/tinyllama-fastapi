"""Measure live known-positive candidate bounds at 10/20/50/100 on Index B."""

from __future__ import annotations

import csv
import io
import json
import os
import statistics
import sys
import time
import zipfile
from pathlib import Path

from qdrant_client import QdrantClient

from topic3_v5r_author_live import REPO, SOURCE, WORK, inputs

sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tmp/topic3/original-author/src"))
from app.research_retrieval.faith_r_live import EvidenceSidecar, live_retrieve  # noqa: E402
from hybrid_search.retrieval.engine import SearchEngine  # noqa: E402


OUT = REPO / "docs/topic3_v5/recovery_live/candidate_coverage.json"


def main() -> None:
    os.environ.setdefault("FASTEMBED_CACHE_PATH", str(REPO / "tmp/topic3/model-cache"))
    with zipfile.ZipFile(SOURCE) as z:
        labels = {(r["case"], r["chunk_id"]): r["final_review_label"] for r in
                  csv.DictReader(io.StringIO(z.read("research/f10_closeout/f10_current_900_rank_checkpoint.csv").decode("utf-8-sig")))}
    cases = inputs("p7l")
    client = QdrantClient(path=str(WORK / "B"))
    rows = []
    try:
        engine = SearchEngine(client=client)
        sidecar = EvidenceSidecar(client)
        for case in cases:
            for budget in (10, 20, 50, 100):
                for arm in ("A2", "A3"):
                    start = time.perf_counter()
                    result = live_retrieve(engine, case["question"], arm, budget, sidecar)
                    ids = [h["chunk_id"] for h in result.hits]
                    if len(ids) != len(set(ids)) or len(ids) > budget:
                        raise ValueError("Candidate budget violation")
                    observed = [labels.get((case["id"], cid), "UNJUDGED") for cid in ids]
                    rows.append({"case": case["id"], "arm": arm, "budget": budget, "returned": len(ids),
                                 "elapsed_ms": round((time.perf_counter() - start) * 1000, 3),
                                 "known_positive_hit": int("YES" in observed),
                                 "possible_positive_hit": int(any(x in ("YES", "UNJUDGED") for x in observed)),
                                 "unjudged_count": observed.count("UNJUDGED"), "ids": ids})
                    print(case["id"], arm, budget, len(ids), flush=True)
    finally:
        client.close()
    summary = {}
    for budget in (10, 20, 50, 100):
        for arm in ("A2", "A3"):
            subset = [r for r in rows if r["arm"] == arm and r["budget"] == budget]
            summary[f"{arm}@{budget}"] = {"questions": len(subset),
                                          "known_positive_hit": sum(r["known_positive_hit"] for r in subset),
                                          "possible_positive_hit": sum(r["possible_positive_hit"] for r in subset),
                                          "unjudged_positions": sum(r["unjudged_count"] for r in subset),
                                          "p50_ms": statistics.median(r["elapsed_ms"] for r in subset)}
    result = {"status": "LIVE_EXECUTED_EXPOSED_DEVELOPMENT", "index": "B_P7K_CORRECTED",
              "method": "bm25_dense", "summary": summary, "rows": rows,
              "qualification": "F10 judgments incomplete; Hit bounds only, not Recall. At k=100 prefetch is 100 rather than author's default 50."}
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

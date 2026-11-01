"""Run live A0–A5 arms on restored indexes with a fixed ten-chunk budget."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import statistics
import sys
import time
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import psutil
from qdrant_client import QdrantClient

from topic3_v5r_author_live import REPO, SOURCE, WORK, inputs

sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tmp/topic3/original-author/src"))
from app.research_retrieval.faith_r_live import EvidenceSidecar, live_retrieve  # noqa: E402
from hybrid_search.retrieval.engine import SearchEngine  # noqa: E402


OUT = REPO / "tmp/topic3_v5r/live"
REPORT = REPO / "docs/topic3_v5/recovery_live"


def labels() -> dict:
    with zipfile.ZipFile(SOURCE) as z:
        rows = csv.DictReader(z.read("research/f10_closeout/f10_current_900_rank_checkpoint.csv").decode("utf-8-sig").splitlines())
        lookup = {}
        for row in rows:
            key = (row["case"], row["chunk_id"])
            value = row["final_review_label"]
            if key in lookup and lookup[key] != value:
                raise ValueError(f"Conflicting F10 label: {key}")
            lookup[key] = value
        return lookup


def qdrant_hits(engine, question: str) -> list[dict]:
    return [{"chunk_id": r.chunk_id, "ticker": r.ticker, "fiscal_period": r.fiscal_period,
             "score": r.score, "text": r.text, "source_url": r.source_url,
             "accession_number": r.document_id.split("_", 1)[-1], "rank": r.rank,
             "verification_status": "UNVERIFIED"}
            for r in engine.search(question, method="bm25_dense", k=10)]


def run_arm(index: str, arms: list[str], filename: str | None = None) -> None:
    os.environ.setdefault("FASTEMBED_CACHE_PATH", str(REPO / "tmp/topic3/model-cache"))
    cases = inputs("p7l")
    path = OUT / (filename or f"ablation_{index}.jsonl")
    done = {(r["id"], r["arm"]) for r in (json.loads(line) for line in path.read_text(encoding="utf-8").splitlines())} if path.exists() else set()
    client = QdrantClient(path=str(WORK / index))
    process = psutil.Process()
    try:
        engine = SearchEngine(client=client)
        sidecar = EvidenceSidecar(client) if index == "B" else None
        with path.open("a", encoding="utf-8") as stream:
            for case in cases:
                for arm in arms:
                    if (case["id"], arm) in done:
                        continue
                    start = time.perf_counter()
                    if arm in {"A0", "A1"}:
                        hits = qdrant_hits(engine, case["question"])
                        pool = [h["chunk_id"] for h in hits]
                    else:
                        result = live_retrieve(engine, case["question"], arm, 10, sidecar)
                        hits, pool = result.hits, result.candidate_pool_ids
                    row = {"experiment_id": "V5R_LIVE_ABLATION_10", "run_utc": datetime.now(timezone.utc).isoformat(),
                           "status": "LIVE_EXECUTED", "index": index, "arm": arm, "id": case["id"],
                           "question": case["question"], "target_accession": case["target_accession"],
                           "budget": 10, "elapsed_ms": round((time.perf_counter() - start) * 1000, 3),
                           "process_rss_mib": round(process.memory_info().rss / 1048576, 2),
                           "free_ram_mib": round(psutil.virtual_memory().available / 1048576, 2),
                           "candidate_pool_ids": pool, "hits": hits}
                    stream.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
                    stream.flush()
                    print(index, case["id"], arm, len(hits), row["elapsed_ms"], flush=True)
    finally:
        client.close()


def summarize() -> None:
    judgment = labels()
    rows = [json.loads(line) for index in ("A", "B") for line in (OUT / f"ablation_{index}.jsonl").read_text(encoding="utf-8").splitlines()]
    cases = inputs("p7l")
    if len(rows) != len(cases) * 6:
        raise ValueError(f"Incomplete ablation: {len(rows)}")
    aggregates = {}
    per_case = []
    for arm in ("A0", "A1", "A2", "A3", "A4", "A5"):
        subset = [r for r in rows if r["arm"] == arm]
        stats = {"runs": len(subset), "target_filing_hit": {}, "known_positive_hit": {}, "possible_positive_hit": {},
                 "top1_labels": {}, "p50_ms": statistics.median(r["elapsed_ms"] for r in subset),
                 "p95_ms": sorted(r["elapsed_ms"] for r in subset)[int(.95 * (len(subset) - 1))],
                 "peak_observed_rss_mib": max(r["process_rss_mib"] for r in subset)}
        all_labels = []
        for k in (1, 3, 10):
            stats["target_filing_hit"][str(k)] = sum(any(r["target_accession"] in h["chunk_id"] for h in r["hits"][:k]) for r in subset)
            stats["known_positive_hit"][str(k)] = sum(any(judgment.get((r["id"], h["chunk_id"])) == "YES" for h in r["hits"][:k]) for r in subset)
            stats["possible_positive_hit"][str(k)] = sum(any(judgment.get((r["id"], h["chunk_id"]), "UNJUDGED") in ("YES", "UNJUDGED") for h in r["hits"][:k]) for r in subset)
        for r in subset:
            all_labels.append(judgment.get((r["id"], r["hits"][0]["chunk_id"]), "UNJUDGED") if r["hits"] else "NO_RESULT")
        stats["top1_labels"] = dict(Counter(all_labels))
        aggregates[arm] = stats
    for case in cases:
        arm_rows = {r["arm"]: r for r in rows if r["id"] == case["id"]}
        per_case.append({"id": case["id"], "question": case["question"], "source_url": case["source_url"],
                         "target_accession": case["target_accession"],
                         "arms": {arm: {"ids": [h["chunk_id"] for h in r["hits"]],
                                        "labels": [judgment.get((case["id"], h["chunk_id"]), "UNJUDGED") for h in r["hits"]],
                                        "elapsed_ms": r["elapsed_ms"]}
                                  for arm, r in arm_rows.items()}})
    result = {"status": "EXPOSED_DEVELOPMENT_LIVE_EXECUTED", "index_a": "P3D_RECOVERED_NOT_EXACT_P3C",
              "index_b": "P7K_FISCAL_CORRECTED", "case_count": len(cases), "budget": 10,
              "arms": aggregates, "cases": per_case,
              "raw_sha256": {arm: hashlib.sha256((OUT / f"ablation_{arm}.jsonl").read_bytes()).hexdigest() for arm in ("A", "B")}}
    REPORT.mkdir(parents=True, exist_ok=True)
    (REPORT / "ablation_summary.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(aggregates, indent=2), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--arm", choices=("A", "B", "summary", "repair"), required=True)
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if args.arm == "summary":
        summarize()
    elif args.arm == "repair":
        run_arm("B", ["A4R"], "ablation_B_repair.jsonl")
    else:
        run_arm(args.arm, ["A0"] if args.arm == "A" else ["A1", "A2", "A3", "A4", "A5"])


if __name__ == "__main__":
    main()

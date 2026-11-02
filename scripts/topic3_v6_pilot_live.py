"""Run frozen author/FAITH-R methods on UNJUDGED pilot questions only."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import statistics
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import psutil
from qdrant_client import QdrantClient

from topic3_v5r_restore import REPO, WORK

sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tmp/topic3/original-author/src"))
from app.research_retrieval.faith_r_live import EvidenceSidecar, live_retrieve  # noqa: E402
from hybrid_search.retrieval.engine import SearchEngine  # noqa: E402

QUEUE = REPO / "docs/topic3_v5/recovery_live/holdout_30_review_queue.csv"
RAW = REPO / "tmp/topic3_v6/pilot_raw.jsonl"
COMPACT = REPO / "docs/topic3_v6/V6_PILOT_RANKS_COMPACT.jsonl"
SUMMARY = REPO / "docs/topic3_v6/V6_PILOT_SUMMARY.json"
METHODS = ("bm25", "dense", "sparse", "bm25_dense", "sparse_dense", "rerank", "A2", "A3", "A4", "A4R")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(limit: int) -> None:
    os.environ.setdefault("FASTEMBED_CACHE_PATH", str(REPO / "tmp/topic3/model-cache"))
    questions = list(csv.DictReader(QUEUE.open(encoding="utf-8", newline="")))
    if len(questions) != 30 or any(row["label"] != "UNJUDGED" for row in questions):
        raise ValueError("Pilot question queue mutated or judged")
    if limit:
        questions = questions[:limit]
    RAW.parent.mkdir(parents=True, exist_ok=True)
    completed = {(row["question_id"], row["method"]) for row in
                 (json.loads(line) for line in RAW.read_text(encoding="utf-8").splitlines())} if RAW.exists() else set()
    client = QdrantClient(path=str(WORK / "B"))
    proc = psutil.Process()
    try:
        if client.count("financial_docs", exact=True).count != 8670:
            raise ValueError("Index B point count changed")
        init_start = time.perf_counter()
        engine = SearchEngine(client=client)
        sidecar = EvidenceSidecar(client)
        init_ms = round((time.perf_counter() - init_start) * 1000, 2)
        with RAW.open("a", encoding="utf-8") as stream:
            for case in questions:
                for method in METHODS:
                    if (case["question_id"], method) in completed:
                        continue
                    start = time.perf_counter()
                    if method in ("A2", "A3", "A4", "A4R"):
                        result = live_retrieve(engine, case["question"], method, 10,
                                               sidecar if method != "A2" else None)
                        hits = result.hits
                        pool = result.candidate_pool_ids
                    else:
                        results = engine.search(case["question"], method=method, k=10)
                        hits = [{"rank": r.rank, "chunk_id": r.chunk_id, "score": float(r.score),
                                 "ticker": r.ticker, "fiscal_period": r.fiscal_period,
                                 "source_url": r.source_url, "text": r.text,
                                 "verification_status": "UNVERIFIED"} for r in results]
                        pool = [r["chunk_id"] for r in hits]
                    row = {"status": "PILOT_UNJUDGED_LIVE_EXECUTED", "run_utc": datetime.now(timezone.utc).isoformat(),
                           "question_id": case["question_id"], "question": case["question"],
                           "source_accession_candidate": case["source_accession"],
                           "category": case["category"], "method": method, "index": "B", "budget": 10,
                           "elapsed_ms": round((time.perf_counter() - start) * 1000, 3),
                           "process_rss_mib": round(proc.memory_info().rss / 1048576, 2),
                           "free_ram_mib": round(psutil.virtual_memory().available / 1048576, 2),
                           "candidate_pool_ids": pool, "hits": hits}
                    stream.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
                    stream.flush()
                    print(case["question_id"], method, len(hits), row["elapsed_ms"], flush=True)
    finally:
        client.close()
    (RAW.parent / "pilot_initialization.json").write_text(json.dumps({"initialization_ms": init_ms,
                                                  "index": "B", "method_count": len(METHODS)}) + "\n")


def summarize() -> None:
    questions = list(csv.DictReader(QUEUE.open(encoding="utf-8", newline="")))
    raw = [json.loads(line) for line in RAW.read_text(encoding="utf-8").splitlines()]
    if len(raw) != 30 * len(METHODS) or len({(r["question_id"], r["method"]) for r in raw}) != len(raw):
        raise ValueError(f"Incomplete pilot raw run: {len(raw)}")
    rows = []
    for row in raw:
        rows.append({"question_id": row["question_id"], "method": row["method"],
                     "source_accession_candidate": row["source_accession_candidate"],
                     "category": row["category"], "elapsed_ms": row["elapsed_ms"],
                     "process_rss_mib": row["process_rss_mib"], "free_ram_mib": row["free_ram_mib"],
                     "candidate_pool_ids": row["candidate_pool_ids"],
                     "hits": [{"rank": h["rank"], "chunk_id": h["chunk_id"], "score": h["score"],
                               "source_url": h["source_url"], "fiscal_period": h["fiscal_period"],
                               "text_sha256": hashlib.sha256(h["text"].encode()).hexdigest()}
                              for h in row["hits"]]})
    rows.sort(key=lambda r: (r["question_id"], METHODS.index(r["method"])))
    COMPACT.write_text("\n".join(json.dumps(r, separators=(",", ":")) for r in rows) + "\n", encoding="utf-8")
    stats = {}
    for method in METHODS:
        subset = [r for r in rows if r["method"] == method]
        times = sorted(r["elapsed_ms"] for r in subset)
        source_hits = [r for r in subset if r["category"] != "UNSUPPORTED_FUTURE"]
        stats[method] = {"runs": len(subset), "p50_ms": round(statistics.median(times), 3),
                         "p95_ms": times[int(.95 * (len(times) - 1))],
                         "peak_observed_rss_mib": max(r["process_rss_mib"] for r in subset),
                         "minimum_observed_free_ram_mib": min(r["free_ram_mib"] for r in subset),
                         "candidate_source_accession_h1": sum(bool(r["hits"] and r["source_accession_candidate"] in r["hits"][0]["chunk_id"]) for r in source_hits),
                         "candidate_source_accession_h10": sum(any(r["source_accession_candidate"] in h["chunk_id"] for h in r["hits"]) for r in source_hits),
                         "source_accession_denominator": len(source_hits)}
    SUMMARY.write_text(json.dumps({"status": "EXPLORATORY_PILOT_UNJUDGED_NOT_INDEPENDENT",
                                   "questions": len(questions), "runs": len(rows),
                                   "index": "B_P7K_CORRECTED", "point_count": 8670,
                                   "queue_sha256": hashlib.sha256(QUEUE.read_bytes().replace(b"\r\n", b"\n")).hexdigest(), "raw_sha256": digest(RAW),
                                   "compact_sha256": hashlib.sha256(COMPACT.read_bytes().replace(b"\r\n", b"\n")).hexdigest(), "methods": stats,
                                   "relevance_labels": 0, "numeric_cells_verified": 0,
                                   "qualification": "Source-accession occurrence is not relevant evidence, Recall, or answer correctness; unsupported-future case excluded from accession denominator"},
                                  indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: {"h1": v["candidate_source_accession_h1"],
                          "h10": v["candidate_source_accession_h10"], "p50": v["p50_ms"]}
                      for k, v in stats.items()}))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args()
    if args.summary:
        summarize()
    else:
        run(args.limit)


if __name__ == "__main__":
    main()

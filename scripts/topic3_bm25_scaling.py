"""Reproducible synthetic scaling probe for the query-time Topic 3 BM25 baseline.

This is a performance characterization, not a financial relevance benchmark.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
from statistics import median
from time import perf_counter
import tracemalloc

from app.services.financial_search_service import bm25_rank


def percentile_95(values: list[float]) -> float:
    return sorted(values)[max(0, (95 * len(values) + 99) // 100 - 1)]


def make_corpus(size: int) -> list[dict]:
    terms = (
        "revenue operating cash flow net income assets liabilities equity "
        "fiscal year annual report segment risk liquidity interest rate"
    ).split()
    chunks = []
    for index in range(size):
        body = " ".join(terms[(index + offset) % len(terms)] for offset in range(72))
        if index % 97 == 0:
            body += f" operating cash flow 2024 {1000 + index:,}.5 USD"
        chunks.append({"chunk_id": f"synthetic-{index:07d}", "text": body})
    return chunks


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sizes", nargs="+", type=int, default=[100, 1000, 5000])
    parser.add_argument("--repeats", type=int, default=7)
    parser.add_argument("--output", type=Path,
                        default=Path("reports/topic3_bm25_scaling.csv"))
    args = parser.parse_args()
    if args.repeats < 2 or any(size < 1 for size in args.sizes):
        parser.error("Use at least two repeats and positive corpus sizes")

    rows = []
    for size in args.sizes:
        corpus = make_corpus(size)
        tracemalloc.start()
        timings = []
        hits = []
        for _ in range(args.repeats):
            started = perf_counter()
            hits = bm25_rank("operating cash flow 2024 1,000.5 USD", corpus, 10)
            timings.append((perf_counter() - started) * 1000)
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        warm = timings[1:]
        rows.append({
            "corpus_chunks": size,
            "repeats": args.repeats,
            "cold_ms": round(timings[0], 3),
            "warm_p50_ms": round(median(warm), 3),
            "warm_p95_ms": round(percentile_95(warm), 3),
            "queries_per_second_from_p50": round(1000 / median(warm), 3),
            "peak_tracemalloc_mb": round(peak / 1024 / 1024, 3),
            "returned_hits": len(hits),
            "index_strategy": "query_time_rebuild",
        })
        print(rows[-1], flush=True)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

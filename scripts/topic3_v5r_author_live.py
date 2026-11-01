"""Run pinned author methods against an isolated restored research index."""

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
from datetime import datetime, timezone
from pathlib import Path

import psutil
from qdrant_client import QdrantClient

from topic3_v5r_restore import REPO, SOURCE, WORK

sys.path.insert(0, str(REPO / "tmp/topic3/original-author/src"))
from hybrid_search.models.filter import MetadataFilter  # noqa: E402
from hybrid_search.retrieval.engine import SearchEngine  # noqa: E402


METHODS = ["bm25", "dense", "sparse", "bm25_dense", "sparse_dense", "rerank"]
OUT = REPO / "tmp/topic3_v5r/live"
REPORT = REPO / "docs/topic3_v5/recovery_live"


def inputs(dataset: str) -> list[dict]:
    with zipfile.ZipFile(SOURCE) as z:
        if dataset == "p5":
            seen = {}
            for line in z.read("baseline/p5_query_results.jsonl").splitlines():
                row = json.loads(line)
                seen[row["query_id"]] = {"id": row["query_id"], "question": row["query"], "category": row["category"]}
            return list(seen.values())
        rows = list(csv.DictReader(z.read("audit/p7g_fiscal_metadata_audit.csv").decode("utf-8-sig").splitlines()))
        query_by_ticker = {"AMD": "What was AMD total revenue in fiscal {year}?",
                           "INTC": "What was Intel total revenue in fiscal {year}?",
                           "AMZN": "What was Amazon total revenue in fiscal {year}?",
                           "TSLA": "What was Tesla total revenue in fiscal {year}?",
                           "META": "What was Meta capital expenditure in fiscal {year}?",
                           "GOOGL": "What was Alphabet total revenue in fiscal {year}?"}
        ticker_by_cik = {"0000002488": "AMD", "0000050863": "INTC", "0001018724": "AMZN",
                         "0001318605": "TSLA", "0001326801": "META", "0001652044": "GOOGL"}
        cases = []
        for row in rows:
            if row["audit_status"] != "MISMATCH":
                continue
            ticker = ticker_by_cik[row["filing_id"].split("_")[0]]
            year = row["sec_report_date"][:4]
            cases.append({"id": f"{ticker}_FY{year}", "question": query_by_ticker[ticker].format(year=year),
                          "ticker": ticker, "period": f"FY{year}", "target_accession": row["accession"],
                          "source_url": row["source_url"]})
        return sorted(cases, key=lambda c: c["id"])


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--arm", choices=("A", "B"), required=True)
    parser.add_argument("--dataset", choices=("p5", "p7l"), required=True)
    parser.add_argument("--limit", type=int, default=0, help="Optional smoke-test question count")
    args = parser.parse_args()
    cases = inputs(args.dataset)
    if args.limit:
        cases = cases[:args.limit]
    OUT.mkdir(parents=True, exist_ok=True)
    REPORT.mkdir(parents=True, exist_ok=True)
    stem = f"{args.dataset}_{args.arm}" + (f"_first{args.limit}" if args.limit else "")
    path = OUT / f"{stem}.jsonl"
    completed = {(r["id"], r["method"]) for r in (json.loads(line) for line in path.read_text(encoding="utf-8").splitlines())} if path.exists() else set()
    os.environ.setdefault("FASTEMBED_CACHE_PATH", str(REPO / "tmp/topic3/model-cache"))
    client = QdrantClient(path=str(WORK / args.arm))
    process = psutil.Process()
    try:
        count = client.count("financial_docs", exact=True).count
        if count != 8670:
            raise ValueError(f"Wrong point count: {count}")
        engine = SearchEngine(client=client)
        with path.open("a", encoding="utf-8") as stream:
            for case in cases:
                filters = MetadataFilter(tickers=[case["ticker"]], fiscal_periods=[case["period"]]) if args.dataset == "p7l" else None
                for method in METHODS:
                    if (case["id"], method) in completed:
                        continue
                    started = time.perf_counter()
                    results = engine.search(case["question"], method=method, k=10, filters=filters)
                    elapsed_ms = round((time.perf_counter() - started) * 1000, 3)
                    row = {"experiment_id": "V5R_AUTHOR_LIVE_" + stem.upper(), "status": "LIVE_EXECUTED",
                           "run_utc": datetime.now(timezone.utc).isoformat(), "index": args.arm,
                           "dataset": args.dataset, "id": case["id"], "question": case["question"],
                           "method": method, "author_commit": "16682dd42ca9cd4887ae74935cb3526dce580c49",
                           "query_filters": filters.model_dump() if filters else None,
                           "target_accession": case.get("target_accession"),
                           "elapsed_ms": elapsed_ms, "process_rss_mib": round(process.memory_info().rss / 1048576, 2),
                           "free_ram_mib": round(psutil.virtual_memory().available / 1048576, 2),
                           "results": [r.model_dump() for r in results]}
                    stream.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
                    stream.flush()
                    print(args.arm, args.dataset, case["id"], method, len(results), elapsed_ms, flush=True)
    finally:
        client.close()
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    latencies = [r["elapsed_ms"] for r in rows]
    report = {"status": "LIVE_EXECUTED", "arm": args.arm, "dataset": args.dataset,
              "questions": len(cases), "methods": METHODS, "runs": len(rows),
              "expected_runs": len(cases) * len(METHODS), "index_points": 8670,
              "raw_path": str(path), "raw_sha256": digest(path),
              "p50_ms": statistics.median(latencies), "p95_ms": sorted(latencies)[int(.95 * (len(latencies) - 1))],
              "peak_observed_process_rss_mib": max(r["process_rss_mib"] for r in rows),
              "minimum_observed_free_ram_mib": min(r["free_ram_mib"] for r in rows),
              "limits": ["Elapsed time includes query embedding and Qdrant local search, warm/cold mixed",
                         "P7L filters are ticker+fiscal period; P5 is unfiltered",
                         "Index A recovered from P3D, equivalence to original P3C unproven"]}
    (REPORT / f"{stem}_manifest.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()

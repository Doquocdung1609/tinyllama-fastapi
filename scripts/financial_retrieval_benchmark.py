"""Compare retrieval-only BM25/dense/hybrid/rerank on independent chunk-level qrels."""
from __future__ import annotations
import argparse
import csv
import json
from math import log2
from pathlib import Path
from statistics import mean, median
from time import perf_counter
import requests

METHODS = ("bm25", "dense", "hybrid", "hybrid_rerank")


def evaluate(retrieved: list[str], relevant: set[str], k: int) -> dict:
    if not relevant:
        raise ValueError("Each case needs at least one independently labeled relevant chunk")
    top = retrieved[:k]
    found = [int(cid in relevant) for cid in top]
    ideal = sum(1 / log2(i + 2) for i in range(min(len(relevant), k)))
    dcg = sum(hit / log2(i + 2) for i, hit in enumerate(found))
    first = next((i + 1 for i, hit in enumerate(found) if hit), None)
    return {"recall": sum(found) / len(relevant),
            "mrr": 1 / first if first else 0.,
            "ndcg": dcg / ideal if ideal else 0.}


def _p95(values: list[float]) -> float:
    return sorted(values)[max(0, (95 * len(values) + 99) // 100 - 1)]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--api", default="http://127.0.0.1:8000")
    parser.add_argument("--output", type=Path, default=Path("reports/financial_retrieval_benchmark"))
    parser.add_argument("--methods", nargs="+", choices=METHODS, default=list(METHODS[:3]))
    parser.add_argument("--k", type=int, default=5)
    args = parser.parse_args()
    if not 1 <= args.k <= 20:
        parser.error("--k must be between 1 and 20")
    cases = json.loads(args.cases.read_text(encoding="utf-8"))
    if not isinstance(cases, list) or not cases:
        parser.error("Cases must contain a nonempty JSON array")
    for c in cases:
        if not c.get("id") or not c.get("query") or not c.get("document_ids") or not c.get("relevant_chunk_ids"):
            parser.error("Cases need id, query, document_ids and independently labeled relevant_chunk_ids")
    rows = []
    for method in args.methods:
        for c in cases:
            payload = {"query": c["query"], "document_ids": c["document_ids"],
                       "method": method, "top_k": args.k, "candidate_limit": max(40, args.k)}
            for field in ("ticker", "fiscal_year", "form_type"):
                if field in c:
                    payload[field] = c[field]
            start = perf_counter()
            response = requests.post(args.api.rstrip("/") + "/financial/search",
                                     json=payload, timeout=180)
            response.raise_for_status()
            data = response.json()
            ids = [r["chunk_id"] for r in data["results"]]
            gold = set(c["relevant_chunk_ids"])
            metrics = evaluate(ids, gold, args.k)
            rows.append({"case_id": c["id"], "method": method, "k": args.k,
                         "recall": metrics["recall"], "mrr": metrics["mrr"],
                         "ndcg": metrics["ndcg"],
                         "latency_ms": round((perf_counter() - start) * 1000, 1),
                         "retrieved_chunk_ids": "|".join(ids),
                         "relevant_chunk_ids": "|".join(sorted(gold))})
            print(method, c["id"], metrics, flush=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.with_suffix(".csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader(); writer.writerows(rows)
    summary = {}
    for method in args.methods:
        group = [r for r in rows if r["method"] == method]
        summary[method] = {"n": len(group),
                           "recall_at_k": mean(r["recall"] for r in group),
                           "mrr_at_k": mean(r["mrr"] for r in group),
                           "ndcg_at_k": mean(r["ndcg"] for r in group),
                           "median_latency_ms": median(r["latency_ms"] for r in group),
                           "p95_latency_ms": _p95([r["latency_ms"] for r in group])}
    args.output.with_suffix(".json").write_text(
        json.dumps({"k": args.k, "results": summary}, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

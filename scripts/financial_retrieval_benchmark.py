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
            "precision": sum(found) / k,
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
    parser.add_argument("--k", type=int, default=None,
                        help="Backward-compatible single cutoff; overrides --ks")
    parser.add_argument("--ks", nargs="+", type=int, default=[1, 3, 5, 10])
    args = parser.parse_args()
    ks = [args.k] if args.k is not None else sorted(set(args.ks))
    if not ks or any(not 1 <= k <= 20 for k in ks):
        parser.error("Every cutoff must be between 1 and 20")
    cases = json.loads(args.cases.read_text(encoding="utf-8"))
    if not isinstance(cases, list) or not cases:
        parser.error("Cases must contain a nonempty JSON array")
    for c in cases:
        if not c.get("id") or not c.get("query") or not c.get("document_ids") or not c.get("relevant_chunk_ids"):
            parser.error("Cases need id, query, document_ids and independently labeled relevant_chunk_ids")
    rows = []
    requests_run = []
    snapshots: dict[str, str] = {}
    max_k = max(ks)
    # Rotate method order by case so cold-cache effects are not assigned to the
    # same method for every question.
    for case_index, c in enumerate(cases):
        offset = case_index % len(args.methods)
        ordered_methods = args.methods[offset:] + args.methods[:offset]
        for method in ordered_methods:
            payload = {"query": c["query"], "document_ids": c["document_ids"],
                       "method": method, "top_k": max_k, "candidate_limit": max(40, max_k)}
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
            latency_ms = round((perf_counter() - start) * 1000, 1)
            snapshot = data.get("corpus_snapshot_sha256")
            if not snapshot:
                raise RuntimeError("Search response omitted corpus_snapshot_sha256")
            prior = snapshots.setdefault(c["id"], snapshot)
            if prior != snapshot:
                raise RuntimeError(f"Corpus snapshot changed across methods for {c['id']}")
            timings = data.get("timings_ms", {})
            requests_run.append({"case_id": c["id"], "method": method,
                                 "latency_ms": latency_ms})
            for k in ks:
                metrics = evaluate(ids, gold, k)
                rows.append({"case_id": c["id"], "method": method, "k": k,
                             "recall": metrics["recall"],
                             "precision": metrics["precision"],
                             "mrr": metrics["mrr"], "ndcg": metrics["ndcg"],
                             "latency_ms": latency_ms,
                             "server_total_ms": timings.get("total"),
                             "corpus_prepare_ms": timings.get("corpus_prepare"),
                             "embedding_ms": timings.get("embedding"),
                             "dense_search_ms": timings.get("dense"),
                             "lexical_ms": timings.get("lexical"),
                             "fusion_ms": timings.get("fusion"),
                             "reranker_load_ms": timings.get("reranker_load"),
                             "rerank_ms": timings.get("cross_encoder"),
                             "corpus_snapshot_sha256": snapshot,
                             "retrieved_chunk_ids": "|".join(ids),
                             "relevant_chunk_ids": "|".join(sorted(gold))})
                print(method, c["id"], f"k={k}", metrics, flush=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.with_suffix(".csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader(); writer.writerows(rows)
    summary = {}
    for method in args.methods:
        method_requests = [r for r in requests_run if r["method"] == method]
        total_latency_ms = sum(r["latency_ms"] for r in method_requests)
        method_summary = {"queries": len(method_requests),
                          "median_latency_ms": median(r["latency_ms"] for r in method_requests),
                          "p95_latency_ms": _p95([r["latency_ms"] for r in method_requests]),
                          "queries_per_second_sequential": round(
                              len(method_requests) * 1000 / max(total_latency_ms, .001), 4)}
        for k in ks:
            group = [r for r in rows if r["method"] == method and r["k"] == k]
            method_summary[f"at_{k}"] = {
                "recall": mean(r["recall"] for r in group),
                "precision": mean(r["precision"] for r in group),
                "mrr": mean(r["mrr"] for r in group),
                "ndcg": mean(r["ndcg"] for r in group),
            }
        summary[method] = method_summary
    args.output.with_suffix(".json").write_text(
        json.dumps({"ks": ks, "corpus_snapshots": snapshots,
                    "results": summary}, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

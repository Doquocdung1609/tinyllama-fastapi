"""Evaluate a frozen persistent-index split without changing its judgments."""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from math import log2
from pathlib import Path
from random import Random
from statistics import mean
from time import perf_counter

from app.financial_index.service import FinancialIndex


FROZEN_QUERY_SHA256 = "c8aedd619f362208fcb097c197f351b117aaa7e2c3bfd758ef97c56df842792a"
METRICS = ("recall", "precision", "mrr", "ndcg")


def score(ids: list[str], relevant: set[str], k: int) -> dict[str, float]:
    hits = [int(cid in relevant) for cid in ids[:k]]
    first = next((rank for rank, hit in enumerate(hits, 1) if hit), None)
    ideal = sum(1 / log2(rank + 1) for rank in range(1, min(k, len(relevant)) + 1))
    dcg = sum(hit / log2(rank + 1) for rank, hit in enumerate(hits, 1))
    return {
        "recall": sum(hits) / len(relevant),
        "precision": sum(hits) / k,
        "mrr": 1 / first if first else 0.0,
        "ndcg": dcg / ideal if ideal else 0.0,
    }


def bootstrap_ci(values: list[float], seed: int = 20261025, samples: int = 5000) -> list[float]:
    rng = Random(seed)
    n = len(values)
    boot = sorted(mean(values[rng.randrange(n)] for _ in range(n)) for _ in range(samples))
    return [boot[int(samples * .025)], boot[min(samples - 1, int(samples * .975))]]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queries", type=Path, required=True)
    parser.add_argument("--index-root", type=Path, required=True)
    parser.add_argument("--split", choices=("development", "held_out"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-sha256", default=FROZEN_QUERY_SHA256)
    args = parser.parse_args()

    raw = args.queries.read_bytes()
    query_sha = sha256(raw).hexdigest()
    if query_sha != args.expected_sha256:
        raise SystemExit(f"Frozen query hash mismatch: {query_sha}")
    definition = json.loads(raw)
    if definition.get("status") != "FROZEN_UNEVALUATED":
        raise SystemExit("Query set is not the frozen unevaluated definition")
    params = definition["parameters"]
    split = definition["splits"][args.split]
    cases = [case for case in definition["cases"] if case["split"] == args.split]
    if not cases:
        raise SystemExit("Selected split has no cases")

    index = FinancialIndex(args.index_root)
    rows = []
    try:
        record = index.lexical.generation(split["dataset_id"], split["generation"])
        if record["metadata"]["embedding"] != definition["embedding_identity"]:
            raise RuntimeError("Frozen embedding identity differs from the generation")
        actual_manifests = sorted(source["manifest"]["manifest_hash"] for source in record["metadata"]["sources"])
        if actual_manifests != [split["manifest_hash"]]:
            raise RuntimeError("Frozen manifest differs from the generation")
        for case in cases:
            for mode in params["modes"]:
                started = perf_counter()
                response = index.search(
                    split["dataset_id"], case["query"], mode,
                    generation=split["generation"], top_k=10,
                    candidate_limit=params["candidate_limit"], filters=case["filters"],
                    expected_manifests=[split["manifest_hash"]],
                )
                elapsed = (perf_counter() - started) * 1000
                ids = [hit["chunk_id"] for hit in response["results"]]
                relevant = set(case["relevant_chunk_ids"])
                item = {
                    "case_id": case["id"], "categories": case["categories"],
                    "query": case["query"], "filters": case["filters"], "mode": mode,
                    "relevant_chunk_ids": sorted(relevant), "retrieved_chunk_ids": ids,
                    "missing_relevant_at_5": sorted(relevant - set(ids[:5])),
                    "missing_relevant_at_10": sorted(relevant - set(ids[:10])),
                    "at_5": score(ids, relevant, 5), "at_10": score(ids, relevant, 10),
                    "elapsed_ms": elapsed, "timings_ms": response["timings_ms"],
                    "provenance_cache": response["provenance_cache"],
                    "results": [{key: hit.get(key) for key in (
                        "rank", "chunk_id", "bm25_score", "dense_score", "bm25_rank",
                        "dense_rank", "rrf_score", "provenance_status", "text")}
                        for hit in response["results"]],
                }
                if any(hit["provenance_status"] != "VERIFIED" for hit in response["results"]):
                    raise RuntimeError("A returned hit did not pass provenance validation")
                rows.append(item)
                print(case["id"], mode, item["at_5"], flush=True)
    finally:
        index.close()

    summary = {}
    for mode in params["modes"]:
        group = [row for row in rows if row["mode"] == mode]
        summary[mode] = {
            "queries": len(group),
            "at_5": {metric: mean(row["at_5"][metric] for row in group) for metric in METRICS},
            "at_10": {metric: mean(row["at_10"][metric] for row in group) for metric in METRICS},
            "bootstrap_95_ci_at_5": {
                metric: bootstrap_ci([row["at_5"][metric] for row in group]) for metric in METRICS
            },
            "provenance_validity": mean(
                all(hit["provenance_status"] == "VERIFIED" for hit in row["results"]) for row in group),
            "mean_total_ms": mean(row["timings_ms"]["total"] for row in group),
        }
    output = {
        "evaluation_version": "persistent-financial-eval-v1", "split": args.split,
        "query_file": str(args.queries), "query_file_sha256": query_sha,
        "dataset_id": split["dataset_id"], "generation": split["generation"],
        "manifest_hash": split["manifest_hash"], "embedding_identity": definition["embedding_identity"],
        "parameters": params, "summary": summary, "per_query": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Source-judged pilot comparison; timing, embeddings and provenance stay separate."""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
from statistics import mean, median
import sys
from time import perf_counter
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import psutil
import requests
from app.financial_index.lexical import LexicalIndex, financial_tokens
from app.financial_index.corpus import verified_source
from app.services import financial_search_service as legacy
from scripts.financial_retrieval_benchmark import evaluate
from scripts.topic3_bm25_scaling import make_corpus


def statistics(values):
    ordered = sorted(values)
    return {"p50_ms": median(ordered), "p95_ms": ordered[max(0, (95 * len(ordered) + 99) // 100 - 1)],
            "sequential_qps": len(ordered) * 1000 / sum(ordered) if sum(ordered) > 0 else None,
            "samples": len(ordered)}


def matched_baseline(query, chunks, limit=40):
    original = legacy.tokenize
    legacy.tokenize = financial_tokens
    try:
        return legacy.bm25_rank(query, chunks, limit)
    finally:
        legacy.tokenize = original


def microbenchmark(chunks, output: Path, name: str):
    root = output / (name + "-" + uuid4().hex)
    index = LexicalIndex(root / "lexical.sqlite3")
    generation = sha256(name.encode()).hexdigest()
    index.start(name, generation, {"component_benchmark_only": True})
    started = perf_counter()
    for begin in range(0, len(chunks), 100):
        batch = [{"chunk": {**chunk, "filing_id": chunk.get("filing_id", "synthetic"),
                              "metadata": chunk.get("metadata", {})}, "source": {"benchmark": name}}
                 for chunk in chunks[begin:begin + 100]]
        index.add(generation, batch)
    index.seal(generation)
    index.publish(name, generation)
    build_ms = (perf_counter() - started) * 1000
    record = index.generation(name)
    query = "operating cash flow 2024 1,000.5 USD" if name.startswith("synthetic") else "net sales cash flow 2026"
    timings = {key: [] for key in ("original_baseline", "matched_baseline", "persistent_bm25")}
    for _ in range(5):
        for mode, function in (("original_baseline", lambda: legacy.bm25_rank(query, chunks, 10)),
                               ("matched_baseline", lambda: matched_baseline(query, chunks, 10)),
                               ("persistent_bm25", lambda: index.search(query, record, 10, {}))):
            started = perf_counter()
            function()
            timings[mode].append((perf_counter() - started) * 1000)
    return {"chunks": len(chunks), "scope": "lexical-component only, no dense index or provenance latency",
            "index_build_ms": build_ms, "index_disk_bytes": sum(p.stat().st_size for p in root.rglob("*") if p.is_file()),
            "cold_query_ms": {mode: values[0] for mode, values in timings.items()},
            "warm": {mode: statistics(values[1:]) for mode, values in timings.items()}}


def run(api: str, index_root: Path, query_path: Path, output: Path, repeats: int, server_pid=None):
    query_bytes = query_path.read_bytes()
    suite = json.loads(query_bytes)
    index = LexicalIndex(index_root / "lexical.sqlite3")
    record = index.generation(suite["dataset_id"], suite["generation"])
    records = {item["chunk"]["chunk_id"]: item for item in index.records(record["generation"])}
    chunks = [item["chunk"] for item in records.values()]
    manifests = sorted(item["manifest"]["manifest_hash"] for item in record["metadata"]["sources"])
    results, source_cache = [], {}
    query_timings = {mode: [] for mode in ("original_baseline", "matched_baseline", "bm25", "dense", "hybrid")}
    end_to_end = {mode: [] for mode in ("bm25", "dense", "hybrid")}
    embedding_times = {mode: [] for mode in ("bm25", "dense", "hybrid")}
    provenance_times = {mode: [] for mode in ("bm25", "dense", "hybrid")}
    cold = {}
    for case_index, case in enumerate(suite["cases"]):
        eligible = [chunk for chunk in chunks if legacy._matches_metadata(chunk, case["filters"])]
        truth = set(case["relevant_chunk_ids"])
        assert truth and truth <= {chunk["chunk_id"] for chunk in eligible}
        local_hits = {}
        for mode, function in (("original_baseline", legacy.bm25_rank), ("matched_baseline", matched_baseline)):
            samples = []
            for _ in range(repeats):
                started = perf_counter()
                hits = function(case["query"], eligible, 40)
                samples.append((perf_counter() - started) * 1000)
            local_hits[mode] = [hit["chunk_id"] for hit in hits[:5]]
            query_timings[mode].extend(samples)
            verified = 0
            for cid in local_hits[mode]:
                source = records[cid]["source"]
                key = source["structured_path"]
                if key not in source_cache:
                    source_cache[key] = verified_source(source)
                assert source_cache[key][cid].model_dump(mode="json") == records[cid]["chunk"]
                verified += 1
            results.append({"case": case["id"], "mode": mode, "metrics_at_5": evaluate(local_hits[mode], truth, 5),
                            "ids": local_hits[mode], "provenance_verified": verified,
                            "returned": len(local_hits[mode]), "lexical_samples_ms": samples})
        # Rotate channel order across cases; exclude each mode's first request from warm timing.
        modes = ["bm25", "dense", "hybrid"]
        offset = case_index % 3
        for mode in modes[offset:] + modes[:offset]:
            for repeat in range(repeats):
                payload = {"dataset_id": suite["dataset_id"], "generation": record["generation"],
                           "expected_manifests": manifests, "query": case["query"], "mode": mode,
                           "top_k": 5, "candidate_limit": 40, **case["filters"]}
                started = perf_counter()
                response = requests.post(api.rstrip("/") + "/financial-index/search", json=payload, timeout=180)
                response.raise_for_status()
                data = response.json()
                elapsed = (perf_counter() - started) * 1000
                assert data["generation"] == record["generation"] and data["manifests"] == manifests
                ids = [item["chunk_id"] for item in data["results"]]
                assert len(ids) == len(set(ids))
                assert all(item["provenance_status"] == "VERIFIED" for item in data["results"])
                if mode == "bm25":
                    assert ids == local_hits["matched_baseline"], "Persistent BM25 changed formula-matched ranking"
                if mode not in cold:
                    cold[mode] = {"http_ms": elapsed, "timings_ms": data["timings_ms"]}
                else:
                    query_timings[mode].append(data["timings_ms"]["retrieval_without_embedding_or_provenance"])
                    end_to_end[mode].append(elapsed)
                    embedding_times[mode].append(data["timings_ms"]["embedding"])
                    provenance_times[mode].append(data["timings_ms"]["provenance"])
                if repeat == 0:
                    results.append({"case": case["id"], "mode": mode, "metrics_at_5": evaluate(ids, truth, 5),
                                    "ids": ids, "provenance_verified": len(ids), "returned": len(ids),
                                    "http_ms": elapsed, "timings_ms": data["timings_ms"]})
        print("Judged", case["id"], flush=True)
    quality = {}
    for mode in query_timings:
        group = [item for item in results if item["mode"] == mode]
        quality[mode] = {key: mean(item["metrics_at_5"][key] for item in group) for key in ("recall", "mrr", "ndcg", "precision")}
        quality[mode]["provenance_validity"] = sum(item["provenance_verified"] for item in group) / max(1, sum(item["returned"] for item in group))
    synthetic = [microbenchmark(make_corpus(size), output, "synthetic-" + str(size)) for size in (100, 1000, 5000)]
    real = [microbenchmark(chunks[:size], output, "real-" + str(size)) for size in (100, 400, len(chunks))]
    memory = psutil.Process().memory_info()
    report = {"dataset": suite["dataset_id"], "generation": record["generation"], "manifests": manifests,
              "membership_hash": record["membership_hash"], "query_file_sha256": sha256(query_bytes).hexdigest(),
              "chunks": len(chunks), "queries": len(suite["cases"]), "repeats": repeats,
              "quality_at_5": quality, "cold_api_requests": cold,
              "warm_retrieval_without_embedding_or_provenance": {mode: statistics(values) for mode, values in query_timings.items()},
              "warm_http_end_to_end": {mode: statistics(values) for mode, values in end_to_end.items()},
              "warm_embedding": {mode: statistics(values) for mode, values in embedding_times.items()},
              "warm_provenance": {mode: statistics(values) for mode, values in provenance_times.items()},
              "synthetic_lexical_scaling": synthetic, "real_lexical_scaling": real,
              "retained_index_total_disk_bytes": sum(p.stat().st_size for p in index_root.rglob("*") if p.is_file()),
              "benchmark_process_peak_rss_mb": getattr(memory, "peak_wset", memory.rss) / 2**20,
              "memory_scope": "One benchmark process shared across modes, including baseline corpus and source checks. Not a per-mode or Ollama-runtime peak.",
              "limitations": ["14 development queries, source-row targets, incomplete semantic judgments and shared facts; not held-out evaluation.",
                              "API retrieval excludes measured embedding/provenance times; HTTP totals include both. Baselines are local lexical scoring functions.",
                              "Lexical scaling uses real selected subsets; dense scaling beyond the 822-chunk pilot is NOT_MEASURED."],
              "requests": results}
    if server_pid:
        server_memory = psutil.Process(server_pid).memory_info()
        report["api_process_peak_rss_mb"] = getattr(server_memory, "peak_wset", server_memory.rss) / 2**20
        report["api_memory_scope"] = "Shared API process lifetime peak, not per-mode and excludes external Ollama RAM/VRAM."
    output.mkdir(parents=True, exist_ok=True)
    (output / "benchmark.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", default="http://127.0.0.1:8000")
    parser.add_argument("--index-root", type=Path, default=Path("financial_search_data"))
    parser.add_argument("--queries", type=Path, default=Path("docs/topic3/MILESTONE_C_QUERIES.json"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--server-pid", type=int)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    result = run(args.api, args.index_root, args.queries, args.output, args.repeats, args.server_pid)
    print(json.dumps(result["quality_at_5"], ensure_ascii=True, indent=2))

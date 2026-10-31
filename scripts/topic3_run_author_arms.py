"""Run six real Qdrant author-style retrieval arms plus deterministic stage 2.

The corpus and qrels are provisional. All arms share one immutable 121-point
index and identical questions/top-k. Embedding time is measured separately.
"""

from __future__ import annotations

import hashlib
import json
import statistics
import time
from pathlib import Path

from qdrant_client import QdrantClient, models
from hybrid_search.retrieval.base import BaseRetriever
from hybrid_search.retrieval.reranker import NeuralReranker


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs/topic3/01_REPRODUCTION"
WORK = ROOT / "tmp/topic3/replication"
COLLECTION = "topic3_author_methods_2sec_2026"
ARM_MAP = {
    "R0_BM25": ["bm25"], "R1_DENSE": ["dense"], "R2_SPLADE": ["splade"],
    "R3_BM25_DENSE_RRF": ["bm25", "dense"],
    "R4_SPLADE_DENSE_RRF": ["splade", "dense"],
    "R5_THREE_WAY_RRF": ["bm25", "dense", "splade"],
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    manifest = json.loads((DATA / "INDEX_MANIFEST.json").read_text(encoding="utf-8"))
    if manifest["status"] != "PASS_THREE_VECTOR_ISOLATED_INDEX" or manifest["collection"] != COLLECTION:
        raise SystemExit("INDEX_MANIFEST_MISMATCH")
    qrels_path = DATA / "PROVISIONAL_SOURCE_QRELS.jsonl"
    qrels = [json.loads(line) for line in qrels_path.read_text(encoding="utf-8").splitlines()]
    vectors = {}
    query_manifests = {}
    for arm in ["bm25", "dense", "splade"]:
        m = json.loads((WORK / f"{arm}_query_manifest.json").read_text(encoding="utf-8"))
        p = WORK / f"{arm}_query_vectors.jsonl"
        if m["status"] != "PASS" or m["qrels_sha256"] != sha(qrels_path) or m["query_vectors_sha256"] != sha(p):
            raise SystemExit(f"QUERY_VECTOR_LOCK_CHANGED_{arm}")
        vectors[arm] = {r["id"]: r for r in map(json.loads, p.read_text(encoding="utf-8").splitlines())}
        query_manifests[arm] = m
    if any(set(v) != {q["id"] for q in qrels} for v in vectors.values()):
        raise SystemExit("QUERY_ID_MISMATCH")
    out = DATA / "RETRIEVAL_RESULTS.json"
    if out.exists():
        raise SystemExit("EXISTING_BENCHMARK_REFUSED")
    client = QdrantClient(path=str(WORK / "qdrant"))
    try:
        if client.get_collection(COLLECTION).points_count != manifest["points"]:
            raise SystemExit("QDRANT_INDEX_COUNT_CHANGED")
        results = []
        for q in qrels:
            qid = q["id"]
            arm_hits = {}
            for arm, spaces in ARM_MAP.items():
                prepared = {}
                for space in spaces:
                    v = vectors[space][qid]
                    prepared[space] = v["vector"] if space == "dense" else models.SparseVector(indices=v["indices"], values=v["values"])
                t = time.perf_counter()
                if len(spaces) == 1:
                    response = client.query_points(collection_name=COLLECTION, query=prepared[spaces[0]], using="sparse" if spaces[0] == "splade" else spaces[0], limit=10)
                else:
                    response = client.query_points(
                        collection_name=COLLECTION,
                        prefetch=[models.Prefetch(query=prepared[s], using="sparse" if s == "splade" else s, limit=50) for s in spaces],
                        query=models.FusionQuery(fusion=models.Fusion.RRF), limit=10,
                    )
                ms = round((time.perf_counter() - t) * 1000, 3)
                arm_hits[arm] = {"query_ms": ms, "results": [
                    {"rank": i, "chunk_id": p.payload["chunk_id"], "ticker": p.payload["ticker"], "section": p.payload["section"], "score": p.score}
                    for i, p in enumerate(response.points, 1)
                ]}

            # Stage 2: the author's deterministic cross-feature reranker on
            # top-20 SPLADE+Dense candidates. It is not a neural model run.
            sv = vectors["splade"][qid]
            dv = vectors["dense"][qid]
            t = time.perf_counter()
            response = client.query_points(
                collection_name=COLLECTION,
                prefetch=[
                    models.Prefetch(query=models.SparseVector(indices=sv["indices"], values=sv["values"]), using="sparse", limit=50),
                    models.Prefetch(query=dv["vector"], using="dense", limit=50),
                ],
                query=models.FusionQuery(fusion=models.Fusion.RRF), limit=20,
            )
            raw_candidates = BaseRetriever._points_to_search_results(None, response.points, "sparse_dense", query=q["query"])
            hits = NeuralReranker().rerank(q["query"], raw_candidates, top_k=10)
            arm_hits["R6_AUTHOR_DETERMINISTIC_STAGE2"] = {
                "query_ms": round((time.perf_counter() - t) * 1000, 3),
                "results": [{"rank": h.rank, "chunk_id": h.chunk_id, "ticker": h.ticker, "section": h.section, "score": h.score, "exact_answer": h.exact_answer[:180]} for h in hits],
            }
            results.append({"id": qid, "query": q["query"], "answerable": q["answerable"], "expected_chunk_ids": q["relevant_chunk_ids"], "arms": arm_hits})
        metrics = {}
        for arm in [*ARM_MAP, "R6_AUTHOR_DETERMINISTIC_STAGE2"]:
            positive = [r for r in results if r["answerable"]]
            counts = {"known_target_at_1": 0, "known_target_at_5": 0, "known_target_at_10": 0, "mrr_at_10_sum": 0.0}
            for r in positive:
                ids = [h["chunk_id"] for h in r["arms"][arm]["results"]]
                targets = set(r["expected_chunk_ids"])
                for k in (1, 5, 10):
                    counts[f"known_target_at_{k}"] += int(bool(targets.intersection(ids[:k])))
                first = next((i for i, cid in enumerate(ids, 1) if cid in targets), None)
                counts["mrr_at_10_sum"] += 1 / first if first else 0.0
            times = [r["arms"][arm]["query_ms"] for r in results]
            metrics[arm] = {
                "known_target_positive_denominator": len(positive),
                "known_target_at_1": counts["known_target_at_1"],
                "known_target_at_5": counts["known_target_at_5"],
                "known_target_at_10": counts["known_target_at_10"],
                "provisional_mrr_at_10": round(counts["mrr_at_10_sum"] / len(positive), 5),
                "negative_queries_unjudged_for_numeric_abstention": len(results) - len(positive),
                "qdrant_query_p50_ms": round(statistics.median(times), 3),
                "qdrant_query_max_ms": max(times),
                "full_latency_includes_embedding": False,
            }
        payload = {
            "status": "PROVISIONAL_UNREVIEWED_METHODOLOGICAL_REPLICATION",
            "corpus_sha256": manifest["corpus_sha256"],
            "qrels_sha256": sha(qrels_path),
            "query_vector_sha256": {k: v["query_vectors_sha256"] for k, v in query_manifests.items()},
            "collection": COLLECTION,
            "corpus_points": manifest["points"],
            "query_count": len(results),
            "metrics": metrics,
            "records": results,
            "warnings": ["Agent-prepared source target IDs are not independent human gold", "Known target count is not exhaustive corpus Recall@k", "Qdrant local payload indexes do not exercise server prefilter performance", "R6 source code is deterministic, despite class name", "Query embeddings were generated in separate model processes; latency is separate"],
        }
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": payload["status"], "metrics": metrics}))
    finally:
        client.close()


if __name__ == "__main__":
    main()

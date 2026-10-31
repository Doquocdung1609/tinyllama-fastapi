"""Controlled BM25 comparison using locked structure-aware SEC row chunks.

Same two source filings, model, query vectors and Qdrant sparse scoring as
R0. Only the indexed evidence unit changes from author 500/100 chunks to
source-bound narrative/table chunks. Outputs remain provisional.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import time
from pathlib import Path

import psutil
from fastembed import SparseTextEmbedding
from qdrant_client import QdrantClient, models
from hybrid_search.indexing.qdrant_index import QdrantIndexManager


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs/topic3"
SOURCE = DATA / "03_IMPROVEMENTS/source_chunks"
WORK = ROOT / "tmp/topic3/replication"
COLLECTION = "topic3_structure_bm25_2sec_2026"
EXPECTED = {
    "0000080424.jsonl": "2de4b808c6f33473e7b9a2e0acf041504b7782a3c1bb77deac09522a2b7ab6aa",
    "0000354950.jsonl": "0b6bb51912420a0e45aeb4e2ddb7a5c3d0a5588c4101f5cfa7e74e3573c8bd21",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def indexed_text(text: str, variant: str) -> str:
    if variant == "full":
        return text
    lines = text.splitlines()
    if variant == "row_only":
        return "\n".join(line for line in lines if line.startswith("Row ")) or text
    prefixes = ("Company:", "CIK:") if variant == "no_issuer" else ("Columns:", "Reporting periods:", "Row period/group:")
    return "\n".join(line for line in lines if not line.startswith(prefixes))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", choices=["full", "row_only", "no_issuer", "no_period"], default="full")
    variant = parser.parse_args().variant
    index = WORK / ("structure-qdrant" if variant == "full" else f"structure-qdrant-{variant}")
    if index.exists():
        raise SystemExit("EXISTING_STRUCTURE_INDEX_REFUSED")
    if psutil.virtual_memory().available < 1024**3:
        raise SystemExit("STRUCTURE_INDEX_LOW_MEMORY_DEFERRED")
    qrels_path = DATA / "01_REPRODUCTION/PROVISIONAL_SOURCE_QRELS.jsonl"
    qrels = [json.loads(x) for x in qrels_path.read_text(encoding="utf-8").splitlines()]
    targets_path = DATA / "03_IMPROVEMENTS/STRUCTURE_TARGETS.json"
    targets = json.loads(targets_path.read_text(encoding="utf-8"))["targets"]
    chunks = []
    for name, expected in EXPECTED.items():
        path = SOURCE / name
        if sha(path) != expected:
            raise SystemExit("STRUCTURE_CHUNK_HASH_CHANGED")
        chunks += [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()]
    by_id = {c["chunk_id"]: c for c in chunks}
    if len(by_id) != len(chunks) or set(targets) != {q["id"] for q in qrels if q["answerable"]}:
        raise SystemExit("STRUCTURE_TARGET_ID_MISMATCH")
    for target in targets.values():
        row = by_id[target["chunk_id"]]
        if row["metadata"]["raw_content_hash"] != target["source_sha256"] or target["row_label"].lower() not in row["text"].lower() or target["candidate_value"] not in row["text"]:
            raise SystemExit("STRUCTURE_TARGET_SOURCE_MISMATCH")
    bm25_query_path = WORK / "bm25_query_vectors.jsonl"
    q_manifest = json.loads((WORK / "bm25_query_manifest.json").read_text(encoding="utf-8"))
    if q_manifest["qrels_sha256"] != sha(qrels_path) or q_manifest["query_vectors_sha256"] != sha(bm25_query_path):
        raise SystemExit("BM25_QUERY_LOCK_CHANGED")
    q_vectors = {r["id"]: r for r in map(json.loads, bm25_query_path.read_text(encoding="utf-8").splitlines())}
    if set(q_vectors) != {q["id"] for q in qrels}:
        raise SystemExit("QUERY_SET_CHANGED")
    model = SparseTextEmbedding(model_name="Qdrant/bm25", threads=1)
    client = QdrantClient(path=str(index))
    started = time.perf_counter()
    try:
        client.create_collection(collection_name=COLLECTION, vectors_config={}, sparse_vectors_config={"bm25": models.SparseVectorParams(modifier=models.Modifier.IDF)})
        for offset in range(0, len(chunks), 32):
            batch = chunks[offset:offset + 32]
            vectors = list(model.embed([indexed_text(c["text"], variant) for c in batch], batch_size=16))
            points = []
            for c, v in zip(batch, vectors, strict=True):
                metadata = c["metadata"]
                points.append(models.PointStruct(
                    id=QdrantIndexManager.hash_to_int_id(c["chunk_id"]),
                    vector={"bm25": models.SparseVector(indices=v.indices.tolist(), values=v.values.tolist())},
                    payload={"chunk_id": c["chunk_id"], "filing_id": c["filing_id"], "kind": c["kind"], "text": c["text"], "source_text_hash": c["source_text_hash"], "raw_content_hash": metadata["raw_content_hash"], "statement_title": metadata.get("statement_title"), "row_index": metadata.get("row_index"), "reporting_periods": metadata.get("reporting_periods", []), "source_location": c["source_location"], "extraction_status": c["extraction_status"]},
                ))
            client.upsert(collection_name=COLLECTION, points=points)
        index_s = round(time.perf_counter() - started, 3)
        count = client.get_collection(COLLECTION).points_count
        if count != len(chunks):
            raise ValueError("STRUCTURE_POINT_COUNT_MISMATCH")
        records = []
        for q in qrels:
            v = q_vectors[q["id"]]
            query = models.SparseVector(indices=v["indices"], values=v["values"])
            t = time.perf_counter()
            response = client.query_points(collection_name=COLLECTION, query=query, using="bm25", limit=10)
            ms = round((time.perf_counter() - t) * 1000, 3)
            hits = [{"rank": i, "chunk_id": p.payload["chunk_id"], "filing_id": p.payload["filing_id"], "kind": p.payload["kind"], "score": p.score, "statement_title": p.payload.get("statement_title"), "source_text_hash": p.payload["source_text_hash"]} for i, p in enumerate(response.points, 1)]
            target = targets.get(q["id"], {}).get("chunk_id")
            rank = next((h["rank"] for h in hits if h["chunk_id"] == target), None) if target else None
            records.append({"id": q["id"], "query": q["query"], "answerable": q["answerable"], "target_id": target, "target_rank_top10": rank, "query_ms": ms, "hits": hits})
        positives = [r for r in records if r["answerable"]]
        summary = {f"known_target_at_{k}": sum(r["target_rank_top10"] is not None and r["target_rank_top10"] <= k for r in positives) for k in (1, 5, 10)}
        summary.update({"positive_denominator": len(positives), "query_p50_ms": round(statistics.median(r["query_ms"] for r in records), 3)})
        output = {"status": "PROVISIONAL_EXPOSED_STRUCTURE_BM25", "variant": variant, "source_chunk_sha256": EXPECTED, "structure_targets_sha256": sha(targets_path), "qrels_sha256": sha(qrels_path), "model": "Qdrant/bm25", "index_points": count, "index_s": index_s, "summary": summary, "records": records, "limits": ["Machine-prepared source row targets, not independent human gold", "Different evidence units change corpus cardinality and BM25 IDF; same raw filings/model/query vectors", "PARTIAL_EXTRACTION source documents; numeric certification not attempted"]}
        path = DATA / "03_IMPROVEMENTS" / ("STRUCTURE_BM25_RESULTS.json" if variant == "full" else f"STRUCTURE_BM25_{variant.upper()}_RESULTS.json")
        path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"points": count, "index_s": index_s, "summary": summary}))
    finally:
        client.close()


if __name__ == "__main__":
    main()

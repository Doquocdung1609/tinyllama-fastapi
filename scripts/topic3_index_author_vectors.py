"""Build isolated Qdrant three-vector index from sequential author embeddings.

The point/vector/payload schema follows the pinned author's index manager.
Embedding separately avoids simultaneous BGE and SPLADE model residency.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import psutil
from qdrant_client import QdrantClient, models
from hybrid_search.config import AppConfig
from hybrid_search.indexing.qdrant_index import QdrantIndexManager


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs/topic3/01_REPRODUCTION"
WORK = ROOT / "tmp/topic3/replication"
INDEX = WORK / "qdrant"
COLLECTION = "topic3_author_methods_2sec_2026"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if INDEX.exists():
        raise SystemExit("EXISTING_INDEX_REFUSED")
    corpus = json.loads((DATA / "CORPUS_MANIFEST.json").read_text(encoding="utf-8"))
    chunks_path = DATA / "author_chunks.jsonl"
    if sha(chunks_path) != corpus["chunks_sha256"]:
        raise SystemExit("CORPUS_HASH_CHANGED")
    chunks = [json.loads(line) for line in chunks_path.read_text(encoding="utf-8").splitlines()]
    vectors = {}
    for arm in ["dense", "bm25", "splade"]:
        manifest = json.loads((WORK / f"{arm}_embed_manifest.json").read_text(encoding="utf-8"))
        path = WORK / f"{arm}_vectors.jsonl"
        if manifest["status"] != "PASS" or manifest["corpus_sha256"] != corpus["chunks_sha256"] or sha(path) != manifest["vectors_sha256"]:
            raise SystemExit(f"VECTOR_LOCK_CHANGED_{arm}")
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        vectors[arm] = {row["chunk_id"]: row for row in rows}
    ids = {c["chunk_id"] for c in chunks}
    if any(set(v) != ids for v in vectors.values()):
        raise SystemExit("VECTOR_ID_MISMATCH")
    if psutil.virtual_memory().available < 1024 * 1024**2:
        raise SystemExit("INDEX_LOW_MEMORY_DEFERRED")
    config = AppConfig()
    config.qdrant.collection_name = COLLECTION
    client = QdrantClient(path=str(INDEX))
    start = time.perf_counter()
    try:
        manager = QdrantIndexManager(config=config, client=client)
        manager.create_collection(recreate=False)
        for offset in range(0, len(chunks), 25):
            points = []
            for chunk in chunks[offset:offset + 25]:
                cid = chunk["chunk_id"]
                dense = vectors["dense"][cid]["dense"]
                bm25 = vectors["bm25"][cid]
                splade = vectors["splade"][cid]
                if len(dense) != 384:
                    raise ValueError("DENSE_DIMENSION_MISMATCH")
                point = models.PointStruct(
                    id=manager.hash_to_int_id(cid),
                    vector={
                        "dense": dense,
                        "bm25": models.SparseVector(indices=bm25["indices"], values=bm25["values"]),
                        "sparse": models.SparseVector(indices=splade["indices"], values=splade["values"]),
                    },
                    payload={k: chunk[k] for k in ["chunk_id", "document_id", "company", "ticker", "cik", "document_type", "filing_date", "fiscal_period", "section", "sector", "geography", "text", "text_hash", "chunk_index", "source_url", "accession_number"]},
                )
                points.append(point)
            client.upsert(collection_name=COLLECTION, points=points)
        actual = client.get_collection(COLLECTION).points_count
        if actual != len(chunks):
            raise ValueError("QDRANT_POINT_COUNT_MISMATCH")
        output = {
            "status": "PASS_THREE_VECTOR_ISOLATED_INDEX",
            "collection": COLLECTION,
            "points": actual,
            "corpus_sha256": corpus["chunks_sha256"],
            "vector_sha256": {arm: sha(WORK / f"{arm}_vectors.jsonl") for arm in vectors},
            "elapsed_s": round(time.perf_counter() - start, 3),
            "point_schema": ["dense:384d_cosine", "bm25:sparse_idf", "sparse:splade_idf"],
            "local_qdrant": True,
            "limitation": "Different two-filing corpus, sequential embedding lifecycle and Qdrant local payload-index warning; not exact author benchmark",
        }
        (DATA / "INDEX_MANIFEST.json").write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(output))
    finally:
        client.close()


if __name__ == "__main__":
    main()

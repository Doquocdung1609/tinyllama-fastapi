"""Restartable P11 development BM25/Dense generations in an owned root."""
import argparse
from contextlib import closing
from hashlib import sha256
import json
import math
from pathlib import Path
import shutil
from time import perf_counter
from uuid import NAMESPACE_URL, uuid5

import psutil
import requests
from qdrant_client import QdrantClient, models

from app.financial_index.corpus import verified_source
from app.financial_index.lexical import LexicalIndex
from app.financial_index.ownership import LocalQdrantOwnership, require_supported_embedded_qdrant
from app.financial_index.service import OllamaVectors, valid_vectors
from app.financial_ingestion.schemas import FinancialChunk
from app.table_evidence.identity import digest
from scripts.p11_acquire_official_sec import OWNER, atomic_json, file_hash


MODEL = "nomic-embed-text:latest"
DIGEST = "0a109f422b47e3a30ba2b10eca18548e944e8a23073ee3f3e947efcf3c45e59f"
URL = "http://127.0.0.1:11434"
DATASET = "p11-new-sec-development-v1"
COLLECTION = "topic3_p11_dev_nomic_v1"
DOCS = Path(__file__).resolve().parents[1] / "docs/topic3/milestone_d/recovery/p11"


def point_id(cid):
    return str(uuid5(NAMESPACE_URL, "topic3-p11-dev/" + cid))


def frozen_sources(root):
    root = root.resolve(strict=True)
    marker = json.loads((root / "ownership.json").read_text(encoding="utf-8"))
    if root.name != "t3-p11-new-sec-20261027-v1" or marker.get("owner") != OWNER:
        raise ValueError("P11_OWNED_ROOT_REQUIRED")
    freeze_bytes = (DOCS / "p11_development_freeze.json").read_bytes()
    freeze = json.loads(freeze_bytes)
    for name, expected in freeze["file_sha256"].items():
        if file_hash(DOCS / name) != expected:
            raise ValueError("P11_DEVELOPMENT_FREEZE_CHANGED:" + name)
    manifest_hash = sha256(freeze_bytes).hexdigest()
    acquired = json.loads((DOCS / "p11_source_registry.json").read_text(encoding="utf-8"))
    parsed = json.loads((DOCS / "p11_parsed_sources.json").read_text(encoding="utf-8"))
    records = {r["ticker"]: r for r in acquired["records"]}
    parsed_records = {r["ticker"]: r for r in parsed["records"]}
    source_rows = []
    parents = []
    for ticker in ("MCD", "CAT"):
        item, info = records[ticker], parsed_records[ticker]
        if item["partition"] != "development" or info["partition"] != "development":
            raise ValueError("P11_PARTITION_MISMATCH")
        raw_path = (root / item["relative_path"]).resolve(strict=True)
        structured_path = (root / info["structured_path"]).resolve(strict=True)
        chunks_path = (root / info["chunks_path"]).resolve(strict=True)
        if any(not p.is_relative_to(root) for p in (raw_path, structured_path, chunks_path)):
            raise ValueError("P11_SOURCE_PATH_ESCAPE")
        frozen = {"filing_id": item["metadata"]["filing_id"],
                  "raw_path": str(raw_path), "structured_path": str(structured_path),
                  "chunks_path": str(chunks_path), "raw_hash": item["raw_sha256"],
                  "structured_hash": info["structured_sha256"],
                  "chunks_hash": info["chunks_sha256"],
                  "normalized_hash": json.loads(structured_path.read_text(encoding="utf-8"))
                                        ["metadata"]["normalized_content_hash"],
                  "manifest_hash": manifest_hash, "source_dataset_id": DATASET}
        canonical = verified_source(frozen)
        with chunks_path.open(encoding="utf-8") as stream:
            listed = [FinancialChunk.model_validate_json(line) for line in stream]
        if (len(listed) != info["parent_count"] or len(canonical) != len(listed)
            or {c.chunk_id for c in listed} != set(canonical)):
            raise ValueError("P11_CANONICAL_SOURCE_MEMBERSHIP_MISMATCH")
        for chunk in listed:
            if (chunk.model_dump(mode="json") != canonical[chunk.chunk_id].model_dump(mode="json")
                or chunk.metadata["cik"] != item["cik"]
                or chunk.filing_id != item["metadata"]["filing_id"]):
                raise ValueError("P11_CANONICAL_PARENT_CONTEXT_MISMATCH")
            parents.append({"cid": chunk.chunk_id, "chunk": chunk, "frozen": frozen,
                            "payload_hash": digest(chunk.model_dump(mode="json"))})
        source_rows.append({"ticker": ticker, "cik": item["cik"],
                            "accession": item["metadata"]["accession_number"],
                            "raw_sha256": item["raw_sha256"],
                            "parent_count": len(listed),
                            "membership_sha256": info["membership_sha256"],
                            "extraction_status": info["document_status"]})
    parents.sort(key=lambda r: r["cid"])
    if len({r["cid"] for r in parents}) != len(parents):
        raise ValueError("P11_CROSS_SOURCE_PARENT_COLLISION")
    membership = sha256(json.dumps([(r["cid"], r["payload_hash"],
                                    r["frozen"]["raw_hash"]) for r in parents],
                                   separators=(",", ":")).encode()).hexdigest()
    generation = sha256((DATASET + manifest_hash + membership).encode()).hexdigest()
    return parents, source_rows, manifest_hash, membership, generation


def lexical_ready(index, parents, sources, manifest_hash, membership, generation):
    try:
        prior = index.generation(DATASET, generation)
    except ValueError as exc:
        if str(exc) != "INDEX_GENERATION_NOT_FOUND":
            raise
        prior = None
    if prior is None or prior["state"] != "READY":
        index.start(DATASET, generation, {"manifest_hash": manifest_hash,
                                         "membership_hash": membership,
                                         "sources": sources, "research_only": True})
        for start in range(0, len(parents), 64):
            index.add(generation, [{"chunk": row["chunk"].model_dump(mode="json"),
                                    "source": row["frozen"]}
                                   for row in parents[start:start + 64]])
        if index.seal(generation) != len(parents):
            raise ValueError("P11_LEXICAL_PARENT_COUNT_MISMATCH")
        index.publish(DATASET, generation)
    record = index.generation(DATASET, generation)
    if record["state"] != "READY" or record["n"] != len(parents):
        raise ValueError("P11_LEXICAL_GENERATION_NOT_READY")
    with closing(index.connect()) as db:
        rows = db.execute("SELECT d.cid,d.payload_hash,m.source FROM documents d JOIN members m "
                          "ON m.cid=d.cid WHERE m.generation=? ORDER BY d.cid", (generation,)).fetchall()
    if len(rows) != len(parents):
        raise ValueError("P11_LEXICAL_MEMBERSHIP_INCOMPLETE")
    for row, expected in zip(rows, parents):
        if (row["cid"] != expected["cid"] or row["payload_hash"] != expected["payload_hash"]
            or json.loads(row["source"]) != expected["frozen"]):
            raise ValueError("P11_LEXICAL_SOURCE_IDENTITY_MISMATCH")
    return record


def scan_points(client):
    found = {}
    offset = None
    while True:
        rows, offset = client.scroll(COLLECTION, limit=128, offset=offset,
                                     with_payload=True, with_vectors=False)
        for row in rows:
            cid = row.payload.get("chunk_id")
            if cid in found:
                raise ValueError("P11_DUPLICATE_VECTOR_PARENT")
            found[cid] = row
        if offset is None:
            return found


def build(root, batch_size, max_batches):
    root = root.resolve(strict=True)
    if not 1 <= batch_size <= 4:
        raise ValueError("P11_BATCH_SIZE_OUT_OF_BOUNDS")
    require_supported_embedded_qdrant()
    parents, sources, manifest_hash, membership, generation = frozen_sources(root)
    folder = root / "index_dev"
    folder.mkdir(exist_ok=True)
    identity = {"schema_version": "topic3-p11-dev-generation/v1",
                "dataset_id": DATASET, "generation": generation,
                "manifest_hash": manifest_hash, "parent_membership_sha256": membership,
                "source_selection_commit": "d04fd4b53c104cbc5208ff33bcf876ae7bcbc03e",
                "label_freeze_commit": "5377534170523a1872f0bcf17b72d69bfc595859",
                "sources": sources, "parent_count": len(parents),
                "model": MODEL, "model_digest": DIGEST,
                "dimension": 768, "document_prefix": OllamaVectors.document_prefix,
                "query_prefix": OllamaVectors.query_prefix,
                "truncation_content_chars": 6000, "distance": "COSINE",
                "collection": COLLECTION, "batch_limit": 4}
    identity_path = folder / "identity.json"
    if identity_path.exists():
        if json.loads(identity_path.read_text(encoding="utf-8")) != identity:
            raise ValueError("P11_INDEX_IDENTITY_CHANGED")
    else:
        atomic_json(identity_path, identity)
    lexical = LexicalIndex(folder / "lexical.sqlite3")
    lexical_record = lexical_ready(lexical, parents, sources, manifest_hash,
                                   membership, generation)
    with requests.Session() as session:
        tags = session.get(URL + "/api/tags", timeout=5)
        tags.raise_for_status()
        live = next((r for r in tags.json().get("models", [])
                     if r.get("name") == MODEL), None)
        if live is None or live.get("digest") != DIGEST:
            raise ValueError("P11_LIVE_MODEL_IDENTITY_MISMATCH")
        owner = LocalQdrantOwnership(folder / "qdrant")
        try:
            client = QdrantClient(path=str(folder / "qdrant"))
            try:
                if not client.collection_exists(COLLECTION):
                    client.create_collection(COLLECTION,
                        vectors_config=models.VectorParams(size=768,
                                                           distance=models.Distance.COSINE))
                params = client.get_collection(COLLECTION).config.params.vectors
                if params.size != 768 or params.distance != models.Distance.COSINE:
                    raise ValueError("P11_VECTOR_CONFIGURATION_MISMATCH")
                expected = {row["cid"]: row for row in parents}
                present = scan_points(client)
                for cid, point in present.items():
                    row = expected.get(cid)
                    if (row is None or str(point.id) != point_id(cid)
                        or point.payload.get("payload_hash") != row["payload_hash"]
                        or point.payload.get("raw_hash") != row["frozen"]["raw_hash"]
                        or point.payload.get("generation") != generation
                        or point.payload.get("manifest_hash") != manifest_hash
                        or point.payload.get("model_digest") != DIGEST):
                        raise ValueError("P11_EXISTING_VECTOR_IDENTITY_CONFLICT")
                missing = [row for row in parents if row["cid"] not in present]
                batches, embedding_ms = 0, 0.0
                for start in range(0, len(missing), batch_size):
                    if max_batches is not None and batches >= max_batches:
                        break
                    if (psutil.virtual_memory().available < 128 * 1024 * 1024
                        or shutil.disk_usage(folder).free < 1_073_741_824):
                        raise RuntimeError("P11_ACTUAL_RESOURCE_GUARD")
                    batch = missing[start:start + batch_size]
                    texts = [OllamaVectors.document_prefix + row["chunk"].text[:6000]
                             for row in batch]
                    started = perf_counter()
                    response = session.post(URL + "/api/embed", json={"model": MODEL,
                        "input": texts, "truncate": True, "keep_alive": "5m"}, timeout=90)
                    response.raise_for_status()
                    vectors = response.json()["embeddings"]
                    valid_vectors(vectors, len(batch), 768)
                    embedding_ms += (perf_counter() - started) * 1000
                    client.upsert(COLLECTION, points=[models.PointStruct(
                        id=point_id(row["cid"]), vector=vector,
                        payload={"chunk_id": row["cid"],
                                 "payload_hash": row["payload_hash"],
                                 "raw_hash": row["frozen"]["raw_hash"],
                                 "cik": row["chunk"].metadata["cik"],
                                 "filing_id": row["chunk"].filing_id,
                                 "generation": generation,
                                 "manifest_hash": manifest_hash,
                                 "model_digest": DIGEST})
                        for row, vector in zip(batch, vectors)], wait=True)
                    batches += 1
                    atomic_json(folder / "progress.json", {"state": "BUILDING",
                        "generation": generation, "completed_points": len(present) +
                        min(start + len(batch), len(missing)), "target_points": len(parents)})
                current = scan_points(client)
                state = "BUILDING"
                if len(current) == len(parents):
                    for start in range(0, len(parents), 64):
                        ids = [point_id(row["cid"]) for row in parents[start:start + 64]]
                        points = client.retrieve(COLLECTION, ids=ids,
                                                 with_payload=True, with_vectors=True)
                        if len(points) != len(ids):
                            raise ValueError("P11_VECTOR_MEMBERSHIP_INCOMPLETE")
                        for point in points:
                            cid = point.payload["chunk_id"]
                            if (cid not in expected or str(point.id) != point_id(cid)
                                or len(point.vector) != 768
                                or not all(isinstance(v, (int, float)) and math.isfinite(v)
                                            for v in point.vector)):
                                raise ValueError("P11_VECTOR_VALUE_OR_DIMENSION_INVALID")
                    state = "READY"
                result = {**identity, "state": state,
                          "lexical_state": lexical_record["state"],
                          "lexical_count": lexical_record["n"],
                          "lexical_membership_hash": lexical_record["membership_hash"],
                          "completed_points": len(current),
                          "missing_points": len(parents) - len(current),
                          "embedding_batches_this_run": batches,
                          "embedding_ms_this_run": round(embedding_ms, 3),
                          "qdrant_client_version": require_supported_embedded_qdrant()}
                atomic_json(folder / "generation_manifest.json", result)
                return result
            finally:
                client.close()
        finally:
            owner.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--max-batches", type=int)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = build(args.root, args.batch_size, args.max_batches)
    atomic_json(args.output, result)
    print(json.dumps({k: result[k] for k in ("state", "lexical_count",
                                            "completed_points", "missing_points",
                                            "embedding_batches_this_run",
                                            "embedding_ms_this_run")}))

"""Restartable isolated research vectors from a pinned, authenticated SEC snapshot."""
import argparse
from contextlib import closing
from hashlib import sha256
import json
import math
import os
from pathlib import Path
from time import perf_counter
from uuid import NAMESPACE_URL, uuid5

import psutil
import requests
from qdrant_client import QdrantClient, models

from app.financial_index.corpus import verified_source
from app.financial_index.ownership import LocalQdrantOwnership, require_supported_embedded_qdrant
from app.financial_index.service import OllamaVectors, valid_vectors
from app.financial_ingestion.schemas import FinancialChunk
from app.research_retrieval.snapshot import FrozenResearchSnapshot
from app.table_evidence.identity import digest


MODEL = "nomic-embed-text:latest"
EXPECTED_DIGEST = "0a109f422b47e3a30ba2b10eca18548e944e8a23073ee3f3e947efcf3c45e59f"
URL = "http://127.0.0.1:11434"
BATCH_LIMIT = 4
COLLECTION = "topic3_p10_isolated_nomic_v1"


def atomic_json(path, value):
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    tmp.replace(path)


def point_id(chunk_id):
    return str(uuid5(NAMESPACE_URL, "topic3-p10/" + chunk_id))


def source_records(snapshot):
    generation = snapshot.freeze["generation"]
    with closing(snapshot.lexical.connect()) as db:
        rows = db.execute("SELECT d.cid,d.payload,d.payload_hash,m.source FROM documents d "
                          "JOIN members m ON m.cid=d.cid WHERE m.generation=? ORDER BY d.cid",
                          (generation,)).fetchall()
    record = snapshot.lexical.generation(snapshot.catalog.dataset_id, generation)
    if record["state"] != "READY" or len(rows) != record["n"]:
        raise ValueError("PINNED_LEXICAL_GENERATION_INCOMPLETE")
    registry_path = Path(__file__).resolve().parents[1] / "docs/topic3/milestone_d/d3/D3_FRESH_EXACT_ROW_FREEZE_v1.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    if (registry["manifest_hash"], registry["generation"]) != (
        snapshot.freeze["manifest_hash"], generation):
        raise ValueError("COMMITTED_SOURCE_REGISTRY_MISMATCH")
    anchors = {entry["raw_hash"]: entry for entry in registry["source_groups"]}
    verified = {}
    prepared = []
    seen = set()
    for row in rows:
        cid = row["cid"]
        if cid in seen:
            raise ValueError("DUPLICATE_LEXICAL_PARENT_ID")
        seen.add(cid)
        frozen = json.loads(row["source"])
        anchor = anchors.get(frozen.get("raw_hash"))
        if anchor is None or frozen.get("manifest_hash") != snapshot.freeze["manifest_hash"]:
            raise ValueError("SOURCE_NOT_IN_PINNED_REGISTRY")
        for key in ("raw_path", "structured_path", "chunks_path"):
            if not Path(frozen[key]).resolve().is_relative_to(snapshot.root):
                raise ValueError("RESEARCH_SOURCE_PATH_ESCAPE")
        if frozen["raw_hash"] not in verified:
            verified[frozen["raw_hash"]] = verified_source(frozen, generation=generation)
        parent = verified[frozen["raw_hash"]].get(cid)
        payload = FinancialChunk.model_validate_json(row["payload"])
        if (parent is None or parent.model_dump(mode="json") != payload.model_dump(mode="json")
            or payload.filing_id != frozen["filing_id"]
            or payload.metadata.get("cik") != anchor["cik"]
            or payload.metadata.get("accession_number") != anchor["accession"]
            or payload.metadata.get("source_url") != anchor["url"]
            or digest(payload.model_dump(mode="json")) != row["payload_hash"]):
            raise ValueError("COMMITTED_PARENT_IDENTITY_MISMATCH")
        prepared.append({"cid": cid, "payload_hash": row["payload_hash"], "parent": payload,
                         "raw_hash": frozen["raw_hash"]})
    return prepared, sorted(verified)


def current_points(client):
    found = {}
    offset = None
    while True:
        batch, offset = client.scroll(COLLECTION, limit=128, offset=offset,
                                      with_payload=True, with_vectors=False)
        for point in batch:
            cid = point.payload.get("chunk_id")
            if cid in found:
                raise ValueError("DUPLICATE_VECTOR_PARENT_ID")
            found[cid] = point
        if offset is None:
            return found


def resource_guard():
    if psutil.virtual_memory().available < 128 * 1024 * 1024:
        raise RuntimeError("ACTUAL_AVAILABLE_MEMORY_TOO_LOW")


def build(root, vector_root, batch_size, max_batches):
    root = root.resolve(strict=True)
    vector_root = vector_root.resolve()
    if ("p7-isolated-review" not in root.name or not (root / "ownership.json").is_file()
        or vector_root.parent != root.parent or not vector_root.name.startswith("t3-p10-isolated-vectors-")):
        raise ValueError("EXPLICIT_ISOLATED_SOURCE_AND_VECTOR_ROOT_REQUIRED")
    if not 1 <= batch_size <= BATCH_LIMIT:
        raise ValueError("BATCH_SIZE_OUT_OF_BOUNDS")
    if vector_root.exists() and not (vector_root / "identity.json").is_file():
        raise ValueError("NONEMPTY_UNOWNED_VECTOR_ROOT")
    require_supported_embedded_qdrant()
    snapshot = FrozenResearchSnapshot(root)
    prepared, source_hashes = source_records(snapshot)
    membership_hash = sha256(json.dumps([(r["cid"], r["payload_hash"], r["raw_hash"])
                                    for r in prepared], separators=(",", ":")).encode()).hexdigest()
    identity = {"schema_version": "topic3-p10-vector-identity/v1", "dataset_id": snapshot.catalog.dataset_id,
                "generation": snapshot.freeze["generation"],
                "manifest_hash": snapshot.freeze["manifest_hash"],
                "source_raw_hashes": source_hashes, "membership_hash": membership_hash,
                "parent_count": len(prepared), "model": MODEL, "model_digest": EXPECTED_DIGEST,
                "dimension": 768, "document_prefix": OllamaVectors.document_prefix,
                "query_prefix": OllamaVectors.query_prefix,
                "truncation": "first-6000-content-characters;ollama-truncate=true",
                "normalization": "unicode-preserved;whitespace-preserved", "distance": "COSINE",
                "collection": COLLECTION}
    vector_root.mkdir(parents=True, exist_ok=True)
    identity_path = vector_root / "identity.json"
    if identity_path.exists():
        if json.loads(identity_path.read_text(encoding="utf-8")) != identity:
            raise ValueError("VECTOR_GENERATION_IDENTITY_CHANGED")
    else:
        atomic_json(identity_path, identity)
    with requests.Session() as session:
        tags = session.get(URL + "/api/tags", timeout=5)
        tags.raise_for_status()
        live = next((m for m in tags.json().get("models", []) if m.get("name") == MODEL), None)
        if live is None or live.get("digest") != EXPECTED_DIGEST:
            raise ValueError("LIVE_MODEL_DIGEST_MISMATCH")
        owner = LocalQdrantOwnership(vector_root / "qdrant")
        try:
            client = QdrantClient(path=str(vector_root / "qdrant"))
            try:
                if not client.collection_exists(COLLECTION):
                    client.create_collection(COLLECTION, vectors_config=models.VectorParams(
                        size=768, distance=models.Distance.COSINE))
                info = client.get_collection(COLLECTION)
                params = info.config.params.vectors
                if params.size != 768 or params.distance != models.Distance.COSINE:
                    raise ValueError("QDRANT_VECTOR_CONTRACT_MISMATCH")
                expected = {row["cid"]: row for row in prepared}
                existing = current_points(client)
                for cid, point in existing.items():
                    row = expected.get(cid)
                    if (row is None or str(point.id) != point_id(cid)
                        or point.payload.get("payload_hash") != row["payload_hash"]
                        or point.payload.get("raw_hash") != row["raw_hash"]
                        or point.payload.get("generation") != identity["generation"]
                        or point.payload.get("manifest_hash") != identity["manifest_hash"]
                        or point.payload.get("model_digest") != EXPECTED_DIGEST):
                        raise ValueError("EXISTING_VECTOR_MEMBERSHIP_CONFLICT")
                missing = [row for row in prepared if row["cid"] not in existing]
                timings = []
                built = 0
                for start in range(0, len(missing), batch_size):
                    if max_batches is not None and built >= max_batches:
                        break
                    resource_guard()
                    batch = missing[start:start + batch_size]
                    texts = [OllamaVectors.document_prefix + row["parent"].text[:6000] for row in batch]
                    tick = perf_counter()
                    response = session.post(URL + "/api/embed", json={"model": MODEL, "input": texts,
                        "truncate": True, "keep_alive": "5m"}, timeout=90)
                    response.raise_for_status()
                    vectors = response.json()["embeddings"]
                    valid_vectors(vectors, len(batch), 768)
                    embed_ms = (perf_counter() - tick) * 1000
                    points = [models.PointStruct(id=point_id(row["cid"]), vector=vector,
                        payload={"chunk_id": row["cid"], "payload_hash": row["payload_hash"],
                                 "raw_hash": row["raw_hash"], "cik": row["parent"].metadata["cik"],
                                 "filing_id": row["parent"].filing_id,
                                 "generation": identity["generation"],
                                 "manifest_hash": identity["manifest_hash"],
                                 "model_digest": EXPECTED_DIGEST})
                              for row, vector in zip(batch, vectors)]
                    client.upsert(COLLECTION, points=points, wait=True)
                    built += 1
                    timings.append(embed_ms)
                    atomic_json(vector_root / "progress.json", {"identity_sha256": sha256(
                        json.dumps(identity, sort_keys=True).encode()).hexdigest(),
                        "state": "BUILDING", "completed_points": len(existing) + min(start + len(batch), len(missing)),
                        "target_points": len(prepared), "last_batch_ms": embed_ms})
                found = current_points(client)
                state = "BUILDING"
                if len(found) == len(prepared):
                    for offset in range(0, len(prepared), 64):
                        ids = [point_id(row["cid"]) for row in prepared[offset:offset + 64]]
                        points = client.retrieve(COLLECTION, ids=ids, with_payload=True, with_vectors=True)
                        if len(points) != len(ids):
                            raise ValueError("VECTOR_MEMBERSHIP_INCOMPLETE")
                        for point in points:
                            cid = point.payload["chunk_id"]
                            if (cid not in expected or str(point.id) != point_id(cid)
                                or len(point.vector) != 768
                                or not all(isinstance(v, (int, float)) and math.isfinite(v) for v in point.vector)):
                                raise ValueError("VECTOR_DIMENSION_OR_VALUE_INVALID")
                    state = "READY"
                manifest = dict(identity, state=state, completed_points=len(found),
                                missing_points=len(prepared) - len(found), batch_limit=BATCH_LIMIT,
                                batches_this_run=built, embedding_ms_this_run=sum(timings),
                                qdrant_client_version=require_supported_embedded_qdrant())
                atomic_json(vector_root / "generation_manifest.json", manifest)
                return manifest
            finally:
                client.close()
        finally:
            owner.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--vector-root", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--max-batches", type=int)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = build(args.root, args.vector_root, args.batch_size, args.max_batches)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("state", "completed_points", "missing_points",
                                                   "batches_this_run", "embedding_ms_this_run")}))

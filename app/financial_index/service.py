"""Atomic snapshot-bound lexical/dense generations, shared by CLI and FastAPI."""
from contextlib import closing
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
import re
from threading import Lock, RLock
from time import perf_counter
from uuid import uuid4, uuid5, NAMESPACE_URL

import requests

from app.config import get_settings
from app.financial_index import INDEX_VERSION, TOKENIZER_VERSION
from app.financial_index.corpus import canonical, digest_file, iter_documents, resolve_sources, verified_source
from app.financial_index.lexical import LexicalIndex
from app.services.financial_search_service import reciprocal_rank_fusion


class OllamaVectors:
    dimension = 768

    def identity(self):
        settings = get_settings()
        if settings.embedding_provider != "ollama":
            raise ValueError("Milestone C requires an explicit supported Ollama embedding identity")
        model = settings.embedding_model
        name = model if ":" in model else model + ":latest"
        response = requests.get(settings.ollama_base_url + "/api/tags", timeout=10)
        response.raise_for_status()
        match = next((item for item in response.json().get("models", []) if item["name"] == name), None)
        if match is None:
            raise ValueError("Configured embedding model is not installed; no automatic model download")
        return {"model": name, "digest": match["digest"], "dimension": self.dimension,
                "input_policy": "first-6000-characters;ollama-truncate=true"}

    def embed(self, texts):
        settings = get_settings()
        response = requests.post(settings.ollama_base_url + "/api/embed", json={
            "model": settings.embedding_model, "input": [text[:6000] for text in texts],
            "truncate": True, "keep_alive": "5m"}, timeout=300)
        response.raise_for_status()
        return response.json()["embeddings"]


def valid_vectors(vectors, count, dimension):
    if len(vectors) != count or any(len(vector) != dimension or not all(
            isinstance(value, (int, float)) and math.isfinite(value) for value in vector) for vector in vectors):
        raise ValueError("EMBEDDING_DIMENSION_OR_VALUE_MISMATCH")


class FinancialIndex:
    def __init__(self, root: Path, provider=None, dense_client=None):
        self.root = Path(root)
        self.lexical = LexicalIndex(self.root / "lexical.sqlite3")
        self.provider = provider or OllamaVectors()
        self._client = dense_client
        self._dense_lock = RLock()
        self._build_lock = Lock()

    @property
    def dense(self):
        with self._dense_lock:
            if self._client is None:
                from qdrant_client import QdrantClient
                self._client = QdrantClient(path=str(self.root / "qdrant"), force_disable_check_same_thread=True)
            return self._client

    def close(self):
        if self._client is not None:
            self._client.close()
            self._client = None

    def plan(self, dataset: str, specs: list[dict], *, force_rebuild=False):
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", dataset):
            raise ValueError("Invalid dataset identity")
        sources = resolve_sources(specs)
        identity = self.provider.identity()
        signature = {"dataset": dataset, "index_version": INDEX_VERSION,
                     "tokenizer_version": TOKENIZER_VERSION, "embedding": identity,
                     "sources": [{"manifest_hash": item["manifest"]["manifest_hash"],
                                  "per_filing_limit": item["per_filing_limit"]} for item in sources]}
        if force_rebuild:
            signature["explicit_rebuild"] = uuid4().hex
        generation = sha256(canonical(signature).encode()).hexdigest()
        metadata = {**signature, "sources": sources, "collection": "financial_c_" + generation[:24],
                    "created_at": datetime.now(timezone.utc).isoformat()}
        self.lexical.start(dataset, generation, metadata)
        return generation

    def _cache_vectors(self, identity: dict, batch: list[dict]):
        identity_hash = sha256(canonical(identity).encode()).hexdigest()
        texts = [item["chunk"]["text"][:6000] for item in batch]
        hashes = [sha256(text.encode()).hexdigest() for text in texts]
        vectors, missing = {}, {}
        with closing(self.lexical.connect()) as c:
            for text_hash, text in zip(hashes, texts):
                row = c.execute("SELECT vector FROM vectors WHERE identity=? AND input_hash=?", (identity_hash, text_hash)).fetchone()
                if row:
                    vectors[text_hash] = json.loads(row[0])
                else:
                    missing[text_hash] = text
        if missing:
            produced = self.provider.embed(list(missing.values()))
            valid_vectors(produced, len(missing), identity["dimension"])
            with closing(self.lexical.connect()) as c, c:
                for text_hash, vector in zip(missing, produced):
                    vectors[text_hash] = vector
                    c.execute("INSERT OR IGNORE INTO vectors VALUES(?,?,?)", (identity_hash, text_hash, canonical(vector)))
        result = [vectors[text_hash] for text_hash in hashes]
        valid_vectors(result, len(batch), identity["dimension"])
        return result, len(missing)

    def build(self, dataset: str, generation: str, *, batch_size: int = 8, fail_after_batches: int | None = None):
        if not 1 <= batch_size <= 32:
            raise ValueError("Use embedding batches of 1-32 chunks")
        if not self._build_lock.acquire(blocking=False):
            raise RuntimeError("BUILD_ALREADY_RUNNING")
        started = perf_counter()
        try:
            record = self.lexical.generation(dataset, generation)
            self.validate_implementation(record)
            metadata = record["metadata"]
            if record["state"] == "READY":
                self.validate_dense(record, complete=True)
                self.validate_sources(record)
                return {"generation": generation, "idempotent_reuse": True, "new_posting_documents": 0, "embedded_texts": 0}
            if self.provider.identity() != metadata["embedding"]:
                raise ValueError("EMBEDDING_IDENTITY_MISMATCH")
            self.lexical.start(dataset, generation, metadata)
            from qdrant_client.http.models import Distance, VectorParams, PointStruct
            collection = metadata["collection"]
            with self._dense_lock:
                if not self.dense.collection_exists(collection):
                    self.dense.create_collection(collection, vectors_config=VectorParams(
                        size=metadata["embedding"]["dimension"], distance=Distance.COSINE))
                info = self.dense.get_collection(collection)
                if info.config.params.vectors.size != metadata["embedding"]["dimension"]:
                    raise ValueError("DENSE_DIMENSION_MISMATCH")
            stats = {"new_posting_documents": 0, "embedded_texts": 0, "upserted_chunks": 0, "embedding_ms": 0.}
            batch, batches = [], 0

            def write(items):
                stats["new_posting_documents"] += self.lexical.add(generation, items)
                before = perf_counter()
                vectors, embedded = self._cache_vectors(metadata["embedding"], items)
                stats["embedding_ms"] += (perf_counter() - before) * 1000
                stats["embedded_texts"] += embedded
                points = []
                for item, vector in zip(items, vectors):
                    chunk = item["chunk"]
                    m = chunk["metadata"]
                    payload = {key: m.get(key) for key in ("cik", "ticker", "form_type", "fiscal_year", "fiscal_period")}
                    for key in ("ticker", "form_type", "fiscal_period"):
                        payload[key] = (payload[key] or "").upper()
                    payload.update(chunk_id=chunk["chunk_id"], filing_id=chunk["filing_id"], generation=generation,
                                   payload_hash=sha256(canonical(chunk).encode()).hexdigest())
                    points.append(PointStruct(id=str(uuid5(NAMESPACE_URL, chunk["chunk_id"])), vector=vector, payload=payload))
                with self._dense_lock:
                    self.dense.upsert(collection, points=points, wait=True)
                stats["upserted_chunks"] += len(items)

            for item in iter_documents(metadata["sources"]):
                batch.append(item)
                if len(batch) == batch_size:
                    write(batch)
                    batch = []
                    batches += 1
                    if fail_after_batches is not None and batches >= fail_after_batches:
                        raise RuntimeError("CONTROLLED_BUILD_INTERRUPTION")
            if batch:
                write(batch)
            self.lexical.seal(generation)
            if self.provider.identity() != metadata["embedding"]:
                raise ValueError("EMBEDDING_IDENTITY_CHANGED_DURING_BUILD")
            record = self.lexical.generation(dataset, generation)
            self.validate_dense(record, complete=True)
            self.lexical.publish(dataset, generation)
            stats.update(generation=generation, chunks=record["n"], idempotent_reuse=False,
                         build_ms=(perf_counter() - started) * 1000)
            return stats
        except Exception as exc:
            self.lexical.fail(generation, str(exc))
            raise
        finally:
            self._build_lock.release()

    def validate_dense(self, record: dict, *, complete=False):
        from qdrant_client.http.models import Filter, FieldCondition, MatchValue
        metadata = record["metadata"]
        collection = metadata["collection"]
        if collection != "financial_c_" + record["generation"][:24]:
            raise ValueError("DENSE_GENERATION_MISMATCH")
        with self._dense_lock:
            info = self.dense.get_collection(collection)
            if info.config.params.vectors.size != metadata["embedding"]["dimension"]:
                raise ValueError("DENSE_DIMENSION_MISMATCH")
            scope = Filter(must=[FieldCondition(key="generation", match=MatchValue(value=record["generation"]))])
            if (self.dense.count(collection, exact=True).count != record["n"] or
                    self.dense.count(collection, count_filter=scope, exact=True).count != record["n"]):
                raise ValueError("DENSE_MEMBERSHIP_MISMATCH")
            if complete:
                expected = {item["chunk"]["chunk_id"] for item in self.lexical.records(record["generation"])}
                actual, offset = set(), None
                while True:
                    points, offset = self.dense.scroll(collection, limit=128, offset=offset, with_payload=True, with_vectors=False)
                    actual.update(point.payload.get("chunk_id") for point in points)
                    if offset is None:
                        break
                if actual != expected:
                    raise ValueError("DENSE_CHUNK_ID_MISMATCH")

    def validate_sources(self, record):
        checked = set()
        for item in self.lexical.records(record["generation"]):
            source = item["source"]
            if source["structured_path"] not in checked:
                for path, key in (("raw_path", "raw_hash"), ("structured_path", "structured_hash"), ("chunks_path", "chunks_hash")):
                    if digest_file(Path(source[path])) != source[key]:
                        raise ValueError("SOURCE_ARTIFACT_HASH_MISMATCH")
                checked.add(source["structured_path"])

    @staticmethod
    def validate_implementation(record):
        metadata = record["metadata"]
        if metadata["index_version"] != INDEX_VERSION or metadata["tokenizer_version"] != TOKENIZER_VERSION:
            raise ValueError("INDEX_IMPLEMENTATION_VERSION_MISMATCH")

    def activate(self, dataset: str, generation: str):
        record = self.lexical.generation(dataset, generation)
        if record["state"] != "READY":
            raise ValueError("INDEX_NOT_READY")
        self.validate_implementation(record)
        self.validate_dense(record, complete=True)
        self.validate_sources(record)
        with closing(self.lexical.connect()) as c, c:
            c.execute("INSERT INTO active VALUES(?,?) ON CONFLICT(dataset) DO UPDATE SET generation=excluded.generation", (dataset, generation))

    def describe(self):
        with closing(self.lexical.connect()) as c:
            rows = c.execute("SELECT g.*,a.generation= g.generation AS is_active FROM generations g LEFT JOIN active a ON a.dataset=g.dataset ORDER BY g.rowid DESC").fetchall()
        result = []
        for row in rows:
            metadata = json.loads(row["metadata"])
            result.append({"dataset_id": row["dataset"], "generation": row["generation"], "state": row["state"],
                           "active": bool(row["is_active"]), "chunks": row["n"], "error": row["error"],
                           "embedding": metadata["embedding"], "membership_hash": row["membership_hash"],
                           "manifests": [source["manifest"]["manifest_hash"] for source in metadata["sources"]],
                           "source_partial_documents": sorted({item for source in metadata["sources"] for item in source["manifest"]["partial_documents"]}),
                           "subset_policy": [source["per_filing_limit"] for source in metadata["sources"]]})
        return result

    def search(self, dataset: str, query: str, mode="hybrid", *, generation=None, top_k=5,
               candidate_limit=40, filters=None, allow_degraded=False, expected_manifests=None):
        started = perf_counter()
        if mode not in {"bm25", "dense", "hybrid"} or not query.strip() or not 1 <= top_k <= candidate_limit <= 100:
            raise ValueError("Invalid financial search scope/mode/limits")
        record = self.lexical.generation(dataset, generation)
        if record["state"] != "READY":
            raise ValueError("INDEX_NOT_READY")
        self.validate_implementation(record)
        metadata = record["metadata"]
        manifest_hashes = sorted(source["manifest"]["manifest_hash"] for source in metadata["sources"])
        if expected_manifests is not None and sorted(expected_manifests) != manifest_hashes:
            raise ValueError("REQUESTED_SNAPSHOT_MISMATCH")
        filters = {key: value for key, value in (filters or {}).items() if value is not None and value != []}
        self.lexical.scope(record["generation"], filters)
        before = perf_counter()
        lexical = self.lexical.search(query, record, candidate_limit, filters) if mode != "dense" else []
        lexical_ms = (perf_counter() - before) * 1000
        dense, degraded, embedding_ms, dense_ms = [], None, 0., 0.
        if mode != "bm25":
            try:
                self.validate_dense(record)
                before = perf_counter()
                if self.provider.identity() != metadata["embedding"]:
                    raise ValueError("EMBEDDING_IDENTITY_MISMATCH")
                vectors = self.provider.embed([query])
                valid_vectors(vectors, 1, metadata["embedding"]["dimension"])
                embedding_ms = (perf_counter() - before) * 1000
                from qdrant_client.http.models import Filter, FieldCondition, MatchValue, MatchAny
                conditions = [FieldCondition(key="generation", match=MatchValue(value=record["generation"]))]
                for key, value in filters.items():
                    if key == "filing_ids":
                        conditions.append(FieldCondition(key="filing_id", match=MatchAny(any=value)))
                    else:
                        conditions.append(FieldCondition(key=key, match=MatchValue(value=value.upper() if isinstance(value, str) else value)))
                before = perf_counter()
                with self._dense_lock:
                    points = self.dense.query_points(metadata["collection"], query=vectors[0],
                        query_filter=Filter(must=conditions), limit=min(record["n"], candidate_limit * 4), with_payload=True).points
                for point in points:
                    if point.payload.get("generation") != record["generation"]:
                        raise ValueError("DENSE_RESULT_GENERATION_MISMATCH")
                    dense.append({"chunk_id": point.payload["chunk_id"], "dense_score": float(point.score),
                                  "payload_hash": point.payload["payload_hash"]})
                dense.sort(key=lambda item: (-item["dense_score"], item["chunk_id"]))
                dense = dense[:candidate_limit]
                dense_ms = (perf_counter() - before) * 1000
            except Exception as exc:
                if mode != "hybrid" or not allow_degraded:
                    raise RuntimeError("DENSE_INDEX_UNAVAILABLE_OR_MISMATCH: " + str(exc)) from exc
                degraded = str(exc)
                dense = []
        ranks = (reciprocal_rank_fusion(lexical, dense) if mode == "hybrid" and not degraded else
                 lexical if mode == "bm25" or degraded else dense)
        retrieval_ms = (perf_counter() - started) * 1000 - embedding_ms
        results, sources = [], {}
        dense_hashes = {item["chunk_id"]: item["payload_hash"] for item in dense}
        with closing(self.lexical.connect()) as c:
            for rank, hit in enumerate(ranks[:top_k], 1):
                row = c.execute("SELECT d.payload,m.source FROM documents d JOIN members m ON m.cid=d.cid WHERE m.generation=? AND d.cid=?", (record["generation"], hit["chunk_id"])).fetchone()
                if row is None:
                    raise RuntimeError("INDEX_MEMBERSHIP_MISMATCH")
                chunk, frozen = json.loads(row["payload"]), json.loads(row["source"])
                if hit["chunk_id"] in dense_hashes and dense_hashes[hit["chunk_id"]] != sha256(canonical(chunk).encode()).hexdigest():
                    raise RuntimeError("DENSE_PAYLOAD_MISMATCH")
                source_key = frozen["structured_path"]
                if source_key not in sources:
                    sources[source_key] = verified_source(frozen)
                expected = sources[source_key].get(chunk["chunk_id"])
                if expected is None or expected.model_dump(mode="json") != chunk:
                    raise RuntimeError("PROVENANCE_CHUNK_CONTEXT_MISMATCH")
                results.append({**chunk, **hit, "rank": rank, "provenance_status": "VERIFIED",
                                "source_manifest_hash": frozen["manifest_hash"]})
        return {"dataset_id": dataset, "generation": record["generation"], "manifests": manifest_hashes,
                "mode": mode, "effective_mode": "bm25" if degraded else mode, "degraded_reason": degraded,
                "indexed_chunks": record["n"], "filters": filters, "results": results,
                "timings_ms": {"lexical": lexical_ms, "embedding": embedding_ms, "dense": dense_ms,
                               "retrieval_without_embedding_or_provenance": retrieval_ms,
                               "provenance": (perf_counter() - started) * 1000 - embedding_ms - retrieval_ms,
                               "total": (perf_counter() - started) * 1000},
                "lexical_contract": {"algorithm": INDEX_VERSION, "tokenizer": TOKENIZER_VERSION, "k1": 1.5, "b": .75},
                "fusion": {"algorithm": "rrf", "k": 60, "candidate_limit": candidate_limit} if mode == "hybrid" else None,
                "source_partial_documents": sorted({item for source in metadata["sources"] for item in source["manifest"]["partial_documents"]})}

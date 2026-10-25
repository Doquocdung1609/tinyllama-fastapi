"""Atomic snapshot-bound lexical/dense generations, shared by CLI and FastAPI."""
from contextlib import closing, contextmanager
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
import re
from threading import Condition, Lock, RLock
from time import perf_counter
from uuid import uuid4, uuid5, NAMESPACE_URL

import requests

from app.config import get_settings
from app.financial_index import INDEX_VERSION, TOKENIZER_VERSION
from app.financial_index.corpus import (ProvenanceCache, canonical, digest_file, iter_documents,
                                        resolve_sources, verified_source)
from app.financial_index.lexical import LexicalIndex
from app.financial_index.ownership import LocalQdrantOwnership
from app.services.financial_search_service import reciprocal_rank_fusion
from app.path_safety import ensure_path_capacity


class OllamaVectors:
    dimension = 768
    document_prefix = "search_document: "
    query_prefix = "search_query: "

    def __init__(self, session=None):
        self.session = session or requests.Session()

    def identity(self):
        settings = get_settings()
        if settings.embedding_provider != "ollama":
            raise ValueError("Milestone C requires an explicit supported Ollama embedding identity")
        model = settings.embedding_model
        name = model if ":" in model else model + ":latest"
        response = self.session.get(settings.ollama_base_url + "/api/tags",
                                    timeout=settings.ollama_identity_timeout_seconds)
        response.raise_for_status()
        match = next((item for item in response.json().get("models", []) if item["name"] == name), None)
        if match is None:
            raise ValueError("Configured embedding model is not installed; no automatic model download")
        reported_dimension = match.get("details", {}).get("embedding_length", self.dimension)
        if reported_dimension != self.dimension:
            raise ValueError("EMBEDDING_MODEL_DIMENSION_MISMATCH")
        return {"model": name, "digest": match["digest"], "dimension": self.dimension,
                "document_prefix": self.document_prefix, "query_prefix": self.query_prefix,
                "normalization_policy": "unicode-preserved;whitespace-preserved",
                "truncation_policy": "first-6000-content-characters;ollama-truncate=true"}

    def _embed(self, texts):
        settings = get_settings()
        response = self.session.post(settings.ollama_base_url + "/api/embed", json={
            "model": settings.embedding_model, "input": texts,
            "truncate": True, "keep_alive": "5m"}, timeout=settings.ollama_embedding_timeout_seconds)
        response.raise_for_status()
        return response.json()["embeddings"]

    def embed_documents(self, texts):
        return self._embed([self.document_prefix + text[:6000] for text in texts])

    def embed_query(self, text):
        return self._embed([self.query_prefix + text])[0]

    def close(self):
        self.session.close()


def valid_vectors(vectors, count, dimension):
    if len(vectors) != count or any(len(vector) != dimension or not all(
            isinstance(value, (int, float)) and math.isfinite(value) for value in vector) for vector in vectors):
        raise ValueError("EMBEDDING_DIMENSION_OR_VALUE_MISMATCH")


def _stable_error_code(exc: Exception, fallback="FINANCIAL_INDEX_OPERATION_FAILED") -> str:
    text = str(exc)
    return text if text.isupper() and text.replace("_", "").isalnum() else fallback


class FinancialIndex:
    def __init__(self, root: Path, provider=None, dense_client=None, *, qdrant_url: str | None = None):
        self.root = Path(root)
        ensure_path_capacity(self.root, Path("qdrant") / ("financial_c_" + "0" * 24))
        self.root.mkdir(parents=True, exist_ok=True)
        settings = get_settings()
        self.qdrant_url = settings.financial_index_qdrant_url if qdrant_url is None else qdrant_url.strip()
        self._ownership = None
        if dense_client is None and not self.qdrant_url:
            self._ownership = LocalQdrantOwnership(self.root)
        try:
            self.lexical = LexicalIndex(self.root / "lexical.sqlite3")
        except Exception:
            if self._ownership is not None:
                self._ownership.close()
            raise
        self.provider = provider or OllamaVectors()
        self.provenance_cache = ProvenanceCache(
            settings.financial_index_provenance_cache_entries,
            settings.financial_index_provenance_cache_mb * 1024 * 1024)
        self._client = dense_client
        self._dense_lock = RLock()
        self._build_lock = Lock()
        self._query_condition = Condition(Lock())
        self._active_queries = 0
        self._cleanup_active = False

    @contextmanager
    def _query_access(self):
        with self._query_condition:
            while self._cleanup_active:
                self._query_condition.wait()
            self._active_queries += 1
        try:
            yield
        finally:
            with self._query_condition:
                self._active_queries -= 1
                self._query_condition.notify_all()

    @contextmanager
    def _cleanup_access(self):
        with self._query_condition:
            self._cleanup_active = True
            while self._active_queries:
                self._query_condition.wait()
        try:
            yield
        finally:
            with self._query_condition:
                self._cleanup_active = False
                self._query_condition.notify_all()

    @property
    def dense(self):
        with self._dense_lock:
            if self._client is None:
                from qdrant_client import QdrantClient
                if self.qdrant_url:
                    self._client = QdrantClient(url=self.qdrant_url)
                else:
                    self._client = QdrantClient(path=str(self.root / "qdrant"), force_disable_check_same_thread=True)
            return self._client

    def close(self):
        if self._client is not None:
            self._client.close()
            self._client = None
        close_provider = getattr(self.provider, "close", None)
        if close_provider:
            close_provider()
        if self._ownership is not None:
            self._ownership.close()
            self._ownership = None
        self.provenance_cache.clear()

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
            produced = self.provider.embed_documents(list(missing.values()))
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
        # API builds are accepted as background work. Serialize them here so a
        # second accepted request is not silently abandoned in BUILDING state.
        self._build_lock.acquire()
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
            self.lexical.fail(generation, _stable_error_code(exc, "INDEX_BUILD_FAILED"))
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

    def protect_generation(self, dataset: str, generation: str, kind: str, reference: str):
        if kind not in {"pin", "evaluation"} or not re.fullmatch(r"[A-Za-z0-9_.:/-]{1,160}", reference):
            raise ValueError("INVALID_GENERATION_PROTECTION")
        record = self.lexical.generation(dataset, generation)
        if record["state"] != "READY":
            raise ValueError("INDEX_NOT_READY")
        with closing(self.lexical.connect()) as c, c:
            c.execute("INSERT OR IGNORE INTO generation_protections VALUES(?,?,?,?)", (
                generation, kind, reference, datetime.now(timezone.utc).isoformat()))

    def unprotect_generation(self, dataset: str, generation: str, kind: str, reference: str):
        self.lexical.generation(dataset, generation)
        if kind not in {"pin", "evaluation"}:
            raise ValueError("INVALID_GENERATION_PROTECTION")
        with closing(self.lexical.connect()) as c, c:
            c.execute("DELETE FROM generation_protections WHERE generation=? AND kind=? AND reference=?",
                      (generation, kind, reference))

    def retention_inventory(self):
        settings = get_settings()
        with closing(self.lexical.connect()) as c:
            rows = c.execute("SELECT g.*,a.generation=g.generation AS is_active FROM generations g "
                             "LEFT JOIN active a ON a.dataset=g.dataset ORDER BY g.dataset,g.rowid DESC").fetchall()
            protections = c.execute("SELECT generation,kind,reference FROM generation_protections").fetchall()
            audits = [dict(row) for row in c.execute(
                "SELECT generation,state,requested_at,completed_at,error_code FROM cleanup_audit ORDER BY id DESC LIMIT 20")]
        protected = {}
        for row in protections:
            protected.setdefault(row["generation"], []).append({"kind": row["kind"], "reference": row["reference"]})
        rollback = set()
        by_dataset = {}
        for row in rows:
            if row["state"] == "READY" and not row["is_active"]:
                by_dataset.setdefault(row["dataset"], []).append(row["generation"])
        for generations in by_dataset.values():
            rollback.update(generations[:max(0, settings.financial_index_rollback_generations)])
        retained_ready = set()
        for dataset_rows in ({row["dataset"] for row in rows}):
            ready = [row["generation"] for row in rows
                     if row["dataset"] == dataset_rows and row["state"] == "READY"]
            retained_ready.update(ready[:max(1, settings.financial_index_retained_ready)])
        result = []
        for row in rows:
            reasons = []
            if row["is_active"]:
                reasons.append("active")
            if row["generation"] in rollback:
                reasons.append("required_rollback")
            reasons.extend(item["kind"] for item in protected.get(row["generation"], []))
            if row["generation"] in retained_ready:
                reasons.append("retention_floor")
            eligible = row["state"] == "FAILED" or (row["state"] == "READY" and not reasons)
            metadata = json.loads(row["metadata"])
            collection = metadata.get("collection")
            points = None
            if collection:
                with self._dense_lock:
                    if self.dense.collection_exists(collection):
                        points = self.dense.count(collection, exact=True).count
            result.append({"dataset_id": row["dataset"], "generation": row["generation"],
                           "state": row["state"], "active": bool(row["is_active"]),
                           "chunks": row["n"], "collection": collection, "vector_points": points,
                           "protections": protected.get(row["generation"], []),
                           "protected_reasons": sorted(set(reasons)), "cleanup_eligible": eligible})
        disk_bytes = sum(path.stat().st_size for path in self.root.rglob("*") if path.is_file())
        return {"root_disk_bytes": disk_bytes, "automatic_cleanup": False,
                "policy": {"retained_ready": settings.financial_index_retained_ready,
                           "rollback_generations": settings.financial_index_rollback_generations},
                "generations": result, "recent_cleanup_audit": audits}

    def cleanup_generations(self, generations: list[str], *, apply=False, fail_after_dense=False):
        if not generations or len(generations) > 20 or len(generations) != len(set(generations)) or any(
                not re.fullmatch(r"[0-9a-f]{64}", value) for value in generations):
            raise ValueError("INVALID_CLEANUP_GENERATIONS")
        inventory = {item["generation"]: item for item in self.retention_inventory()["generations"]}
        plan = []
        for generation in generations:
            item = inventory.get(generation)
            if item is None:
                raise ValueError("INDEX_GENERATION_NOT_FOUND")
            if not item["cleanup_eligible"]:
                raise ValueError("GENERATION_PROTECTED_FROM_CLEANUP")
            plan.append(item)
        if not apply:
            return {"dry_run": True, "planned": plan}
        completed = []
        self._build_lock.acquire()
        try:
            with self._cleanup_access():
                for item in plan:
                    generation = item["generation"]
                    now = datetime.now(timezone.utc).isoformat()
                    with closing(self.lexical.connect()) as c, c:
                        audit_id = c.execute("INSERT INTO cleanup_audit(generation,state,requested_at) VALUES(?,'STARTED',?)",
                                             (generation, now)).lastrowid
                    try:
                        collection = item["collection"]
                        if collection:
                            with self._dense_lock:
                                if self.dense.collection_exists(collection):
                                    self.dense.delete_collection(collection)
                        if fail_after_dense:
                            raise RuntimeError("CONTROLLED_CLEANUP_INTERRUPTION")
                        with closing(self.lexical.connect()) as c, c:
                            c.execute("DELETE FROM members WHERE generation=?", (generation,))
                            c.execute("DELETE FROM frequencies WHERE generation=?", (generation,))
                            c.execute("DELETE FROM generation_protections WHERE generation=?", (generation,))
                            c.execute("DELETE FROM generations WHERE generation=?", (generation,))
                            c.execute("DELETE FROM postings WHERE cid NOT IN (SELECT DISTINCT cid FROM members)")
                            c.execute("DELETE FROM documents WHERE cid NOT IN (SELECT DISTINCT cid FROM members)")
                            used = {sha256(json.loads(row[0])["text"][:6000].encode()).hexdigest()
                                    for row in c.execute("SELECT payload FROM documents")}
                            if used:
                                placeholders = ",".join("?" for _ in used)
                                c.execute(f"DELETE FROM vectors WHERE input_hash NOT IN ({placeholders})", tuple(used))
                            else:
                                c.execute("DELETE FROM vectors")
                            c.execute("UPDATE cleanup_audit SET state='COMPLETE',completed_at=? WHERE id=?",
                                      (datetime.now(timezone.utc).isoformat(), audit_id))
                        self.provenance_cache.invalidate_generation(generation)
                        completed.append(generation)
                    except Exception as exc:
                        with closing(self.lexical.connect()) as c, c:
                            c.execute("UPDATE cleanup_audit SET state='FAILED',completed_at=?,error_code=? WHERE id=?",
                                      (datetime.now(timezone.utc).isoformat(), _stable_error_code(exc), audit_id))
                        raise
        finally:
            self._build_lock.release()
        return {"dry_run": False, "deleted": completed}

    def describe(self):
        with closing(self.lexical.connect()) as c:
            rows = c.execute("SELECT g.*,a.generation= g.generation AS is_active FROM generations g LEFT JOIN active a ON a.dataset=g.dataset ORDER BY g.rowid DESC").fetchall()
        result = []
        for row in rows:
            metadata = json.loads(row["metadata"])
            error = row["error"]
            if error and not (error.isupper() and error.replace("_", "").isalnum()):
                error = "INDEX_BUILD_FAILED"
            result.append({"dataset_id": row["dataset"], "generation": row["generation"], "state": row["state"],
                           "active": bool(row["is_active"]), "chunks": row["n"], "error": error,
                           "embedding": metadata["embedding"], "membership_hash": row["membership_hash"],
                           "manifests": [source["manifest"]["manifest_hash"] for source in metadata["sources"]],
                           "source_partial_documents": sorted({item for source in metadata["sources"] for item in source["manifest"]["partial_documents"]}),
                           "subset_policy": [source["per_filing_limit"] for source in metadata["sources"]]})
        return result

    def search(self, dataset: str, query: str, mode="hybrid", *, generation=None, top_k=5,
               candidate_limit=40, filters=None, allow_degraded=False, expected_manifests=None):
        with self._query_access():
            return self._search(dataset, query, mode, generation=generation, top_k=top_k,
                                candidate_limit=candidate_limit, filters=filters,
                                allow_degraded=allow_degraded, expected_manifests=expected_manifests)

    def _search(self, dataset: str, query: str, mode="hybrid", *, generation=None, top_k=5,
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
                vector = self.provider.embed_query(query)
                valid_vectors([vector], 1, metadata["embedding"]["dimension"])
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
                    points = self.dense.query_points(metadata["collection"], query=vector,
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
                    # Service/CLI callers keep the causal diagnostic. The HTTP
                    # boundary maps it to a stable code and never returns this text.
                    raise RuntimeError("DENSE_INDEX_UNAVAILABLE_OR_MISMATCH: " + str(exc)) from exc
                degraded = _stable_error_code(exc, "DENSE_INDEX_UNAVAILABLE_OR_MISMATCH")
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
                    sources[source_key] = verified_source(
                        frozen, cache=self.provenance_cache, generation=record["generation"])
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
                "provenance_cache": self.provenance_cache.diagnostics(),
                "source_partial_documents": sorted({item for source in metadata["sources"] for item in source["manifest"]["partial_documents"]})}

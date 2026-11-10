"""Read-only product adapter for the pinned P10 SEC development generation.

This exposes genuine source-verified BM25/Dense/RRF results. It neither builds
nor activates a generation, and it never opens validation or held-out sources.
"""
from contextlib import closing
from pathlib import Path
from threading import RLock
from time import perf_counter
import json
import os

from qdrant_client import QdrantClient, models

from app.financial_index.corpus import ProvenanceCache, verified_source
from app.financial_index.ownership import LocalQdrantOwnership
from app.product.workspace import DIGEST, OllamaEmbedder
from app.research_retrieval.snapshot import FrozenResearchSnapshot
from scripts.p10_build_isolated_vectors import COLLECTION, point_id, source_records


class SecResearchIndex:
    def __init__(self, root: Path, vector_root: Path, qa_root: Path | None = None, embedder=None, *, lexical_only=False):
        self.root = Path(root).resolve(strict=True)
        self.vector_root = Path(vector_root).resolve(strict=not lexical_only)
        from app.product.sec_product_snapshot import snapshot as open_snapshot
        snapshot = open_snapshot(self.root)
        prepared, source_hashes = source_records(snapshot)
        freeze = snapshot.freeze
        self.lexical_only = lexical_only
        self.publication_path = self.root/'lexical-publication.json' if lexical_only else self.vector_root/'generation_manifest.json'
        self.identity = json.loads(self.publication_path.read_text(encoding='utf-8'))
        if lexical_only:
            if freeze.get('purpose')!='PRODUCT_USER_LIBRARY_SOURCE_ONLY' or self.identity.get('state')!='LEXICAL_READY' or (
                    self.identity['generation'],self.identity['manifest_hash'],self.identity['parent_count'])!=(
                    freeze['generation'],freeze['manifest_hash'],len(prepared)):
                raise ValueError('SEC_LEXICAL_PUBLICATION_MISMATCH')
        else:
            if (self.identity.get("state") != "READY"
                or self.identity.get("generation") != freeze["generation"]
                or self.identity.get("manifest_hash") != freeze["manifest_hash"]
                or self.identity.get("completed_points") != len(prepared)
                or self.identity.get("parent_count") != len(prepared)
                or self.identity.get("model_digest") != DIGEST
                or self.identity.get("dimension") != 768
                or self.identity.get("distance") != "COSINE"
                or self.identity.get("query_prefix") != "search_query: "
                or self.identity.get("document_prefix") != "search_document: "
                or sorted(self.identity.get("source_raw_hashes", [])) != source_hashes):
                raise ValueError("SEC_SEARCH_QA_GENERATION_MISMATCH")
        if qa_root:
            qa_freeze = open_snapshot(Path(qa_root).resolve(strict=True)).freeze
            if (qa_freeze["generation"], qa_freeze["manifest_hash"]) != (freeze["generation"], freeze["manifest_hash"]):
                raise ValueError("SEC_SEARCH_QA_GENERATION_MISMATCH")
        self.lexical = snapshot.lexical
        self.record = self.lexical.generation(snapshot.catalog.dataset_id, freeze["generation"])
        if self.record["state"] != "READY" or self.record["n"] != len(prepared):
            raise ValueError("SEC_LEXICAL_MEMBERSHIP_INCOMPLETE")
        with closing(self.lexical.connect()) as db:
            rows = db.execute("SELECT d.cid,m.source FROM documents d JOIN members m ON m.cid=d.cid "
                              "WHERE m.generation=?", (freeze["generation"],)).fetchall()
        source_by_id = {row["cid"]: json.loads(row["source"]) for row in rows}
        self.parents = [{**item, "chunk": item["parent"], "frozen": source_by_id[item["cid"]]}
                        for item in prepared]
        self.by_id = {p["cid"]: p for p in self.parents}
        self.embedder = embedder or OllamaEmbedder()
        self._lock = RLock()
        self._owner = None
        self._qdrant = None
        self._cache = ProvenanceCache(max_entries=2, max_bytes=64 * 1024 * 1024)
        self.catalog_rows = []
        seen = set()
        for item in self.parents:
            parent = item["chunk"]
            if parent.filing_id in seen:
                continue
            seen.add(parent.filing_id)
            m = parent.metadata
            self.catalog_rows.append({"ticker": m.get("ticker", ""), "cik": m["cik"],
                "issuer": m.get("company_name", ""), "accession": m["accession_number"],
                "filing_id": parent.filing_id, "form": m.get("form_type", ""),
                "report_period": m.get("report_date", ""), "fiscal_year": m.get("fiscal_year"),
                "fiscal_period": m.get("fiscal_period"), "source_url": m["source_url"],
                "raw_sha256": item["raw_hash"], "extraction_status": parent.extraction_status})
        self.catalog_rows.sort(key=lambda row: (row["ticker"], row["accession"]))
        for row in self.catalog_rows:
            row["chunks"] = sum(p["chunk"].filing_id == row["filing_id"] for p in self.parents)

    def _dense(self):
        if self._qdrant is None:
            self._owner = LocalQdrantOwnership(self.vector_root / "qdrant")
            try:
                self._qdrant = QdrantClient(path=str(self.vector_root / "qdrant"))
                if self._qdrant.count(COLLECTION, exact=True).count != len(self.parents):
                    raise ValueError("SEC_VECTOR_MEMBERSHIP_CHANGED")
            except Exception:
                if self._qdrant is not None:
                    self._qdrant.close()
                    self._qdrant = None
                self._owner.close()
                self._owner = None
                raise
        return self._qdrant

    def close(self):
        with self._lock:
            if self._qdrant is not None:
                self._qdrant.close()
                self._qdrant = None
            if self._owner is not None:
                self._owner.close()
                self._owner = None

    def catalog(self):
        return {"status": "READY", "dataset_id": self.identity["dataset_id"],
                "generation": self.identity["generation"],
                "manifest_hash": self.identity["manifest_hash"],
                "parents": len(self.parents), "dense_vectors": self.identity["completed_points"],
                "model_digest": None if self.lexical_only else DIGEST, "filings": self.catalog_rows,
                "scope_note": "Official SEC development filings shared with Financial AI; not human-adjudicated evaluation"}

    def search(self, query: str, mode: str = "hybrid", top_k: int = 5,
               ticker: str = "", report_period: str = "", _filing_ids=None):
        if mode not in {"bm25", "dense", "hybrid"} or not 1 <= top_k <= 20 or not query.strip() or len(query) > 2000:
            raise ValueError("INVALID_SEC_SEARCH_REQUEST")
        if self.lexical_only and mode!='bm25':
            raise ValueError('SEC_DENSE_GENERATION_NOT_READY')
        selected = [r for r in self.catalog_rows if (not ticker or r["ticker"] == ticker.upper())
                    and (not report_period or r["report_period"] == report_period)
                    and (_filing_ids is None or r['filing_id'] in _filing_ids)]
        if not selected:
            return {"status": "NO_ELIGIBLE_FILING", "results": [], "generation": self.identity["generation"]}
        with self._lock:
            started = perf_counter()
            filing_ids = [r["filing_id"] for r in selected]
            filters = {"filing_ids": filing_ids}
            b, d = [], []
            b_started = perf_counter()
            if mode in {"bm25", "hybrid"}:
                b = self.lexical.search(query, self.record, 40, filters)
            b_ms = (perf_counter() - b_started) * 1000
            embed_ms = dense_ms = 0.0
            if mode in {"dense", "hybrid"}:
                self.embedder.identity()
                e_started = perf_counter()
                vector = self.embedder.embed([query], query=True)[0]
                embed_ms = (perf_counter() - e_started) * 1000
                d_started = perf_counter()
                points = self._dense().query_points(COLLECTION, query=vector, limit=40,
                    query_filter=models.Filter(must=[models.FieldCondition(key="filing_id",
                        match=models.MatchAny(any=filing_ids))]), with_payload=True).points
                for point in points:
                    payload = point.payload or {}
                    item = self.by_id.get(payload.get("chunk_id"))
                    if (item is None or str(point.id) != point_id(item["cid"])
                        or payload.get("generation") != self.identity["generation"]
                        or payload.get("manifest_hash") != self.identity["manifest_hash"]
                        or payload.get("model_digest") != DIGEST
                        or payload.get("raw_hash") != item["frozen"]["raw_hash"]
                        or payload.get("payload_hash") != item["payload_hash"]
                        or item["chunk"].filing_id not in filing_ids):
                        raise ValueError("SEC_VECTOR_SOURCE_MISMATCH")
                    d.append({"chunk_id": item["cid"], "dense_score": float(point.score)})
                dense_ms = (perf_counter() - d_started) * 1000
            ranks = {}
            for channel, hits, key in (("B", b, "bm25_score"), ("D", d, "dense_score")):
                for rank, hit in enumerate(hits, 1):
                    row = ranks.setdefault(hit["chunk_id"], {"channels": {}, "scores": {}})
                    row["channels"][channel] = rank
                    row["scores"][channel] = hit[key]
            scored = []
            for cid, row in ranks.items():
                score = (row["scores"].get("B") if mode == "bm25" else
                         row["scores"].get("D") if mode == "dense" else
                         sum(1 / (60 + rank) for rank in row["channels"].values()))
                scored.append((score, cid, row))
            scored.sort(key=lambda x: (-x[0], x[1]))
            output = []
            verified_by_source = {}
            for rank, (score, cid, item) in enumerate(scored[:top_k], 1):
                parent = self.by_id[cid]
                frozen = parent["frozen"]
                source_key = json.dumps(frozen,sort_keys=True)
                if source_key not in verified_by_source:
                    verified_by_source[source_key] = verified_source(frozen,cache=self._cache,
                                                                     generation=self.identity["generation"])
                canonical = verified_by_source[source_key]
                if cid not in canonical or canonical[cid].model_dump(mode="json") != parent["chunk"].model_dump(mode="json"):
                    raise ValueError("SEC_PARENT_SOURCE_CHANGED")
                chunk = parent["chunk"]
                source = next(r for r in selected if r["filing_id"] == chunk.filing_id)
                output.append({"rank": rank, "chunk_id": cid, "score": score,
                    "bm25_rank": item["channels"].get("B"), "dense_rank": item["channels"].get("D"),
                    "bm25_score": item["scores"].get("B"), "dense_score": item["scores"].get("D"),
                    "ticker": source["ticker"], "cik": source["cik"],
                    "issuer": source["issuer"], "form": source["form"],
                    "report_period": source["report_period"], "accession": source["accession"],
                    "filing_id": source["filing_id"], "source_url": source["source_url"],
                    "source_sha256": source["raw_sha256"], "text": chunk.text[:1800],
                    "source_location": chunk.source_location.model_dump(mode="json"),
                    "extraction_status": chunk.extraction_status,
                    "provenance_status": "VERIFIED_LOCAL_SEC_SOURCE_BYTES"})
                if len(os.getenv('STUDIO_API_TOKEN',''))>=16:
                    from app.product.sec_viewer import reference,server_key
                    from app.product.api import workspace
                    output[-1]['source_reference']=reference(self,cid,server_key(workspace().root))
            return {"status": "READY", "dataset_id": self.identity["dataset_id"], "mode": mode,
                "generation": self.identity["generation"], "manifest_hash": self.identity["manifest_hash"],
                "results": output, "latency_ms": round((perf_counter()-started)*1000, 2),
                "timings_ms": {"bm25": round(b_ms, 2), "embedding": round(embed_ms, 2),
                               "dense": round(dense_ms, 2)},
                "fusion": {"method": "RRF", "k": 60} if mode == "hybrid" else None,
                "scope_note": "Filing report period filters do not verify every financial statement column period"}

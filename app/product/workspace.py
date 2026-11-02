"""Bounded, source-bound PDF BM25/Dense/RRF workspace.

This store never opens accepted SEC or Qdrant generations. A PDF is searchable
only after its SQLite postings and isolated Qdrant vectors are both complete.
"""
from __future__ import annotations

from contextlib import closing
from datetime import datetime, timezone
from hashlib import sha256
import io
import json
import math
import os
from pathlib import Path
import re
import shutil
import sqlite3
from threading import RLock, Lock
from time import perf_counter
from uuid import NAMESPACE_URL, uuid5

import pymupdf
from qdrant_client import QdrantClient, models
import requests

from app.financial_index.ownership import LocalQdrantOwnership, require_supported_embedded_qdrant


OWNER = "TOPIC3_FINAL_PRODUCT_USER_PDF_WORKSPACE_V1"
MODEL = "nomic-embed-text:latest"
DIGEST = "0a109f422b47e3a30ba2b10eca18548e944e8a23073ee3f3e947efcf3c45e59f"
COLLECTION = "studio_user_pdf_v1"
DIMENSION = 768
MAX_PDF_BYTES = 20 * 1024 * 1024
MAX_PAGES = 250
MAX_CHUNKS = 3000
MAX_TEXT_CHARS = 2_000_000


def _now():
    return datetime.now(timezone.utc).isoformat()


def _hash_file(path: Path):
    digest = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _point_id(chunk_id: str):
    return str(uuid5(NAMESPACE_URL, "studio-pdf-v1/" + chunk_id))


def _tokens(query: str):
    return list(dict.fromkeys(re.findall(r"\w+", query.casefold(), re.UNICODE)))[:30]


def _validate_vector(vector):
    if len(vector) != DIMENSION or not all(isinstance(x, (float, int)) and math.isfinite(x) for x in vector):
        raise ValueError("EMBEDDING_VECTOR_INVALID")


class OllamaEmbedder:
    def __init__(self, base_url: str = "http://127.0.0.1:11434"):
        self.base_url = base_url.rstrip("/")
        if self.base_url not in {"http://127.0.0.1:11434", "http://localhost:11434"}:
            raise ValueError("LOCAL_OLLAMA_ENDPOINT_REQUIRED")
        self.session = requests.Session()

    def identity(self):
        response = self.session.get(self.base_url + "/api/tags", timeout=5)
        response.raise_for_status()
        found = next((m for m in response.json().get("models", []) if m.get("name") == MODEL), None)
        if not found or found.get("digest") != DIGEST:
            raise ValueError("EMBEDDING_MODEL_DIGEST_MISMATCH")
        return {"model": MODEL, "digest": DIGEST, "dimension": DIMENSION,
                "document_prefix": "search_document: ", "query_prefix": "search_query: ",
                "distance": "COSINE"}

    def embed(self, texts: list[str], *, query: bool = False):
        prefix = "search_query: " if query else "search_document: "
        response = self.session.post(self.base_url + "/api/embed",
            json={"model": MODEL, "input": [prefix + text[:6000] for text in texts],
                  "truncate": True, "keep_alive": "5m"}, timeout=90)
        response.raise_for_status()
        vectors = response.json()["embeddings"]
        if len(vectors) != len(texts):
            raise ValueError("EMBEDDING_COUNT_MISMATCH")
        for vector in vectors:
            _validate_vector(vector)
        return vectors


class PdfWorkspace:
    TABLE_LAYOUT_VERSION = 'TABLE_LAYOUT_V3'

    def _extraction_engine(self):
        from app.product import pdf_extract
        return pdf_extract

    def _page_tables(self, saved, page_number):
        from app.product.pdf_extract import table_candidates
        return table_candidates(saved.get('lines', []), page_number, saved.get('engine', {}).get('correction_clockwise', 0))

    def __init__(self, root: Path, embedder=None):
        self.root = Path(root).resolve()
        self._lock = RLock()
        self._processing = set()
        self._ingestion_lock = Lock()
        self.embedder = embedder or OllamaEmbedder(os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434"))
        if self.root.exists() and any(self.root.iterdir()):
            marker = self.root / "ownership.json"
            if not marker.exists() or json.loads(marker.read_text(encoding="utf-8")).get("owner") != OWNER:
                raise ValueError("UNOWNED_PRODUCT_WORKSPACE")
        self.root.mkdir(parents=True, exist_ok=True)
        marker = self.root / "ownership.json"
        if not marker.exists():
            marker.write_text(json.dumps({"owner": OWNER, "version": 1}), encoding="utf-8")
        self.files = self.root / "files"
        self.files.mkdir(exist_ok=True)
        self.db_path = self.root / "index.sqlite3"
        self.qdrant_path = self.root / "qdrant"
        self.qdrant_path.mkdir(exist_ok=True)
        self._owner = None
        self._qdrant = None
        with closing(self._connect()) as db, db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS documents(
                  id TEXT PRIMARY KEY, filename TEXT NOT NULL, sha256 TEXT NOT NULL UNIQUE,
                  issuer TEXT NOT NULL DEFAULT '', document_type TEXT NOT NULL DEFAULT 'PDF',
                  report_period TEXT NOT NULL DEFAULT '', size_bytes INTEGER NOT NULL,
                  status TEXT NOT NULL, stage TEXT NOT NULL, error_code TEXT,
                  pages INTEGER NOT NULL DEFAULT 0, chunks INTEGER NOT NULL DEFAULT 0,
                  created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS chunks(
                  id TEXT PRIMARY KEY, document_id TEXT NOT NULL, page INTEGER NOT NULL,
                  text TEXT NOT NULL, text_hash TEXT NOT NULL, page_text_hash TEXT NOT NULL,
                  line_boxes TEXT NOT NULL, FOREIGN KEY(document_id) REFERENCES documents(id));
                CREATE INDEX IF NOT EXISTS chunks_document ON chunks(document_id);
                CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(chunk_id UNINDEXED, text, tokenize='unicode61');
                CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts_vi USING fts5(chunk_id UNINDEXED, text, tokenize='unicode61 remove_diacritics 2');
                CREATE TABLE IF NOT EXISTS page_evidence(
                  document_id TEXT NOT NULL,page INTEGER NOT NULL,payload TEXT NOT NULL,payload_hash TEXT NOT NULL,
                  PRIMARY KEY(document_id,page));
                CREATE TABLE IF NOT EXISTS reviewed_facts(id TEXT PRIMARY KEY,document_id TEXT NOT NULL,payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS analysis_jobs(id TEXT PRIMARY KEY,payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS fact_review_history(event_hash TEXT PRIMARY KEY,fact_id TEXT NOT NULL,payload TEXT NOT NULL);
            """)
            # New derived lexical cache only; original text, old FTS, IDs and dense vectors remain intact.
            from app.product.pdf_extract import folded
            for row in db.execute('SELECT id,text FROM chunks WHERE id NOT IN (SELECT chunk_id FROM chunks_fts_vi)').fetchall():
                db.execute('INSERT INTO chunks_fts_vi VALUES(?,?)',(row['id'],folded(row['text'])))
            for row in db.execute('SELECT id,payload FROM analysis_jobs').fetchall():
                job=json.loads(row['payload'])
                if job.get('status') in {'QUEUED','RUNNING'}:
                    job['status']='INTERRUPTED';db.execute('UPDATE analysis_jobs SET payload=? WHERE id=?',(json.dumps(job),row['id']))
            db.execute("UPDATE documents SET status='INTERRUPTED', stage='INTERRUPTED', updated_at=? "
                       "WHERE status IN ('UPLOADED','RETRY_QUEUED','PROCESSING','EXTRACTING',"
                       "'CHUNKING','INDEXING_BM25','EMBEDDING','INDEXING_DENSE')", (_now(),))
        self._revalidate_ready()

    def _revalidate_ready(self):
        """A persisted READY flag is trusted only with matching bytes and both indexes."""
        ready = [doc for doc in self.list_documents() if doc["status"] == "READY"]
        if not ready:
            return
        client = self._vector_client()
        for doc in ready:
            try:
                path = self.files / f"{doc['id']}.pdf"
                if not path.is_file() or _hash_file(path) != doc["sha256"]:
                    raise ValueError("PDF_SOURCE_HASH_MISMATCH")
                with closing(self._connect()) as db:
                    rows = db.execute("SELECT id,text_hash FROM chunks WHERE document_id=? ORDER BY id",
                                      (doc["id"],)).fetchall()
                    fts_count = db.execute("SELECT COUNT(*) AS n FROM chunks_fts f JOIN chunks c "
                        "ON c.id=f.chunk_id WHERE c.document_id=?", (doc["id"],)).fetchone()["n"]
                    vi_count=db.execute('SELECT COUNT(*) AS n FROM chunks_fts_vi f JOIN chunks c ON c.id=f.chunk_id WHERE c.document_id=?',(doc['id'],)).fetchone()['n']
                if not rows or len(rows) != doc["chunks"] or fts_count != len(rows) or vi_count!=len(rows):
                    raise ValueError("PDF_INDEX_MEMBERSHIP_INCOMPLETE")
                for start in range(0, len(rows), 100):
                    batch = rows[start:start + 100]
                    points = client.retrieve(COLLECTION, ids=[_point_id(row["id"]) for row in batch],
                                             with_payload=True, with_vectors=True)
                    if len(points) != len(batch):
                        raise ValueError("PDF_INDEX_MEMBERSHIP_INCOMPLETE")
                    expected = {row["id"]: row for row in batch}
                    for point in points:
                        payload = point.payload or {}
                        cid = payload.get("chunk_id")
                        row = expected.get(cid)
                        if (row is None or str(point.id) != _point_id(cid)
                            or payload.get("source_hash") != doc["sha256"]
                            or payload.get("text_hash") != row["text_hash"]
                            or payload.get("document_id") != doc["id"]
                            or payload.get("model_digest") != DIGEST):
                            raise ValueError("PDF_VECTOR_SOURCE_MISMATCH")
                        _validate_vector(point.vector)
            except ValueError as exc:
                self._stage(doc["id"], "FAILED", "RESTART_VALIDATION", error=str(exc))

    def _connect(self):
        db = sqlite3.connect(self.db_path, timeout=15)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA busy_timeout=15000")
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA journal_mode=WAL")
        return db

    def _vector_client(self):
        if self._qdrant is None:
            require_supported_embedded_qdrant()
            self._owner = LocalQdrantOwnership(self.qdrant_path)
            try:
                self._qdrant = QdrantClient(path=str(self.qdrant_path))
                if not self._qdrant.collection_exists(COLLECTION):
                    self._qdrant.create_collection(COLLECTION, vectors_config=models.VectorParams(
                        size=DIMENSION, distance=models.Distance.COSINE))
                config = self._qdrant.get_collection(COLLECTION).config.params.vectors
                if config.size != DIMENSION or config.distance != models.Distance.COSINE:
                    raise ValueError("PRODUCT_VECTOR_CONFIG_MISMATCH")
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

    def list_documents(self):
        with closing(self._connect()) as db:
            return [dict(row) for row in db.execute("SELECT * FROM documents ORDER BY created_at DESC")]

    def document(self, document_id: str):
        with closing(self._connect()) as db:
            row = db.execute("SELECT * FROM documents WHERE id=?", (document_id,)).fetchone()
        return dict(row) if row else None

    def add_pdf(self, name: str, data: bytes, issuer: str = "", document_type: str = "PDF",
                report_period: str = ""):
        if not name.lower().endswith(".pdf") or not data.startswith(b"%PDF-"):
            raise ValueError("PDF_SIGNATURE_REQUIRED")
        if not 0 < len(data) <= MAX_PDF_BYTES:
            raise ValueError("PDF_SIZE_OUT_OF_BOUNDS")
        if len(issuer) > 160 or len(document_type) > 40 or len(report_period) > 80:
            raise ValueError("DOCUMENT_METADATA_TOO_LONG")
        if shutil.disk_usage(self.root).free < len(data) + 256 * 1024 * 1024:
            raise RuntimeError("PRODUCT_WORKSPACE_DISK_GUARD")
        digest = sha256(data).hexdigest()
        document_id = digest[:32]
        with self._lock:
            prior = self.document(document_id)
            if prior:
                return {**prior, "duplicate": True}
            filename = Path(name.replace("\\", "/")).name[:160] or "document.pdf"
            target = self.files / f"{document_id}.pdf"
            temporary = self.files / f".{document_id}.tmp"
            temporary.write_bytes(data)
            temporary.replace(target)
            from app.product.document_metadata import extract_metadata,save_metadata
            try:metadata=extract_metadata(target)
            except (RuntimeError,ValueError) as exc:
                target.unlink(missing_ok=True)
                raise ValueError('PDF_CONTENT_INVALID_OR_ENCRYPTED') from exc
            issuer=issuer or metadata['fields']['issuer']['value'] or ''
            report_period=report_period or metadata['fields']['report_period']['value'] or ''
            if document_type=='PDF':document_type=metadata['fields']['document_type']['value'] or 'PDF'
            now = _now()
            with closing(self._connect()) as db, db:
                db.execute("INSERT INTO documents(id,filename,sha256,issuer,document_type,report_period,"
                           "size_bytes,status,stage,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                           (document_id, filename, digest, issuer.strip(), document_type.strip(),
                            report_period.strip(), len(data), "UPLOADED", "UPLOAD", now, now))
            save_metadata(self,document_id,metadata)
            return {**self.document(document_id), "duplicate": False,'metadata':metadata}

    def _stage(self, document_id: str, status: str, stage: str, *, error=None, pages=None, chunks=None):
        with closing(self._connect()) as db, db:
            db.execute("UPDATE documents SET status=?,stage=?,error_code=?,pages=COALESCE(?,pages),"
                       "chunks=COALESCE(?,chunks),updated_at=? WHERE id=?",
                       (status, stage, error, pages, chunks, _now(), document_id))

    @staticmethod
    def _extract(path: Path, document_id: str):
        found = []
        with pymupdf.open(path) as pdf:
            if pdf.page_count == 0 or pdf.page_count > MAX_PAGES:
                raise ValueError("PDF_PAGE_LIMIT")
            total_chars = 0
            for page_number, page in enumerate(pdf, 1):
                page_text_hash = sha256(page.get_text("text").encode("utf-8")).hexdigest()
                lines = []
                for block in page.get_text("dict").get("blocks", []):
                    if "lines" not in block:
                        continue
                    for line in block["lines"]:
                        spans = [s for s in line.get("spans", []) if s.get("text", "").strip()]
                        if not spans:
                            continue
                        text = "".join(s["text"] for s in spans).strip()
                        box = [min(s["bbox"][0] for s in spans), min(s["bbox"][1] for s in spans),
                               max(s["bbox"][2] for s in spans), max(s["bbox"][3] for s in spans)]
                        lines.append((text, [round(float(v), 2) for v in box]))
                        total_chars += len(text)
                        if total_chars > MAX_TEXT_CHARS:
                            raise ValueError("PDF_TEXT_LIMIT")
                group = []
                length = 0
                def flush():
                    nonlocal group, length
                    if not group:
                        return
                    text = "\n".join(item[0] for item in group)
                    cid = f"pdf_{document_id}_{page_number}_{len(found):05d}"
                    found.append({"id": cid, "document_id": document_id, "page": page_number,
                                  "text": text, "text_hash": sha256(text.encode()).hexdigest(),
                                  "page_text_hash": page_text_hash,
                                  "line_boxes": [item[1] for item in group]})
                    group, length = [], 0
                    if len(found) > MAX_CHUNKS:
                        raise ValueError("PDF_CHUNK_LIMIT")
                for line in lines:
                    if group and length + len(line[0]) > 700:
                        flush()
                    group.append(line)
                    length += len(line[0])
                flush()
            if not found:
                raise ValueError("PDF_NO_EXTRACTABLE_TEXT")
            return pdf.page_count, found

    def process(self, document_id: str):
        with self._lock:
            if document_id in self._processing:
                return self.document(document_id)
            self._processing.add(document_id)
        try:
            with self._ingestion_lock:
                return self._process_document(document_id)
        finally:
            with self._lock:
                self._processing.discard(document_id)

    def _process_document(self, document_id: str):
        # Processing is single-owner per document; progress reads remain available.
        doc = self.document(document_id)
        if doc is None:
            raise ValueError("DOCUMENT_NOT_FOUND")
        if doc["status"] == "READY":
            return doc
        path = self.files / f"{document_id}.pdf"
        try:
            if not path.is_file() or _hash_file(path) != doc["sha256"]:
                raise ValueError("PDF_SOURCE_HASH_MISMATCH")
            self._stage(document_id, "PROCESSING", "EXTRACTING")
            engine = self._extraction_engine()
            VERSION = engine.VERSION
            def checkpoint(number):
                with closing(self._connect()) as db:
                    row=db.execute('SELECT payload,payload_hash FROM page_evidence WHERE document_id=? AND page=?',
                                   (document_id,number)).fetchone()
                if row and sha256(row['payload'].encode()).hexdigest()==row['payload_hash']:
                    saved=json.loads(row['payload'])
                    if saved.get('status')!='FAILED' and saved.get('version')==VERSION and saved.get('source_sha256')==doc['sha256']:
                        return saved
                return None
            def progress(number,saved,total):
                saved['source_sha256']=doc['sha256']
                encoded=json.dumps(saved,ensure_ascii=False,sort_keys=True)
                with closing(self._connect()) as db,db:
                    db.execute('INSERT OR REPLACE INTO page_evidence VALUES(?,?,?,?)',
                               (document_id,number,encoded,sha256(encoded.encode()).hexdigest()))
                self._stage(document_id,'PROCESSING',f'EXTRACTING {number}/{total}',pages=total)
            pages, chunks = engine.extract_document(path, document_id, checkpoint, progress)
            self._stage(document_id, "PROCESSING", "CHUNKING", pages=pages, chunks=len(chunks))
            self.embedder.identity()
            with self._lock:
                client = self._vector_client()
            ids = [_point_id(c["id"]) for c in chunks]
            with closing(self._connect()) as db:
                old_ids = [_point_id(r["id"]) for r in db.execute(
                    "SELECT id FROM chunks WHERE document_id=?", (document_id,))]
            stale_ids = list(set(ids) | set(old_ids))
            if stale_ids:
                with self._lock:
                    client.delete(COLLECTION, points_selector=models.PointIdsList(points=stale_ids), wait=True)
            self._stage(document_id, "PROCESSING", "INDEXING_BM25")
            with closing(self._connect()) as db, db:
                old = [r["id"] for r in db.execute("SELECT id FROM chunks WHERE document_id=?", (document_id,))]
                for cid in old:
                    db.execute("DELETE FROM chunks_fts WHERE chunk_id=?", (cid,))
                    db.execute("DELETE FROM chunks_fts_vi WHERE chunk_id=?", (cid,))
                db.execute("DELETE FROM chunks WHERE document_id=?", (document_id,))
                for c in chunks:
                    db.execute("INSERT INTO chunks VALUES(?,?,?,?,?,?,?)", (c["id"], document_id,
                               c["page"], c["text"], c["text_hash"], c["page_text_hash"],
                               json.dumps(c["line_boxes"])))
                    db.execute("INSERT INTO chunks_fts(chunk_id,text) VALUES(?,?)", (c["id"], c["text"]))
                    from app.product.pdf_extract import folded
                    db.execute("INSERT INTO chunks_fts_vi(chunk_id,text) VALUES(?,?)", (c["id"], folded(c["text"])))
            self._stage(document_id, "PROCESSING", "EMBEDDING")
            for start in range(0, len(chunks), 4):
                if shutil.disk_usage(self.root).free < 256 * 1024 * 1024:
                    raise RuntimeError("PRODUCT_WORKSPACE_DISK_GUARD")
                batch = chunks[start:start + 4]
                vectors = self.embedder.embed([c["text"] for c in batch])
                self._stage(document_id, "PROCESSING", f"EMBEDDING {min(start+4,len(chunks))}/{len(chunks)}")
                with self._lock:
                    client.upsert(COLLECTION, points=[models.PointStruct(id=_point_id(c["id"]),
                        vector=vector, payload={"chunk_id": c["id"], "document_id": document_id,
                        "source_hash": doc["sha256"], "text_hash": c["text_hash"],
                        "model_digest": DIGEST}) for c, vector in zip(batch, vectors)], wait=True)
            self._stage(document_id, "PROCESSING", "INDEXING_DENSE")
            with closing(self._connect()) as db:
                row = db.execute("SELECT COUNT(*) AS n FROM chunks WHERE document_id=?", (document_id,)).fetchone()
                lexical_count = row["n"]
                vi_count=db.execute('SELECT COUNT(*) AS n FROM chunks_fts_vi f JOIN chunks c ON c.id=f.chunk_id WHERE c.document_id=?',(document_id,)).fetchone()['n']
            points = client.retrieve(COLLECTION, ids=ids, with_payload=True, with_vectors=True)
            if lexical_count != len(chunks) or vi_count!=len(chunks) or len(points) != len(chunks):
                raise ValueError("PDF_INDEX_MEMBERSHIP_INCOMPLETE")
            expected = {c["id"]: c for c in chunks}
            for point in points:
                cid = point.payload.get("chunk_id")
                c = expected.get(cid)
                if (c is None or str(point.id) != _point_id(cid) or point.payload.get("source_hash") != doc["sha256"]
                    or point.payload.get("text_hash") != c["text_hash"]
                    or point.payload.get("model_digest") != DIGEST):
                    raise ValueError("PDF_VECTOR_SOURCE_MISMATCH")
                _validate_vector(point.vector)
            self._stage(document_id, "READY", "READY", pages=pages, chunks=len(chunks))
        except Exception as exc:
            code = str(exc)
            if not (code.isupper() and code.replace("_", "").isalnum()):
                code = "PDF_PROCESSING_FAILED"
            self._stage(document_id, "FAILED", "FAILED", error=code)
        return self.document(document_id)

    def delete(self, document_id: str):
        with self._lock:
            if document_id in self._processing:
                raise ValueError("DOCUMENT_PROCESSING_IN_PROGRESS")
            doc = self.document(document_id)
            if doc is None:
                return False
            if doc["status"] in {"UPLOADED", "PROCESSING", "RETRY_QUEUED"}:
                raise ValueError("DOCUMENT_PROCESSING_IN_PROGRESS")
            with closing(self._connect()) as db:
                ids = [_point_id(r["id"]) for r in db.execute("SELECT id FROM chunks WHERE document_id=?", (document_id,))]
            if ids:
                self._vector_client().delete(COLLECTION, points_selector=models.PointIdsList(points=ids), wait=True)
            with closing(self._connect()) as db, db:
                for row in db.execute("SELECT id FROM chunks WHERE document_id=?", (document_id,)):
                    db.execute("DELETE FROM chunks_fts WHERE chunk_id=?", (row["id"],))
                    db.execute("DELETE FROM chunks_fts_vi WHERE chunk_id=?", (row["id"],))
                db.execute("DELETE FROM chunks WHERE document_id=?", (document_id,))
                db.execute("DELETE FROM documents WHERE id=?", (document_id,))
                db.execute("DELETE FROM page_evidence WHERE document_id=?", (document_id,))
                db.execute("DELETE FROM reviewed_facts WHERE document_id=?", (document_id,))
                if db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='document_metadata'").fetchone():
                    db.execute('DELETE FROM document_metadata WHERE document_id=?',(document_id,))
                if db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='financial_chat_sessions'").fetchone():
                    db.execute('DELETE FROM financial_chat_sessions WHERE payload LIKE ?',('%'+document_id+'%',))
            (self.files / f"{document_id}.pdf").unlink(missing_ok=True)
            return True

    def _eligible(self, document_ids: list[str] | None):
        docs = [d for d in self.list_documents() if d["status"] == "READY"]
        if document_ids:
            requested = set(document_ids)
            docs = [d for d in docs if d["id"] in requested]
        return docs

    def first_chunk(self, document_id: str):
        with self._lock:
            doc = self.document(document_id)
            if doc is None or doc["status"] != "READY":
                raise ValueError("PDF_DOCUMENT_NOT_READY")
            path = self.files / f"{document_id}.pdf"
            if _hash_file(path) != doc["sha256"]:
                raise ValueError("PDF_SOURCE_HASH_MISMATCH")
            with closing(self._connect()) as db:
                row = db.execute("SELECT * FROM chunks WHERE document_id=? ORDER BY page, id LIMIT 1",
                                 (document_id,)).fetchone()
            if row is None or sha256(row["text"].encode()).hexdigest() != row["text_hash"]:
                raise ValueError("PDF_CHUNK_SOURCE_MISMATCH")
            return {"rank": 1, "chunk_id": row["id"], "document_id": document_id,
                    "filename": doc["filename"], "issuer": doc["issuer"],
                    "document_type": doc["document_type"], "report_period": doc["report_period"],
                    "page": row["page"], "text": row["text"][:1400],
                    "source_sha256": doc["sha256"], "provenance_status": "VERIFIED_LOCAL_PDF_BYTES"}

    def search(self, query: str, mode: str = "hybrid", top_k: int = 5,
               document_ids: list[str] | None = None):
        if mode not in {"bm25", "dense", "hybrid"} or not 1 <= top_k <= 20 or not query.strip() or len(query) > 2000:
            raise ValueError("INVALID_PDF_SEARCH_REQUEST")
        started = perf_counter()
        with self._lock:
            docs = self._eligible(document_ids)
            if not docs:
                return {"mode": mode, "results": [], "documents": 0, "latency_ms": 0,
                        "status": "NO_READY_DOCUMENTS"}
            allowed = {d["id"]: d for d in docs}
            generation = sha256(json.dumps({'documents':sorted((d['id'],d['sha256'],d['chunks']) for d in docs),
                'lexical_version':'PDF_VI_FOLDED_FTS5_V2','embedding_digest':DIGEST,
                'embedding_policy':'nomic-prefix-first6000-truncate'},sort_keys=True,separators=(',',':')).encode()).hexdigest()
            from app.product.pdf_extract import folded
            terms = _tokens(folded(query))
            if not terms:
                raise ValueError("QUERY_HAS_NO_SEARCH_TERMS")
            b, d = [], []
            bm25_started = perf_counter()
            if mode in {"bm25", "hybrid"}:
                expression = " OR ".join('"' + term.replace('"', '""') + '"' for term in terms)
                with closing(self._connect()) as db:
                    placeholders = ",".join("?" for _ in allowed)
                    rows = db.execute("SELECT c.*, bm25(chunks_fts_vi) AS bm25_score FROM chunks_fts_vi "
                        "JOIN chunks c ON c.id=chunks_fts_vi.chunk_id WHERE chunks_fts_vi MATCH ? "
                        f"AND c.document_id IN ({placeholders}) ORDER BY bm25_score ASC, c.id ASC LIMIT 40",
                        (expression, *allowed)).fetchall()
                    b = [(dict(row), -float(row["bm25_score"])) for row in rows]
            bm25_ms = (perf_counter() - bm25_started) * 1000
            embed_ms = dense_ms = 0.0
            if mode in {"dense", "hybrid"}:
                self.embedder.identity()
                embed_started = perf_counter()
                vector = self.embedder.embed([query], query=True)[0]
                embed_ms = (perf_counter() - embed_started) * 1000
                dense_started = perf_counter()
                client = self._vector_client()
                points = client.query_points(COLLECTION, query=vector, limit=min(200, len(allowed) * 40),
                    query_filter=models.Filter(must=[models.FieldCondition(key="document_id",
                        match=models.MatchAny(any=list(allowed)))]), with_payload=True).points
                with closing(self._connect()) as db:
                    for point in points:
                        payload = point.payload or {}
                        cid = payload.get("chunk_id")
                        row = db.execute("SELECT * FROM chunks WHERE id=?", (cid,)).fetchone()
                        if (row is None or row["document_id"] not in allowed or str(point.id) != _point_id(cid)
                            or payload.get("source_hash") != allowed[row["document_id"]]["sha256"]
                            or payload.get("text_hash") != row["text_hash"] or payload.get("model_digest") != DIGEST):
                            raise ValueError("PDF_VECTOR_SOURCE_MISMATCH")
                        d.append((dict(row), float(point.score)))
                d = d[:40]
                dense_ms = (perf_counter() - dense_started) * 1000
            ranked = {}
            for channel, rows in (("B", b), ("D", d)):
                for rank, (row, score) in enumerate(rows, 1):
                    entry = ranked.setdefault(row["id"], {"row": row, "channels": {}, "scores": {}})
                    entry["channels"][channel] = rank
                    entry["scores"][channel] = score
            results = []
            for cid, entry in ranked.items():
                if mode == "bm25":
                    score = entry["scores"].get("B", float("-inf"))
                elif mode == "dense":
                    score = entry["scores"].get("D", float("-inf"))
                else:
                    score = sum(1 / (60 + rank) for rank in entry["channels"].values())
                results.append((score, cid, entry))
            results.sort(key=lambda item: (-item[0], item[1]))
            output = []
            for rank, (score, cid, entry) in enumerate(results[:top_k], 1):
                row = entry["row"]
                doc = allowed[row["document_id"]]
                path = self.files / f"{doc['id']}.pdf"
                if _hash_file(path) != doc["sha256"] or sha256(row["text"].encode()).hexdigest() != row["text_hash"]:
                    raise ValueError("PDF_SOURCE_HASH_MISMATCH")
                output.append({"rank": rank, "chunk_id": cid, "document_id": doc["id"],
                    "filename": doc["filename"], "issuer": doc["issuer"],
                    "document_type": doc["document_type"], "report_period": doc["report_period"],
                    "page": row["page"], "text": row["text"][:1400], "score": score,
                    "bm25_rank": entry["channels"].get("B"), "dense_rank": entry["channels"].get("D"),
                    "bm25_score": entry["scores"].get("B"), "dense_score": entry["scores"].get("D"),
                    "source_sha256": doc["sha256"], "provenance_status": "VERIFIED_LOCAL_PDF_BYTES",
                    "highlight_status": "EXACT_EXTRACTED_LINE_COORDINATES" if json.loads(row["line_boxes"]) else "NO_COORDINATES"})
            return {"mode": mode, "status": "READY", "documents": len(allowed),
                    "generation": generation,
                    "results": output, "latency_ms": round((perf_counter()-started)*1000, 2),
                    "timings_ms": {"bm25": round(bm25_ms, 2), "embedding": round(embed_ms, 2),
                                   "dense": round(dense_ms, 2)},
                    "source_scope": "ISOLATED_USER_PDF", "model_digest": DIGEST if mode != "bm25" else None,
                    "fusion": {"method": "RRF", "k": 60} if mode == "hybrid" else None}

    def page_image(self, document_id: str, page_number: int, chunk_ids: list[str], phrase: str = ""):
        if not 1 <= page_number <= MAX_PAGES or len(chunk_ids) > 10:
            raise ValueError("INVALID_PDF_PAGE_REQUEST")
        with self._lock:
            doc = self.document(document_id)
            if doc is None or doc["status"] != "READY" or page_number > doc["pages"]:
                raise ValueError("PDF_PAGE_NOT_READY")
            path = self.files / f"{document_id}.pdf"
            if _hash_file(path) != doc["sha256"]:
                raise ValueError("PDF_SOURCE_HASH_MISMATCH")
            with closing(self._connect()) as db:
                selected = [db.execute("SELECT * FROM chunks WHERE id=? AND document_id=? AND page=?",
                                       (cid, document_id, page_number)).fetchone() for cid in chunk_ids]
            if any(row is None for row in selected):
                raise ValueError("PDF_CHUNK_PAGE_MISMATCH")
            with pymupdf.open(path) as pdf:
                page = pdf[page_number - 1]
                current_hash = sha256(page.get_text("text").encode()).hexdigest()
                exact_phrase = False
                for row in selected:
                    if current_hash != row["page_text_hash"] or sha256(row["text"].encode()).hexdigest() != row["text_hash"]:
                        raise ValueError("PDF_PAGE_TEXT_CHANGED")
                    rects = []
                    if phrase and len(phrase) <= 120 and phrase.casefold() in row["text"].casefold():
                        rects = page.search_for(phrase)
                        exact_phrase = bool(rects)
                    if not rects:
                        rects = [pymupdf.Rect(*box) for box in json.loads(row["line_boxes"])]
                        with closing(self._connect()) as db:
                            normalized=db.execute('SELECT 1 FROM page_evidence WHERE document_id=? AND page=?',(document_id,page_number)).fetchone()
                        if normalized:rects=[rect*page.derotation_matrix for rect in rects]
                    if rects:
                        annotation = page.add_highlight_annot(rects)
                        annotation.set_colors(stroke=(1, .78, .18))
                        annotation.update()
                pixmap = page.get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5), alpha=False)
                status = "EXACT_PDF_TEXT_MATCH" if exact_phrase else (
                    "EXACT_EXTRACTED_LINE_COORDINATES" if selected else "NO_HIGHLIGHT")
                return pixmap.tobytes("png"), status

    def health(self):
        docs = self.list_documents()
        return {"workspace": "ISOLATED_USER_PDF", "ready_documents": sum(d["status"] == "READY" for d in docs),
                "total_documents": len(docs), "ready_chunks": sum(d["chunks"] for d in docs if d["status"] == "READY"),
                "vector_collection": COLLECTION, "model": MODEL, "dimension": DIMENSION,
                "lexical_version": "PDF_VI_FOLDED_FTS5_V2",
                "disk_free_bytes": shutil.disk_usage(self.root).free}

    def source_file(self, document_id):
        doc=self.document(document_id)
        if not doc:
            raise ValueError('DOCUMENT_NOT_FOUND')
        path=self.files / f'{doc["id"]}.pdf'
        if _hash_file(path)!=doc['sha256']:
            raise ValueError('PDF_SOURCE_HASH_MISMATCH')
        return path

    def page_evidence(self, document_id, page_number):
        self.source_file(document_id)
        with closing(self._connect()) as db:
            row=db.execute('SELECT payload,payload_hash FROM page_evidence WHERE document_id=? AND page=?',
                           (document_id,page_number)).fetchone()
        if row is None:
            raise ValueError('PAGE_EVIDENCE_NOT_AVAILABLE')
        if sha256(row['payload'].encode()).hexdigest()!=row['payload_hash']:
            raise ValueError('PDF_PAGE_EVIDENCE_HASH_MISMATCH')
        saved=json.loads(row['payload'])
        # A versioned, derived layout view; immutable OCR checkpoint bytes are retained.
        tables=self._page_tables(saved,page_number)
        layout_hash=sha256(json.dumps(tables,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        evidence_hash=sha256((row['payload_hash']+self.TABLE_LAYOUT_VERSION+layout_hash).encode()).hexdigest()
        confidences=[w['confidence'] for line in saved.get('lines',[]) for w in line['words'] if w.get('confidence') is not None]
        quality={'engine_mean_word_confidence':sum(confidences)/len(confidences) if confidences else None,
                 'low_confidence_words':sum(v<60 for v in confidences),
                 'status':'OCR_EXTRACTED_NOT_CERTIFIED' if saved.get('method') in {'OCR','REGION_FUSION'} else 'NATIVE_TEXT_EXTRACTED'}
        return {**saved,'tables':tables,'table_layout_version':self.TABLE_LAYOUT_VERSION,
                'quality':quality,'checkpoint_sha256':row['payload_hash'],'evidence_sha256':evidence_hash}

    def extraction_status(self, document_id):
        doc=self.document(document_id)
        if not doc:raise ValueError('DOCUMENT_NOT_FOUND')
        with closing(self._connect()) as db:
            pages=[json.loads(row['payload']) for row in db.execute(
                'SELECT payload FROM page_evidence WHERE document_id=? ORDER BY page',(document_id,))]
        types={p.get('pdf_type') for p in pages}
        return {'pages_completed':sum(p['status']!='FAILED' for p in pages),'pages_total':doc['pages'],
                'pdf_type':'MIXED' if len(types)>1 else next(iter(types),'UNKNOWN'),
                'table_status':'TABLE_STRUCTURE_UNVERIFIED' if any(p.get('tables') for p in pages) else 'NO_TABLE_CANDIDATES',
                'search_ready':doc['status']=='READY',
                'pages':[{'page':p['page'],'status':p['status'],'method':p.get('method'),'error':p.get('error'),
                          'table_rows':len(p.get('tables',[]))} for p in pages]}

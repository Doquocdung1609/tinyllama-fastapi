"""SQLite registry and atomic filesystem helpers for resumable corpus ingestion."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Any

from app.financial_ingestion.schemas import FinancialChunk, FilingMetadata, IngestionJob

ACTIVE_STATES = ("DOWNLOADING", "VALIDATING", "PARSING", "CHUNKING", "STAGING", "RUNNING")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def atomic_write_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(content)
    temporary.replace(path)


def atomic_write_json(path: Path, payload: Any) -> None:
    atomic_write_bytes(path, json.dumps(payload, ensure_ascii=False, indent=2,
                                        sort_keys=True).encode("utf-8"))


class FinancialRegistry:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.init_database()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def init_database(self) -> None:
        with self.connect() as connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS filings (
                    filing_id TEXT PRIMARY KEY,
                    dataset_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    raw_path TEXT,
                    structured_path TEXT,
                    chunks_path TEXT,
                    raw_hash TEXT,
                    normalized_hash TEXT,
                    chunk_count INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL,
                    error TEXT
                );
                CREATE INDEX IF NOT EXISTS filings_dataset_status
                    ON filings(dataset_id, status);
                CREATE TABLE IF NOT EXISTS chunks (
                    chunk_id TEXT PRIMARY KEY,
                    filing_id TEXT NOT NULL,
                    chunk_json TEXT NOT NULL,
                    source_text_hash TEXT NOT NULL,
                    FOREIGN KEY(filing_id) REFERENCES filings(filing_id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS chunks_filing ON chunks(filing_id);
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    dataset_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    job_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS manifests (
                    manifest_hash TEXT PRIMARY KEY,
                    dataset_id TEXT NOT NULL,
                    snapshot_version TEXT NOT NULL,
                    path TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(dataset_id, snapshot_version)
                );
            """)

    def recover_interrupted(self) -> dict[str, int]:
        now = utc_now()
        with self.connect() as connection:
            filing_result = connection.execute(
                f"UPDATE filings SET status='INTERRUPTED', updated_at=? "
                f"WHERE status IN ({','.join('?' for _ in ACTIVE_STATES[:-1])})",
                (now, *ACTIVE_STATES[:-1]))
            job_rows = connection.execute(
                "SELECT job_id, job_json FROM jobs WHERE status='RUNNING'").fetchall()
            for row in job_rows:
                payload = json.loads(row["job_json"])
                payload["status"] = "INTERRUPTED"
                payload["updated_at"] = now
                connection.execute(
                    "UPDATE jobs SET status='INTERRUPTED', job_json=?, updated_at=? WHERE job_id=?",
                    (json.dumps(payload, ensure_ascii=False), now, row["job_id"]))
        return {"filings": filing_result.rowcount, "jobs": len(job_rows)}

    def upsert_filing(self, dataset_id: str, metadata: FilingMetadata, *,
                      raw_path: Path | None = None, structured_path: Path | None = None,
                      chunks_path: Path | None = None, error: str | None = None,
                      chunk_count: int | None = None) -> None:
        with self.connect() as connection:
            existing = connection.execute(
                "SELECT raw_path, structured_path, chunks_path, chunk_count FROM filings WHERE filing_id=?",
                (metadata.filing_id,)).fetchone()
            values = {
                "raw_path": str(raw_path) if raw_path else (existing["raw_path"] if existing else None),
                "structured_path": str(structured_path) if structured_path else (existing["structured_path"] if existing else None),
                "chunks_path": str(chunks_path) if chunks_path else (existing["chunks_path"] if existing else None),
                "chunk_count": chunk_count if chunk_count is not None else (existing["chunk_count"] if existing else 0),
            }
            connection.execute("""
                INSERT INTO filings(filing_id,dataset_id,status,metadata_json,raw_path,
                    structured_path,chunks_path,raw_hash,normalized_hash,chunk_count,updated_at,error)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(filing_id) DO UPDATE SET
                    dataset_id=excluded.dataset_id,status=excluded.status,
                    metadata_json=excluded.metadata_json,raw_path=excluded.raw_path,
                    structured_path=excluded.structured_path,chunks_path=excluded.chunks_path,
                    raw_hash=excluded.raw_hash,normalized_hash=excluded.normalized_hash,
                    chunk_count=excluded.chunk_count,updated_at=excluded.updated_at,error=excluded.error
            """, (metadata.filing_id, dataset_id, metadata.document_status.value,
                    metadata.model_dump_json(), values["raw_path"], values["structured_path"],
                    values["chunks_path"], metadata.raw_content_hash,
                    metadata.normalized_content_hash, values["chunk_count"], utc_now(), error))

    def store_chunks(self, filing_id: str, chunks: list[FinancialChunk]) -> None:
        with self.connect() as connection:
            connection.execute("DELETE FROM chunks WHERE filing_id=?", (filing_id,))
            connection.executemany(
                "INSERT INTO chunks(chunk_id,filing_id,chunk_json,source_text_hash) VALUES(?,?,?,?)",
                [(chunk.chunk_id, filing_id, chunk.model_dump_json(), chunk.source_text_hash)
                 for chunk in chunks])

    def get_filing(self, filing_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute("SELECT * FROM filings WHERE filing_id=?", (filing_id,)).fetchone()
        return dict(row) if row else None

    def list_filings(self, dataset_id: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM filings"
        args: tuple = ()
        if dataset_id:
            query += " WHERE dataset_id=?"
            args = (dataset_id,)
        query += " ORDER BY filing_id"
        with self.connect() as connection:
            return [dict(row) for row in connection.execute(query, args).fetchall()]

    def get_chunk(self, chunk_id: str) -> FinancialChunk | None:
        with self.connect() as connection:
            row = connection.execute("SELECT chunk_json FROM chunks WHERE chunk_id=?", (chunk_id,)).fetchone()
        return FinancialChunk.model_validate_json(row["chunk_json"]) if row else None

    def create_job(self, job: IngestionJob) -> None:
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO jobs(job_id,dataset_id,status,job_json,created_at,updated_at) VALUES(?,?,?,?,?,?)",
                (job.job_id, job.dataset_id, job.status, job.model_dump_json(),
                 job.created_at, job.updated_at))

    def update_job(self, job: IngestionJob) -> None:
        with self.connect() as connection:
            connection.execute(
                "UPDATE jobs SET status=?,job_json=?,updated_at=? WHERE job_id=?",
                (job.status, job.model_dump_json(), job.updated_at, job.job_id))

    def get_job(self, job_id: str) -> IngestionJob | None:
        with self.connect() as connection:
            row = connection.execute("SELECT job_json FROM jobs WHERE job_id=?", (job_id,)).fetchone()
        return IngestionJob.model_validate_json(row["job_json"]) if row else None

    def add_manifest(self, manifest_hash: str, dataset_id: str, snapshot_version: str,
                     path: Path, created_at: str) -> None:
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO manifests(manifest_hash,dataset_id,snapshot_version,path,created_at) VALUES(?,?,?,?,?)",
                (manifest_hash, dataset_id, snapshot_version, str(path), created_at))

    def manifests(self, dataset_id: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM manifests"
        args: tuple = ()
        if dataset_id:
            query += " WHERE dataset_id=?"
            args = (dataset_id,)
        query += " ORDER BY created_at DESC"
        with self.connect() as connection:
            return [dict(row) for row in connection.execute(query, args).fetchall()]

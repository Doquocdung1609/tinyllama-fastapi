"""Resumable SEC filing ingestion pipeline with immutable manifests and lineage."""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import logging
import re
from pathlib import Path
from uuid import uuid4

from app.config import get_settings
from app.financial_ingestion import CHUNKER_VERSION, INGESTION_VERSION, PARSER_VERSION
from app.financial_ingestion.chunker import chunk_filing
from app.financial_ingestion.html_parser import normalized_filing_text, parse_sec_html
from app.financial_ingestion.registry import (
    FinancialRegistry, atomic_write_bytes, atomic_write_json, utc_now,
)
from app.financial_ingestion.schemas import (
    DatasetManifest, DocumentStatus, FilingMetadata, FinancialChunk, IngestionJob,
    StructuredFiling,
)
from app.financial_ingestion.sec_client import ALLOWED_FORMS, SECClient, filing_source_url
from app.path_safety import ensure_path_capacity

logger = logging.getLogger(__name__)


def file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_metadata_identity(metadata: FilingMetadata, *, additional_forms=()) -> None:
    if not re.fullmatch(r"[0-9]{10}", metadata.cik):
        raise ValueError("Metadata CIK must be exactly 10 canonical ASCII digits")
    if not re.fullmatch(r"[0-9]{10}-[0-9]{2}-[0-9]{6}", metadata.accession_number):
        raise ValueError("Metadata accession must use the canonical SEC format")
    expected_id = f"sec:{metadata.cik}:{metadata.accession_number}"
    if metadata.filing_id != expected_id:
        raise ValueError(f"filing_id must equal {expected_id}")
    if metadata.form_type not in ALLOWED_FORMS and metadata.form_type not in additional_forms:
        raise ValueError(f"Unsupported SEC form: {metadata.form_type}")
    expected_url = filing_source_url(
        metadata.cik, metadata.accession_number, metadata.primary_document)
    if metadata.source_url != expected_url:
        raise ValueError("source_url does not match CIK, accession and primary_document")


class FinancialCorpusPipeline:
    @staticmethod
    def validate_dataset_id(dataset_id: str) -> None:
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", dataset_id):
            raise ValueError("dataset_id must use 1-80 letters, digits, '-' or '_'")

    def __init__(self, *, root: Path | None = None,
                 registry: FinancialRegistry | None = None,
                 client: SECClient | None = None):
        settings = get_settings()
        self.root = Path(root or settings.financial_corpus_dir)
        for name in ("raw", "structured", "chunks", "manifests", "jobs", "staging_index"):
            (self.root / name).mkdir(parents=True, exist_ok=True)
        self.registry = registry or FinancialRegistry(settings.financial_registry_db)
        self.client = client

    @classmethod
    def from_settings(cls) -> "FinancialCorpusPipeline":
        settings = get_settings()
        client = SECClient(
            settings.sec_user_agent,
            requests_per_second=settings.sec_requests_per_second,
            timeout_seconds=settings.sec_timeout_seconds,
            max_retries=settings.sec_max_retries,
        )
        return cls(client=client)

    def raw_path(self, metadata: FilingMetadata, raw_hash: str) -> Path:
        relative = Path("raw") / metadata.cik / metadata.accession_number / raw_hash / metadata.primary_document
        ensure_path_capacity(self.root, relative)
        return self.root / relative

    def incoming_path(self, metadata: FilingMetadata) -> Path:
        key = sha256(metadata.filing_id.encode()).hexdigest()[:24]
        suffix = Path(metadata.primary_document).suffix or ".html"
        return self.root / "raw" / ".incoming" / f"{key}{suffix}"

    def structured_path(self, metadata: FilingMetadata) -> Path:
        key = sha256(metadata.filing_id.encode()).hexdigest()[:24]
        relative = Path("structured") / key / metadata.raw_content_hash / f"{self._derived_version(metadata)}.json"
        ensure_path_capacity(self.root, relative)
        return self.root / relative

    def chunks_path(self, metadata: FilingMetadata) -> Path:
        key = sha256(metadata.filing_id.encode()).hexdigest()[:24]
        relative = Path("chunks") / key / metadata.raw_content_hash / f"{self._derived_version(metadata)}.jsonl"
        ensure_path_capacity(self.root, relative)
        return self.root / relative

    @staticmethod
    def _derived_version(metadata: FilingMetadata) -> str:
        return sha256(f"{metadata.parser_version}|{CHUNKER_VERSION}|{metadata.ingestion_version}".encode()).hexdigest()[:24]

    def stage_path(self, dataset_id: str, metadata: FilingMetadata) -> Path:
        key = sha256(metadata.filing_id.encode()).hexdigest()[:24]
        relative = (Path("staging_index") / dataset_id / key /
                    metadata.raw_content_hash / f"{self._derived_version(metadata)}.json")
        ensure_path_capacity(self.root, relative)
        return self.root / relative

    def _mark(self, dataset_id: str, metadata: FilingMetadata, status: DocumentStatus,
              *, error: str | None = None, **paths) -> None:
        metadata.document_status = status
        self.registry.upsert_filing(dataset_id, metadata, error=error, **paths)

    def _find_amendment_parent(self, metadata: FilingMetadata) -> str | None:
        if not metadata.form_type.endswith("/A"):
            return None
        base_form = metadata.form_type[:-2]
        matches = []
        for row in self.registry.list_filings():
            existing = FilingMetadata.model_validate_json(row["metadata_json"])
            if (existing.cik == metadata.cik and existing.form_type == base_form and
                    existing.report_date == metadata.report_date and
                    existing.filing_id != metadata.filing_id):
                matches.append(existing)
        matches.sort(key=lambda item: (item.filing_date or "", item.accession_number), reverse=True)
        return matches[0].filing_id if matches else None

    def ingest_one(self, dataset_id: str, metadata: FilingMetadata,
                   *, force: bool = False) -> dict:
        self.validate_dataset_id(dataset_id)
        validate_metadata_identity(metadata)
        existing = self.registry.get_filing(metadata.filing_id)
        if existing and not force and existing["status"] in {"READY", "PARTIAL_EXTRACTION"}:
            prior = FilingMetadata.model_validate_json(existing["metadata_json"])
            path = Path(existing["raw_path"] or "")
            if (prior.parser_version == PARSER_VERSION and prior.chunker_version == CHUNKER_VERSION
                    and path.is_file() and existing["raw_hash"] == file_sha256(path)):
                return {"filing_id": metadata.filing_id, "status": existing["status"],
                        "idempotent_reuse": True, "chunk_count": existing["chunk_count"]}
        if self.client is None:
            raise RuntimeError("SEC client is required for live ingestion")
        metadata.parser_version = PARSER_VERSION
        metadata.chunker_version = CHUNKER_VERSION
        metadata.ingestion_version = INGESTION_VERSION
        prior_raw_path = Path(existing["raw_path"]) if existing and existing["raw_path"] else None
        download_path = self.incoming_path(metadata)
        prior_response = {}
        if existing:
            prior_metadata = FilingMetadata.model_validate_json(existing["metadata_json"])
            prior_response = prior_metadata.response_metadata
        self._mark(dataset_id, metadata, DocumentStatus.DOWNLOADING,
                   raw_path=prior_raw_path or download_path)
        result = self.client.download(
            metadata.source_url, download_path,
            etag=prior_response.get("etag"), last_modified=prior_response.get("last_modified"),
            cached_path=prior_raw_path,
            max_bytes=get_settings().sec_max_filing_mb * 1024 * 1024,
        )
        metadata.retrieved_at = result.retrieved_at
        metadata.response_metadata = result.response_metadata()
        metadata.raw_content_hash = file_sha256(result.path)
        raw_path = self.raw_path(metadata, metadata.raw_content_hash)
        if result.not_modified:
            raw_path = result.path
        elif raw_path.exists():
            if file_sha256(raw_path) != metadata.raw_content_hash:
                raise RuntimeError("Immutable raw snapshot hash collision")
            result.path.unlink(missing_ok=True)
        else:
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            result.path.replace(raw_path)
        self._mark(dataset_id, metadata, DocumentStatus.DOWNLOADED, raw_path=raw_path)

        self._mark(dataset_id, metadata, DocumentStatus.VALIDATING, raw_path=raw_path)
        raw = raw_path.read_bytes()
        probe = raw[:10000].lstrip().lower()
        if b"<html" not in probe and b"<xhtml" not in probe:
            raise ValueError("Downloaded SEC primary document is not HTML/XHTML")
        if metadata.accession_number.replace("-", "") not in metadata.source_url:
            raise ValueError("Source URL does not contain the filing accession number")

        self._mark(dataset_id, metadata, DocumentStatus.PARSING, raw_path=raw_path)
        metadata.amendment_of = self._find_amendment_parent(metadata)
        if metadata.form_type.endswith("/A") and metadata.amendment_of is None:
            metadata.unknown_reasons["amendment_of"] = "Base filing was not present in this registry."
        structured = parse_sec_html(raw, metadata)
        normalized = normalized_filing_text(structured)
        metadata.normalized_content_hash = sha256(normalized.encode("utf-8")).hexdigest()
        final_status = (DocumentStatus.PARTIAL_EXTRACTION if structured.parser_warnings
                        else DocumentStatus.READY)
        structured.metadata = metadata.model_copy(deep=True, update={"document_status": final_status})
        structured_path = self.structured_path(metadata)
        atomic_write_json(structured_path, structured.model_dump(mode="json"))

        self._mark(dataset_id, metadata, DocumentStatus.CHUNKING, raw_path=raw_path,
                   structured_path=structured_path)
        chunks = chunk_filing(structured)
        chunks_path = self.chunks_path(metadata)
        content = "".join(chunk.model_dump_json() + "\n" for chunk in chunks).encode("utf-8")
        atomic_write_bytes(chunks_path, content)

        self._mark(dataset_id, metadata, DocumentStatus.STAGING, raw_path=raw_path,
                   structured_path=structured_path, chunks_path=chunks_path,
                   chunk_count=len(chunks))
        index_generation = sha256("\n".join(
            f"{chunk.chunk_id}:{chunk.source_text_hash}" for chunk in sorted(chunks, key=lambda item: item.chunk_id)
        ).encode()).hexdigest()
        atomic_write_json(self.stage_path(dataset_id, metadata), {
            "dataset_id": dataset_id,
            "filing_id": metadata.filing_id,
            "document_version": (f"{metadata.filing_id}@{metadata.raw_content_hash}"
                                 f":{metadata.parser_version}:{CHUNKER_VERSION}"),
            "index_generation": index_generation,
            "chunk_ids": [chunk.chunk_id for chunk in chunks],
            "chunks_path": str(chunks_path),
            "qdrant_collection": None,
            "note": "Metadata/chunk staging only; production knowledgebase is untouched.",
        })
        self.registry.store_chunks(metadata.filing_id, chunks)
        final_status = (DocumentStatus.PARTIAL_EXTRACTION if structured.parser_warnings
                        else DocumentStatus.READY)
        self._mark(dataset_id, metadata, final_status, raw_path=raw_path,
                   structured_path=structured_path, chunks_path=chunks_path,
                   chunk_count=len(chunks))
        return {"filing_id": metadata.filing_id, "status": final_status.value,
                "idempotent_reuse": False, "chunk_count": len(chunks),
                "tables": len(structured.tables), "warnings": structured.parser_warnings,
                "raw_hash": metadata.raw_content_hash,
                "normalized_hash": metadata.normalized_content_hash,
                "index_generation": index_generation}

    def create_job(self, dataset_id: str, filings: list[FilingMetadata], *,
                   dry_run: bool = False) -> IngestionJob:
        self.validate_dataset_id(dataset_id)
        for metadata in filings:
            validate_metadata_identity(metadata)
        if len({item.filing_id for item in filings}) != len(filings):
            raise ValueError("filings must not contain duplicate filing_id values")
        now = utc_now()
        job = IngestionJob(job_id=uuid4().hex, dataset_id=dataset_id,
                           status="DRY_RUN" if dry_run else "PENDING",
                           created_at=now, updated_at=now,
                           filing_ids=[item.filing_id for item in filings], dry_run=dry_run)
        for metadata in filings:
            self.registry.upsert_filing(dataset_id, metadata)
        self.registry.create_job(job)
        atomic_write_json(self.root / "jobs" / f"{job.job_id}.json", job.model_dump(mode="json"))
        return job

    def run_job(self, job_id: str, *, stop_after: int | None = None) -> IngestionJob:
        job = self.registry.get_job(job_id)
        if not job:
            raise ValueError("Ingestion job not found")
        if job.dry_run:
            return job
        job.status = "RUNNING"
        job.updated_at = utc_now()
        self.registry.update_job(job)
        processed_this_run = 0
        for index, filing_id in enumerate(job.filing_ids):
            if filing_id in job.completed:
                continue
            if index < job.next_index and filing_id not in job.failed:
                continue
            row = self.registry.get_filing(filing_id)
            if not row:
                job.failed[filing_id] = "Filing metadata missing from registry"
            else:
                metadata = FilingMetadata.model_validate_json(row["metadata_json"])
                try:
                    result = self.ingest_one(job.dataset_id, metadata)
                    if result["status"] in {"READY", "PARTIAL_EXTRACTION"} and filing_id not in job.completed:
                        job.completed.append(filing_id)
                    job.failed.pop(filing_id, None)
                except Exception as exc:
                    metadata.document_status = DocumentStatus.FAILED
                    self.registry.upsert_filing(job.dataset_id, metadata, error=str(exc))
                    job.failed[filing_id] = str(exc)
                    logger.exception("SEC filing ingestion failed filing_id=%s", filing_id)
            job.next_index = max(job.next_index, index + 1)
            job.updated_at = utc_now()
            self.registry.update_job(job)
            atomic_write_json(self.root / "jobs" / f"{job.job_id}.json", job.model_dump(mode="json"))
            processed_this_run += 1
            if stop_after is not None and processed_this_run >= stop_after:
                job.status = "INTERRUPTED"
                job.updated_at = utc_now()
                self.registry.update_job(job)
                return job
        job.status = "COMPLETED_WITH_ERRORS" if job.failed else "COMPLETED"
        job.updated_at = utc_now()
        self.registry.update_job(job)
        atomic_write_json(self.root / "jobs" / f"{job.job_id}.json", job.model_dump(mode="json"))
        return job

    def create_manifest(self, dataset_id: str) -> DatasetManifest:
        self.validate_dataset_id(dataset_id)
        rows = self.registry.list_filings(dataset_id)
        if not rows:
            raise ValueError("Dataset has no registered filings")
        parsed = [(row, FilingMetadata.model_validate_json(row["metadata_json"])) for row in rows]
        index_seed = "\n".join(
            f"{meta.filing_id}|{row['raw_hash']}|{row['normalized_hash']}|{row['chunk_count']}|{row['status']}"
            for row, meta in sorted(parsed, key=lambda item: item[1].filing_id))
        index_seed += f"\n{PARSER_VERSION}|{CHUNKER_VERSION}|{INGESTION_VERSION}"
        index_generation = sha256(index_seed.encode()).hexdigest()
        snapshot_version = f"v1-{index_generation[:16]}"
        existing_path = self.root / "manifests" / dataset_id / f"{snapshot_version}.json"
        if existing_path.exists():
            return DatasetManifest.model_validate_json(existing_path.read_text(encoding="utf-8"))
        created_at = utc_now()
        manifest = DatasetManifest(
            dataset_id=dataset_id, snapshot_version=snapshot_version, created_at=created_at,
            sources=sorted({meta.source_url for _, meta in parsed}),
            filing_ids=[meta.filing_id for _, meta in parsed],
            raw_hashes={meta.filing_id: row["raw_hash"] for row, meta in parsed if row["raw_hash"]},
            normalized_hashes={meta.filing_id: row["normalized_hash"] for row, meta in parsed if row["normalized_hash"]},
            parser_version=PARSER_VERSION, chunker_version=CHUNKER_VERSION,
            ingestion_version=INGESTION_VERSION, embedding_model=None,
            chunk_counts={meta.filing_id: row["chunk_count"] for row, meta in parsed},
            document_count=len(parsed), index_generation=index_generation,
            failed_documents=[meta.filing_id for row, meta in parsed if row["status"] == "FAILED"],
            partial_documents=[meta.filing_id for row, meta in parsed if row["status"] == "PARTIAL_EXTRACTION"],
            reproduction_commands=[
                f"python scripts/financial_corpus.py status --dataset-id {dataset_id}",
                f"python scripts/financial_corpus.py manifest --dataset-id {dataset_id}",
            ],
        )
        manifest.manifest_hash = manifest.content_hash()
        atomic_write_json(existing_path, manifest.model_dump(mode="json"))
        self.registry.add_manifest(manifest.manifest_hash, dataset_id, snapshot_version,
                                   existing_path, created_at)
        return manifest

    def evidence(self, chunk_id: str) -> dict:
        chunk = self.registry.get_chunk(chunk_id)
        if not chunk:
            raise ValueError("Financial chunk not found")
        row = self.registry.get_filing(chunk.filing_id)
        if not row:
            raise ValueError("Parent filing not found")
        raw_path = Path(row["raw_path"] or "")
        if not raw_path.is_file():
            return {"status": "SOURCE_UNAVAILABLE", "chunk": chunk.model_dump(mode="json")}
        metadata = FilingMetadata.model_validate_json(row["metadata_json"])
        if file_sha256(raw_path) != metadata.raw_content_hash:
            return {"status": "INVALID_RAW_HASH", "chunk": chunk.model_dump(mode="json")}
        filing = parse_sec_html(raw_path.read_bytes(), metadata)
        normalized_hash = sha256(normalized_filing_text(filing).encode("utf-8")).hexdigest()
        if normalized_hash != metadata.normalized_content_hash:
            return {"status": "INVALID_NORMALIZED_HASH", "chunk": chunk.model_dump(mode="json")}
        expected_chunk = next((item for item in chunk_filing(filing) if item.chunk_id == chunk_id), None)
        context_verified = expected_chunk is not None and expected_chunk.model_dump() == chunk.model_dump()
        disclosure = None
        if chunk.kind == "text":
            element = next((item for item in filing.elements
                            if item.source_location.structural_path == chunk.source_location.structural_path), None)
            if element:
                start = chunk.source_location.text_start or 0
                end = chunk.source_location.text_end if chunk.source_location.text_end is not None else len(element.text)
                disclosure = element.text[start:end].strip()
        else:
            table = next((item for item in filing.tables if item.table_id == chunk.source_location.table_id), None)
            row_index = chunk.source_location.row_index
            if table and row_index is not None:
                indices = table.row_indices or list(range(1, len(table.rows) + 1))
                if row_index in indices:
                    disclosure = " | ".join(table.rows[indices.index(row_index)])
        source_verified = disclosure is not None and sha256(disclosure.encode("utf-8")).hexdigest() == chunk.source_text_hash
        verified = source_verified and context_verified
        return {
            "status": ("VERIFIED" if verified else
                       "INVALID_CHUNK_CONTEXT" if source_verified else "INVALID_SOURCE_LOCATOR"),
            "verified": verified,
            "context_verified": context_verified,
            "chunk": chunk.model_dump(mode="json"),
            "source_chain": {
                "chunk_id": chunk.chunk_id,
                "filing_id": metadata.filing_id,
                "document_version": chunk.document_version,
                "company_name": metadata.company_name,
                "cik": metadata.cik,
                "accession_number": metadata.accession_number,
                "source_url": metadata.source_url,
                "source_location": chunk.source_location.model_dump(exclude_none=True),
                "raw_content_hash": metadata.raw_content_hash,
                "original_disclosure": disclosure,
            },
        }

    def extraction_quality(self, filing_id: str) -> dict:
        """Read-only diagnostics; structural success never implies financial completeness."""
        row = self.registry.get_filing(filing_id)
        if row is None:
            raise LookupError("Financial filing not found")
        path = Path(row["structured_path"] or "")
        if not path.is_file():
            raise FileNotFoundError("Structured snapshot is unavailable")
        filing = StructuredFiling.model_validate_json(path.read_text(encoding="utf-8"))
        tables = [{
            "table_id": table.table_id,
            "source_location": table.source_location.model_dump(exclude_none=True),
            "extraction_status": table.extraction_status,
            "warnings": table.extraction_warnings,
            "numeric_fact_count": sum(len(cell.numeric_facts) for cell in table.cells),
            "context_present": {
                "column_labels": any(table.columns),
                "reporting_periods": bool(table.reporting_periods),
                "unit_context": bool(table.unit_context),
                "statement_title": bool(table.statement_title),
            },
        } for table in filing.tables]
        return {
            "filing_id": filing_id,
            "document_status": row["status"],
            "registered_raw_hash": row["raw_hash"],
            "financial_completeness": "NOT_ASSESSED",
            "assessment_reason": "Table context flags do not classify purpose or prove financial completeness; independent source review is required.",
            "source_provenance_verification": "NOT_PERFORMED_BY_THIS_DIAGNOSTIC",
            "table_count": len(tables),
            "unresolved_table_count": sum(table["extraction_status"] != "OK" for table in tables),
            "tables": tables,
        }

"""Strict schemas for SEC filings, structured evidence, jobs and manifests."""
from __future__ import annotations

from enum import Enum
from hashlib import sha256
import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class DocumentStatus(str, Enum):
    DISCOVERED = "DISCOVERED"
    DOWNLOADING = "DOWNLOADING"
    DOWNLOADED = "DOWNLOADED"
    VALIDATING = "VALIDATING"
    PARSING = "PARSING"
    CHUNKING = "CHUNKING"
    STAGING = "STAGING"
    READY = "READY"
    PARTIAL_EXTRACTION = "PARTIAL_EXTRACTION"
    INTERRUPTED = "INTERRUPTED"
    FAILED = "FAILED"


class SourceLocation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    section: str | None = None
    html_anchor: str | None = None
    structural_path: str
    table_id: str | None = None
    row_index: int | None = None
    column_index: int | None = None
    text_start: int | None = None
    text_end: int | None = None
    pdf_page: int | None = None
    bbox: list[float] | None = None

    def canonical(self) -> str:
        return json.dumps(self.model_dump(exclude_none=True), sort_keys=True,
                          separators=(",", ":"), ensure_ascii=False)


class TableCell(BaseModel):
    model_config = ConfigDict(extra="forbid")

    row: int
    column: int
    text: str
    is_header: bool = False
    rowspan: int = 1
    colspan: int = 1
    unit_ref: str | None = None
    context_ref: str | None = None
    source_location: SourceLocation


class FinancialTable(BaseModel):
    model_config = ConfigDict(extra="forbid")

    table_id: str
    section: str | None = None
    caption: str | None = None
    columns: list[str] = Field(default_factory=list)
    rows: list[list[str]] = Field(default_factory=list)
    cells: list[TableCell] = Field(default_factory=list)
    units: list[str] = Field(default_factory=list)
    reporting_periods: list[str] = Field(default_factory=list)
    footnotes: list[str] = Field(default_factory=list)
    source_location: SourceLocation
    extraction_status: Literal["OK", "PARTIAL_EXTRACTION"] = "OK"
    raw_text: str
    raw_content_hash: str


class StructuredElement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    element_id: str
    kind: Literal["heading", "paragraph", "list_item", "footnote"]
    text: str
    source_location: SourceLocation
    source_text_hash: str


class FilingMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    filing_id: str
    company_name: str
    cik: str
    ticker: str | None = None
    form_type: str
    accession_number: str
    filing_date: str | None = None
    report_date: str | None = None
    fiscal_year: int | None = None
    fiscal_period: str | None = None
    primary_document: str
    source_url: str
    retrieved_at: str | None = None
    source_type: Literal["SEC_EDGAR"] = "SEC_EDGAR"
    raw_content_hash: str | None = None
    normalized_content_hash: str | None = None
    parser_version: str
    ingestion_version: str
    document_status: DocumentStatus = DocumentStatus.DISCOVERED
    amendment_of: str | None = None
    unknown_reasons: dict[str, str] = Field(default_factory=dict)
    response_metadata: dict[str, Any] = Field(default_factory=dict)


class StructuredFiling(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metadata: FilingMetadata
    title: str | None = None
    elements: list[StructuredElement] = Field(default_factory=list)
    tables: list[FinancialTable] = Field(default_factory=list)
    parser_warnings: list[str] = Field(default_factory=list)


class FinancialChunk(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chunk_id: str
    filing_id: str
    document_version: str
    kind: Literal["text", "table"]
    text: str
    source_location: SourceLocation
    source_text_hash: str
    metadata: dict[str, Any]
    extraction_status: Literal["OK", "PARTIAL_EXTRACTION"] = "OK"


class DatasetManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dataset_id: str
    snapshot_version: str
    created_at: str
    sources: list[str]
    filing_ids: list[str]
    raw_hashes: dict[str, str]
    normalized_hashes: dict[str, str]
    parser_version: str
    chunker_version: str
    ingestion_version: str
    embedding_model: str | None = None
    chunk_counts: dict[str, int]
    document_count: int
    index_generation: str
    failed_documents: list[str] = Field(default_factory=list)
    partial_documents: list[str] = Field(default_factory=list)
    reproduction_commands: list[str]
    manifest_hash: str | None = None

    def content_hash(self) -> str:
        payload = self.model_dump(exclude={"manifest_hash"})
        return sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False,
                                 separators=(",", ":")).encode("utf-8")).hexdigest()


class IngestionJob(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: str
    dataset_id: str
    status: str
    created_at: str
    updated_at: str
    filing_ids: list[str]
    next_index: int = 0
    completed: list[str] = Field(default_factory=list)
    failed: dict[str, str] = Field(default_factory=dict)
    dry_run: bool = False
    error: str | None = None

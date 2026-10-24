"""Stable structure-aware chunking for SEC filing text and financial tables."""
from __future__ import annotations

from hashlib import sha256

from app.financial_ingestion import CHUNKER_VERSION
from app.financial_ingestion.schemas import FinancialChunk, SourceLocation, StructuredFiling


def _chunk_id(document_version: str, kind: str, location: SourceLocation) -> str:
    seed = f"{document_version}|{kind}|{location.canonical()}|{CHUNKER_VERSION}"
    return f"fin_{sha256(seed.encode('utf-8')).hexdigest()[:32]}"


def _metadata(filing: StructuredFiling) -> dict:
    item = filing.metadata
    return {
        "company_name": item.company_name,
        "cik": item.cik,
        "ticker": item.ticker,
        "form_type": item.form_type,
        "accession_number": item.accession_number,
        "filing_date": item.filing_date,
        "report_date": item.report_date,
        "fiscal_year": item.fiscal_year,
        "fiscal_period": item.fiscal_period,
        "primary_document": item.primary_document,
        "source_url": item.source_url,
        "source_type": item.source_type,
        "raw_content_hash": item.raw_content_hash,
        "normalized_content_hash": item.normalized_content_hash,
        "parser_version": item.parser_version,
        "ingestion_version": item.ingestion_version,
        "document_status": item.document_status.value,
        "amendment_of": item.amendment_of,
    }


def chunk_filing(filing: StructuredFiling, *, max_chars: int = 1200,
                 overlap: int = 120) -> list[FinancialChunk]:
    if max_chars < 200 or overlap < 0 or overlap >= max_chars:
        raise ValueError("max_chars must be >= 200 and overlap smaller than max_chars")
    chunks = []
    base_metadata = _metadata(filing)
    document_version = f"{filing.metadata.filing_id}@{filing.metadata.raw_content_hash}"
    for element in filing.elements:
        start = 0
        while start < len(element.text):
            end = min(start + max_chars, len(element.text))
            if end < len(element.text):
                boundary = element.text.rfind(" ", start + max_chars // 2, end)
                if boundary > start:
                    end = boundary
            text = element.text[start:end].strip()
            if text:
                location = element.source_location.model_copy(update={
                    "text_start": start, "text_end": end})
                chunks.append(FinancialChunk(
                    chunk_id=_chunk_id(document_version, "text", location),
                    filing_id=filing.metadata.filing_id, document_version=document_version,
                    kind="text", text=text, source_location=location,
                    source_text_hash=sha256(text.encode("utf-8")).hexdigest(),
                    metadata={**base_metadata, "element_kind": element.kind,
                              "section": location.section},
                ))
            if end >= len(element.text):
                break
            start = max(start + 1, end - overlap)

    for table in filing.tables:
        header = " | ".join(table.columns)
        rows = table.rows or [[]]
        for row_index, row in enumerate(rows, start=1):
            location = table.source_location.model_copy(update={"row_index": row_index})
            row_text = " | ".join(row)
            content = (
                f"TABLE {table.table_id}\n"
                f"Section: {table.section or 'UNKNOWN'}\n"
                f"Caption: {table.caption or 'UNKNOWN'}\n"
                f"Columns: {header}\n"
                f"Row {row_index}: {row_text}\n"
                f"Units: {', '.join(table.units) or 'UNKNOWN'}\n"
                f"Reporting periods: {', '.join(table.reporting_periods) or 'UNKNOWN'}"
            )
            chunks.append(FinancialChunk(
                chunk_id=_chunk_id(document_version, "table", location),
                filing_id=filing.metadata.filing_id, document_version=document_version,
                kind="table", text=content, source_location=location,
                source_text_hash=sha256(row_text.encode("utf-8")).hexdigest(),
                metadata={**base_metadata, "table_id": table.table_id,
                          "section": table.section, "row_index": row_index,
                          "units": table.units, "reporting_periods": table.reporting_periods},
                extraction_status=table.extraction_status,
            ))
    seen = set()
    for chunk in chunks:
        if chunk.chunk_id in seen:
            raise RuntimeError(f"Duplicate stable chunk ID: {chunk.chunk_id}")
        seen.add(chunk.chunk_id)
    return chunks

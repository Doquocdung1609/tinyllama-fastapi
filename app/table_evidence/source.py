"""Read-only, in-memory reconstruction of C verification's parse/rechunk step.

The binding is a trusted upstream capability INPUT, never client metadata. No
files, registry, index, network or database are opened. No ingestion is run.
"""
from dataclasses import dataclass
from hashlib import sha256
from html.parser import HTMLParser
import re

from app.financial_ingestion import PARSER_VERSION, CHUNKER_VERSION
from app.financial_ingestion.chunker import chunk_filing
from app.financial_ingestion.html_parser import parse_sec_html, normalized_filing_text
from app.financial_ingestion.schemas import FilingMetadata, StructuredFiling, FinancialChunk
from app.table_evidence.contracts import SourceBindingV1
from app.table_evidence.identity import digest
from app.table_evidence.bounds import validate_budget


class _BoundedHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = self.cells = 0
        self.stack=[]

    def handle_starttag(self, tag, attrs):
        self.tags += 1
        if self.tags > 5000:
            raise ValueError('SOURCE_NODE_BUDGET')
        if tag not in {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}:
            self.stack.append(tag)
        if len(self.stack) > 64:
            raise ValueError('SOURCE_DEPTH_BUDGET')
        if tag in {'td','th'}:
            self.cells += 1
            if self.cells > 2000:
                raise ValueError('SOURCE_CELL_BUDGET')
        for key, value in attrs:
            if key in {'rowspan','colspan'} and (not (value or '').isdigit() or not 1 <= int(value) <= 32):
                raise ValueError('UNSUPPORTED_SOURCE_SPAN')

    def handle_endtag(self, tag):
        if tag in self.stack:
            index=len(self.stack)-1-self.stack[::-1].index(tag)
            del self.stack[index:]

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag,attrs)
        self.handle_endtag(tag)


@dataclass(frozen=True, slots=True)
class SourceVerificationContext:
    """Process-local immutable snapshot; not a serializable authentication token."""
    binding: SourceBindingV1
    filing_json: str
    parents: tuple[tuple[str, str], ...]

    def parent(self, identifier):
        return next((FinancialChunk.model_validate_json(v) for k,v in self.parents if k==identifier), None)

    def filing(self):
        return StructuredFiling.model_validate_json(self.filing_json)


def context_from_snapshot(raw: bytes, metadata: FilingMetadata, trusted_binding: SourceBindingV1):
    """Verify supplied bytes/metadata against a separately trusted pinned anchor.

    Caller must authenticate the anchor through C's pinned generation/source
    provenance before calling. Self-issued hashes cannot authenticate SEC data.
    Maximum 250KB snapshot, 5000 tags, 2000 cells, span32/depth64 for this pilot.
    Reconstructs accepted C objects in memory without changing parser/chunker.
    """
    if not isinstance(raw,bytes) or len(raw)>250000 or not isinstance(metadata,FilingMetadata) or not isinstance(trusted_binding,SourceBindingV1):
        raise ValueError('INVALID_SOURCE_CONTEXT')
    validate_budget(metadata)
    validate_budget(trusted_binding)
    b=SourceBindingV1.model_validate(trusted_binding.model_dump())
    m=FilingMetadata.model_validate(metadata.model_dump())
    if m.parser_version!=PARSER_VERSION or m.chunker_version!=CHUNKER_VERSION:
        raise ValueError('SOURCE_VERSION_MISMATCH')
    if not re.fullmatch('[0-9]{10}',m.cik) or not re.fullmatch('[0-9]{10}-[0-9]{2}-[0-9]{6}',m.accession_number) or m.filing_id!=f'sec:{m.cik}:{m.accession_number}':
        raise ValueError('SOURCE_FILING_IDENTITY_MISMATCH')
    if b.filing_id!=m.filing_id or digest(m.model_dump(mode='json'))!=b.metadata_hash:
        raise ValueError('SOURCE_METADATA_MISMATCH')
    if sha256(raw).hexdigest()!=b.raw_hash or m.raw_content_hash!=b.raw_hash:
        raise ValueError('SOURCE_BYTES_MISMATCH')
    guard=_BoundedHTML(); guard.feed(raw.decode('utf-8',errors='strict')); guard.close()
    filing=parse_sec_html(raw,m)
    if sha256(normalized_filing_text(filing).encode()).hexdigest()!=b.normalized_hash:
        raise ValueError('SOURCE_NORMALIZED_MISMATCH')
    chunks=chunk_filing(filing)
    actual=tuple(sorted((c.chunk_id,digest(c.model_dump(mode='json'))) for c in chunks))
    if actual!=tuple(sorted(b.parent_hashes)):
        raise ValueError('SOURCE_PARENT_MEMBERSHIP_MISMATCH')
    return SourceVerificationContext(b,filing.model_dump_json(),tuple(sorted((c.chunk_id,c.model_dump_json()) for c in chunks)))

"""D2 immutable, versioned, source-preserving views. No persistence or services."""
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

REPRESENTATION = 'table-evidence-v1'
Status = Literal['VERIFIED_CONTEXT', 'PARTIAL_CONTEXT', 'CONFLICTED_CONTEXT',
                 'INVALID_SOURCE', 'UNSUPPORTED_STRUCTURE']


class Contract(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True, str_max_length=250000)


class SourceBindingV1(Contract):
    """TRUSTED caller anchor from a pinned, authenticated upstream generation.

    Shape validation does not establish the authenticity of this anchor. Do not
    construct it from client query JSON or accept a client's self-declared hash.
    """
    contract_version: Literal['table-source-binding/v1'] = 'table-source-binding/v1'
    dataset_id: str = Field(min_length=1, max_length=80)
    manifest_hash: str = Field(pattern=r'^[0-9a-f]{64}$')
    generation_id: str = Field(pattern=r'^[0-9a-f]{64}$')
    filing_id: str
    raw_hash: str = Field(pattern=r'^[0-9a-f]{64}$')
    normalized_hash: str = Field(pattern=r'^[0-9a-f]{64}$')
    metadata_hash: str = Field(pattern=r'^[0-9a-f]{64}$')
    parent_hashes: tuple[tuple[str, str], ...] = Field(max_length=2000)

    @model_validator(mode='after')
    def unique(self):
        import re
        if len({k for k, _ in self.parent_hashes}) != len(self.parent_hashes):
            raise ValueError('DUPLICATE_PARENT')
        if not self.parent_hashes or any(not re.fullmatch('[0-9a-f]{64}', h) for _, h in self.parent_hashes):
            raise ValueError('INVALID_PARENT_HASHES')
        return self


class LocatorV1(Contract):
    structural_path: str
    source_location_json: str
    table_id: str
    row: int = Field(ge=0)
    column: int = Field(ge=0)


class PeriodContextV1(Contract):
    kind: Literal['FISCAL_YEAR', 'FISCAL_QUARTER', 'CALENDAR_YEAR', 'INSTANT', 'DURATION']
    year: int | None = Field(default=None,ge=1900,le=2200)
    quarter: int | None = Field(default=None,ge=1,le=4)
    end: str | None = None
    months: int | None = Field(default=None,ge=1,le=12)
    raw_labels: tuple[str, ...]

    @model_validator(mode='after')
    def coherent(self):
        from datetime import date
        if self.end is not None:
            date.fromisoformat(self.end)
        if self.kind in {'FISCAL_YEAR','FISCAL_QUARTER','CALENDAR_YEAR'} and self.year is None:
            raise ValueError('YEAR_REQUIRED')
        if self.kind=='FISCAL_QUARTER' and self.quarter is None:
            raise ValueError('QUARTER_REQUIRED')
        if self.kind in {'INSTANT','DURATION'} and self.end is None:
            raise ValueError('END_REQUIRED')
        if self.kind=='DURATION' and self.months is None:
            raise ValueError('DURATION_REQUIRED')
        return self


class HeaderContextV1(Contract):
    row: int
    column: int
    rowspan: int
    colspan: int
    original_text: str
    locator: LocatorV1
    period: PeriodContextV1 | None = None
    interpretation_status: Status


class ConflictV1(Contract):
    code: str
    row: int | None = None
    column: int | None = None
    detail: str


class CellEvidenceV1(Contract):
    evidence_id: str
    table_id: str
    row: int
    column: int
    rowspan: int
    colspan: int
    original_text: str
    raw_numeric_string: str | None
    value: Decimal | None
    sign_representation: Literal['NONE', 'PLUS', 'MINUS', 'PARENTHESES', 'INLINE']
    missing_kind: Literal['BLANK', 'DASH', 'NOT_AVAILABLE', 'TEXT', 'NUMBER']
    header_path: tuple[HeaderContextV1, ...]
    period: PeriodContextV1 | None
    measurement_basis: str
    entity_basis: str
    unit: Literal['UNKNOWN', 'USD', 'USD_PER_SHARE', 'SHARES', 'PERCENT', 'PERCENTAGE_POINTS']
    multiplier: Decimal | None
    effective_value: Decimal | None
    locator: LocatorV1
    inline_attributes: tuple[str, ...]  # canonical JSON, immutable exact accepted attributes
    footnote_references: tuple[str, ...]
    status: Status
    unresolved_fields: tuple[str, ...]
    conflicts: tuple[ConflictV1, ...]

    @model_validator(mode='after')
    def coherent(self):
        if any(x is not None and not x.is_finite() for x in (self.value,self.multiplier,self.effective_value)):
            raise ValueError('NONFINITE_NUMBER')
        if self.multiplier is not None and self.multiplier<=0:
            raise ValueError('INVALID_MULTIPLIER')
        if self.conflicts and self.status!='CONFLICTED_CONTEXT':
            raise ValueError('CONFLICTS_CANNOT_BE_VERIFIED')
        if self.effective_value is not None and self.status!='VERIFIED_CONTEXT':
            raise ValueError('UNRESOLVED_EFFECTIVE_VALUE')
        if self.status=='VERIFIED_CONTEXT' and (self.unresolved_fields or not self.header_path or self.period is None or self.unit=='UNKNOWN' or self.value is None or self.multiplier is None or self.missing_kind!='NUMBER'):
            raise ValueError('VERIFIED_CELL_CONTEXT_INCOMPLETE')
        return self


class TableEvidenceV1(Contract):
    contract_version: Literal['financial-table-evidence/v1'] = 'financial-table-evidence/v1'
    representation_version: Literal['table-evidence-v1'] = REPRESENTATION
    parent_chunk_id: str
    parent_payload_hash: str
    original_parent_text: str
    original_parent_json: str
    filing_id: str
    document_version: str
    cik: str
    accession: str
    form: str
    filing_date: str | None
    source_url: str
    parser_version: str
    chunker_version: str
    table_id: str
    caption: str | None
    section: str | None
    row_label: str
    row_group: str | None
    original_row: int
    original_locator_json: str
    footnotes: tuple[str, ...]
    footnote_locations: tuple[str, ...]
    context_locations: tuple[str, ...]
    continuation_of: str | None
    extraction_warnings: tuple[str, ...]
    parent_provenance: Literal['MATCHED_UPSTREAM_BINDING', 'UNAUTHENTICATED']
    source_generation: str | None
    manifest_hash: str | None
    cells: tuple[CellEvidenceV1, ...]
    status: Status
    evidence_hash: str


class EvidenceValidationResultV1(Contract):
    contract_version: Literal['table-evidence-result/v1'] = 'table-evidence-result/v1'
    status: Status
    evidence: TableEvidenceV1 | None = None
    warnings: tuple[str, ...] = ()

    @model_validator(mode='after')
    def coherent(self):
        if self.status == 'VERIFIED_CONTEXT' and (not self.evidence or self.evidence.parent_provenance != 'MATCHED_UPSTREAM_BINDING'):
            raise ValueError('VERIFIED_REQUIRES_SOURCE_CONTEXT')
        if self.evidence and self.status != self.evidence.status:
            raise ValueError('INCONSISTENT_STATUS')
        return self


class EvidenceBundleV1(Contract):
    contract_version: Literal['table-evidence-bundle/v1'] = 'table-evidence-bundle/v1'
    representation_version: Literal['table-evidence-v1'] = REPRESENTATION
    source_generation: str
    manifest_hash: str
    selected_parent_ids: tuple[str, ...]
    expanded_parent_ids: tuple[str, ...]
    results: tuple[EvidenceValidationResultV1, ...]
    completeness_status: Status
    warnings: tuple[str, ...]
    evidence_hash: str

    @model_validator(mode='after')
    def coherent(self):
        if not self.results or self.completeness_status=='VERIFIED_CONTEXT' and any(r.status!='VERIFIED_CONTEXT' for r in self.results):
            raise ValueError('INVALID_BUNDLE_COMPLETENESS')
        return self

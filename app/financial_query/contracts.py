"""Versioned, strict D1 contracts. Catalogs are supplied trusted metadata snapshots."""
from datetime import date
from decimal import Decimal
from enum import Enum
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Status(str, Enum):
    RESOLVED = "RESOLVED"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"
    UNSUPPORTED = "UNSUPPORTED"
    NO_ELIGIBLE_EVIDENCE = "NO_ELIGIBLE_EVIDENCE"
    INVALID_INPUT = "INVALID_INPUT"


class IntentCategory(str, Enum):
    EXACT_FINANCIAL_VALUE = "EXACT_FINANCIAL_VALUE"
    SEMANTIC_PARAPHRASE = "SEMANTIC_PARAPHRASE"
    FINANCIAL_TERMINOLOGY = "FINANCIAL_TERMINOLOGY"
    FINANCIAL_TABLE = "FINANCIAL_TABLE"
    PERIOD_COMPARISON = "PERIOD_COMPARISON"
    CROSS_SECTION = "CROSS_SECTION"
    AMBIGUOUS = "AMBIGUOUS"
    UNSUPPORTED = "UNSUPPORTED"


Form = Literal["10-K", "10-Q", "10-K/A", "10-Q/A"]
Amendment = Literal["UNSPECIFIED", "ORIGINAL", "AMENDED"]
def canonical_cik(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{1,10}", value.strip()):
        raise ValueError("CIK must contain 1-10 ASCII digits")
    if int(value) == 0:
        raise ValueError("CIK must be positive")
    return value.strip().zfill(10)


class PeriodV1(Contract):
    kind: Literal["FISCAL_YEAR", "FISCAL_QUARTER", "CALENDAR_YEAR", "INSTANT", "DURATION"]
    year: int | None = Field(default=None, ge=1900, le=2200)
    quarter: int | None = Field(default=None, ge=1, le=4)
    end: date | None = None
    months: int | None = Field(default=None, ge=1, le=12)
    raw: str

    @model_validator(mode="after")
    def coherent(self):
        if self.kind in {"FISCAL_YEAR", "FISCAL_QUARTER", "CALENDAR_YEAR"} and self.year is None:
            raise ValueError("Year required")
        if self.kind == "FISCAL_QUARTER" and self.quarter is None:
            raise ValueError("Quarter required")
        if self.kind in {"INSTANT", "DURATION"} and self.end is None:
            raise ValueError("Period end required")
        if self.kind == "DURATION" and self.months is None:
            raise ValueError("Duration required")
        if self.kind != "FISCAL_QUARTER" and self.quarter is not None:
            raise ValueError("Unexpected quarter")
        return self


class ColumnPeriodV1(Contract):
    period: PeriodV1
    # Required source metadata coordinate/reference, not an inferred fiscal calendar.
    source_ref: str = Field(min_length=1, max_length=500)

    @field_validator('source_ref')
    @classmethod
    def nonblank_reference(cls, value):
        if not value.strip():
            raise ValueError('Column reference must be nonblank')
        return value


class DateRangeV1(Contract):
    start: date
    end: date

    @model_validator(mode="after")
    def ordered(self):
        if self.start > self.end:
            raise ValueError("Inverted filing date range")
        return self


class IssuerMentionV1(Contract):
    text: str
    kind: Literal["CIK", "TICKER", "NAME", "ALIAS", "UNKNOWN"]
    candidate_ciks: list[str]


class MetricMentionV1(Contract):
    raw: str
    canonical: str
    relationship: Literal["EXACT", "SYNONYM", "AMBIGUOUS"]
    related_concepts: list[str] = Field(default_factory=list)
    rule_id: str


class NumericConstraintV1(Contract):
    raw: str
    value: Decimal
    multiplier: Decimal = Decimal(1)
    unit: Literal["UNKNOWN", "USD", "USD_PER_SHARE", "PERCENT", "PERCENTAGE_POINTS"]
    sign_source: Literal["NONE", "MINUS", "PLUS", "PARENTHESES"]

    @field_validator("value", "multiplier")
    @classmethod
    def finite(cls, value):
        if not value.is_finite():
            raise ValueError("Nonfinite number")
        return value


class QueryIntentV1(Contract):
    contract_version: Literal["financial-query-intent/v1"] = "financial-query-intent/v1"
    original_question: str
    normalized_question: str
    category: IntentCategory
    secondary_intents: list[IntentCategory] = Field(default_factory=list)
    issuer_mentions: list[IssuerMentionV1] = Field(default_factory=list)
    metric_mentions: list[MetricMentionV1] = Field(default_factory=list)
    forms: list[Form] = Field(default_factory=list)
    accessions: list[str] = Field(default_factory=list)
    filing_dates: DateRangeV1 | None = None
    reporting_periods: list[PeriodV1] = Field(default_factory=list)
    amendment_preference: Amendment = "UNSPECIFIED"
    numerical_constraints: list[NumericConstraintV1] = Field(default_factory=list)
    comparison_operation: Literal["COMPARE", "DIFFERENCE", "RELATIVE_CHANGE", "PERCENTAGE_POINTS"] | None = None
    unresolved_slots: list[str] = Field(default_factory=list)
    matched_rule_ids: list[str] = Field(default_factory=list)
    unit_mentions: list[str] = Field(default_factory=list)


class IssuerV1(Contract):
    cik: str
    company_name: str = Field(min_length=1, max_length=300)
    tickers: list[str] = Field(default_factory=list, max_length=100)
    verified_aliases: list[str] = Field(default_factory=list, max_length=100)

    _cik = field_validator("cik", mode="before")(canonical_cik)

    @model_validator(mode='after')
    def nonblank_names(self):
        if any(not v.strip() or len(v) > 300 for v in [self.company_name, *self.tickers, *self.verified_aliases]):
            raise ValueError('Blank or overlong issuer alias')
        return self


class CatalogFilingV1(Contract):
    filing_id: str = Field(max_length=100)
    cik: str
    accession: str = Field(pattern=r"^[0-9]{10}-[0-9]{2}-[0-9]{6}$")
    form: Form
    filing_date: date | None = None
    report_end: date | None = None
    fiscal_year: int | None = None
    fiscal_period: str | None = None
    amendment_of: str | None = None
    extraction_status: Literal["READY", "PARTIAL_EXTRACTION"]
    column_periods: list[ColumnPeriodV1] = Field(default_factory=list)
    # False means absence of a column label cannot prove absence of evidence.
    column_periods_complete: bool = False
    raw_column_labels: list[str] = Field(default_factory=list)

    _cik = field_validator("cik", mode="before")(canonical_cik)

    @model_validator(mode="after")
    def identity(self):
        if self.filing_id != f"sec:{self.cik}:{self.accession}":
            raise ValueError("Filing identity differs from CIK/accession")
        if self.amendment_of and not self.form.endswith("/A"):
            raise ValueError("Only amendment forms have a parent")
        return self


class CorpusCatalogV1(Contract):
    contract_version: Literal["financial-query-catalog/v1"] = "financial-query-catalog/v1"
    dataset_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,80}$")
    manifest_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    generation_id: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    provenance: str = Field(min_length=1)
    issuers: list[IssuerV1] = Field(max_length=10000)
    filings: list[CatalogFilingV1] = Field(max_length=50000)

    @model_validator(mode="after")
    def membership(self):
        ciks = {i.cik for i in self.issuers}
        ids = [f.filing_id for f in self.filings]
        if len(ciks) != len(self.issuers) or len(set(ids)) != len(ids):
            raise ValueError("Duplicate corpus identity")
        by_id = {f.filing_id: f for f in self.filings}
        for f in self.filings:
            if f.cik not in ciks:
                raise ValueError("Issuer missing from catalog")
            if f.amendment_of:
                parent = by_id.get(f.amendment_of)
                if not parent or parent.cik != f.cik or parent.form != f.form.removesuffix("/A"):
                    raise ValueError("Invalid amendment linkage")
        return self


class ExplicitFiltersV1(Contract):
    cik: str | None = None
    ticker: str | None = Field(default=None, min_length=1, max_length=20)
    form_type: Form | None = None
    filing_ids: list[str] = Field(default_factory=list, max_length=20)
    fiscal_year: int | None = Field(default=None, ge=1900, le=2200)
    fiscal_period: Literal["FY", "Q1", "Q2", "Q3", "Q4"] | None = None
    filing_dates: DateRangeV1 | None = None
    amendment_preference: Amendment = "UNSPECIFIED"

    @field_validator("cik", mode="before")
    @classmethod
    def cik_or_none(cls, value):
        return canonical_cik(value) if value is not None else None


class TraceStepV1(Contract):
    stage: str
    rule_id: str
    detail: str


class ResolvedScopeV1(Contract):
    contract_version: Literal["financial-resolved-scope/v1"] = "financial-resolved-scope/v1"
    dataset_id: str
    manifest_hash: str
    generation_id: str | None
    cik: str
    issuer_aliases: list[str]
    eligible_filing_ids: list[str]
    forms: list[Form]
    filing_dates: DateRangeV1 | None
    requested_periods: list[PeriodV1]
    comparative_column_requirements: list[PeriodV1]
    matched_column_refs: dict[str, list[str]]
    amendment_selection: Amendment
    warnings: list[str]
    resolution_reasons: list[str]
    status: Status

    @model_validator(mode="after")
    def resolved_members(self):
        if self.status == Status.RESOLVED and not self.eligible_filing_ids:
            raise ValueError("Resolved scope requires filing membership")
        return self


class ScopeResolutionResultV1(Contract):
    contract_version: Literal["financial-scope-result/v1"] = "financial-scope-result/v1"
    query_intent: QueryIntentV1 | None
    resolved_scope: ResolvedScopeV1 | None = None
    status: Status
    clarification_questions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    trace: list[TraceStepV1] = Field(default_factory=list)

    @model_validator(mode="after")
    def consistent(self):
        if self.status == Status.RESOLVED and (self.resolved_scope is None or self.query_intent is None):
            raise ValueError("Resolved result requires intent and scope")
        if self.resolved_scope and self.resolved_scope.status != self.status:
            raise ValueError("Scope/result status mismatch")
        return self

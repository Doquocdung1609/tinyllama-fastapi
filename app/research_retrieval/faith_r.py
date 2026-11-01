"""Opt-in FAITH-R development replay on an unchanged, recorded Top-10 pool.

This module does not create Qdrant candidates or verify a financial value.
The original source text and candidate identifiers remain immutable.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from app.financial_query.normalizer import normalize_question
from app.financial_query.terminology import resolve_terms


ISSUER_ALIASES = {
    "AMD": ("amd", "advanced micro devices"),
    "INTC": ("intel", "intc"),
    "AMZN": ("amazon", "amzn"),
    "TSLA": ("tesla", "tsla"),
    "META": ("meta", "meta platforms"),
    "GOOGL": ("alphabet", "google", "googl"),
}
METRIC_PHRASES = {
    "TOTAL_REVENUE": (r"\btotal\s+(?:net\s+)?revenues?\b", r"\bnet\s+sales\b"),
    "CAPEX": (r"\bcapital\s+expenditures?\b", r"\bpurchases?\s+of\s+property\s+and\s+equipment\b"),
}


@dataclass(frozen=True)
class QuerySlots:
    issuer: str | None
    fiscal_year: int | None
    metric: str | None
    total_required: bool
    unresolved: tuple[str, ...]


@dataclass(frozen=True)
class EvidenceCandidate:
    chunk_id: str
    original_rank: int
    original_score: float
    source_sha256: str
    issuer_match: bool | None
    corrected_period_match: bool | None
    metric_relation: str
    table_row_candidate: bool
    year_in_body: bool
    row_excerpt: str | None
    period: str | None = None
    unit: str | None = None
    value: str | None = None
    verification_status: str = "UNVERIFIED"

    def ordering(self) -> tuple[int, int, int, int, int, int]:
        # No relevance labels, numeric OCR values or cross-method scores are used.
        return (int(self.issuer_match is True), int(self.corrected_period_match is True),
                int(self.table_row_candidate and self.metric_relation == "EXACT"),
                int(self.metric_relation == "EXACT"), int(self.metric_relation == "RELATED"),
                int(self.year_in_body))


def parse_query(question: str) -> QuerySlots:
    q = normalize_question(question)
    issuers = [ticker for ticker, aliases in ISSUER_ALIASES.items()
               if any(re.search(r"(?<!\w)" + re.escape(alias) + r"(?!\w)", q) for alias in aliases)]
    years = {int(y) for y in re.findall(r"\b(?:19|20)\d{2}\b", q)}
    terms = resolve_terms(q)
    metric = "CAPEX" if re.search(r"\bcapital\s+expenditures?\b|\bcapex\b", q) else (
        "TOTAL_REVENUE" if "total revenue" in q or "total revenues" in q else None)
    unresolved = []
    if len(issuers) != 1:
        unresolved.append("ISSUER_AMBIGUOUS_OR_ABSENT")
    if len(years) != 1:
        unresolved.append("FISCAL_YEAR_AMBIGUOUS_OR_ABSENT")
    if metric is None or (terms and not any(t.canonical == "revenue" for t in terms) and metric == "TOTAL_REVENUE"):
        unresolved.append("METRIC_AMBIGUOUS_OR_ABSENT")
    return QuerySlots(issuers[0] if len(issuers) == 1 else None,
                      next(iter(years)) if len(years) == 1 else None,
                      metric, "total" in q, tuple(unresolved))


def candidate(hit: dict, rank: int, slots: QuerySlots) -> EvidenceCandidate:
    raw = hit.get("text", "")
    body = raw.split("\n\n", 1)[-1] if "\n\n" in raw else raw
    body_lower = body.casefold()
    exact, related = METRIC_PHRASES.get(slots.metric, (r"(?!)", r"(?!)"))
    exact_matches = list(re.finditer(exact, body_lower))
    related_matches = list(re.finditer(related, body_lower))
    relation = "EXACT" if exact_matches else "RELATED" if related_matches else "UNKNOWN"
    match = (exact_matches or related_matches or [None])[0]
    excerpt = body[max(0, match.start() - 75):match.end() + 125].strip() if match else None
    # Pipe boundaries and a nearby numeric token identify only a candidate row.
    # They cannot establish the right column, unit, value or source-cell validity.
    around = body[max(0, match.start() - 80):match.end() + 120] if match else ""
    table_like = bool(match and "|" in around and re.search(r"\b\d[\d,]{2,}\b", around))
    period = hit.get("fiscal_period")
    return EvidenceCandidate(
        chunk_id=hit["chunk_id"], original_rank=rank,
        original_score=float(hit.get("score", 0)),
        source_sha256=hashlib.sha256(raw.encode("utf-8")).hexdigest(),
        issuer_match=hit.get("ticker") == slots.issuer if slots.issuer else None,
        corrected_period_match=period == f"FY{slots.fiscal_year}" if slots.fiscal_year else None,
        metric_relation=relation, table_row_candidate=table_like,
        year_in_body=bool(slots.fiscal_year and re.search(r"\b" + str(slots.fiscal_year) + r"\b", body)),
        row_excerpt=excerpt,
    )


def rank_recorded_top10(hits: list[dict], slots: QuerySlots) -> list[EvidenceCandidate]:
    if len(hits) > 10 or len({h["chunk_id"] for h in hits}) != len(hits):
        raise ValueError("RECORDED_TOP10_BUDGET_OR_DUPLICATE")
    candidates = [candidate(hit, i, slots) for i, hit in enumerate(hits, 1)]
    return sorted(candidates, key=lambda item: (tuple(-x for x in item.ordering()), item.original_rank, item.chunk_id))

"""Opt-in FAITH-R research path over a restored Qdrant collection.

The source sidecar references the same immutable chunk IDs; it does not
create cells, vectors or a second production index.
"""

from __future__ import annotations

from dataclasses import dataclass
import re

from app.research_retrieval.faith_r import candidate, parse_query, rank_candidates


@dataclass(frozen=True)
class LiveArmResult:
    arm: str
    status: str
    query_slots: dict
    hits: list[dict]
    candidate_pool_ids: list[str]


class EvidenceSidecar:
    """Bounded row-like lookup over original Qdrant payloads, same source IDs."""

    def __init__(self, client, collection: str = "financial_docs"):
        self.payloads: list[dict] = []
        offset = None
        while True:
            batch, offset = client.scroll(collection, offset=offset, limit=128, with_payload=True, with_vectors=False)
            self.payloads.extend(p.payload for p in batch)
            if offset is None:
                break

    def find(self, question: str, budget: int) -> list[dict]:
        slots = parse_query(question)
        if slots.issuer is None or slots.metric is None:
            return []
        found = []
        for payload in self.payloads:
            if payload.get("ticker") != slots.issuer:
                continue
            if slots.fiscal_year and not slots.comparative_intent and payload.get("fiscal_period") != f"FY{slots.fiscal_year}":
                continue
            hit = {"chunk_id": payload["chunk_id"], "ticker": payload["ticker"],
                   "fiscal_period": payload.get("fiscal_period"), "score": 0,
                   "text": payload.get("text", ""), "source_url": payload.get("source_url", ""),
                   "accession_number": payload.get("accession_number", "")}
            evidence = candidate(hit, len(found) + 1, slots)
            if evidence.metric_relation != "UNKNOWN" and evidence.table_row_candidate:
                found.append((evidence, hit))
        found.sort(key=lambda pair: (tuple(-x for x in pair[0].ordering()), pair[0].chunk_id))
        return [hit for _, hit in found[:budget]]


def financial_alignment(hit: dict, slots) -> tuple[int, int, int, int, int, int, int]:
    """Source-text features for a post-hoc repair; no company or gold IDs."""
    body = hit["text"].split("\n\n", 1)[-1]
    lower = body.casefold()
    if slots.metric == "TOTAL_REVENUE":
        strict_row = bool(re.search(r"(?:^|\|)\s*total\s+(?:net\s+)?(?:revenues?|sales)\s*\|", lower))
        consolidated_row = bool(re.search(r"\b(?:net sales|revenues?)\s*:\s*(?:\|[^\n]{0,400})?\bconsolidated\s*\|\s*\$?\s*\d", lower))
        phrases = list(re.finditer(r"\btotal\s+(?:net\s+)?revenues?\b|\btotal\s+net\s+sales\b", lower))
    elif slots.metric == "CAPEX":
        strict_row = bool(re.search(r"(?:^|\|)\s*capital\s+expenditures?\s*\|", lower))
        consolidated_row = False
        phrases = list(re.finditer(r"\bcapital\s+expenditures?\b", lower))
    else:
        strict_row = consolidated_row = False
        phrases = []
    year_alignment = -1
    numeric_assertion = False
    for match in phrases:
        around = lower[max(0, match.start() - 100):match.end() + 100]
        years = {int(y) for y in re.findall(r"\b20\d{2}\b", around)}
        if slots.fiscal_year in years:
            year_alignment = max(year_alignment, 1)
        elif not years:
            year_alignment = max(year_alignment, 0)
        numeric_assertion |= bool(re.search(r"\$\s*\d[\d,.]*", around))
    relation = candidate(hit, 1, slots).metric_relation
    comparative_filing = int(bool(slots.comparative_intent and slots.requested_years and
                                  hit.get("fiscal_period") == f"FY{max(slots.requested_years)}"))
    return (comparative_filing, int(strict_row), int(consolidated_row), year_alignment,
            int(numeric_assertion), int(relation == "EXACT"), int(relation == "RELATED"))


def safe_filters(question: str):
    """Filter explicit issuer; add fiscal period only for one unambiguous year."""
    slots = parse_query(question)
    if slots.issuer is None:
        return None
    from hybrid_search.models.filter import MetadataFilter
    period = [f"FY{slots.fiscal_year}"] if slots.fiscal_year and not slots.comparative_intent else None
    return MetadataFilter(tickers=[slots.issuer], fiscal_periods=period)


def live_retrieve(engine, question: str, arm: str, budget: int = 10,
                  sidecar: EvidenceSidecar | None = None) -> LiveArmResult:
    """A2/A3/A4/A5 are individually executable on a real author engine."""
    if arm not in {"A2", "A3", "A4", "A5", "A4R"} or not 1 <= budget <= 100:
        raise ValueError("INVALID_FAITH_R_ARM_OR_BUDGET")
    slots = parse_query(question)
    filters = safe_filters(question)
    base = engine.search(question, method="bm25_dense", k=budget, filters=filters,
                         prefetch_k=max(50, budget))
    hits = [{"chunk_id": r.chunk_id, "ticker": r.ticker, "fiscal_period": r.fiscal_period,
             "score": float(r.score), "text": r.text, "source_url": r.source_url,
             "accession_number": r.document_id.split("_", 1)[-1]}
            for r in base]
    if arm in {"A3", "A4", "A5", "A4R"}:
        if sidecar is None:
            raise ValueError("A3_SIDECAR_REQUIRED")
        row_quota = max(1, budget // 4)
        rows = sidecar.find(question, row_quota)
        combined = hits[:budget - row_quota] + rows
        seen = {h["chunk_id"] for h in combined}
        combined += [h for h in hits if h["chunk_id"] not in seen]
        deduped, seen = [], set()
        for h in combined:
            if h["chunk_id"] not in seen and len(deduped) < budget:
                deduped.append(h)
                seen.add(h["chunk_id"])
        hits = deduped
    pool = [h["chunk_id"] for h in hits]
    if arm in {"A4", "A5"}:
        ranked = rank_candidates(hits, slots, budget)
        lookup = {h["chunk_id"]: h for h in hits}
        hits = [lookup[c.chunk_id] for c in ranked]
    elif arm == "A4R":
        hits = sorted(hits, key=lambda h: tuple(-x for x in financial_alignment(h, slots)) + (pool.index(h["chunk_id"]), h["chunk_id"]))
    public = [{"rank": rank, **h, "verification_status": "UNVERIFIED"}
              for rank, h in enumerate(hits, 1)]
    return LiveArmResult(arm, "LIVE_EXECUTED", slots.__dict__, public, pool)

"""Strict independent-gold gate; incomplete judgments never become negatives."""

from __future__ import annotations

from dataclasses import dataclass


LABELS = {"YES", "NO", "PARTIAL_NOT_GOLD", "UNCERTAIN"}


@dataclass(frozen=True)
class Judgment:
    question_id: str
    chunk_id: str
    label: str
    accession: str
    source_locator: str
    metric: str
    period: str
    unit: str | None
    adjudicator: str
    reviewer_kind: str


def validate_independent_gold(judgments: list[Judgment]) -> dict:
    if not judgments:
        return {"status": "NO_INDEPENDENT_GOLD", "judged": 0}
    seen = set()
    for j in judgments:
        if j.label not in LABELS or not j.question_id or not j.chunk_id:
            raise ValueError("INVALID_QREL")
        key = (j.question_id, j.chunk_id)
        if key in seen:
            raise ValueError("DUPLICATE_QREL")
        seen.add(key)
        if j.reviewer_kind != "HUMAN" or not j.adjudicator:
            raise ValueError("INDEPENDENT_GOLD_REQUIRES_HUMAN_REVIEW")
        if j.label == "YES" and not all((j.accession, j.source_locator, j.metric, j.period)):
            raise ValueError("GOLD_SOURCE_FIELDS_MISSING")
    return {"status": "HUMAN_REVIEWED_QRELS", "judged": len(judgments)}


def judged_hit_bounds(ids: list[str], labels: dict[str, str], k: int) -> dict:
    """Question-level known-positive lower and unknown-sensitive upper hit bounds."""
    if len(ids) != len(set(ids)) or k < 1:
        raise ValueError("INVALID_RANKING")
    top = ids[:k]
    observed = [labels.get(cid, "UNCERTAIN") for cid in top]
    if any(v not in LABELS for v in observed):
        raise ValueError("INVALID_LABEL")
    return {"known_positive_hit": int("YES" in observed),
            "possible_positive_hit": int(any(v in ("YES", "UNCERTAIN") for v in observed)),
            "unknown_count": observed.count("UNCERTAIN"), "recall": None}

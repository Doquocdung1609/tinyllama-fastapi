"""Conservative, source-bound status for Topic 3 research candidates.

No retrieval score or OCR confidence can make a value VERIFIED. This module
only determines whether a provisional row candidate is within the explicit
issuer/period scope of the question.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Mapping, Sequence


DATE = re.compile(r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),\s*(20\d{2})\b", re.I)


def requested_date(question: str) -> str | None:
    match = DATE.search(question)
    if not match:
        return None
    try:
        d = datetime.strptime(match.group(0).title(), "%B %d, %Y")
        return f"{d.strftime('%B')} {d.day}, {d.year}"
    except ValueError:
        return None


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _row_label(source_text: str) -> str | None:
    for line in source_text.splitlines():
        match = re.match(r"Row\s+\d+:\s*([^|]+)", line)
        if match:
            return match.group(1).strip()
    return None


def assess_candidate(
    question: str,
    requested_issuer: str,
    ranked_ids: Sequence[str],
    chunks: Mapping[str, dict],
    issuer_by_filing: Mapping[str, str],
) -> dict:
    """Return a review status; never promote a candidate to verified fact."""
    issuer = requested_issuer.upper().strip()
    available = {v.upper() for v in issuer_by_filing.values()}
    if not issuer or issuer not in available:
        return {"status": "UNSUPPORTED_REQUEST", "reason": "ISSUER_NOT_IN_LOCKED_CORPUS", "numeric_answer_eligible": False}
    period = requested_date(question)
    if period is None:
        return {"status": "AMBIGUOUS", "reason": "EXPLICIT_DATE_REQUIRED", "numeric_answer_eligible": False}
    scoped = [c for c in chunks.values() if issuer_by_filing.get(c["filing_id"], "").upper() == issuer and c["kind"] == "table"]
    if not any(period in c.get("metadata", {}).get("reporting_periods", []) for c in scoped):
        return {"status": "INSUFFICIENT_EVIDENCE", "reason": "PERIOD_NOT_IN_LOCKED_CORPUS", "numeric_answer_eligible": False}
    if not ranked_ids:
        return {"status": "INSUFFICIENT_EVIDENCE", "reason": "NO_RETRIEVED_CANDIDATE", "numeric_answer_eligible": False}
    top = chunks.get(ranked_ids[0])
    if top is None or top["kind"] != "table" or issuer_by_filing.get(top["filing_id"], "").upper() != issuer:
        return {"status": "AMBIGUOUS", "reason": "TOP1_NOT_SOURCE_TABLE_IN_ISSUER", "numeric_answer_eligible": False}
    metadata = top.get("metadata", {})
    if period not in metadata.get("reporting_periods", []):
        return {"status": "AMBIGUOUS", "reason": "TOP1_PERIOD_MISMATCH", "numeric_answer_eligible": False}
    label = _row_label(top["text"])
    if not label or len(_words(label)) < 2:
        return {"status": "AMBIGUOUS", "reason": "ROW_LABEL_UNRESOLVED", "numeric_answer_eligible": False}
    query_words = _words(question)
    label_words = _words(label)
    if not all(word in query_words for word in label_words):
        return {"status": "AMBIGUOUS", "reason": "TOP1_METRIC_MISMATCH", "numeric_answer_eligible": False}
    if not metadata.get("raw_content_hash") or not top.get("source_text_hash"):
        return {"status": "AMBIGUOUS", "reason": "SOURCE_HASH_MISSING", "numeric_answer_eligible": False}
    return {"status": "SOURCE_SUPPORTED_UNREVIEWED", "reason": "SOURCE_ROW_LOCATED_HUMAN_REVIEW_PENDING", "source_chunk_id": top["chunk_id"], "source_hash": metadata["raw_content_hash"], "numeric_answer_eligible": False}

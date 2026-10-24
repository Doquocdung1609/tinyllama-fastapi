"""Retrieval-only financial search API: answer generation is deliberately separate."""
from typing import Literal
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.services.financial_search_service import search
from app.financial_ingestion.registry import FinancialRegistry
from app.config import get_settings

router = APIRouter(prefix="/financial", tags=["financial-search"])


def _unavailable_scope_detail(document_ids: list[str]) -> tuple[int, dict]:
    """Translate an empty retrieval scope into a stable, user-facing reason.

    SEC filings are intentionally staged outside the production Qdrant collection
    in Milestone B.  This lookup does not mutate either index.
    """
    registry = FinancialRegistry(get_settings().financial_registry_db)
    rows = {document_id: registry.get_filing(document_id) for document_id in document_ids}
    missing = [document_id for document_id, row in rows.items() if row is None]
    if missing:
        return 404, {"code": "DOCUMENT_NOT_FOUND", "document_ids": missing}
    partial = [document_id for document_id, row in rows.items()
               if row and row["status"] == "PARTIAL_EXTRACTION"]
    if partial:
        return 409, {"code": "PARTIAL_INGESTION", "document_ids": partial}
    return 409, {
        "code": "FILING_NOT_INDEXED",
        "document_statuses": {document_id: row["status"] for document_id, row in rows.items()},
        "message": "The filing is registered but is not present in the active retrieval index.",
    }


class FinancialSearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=2000)
    document_ids: list[str] = Field(min_length=1, max_length=20)
    method: Literal["bm25", "dense", "hybrid", "hybrid_rerank"] = "hybrid"
    top_k: int = Field(default=5, ge=1, le=20)
    candidate_limit: int = Field(default=40, ge=1, le=100)
    ticker: str | None = Field(default=None, max_length=20)
    fiscal_year: int | None = Field(default=None, ge=1900, le=2200)
    form_type: str | None = Field(default=None, max_length=24)


@router.post("/search")
def financial_search(request: FinancialSearchRequest):
    if not request.query.strip():
        raise HTTPException(status_code=422, detail="query must contain non-whitespace text")
    if any(not document_id.strip() for document_id in request.document_ids):
        raise HTTPException(status_code=422, detail="document_ids must contain non-whitespace text")
    if request.top_k > request.candidate_limit:
        raise HTTPException(status_code=422, detail="top_k must not exceed candidate_limit")
    filters = {key: value for key, value in {
        "ticker": request.ticker, "fiscal_year": request.fiscal_year,
        "form_type": request.form_type}.items() if value is not None}
    try:
        return search(request.query, request.document_ids, request.method,
                      request.top_k, request.candidate_limit, filters)
    except ValueError as exc:
        message = str(exc)
        if message == "No indexed chunks found in the selected document scope":
            status_code, detail = _unavailable_scope_detail(request.document_ids)
            raise HTTPException(status_code=status_code, detail=detail) from exc
        if message.startswith("Metadata unavailable for selected document scope:"):
            fields = [item.strip() for item in message.partition(":")[2].split(",") if item.strip()]
            raise HTTPException(status_code=409, detail={
                "code": "METADATA_UNAVAILABLE", "fields": fields}) from exc
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

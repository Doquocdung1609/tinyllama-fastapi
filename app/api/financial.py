"""Retrieval-only financial search API: answer generation is deliberately separate."""
from typing import Literal
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.services.financial_search_service import search

router = APIRouter(prefix="/financial", tags=["financial-search"])


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
    if request.top_k > request.candidate_limit:
        raise HTTPException(status_code=422, detail="top_k must not exceed candidate_limit")
    filters = {key: value for key, value in {
        "ticker": request.ticker, "fiscal_year": request.fiscal_year,
        "form_type": request.form_type}.items() if value is not None}
    try:
        return search(request.query, request.document_ids, request.method,
                      request.top_k, request.candidate_limit, filters)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

"""Persistent SEC evidence search integrated into the existing application."""
import logging
from threading import Lock
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

from app.config import get_settings
from app.financial_index.service import FinancialIndex
from app.financial_ingestion.sec_client import normalize_cik

router = APIRouter(prefix="/financial-index", tags=["financial-search"])
logger = logging.getLogger(__name__)


_engine = None
_engine_lock = Lock()


def get_index():
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = FinancialIndex(get_settings().financial_index_path)
    return _engine


def close_index():
    global _engine
    with _engine_lock:
        if _engine is not None:
            _engine.close()
            _engine = None


class BuildRequest(BaseModel):
    dataset_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,80}$")
    source_dataset_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,80}$")
    manifest_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    per_filing_limit: int | None = Field(default=None, ge=1, le=100000)
    allow_partial: bool = False
    force_rebuild: bool = False


class SearchRequest(BaseModel):
    dataset_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,80}$")
    query: str = Field(min_length=2, max_length=2000)
    mode: Literal["bm25", "dense", "hybrid"] = "hybrid"
    generation: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    top_k: int = Field(default=5, ge=1, le=20)
    candidate_limit: int = Field(default=40, ge=1, le=100)
    cik: str | None = Field(default=None, pattern=r"^[0-9]{1,10}$")
    ticker: str | None = Field(default=None, min_length=1, max_length=20)
    form_type: Literal["10-K", "10-Q", "10-K/A", "10-Q/A"] | None = None
    fiscal_year: int | None = Field(default=None, ge=1900, le=2200)
    fiscal_period: str | None = Field(default=None, min_length=1, max_length=8)
    filing_ids: list[str] = Field(default_factory=list, max_length=20)
    expected_manifests: list[str] | None = Field(default=None, max_length=8)
    allow_degraded: bool = False


class ActivateRequest(BaseModel):
    dataset_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,80}$")
    generation: str = Field(pattern=r"^[0-9a-f]{64}$")


@router.get("/datasets")
def indexed_datasets():
    return {"datasets": get_index().describe()}


def run_build(dataset, generation):
    try:
        get_index().build(dataset, generation)
    except Exception:
        logger.exception("Financial index generation build failed generation=%s", generation)


@router.post("/build", status_code=202)
def build_index(request: BuildRequest, background_tasks: BackgroundTasks):
    try:
        generation = get_index().plan(request.dataset_id, [{
            "root": str(get_settings().financial_corpus_dir), "dataset_id": request.source_dataset_id,
            "manifest_hash": request.manifest_hash, "per_filing_limit": request.per_filing_limit,
            "allow_partial": request.allow_partial}], force_rebuild=request.force_rebuild)
        background_tasks.add_task(run_build, request.dataset_id, generation)
        return {"dataset_id": request.dataset_id, "generation": generation, "state": "BUILD_QUEUED"}
    except ValueError as exc:
        raise HTTPException(409, detail={"code": str(exc)}) from exc
    except Exception as exc:
        raise HTTPException(503, detail={"code": "INDEX_BUILD_UNAVAILABLE", "message": str(exc)}) from exc


@router.post("/search")
def financial_search(request: SearchRequest):
    if not request.query.strip() or request.top_k > request.candidate_limit:
        raise HTTPException(422, detail={"code": "INVALID_QUERY_OR_LIMITS"})
    filters = {key: value for key, value in {
        "cik": normalize_cik(request.cik) if request.cik else None, "ticker": request.ticker,
        "form_type": request.form_type, "fiscal_year": request.fiscal_year,
        "fiscal_period": request.fiscal_period, "filing_ids": request.filing_ids}.items() if value is not None and value != []}
    try:
        return get_index().search(request.dataset_id, request.query, request.mode,
            generation=request.generation, top_k=request.top_k, candidate_limit=request.candidate_limit,
            filters=filters, allow_degraded=request.allow_degraded, expected_manifests=request.expected_manifests)
    except ValueError as exc:
        raise HTTPException(409, detail={"code": str(exc)}) from exc
    except Exception as exc:
        raise HTTPException(503, detail={"code": "INDEX_SEARCH_UNAVAILABLE", "message": str(exc)}) from exc


@router.post("/activate")
def activate_generation(request: ActivateRequest):
    try:
        get_index().activate(request.dataset_id, request.generation)
        return {"dataset_id": request.dataset_id, "generation": request.generation, "state": "READY"}
    except Exception as exc:
        raise HTTPException(409, detail={"code": "GENERATION_ACTIVATION_FAILED", "message": str(exc)}) from exc

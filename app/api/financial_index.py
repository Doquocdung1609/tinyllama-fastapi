"""Persistent SEC evidence search integrated into the existing application."""
from hmac import compare_digest
import logging
from threading import Lock
from time import monotonic
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.config import get_settings
from app.financial_index.service import FinancialIndex
from app.financial_ingestion.sec_client import normalize_cik

router = APIRouter(prefix="/financial-index", tags=["financial-search"])
logger = logging.getLogger(__name__)


_engine = None
_engine_lock = Lock()
_admission_lock = Lock()
_pending_builds = 0
_last_forced_build: dict[str, float] = {}


def _safe_code(exc: Exception, fallback: str) -> str:
    text = str(exc)
    return text if text.isupper() and text.replace("_", "").isalnum() else fallback


def require_financial_admin(request: Request, authorization: str | None = Header(default=None)):
    """Authorize state mutation without ever logging or echoing the credential."""
    settings = get_settings()
    length = request.headers.get("content-length")
    if length:
        try:
            if int(length) > settings.financial_index_max_request_bytes:
                raise HTTPException(413, detail={"code": "MUTATION_REQUEST_TOO_LARGE"})
        except ValueError as exc:
            raise HTTPException(400, detail={"code": "INVALID_CONTENT_LENGTH"}) from exc
    client_host = request.client.host if request.client else ""
    if settings.financial_index_allow_local_mutations and client_host in {"127.0.0.1", "::1", "testclient"}:
        return
    configured = settings.financial_index_admin_token
    if not configured:
        raise HTTPException(503, detail={"code": "FINANCIAL_ADMIN_NOT_CONFIGURED"})
    scheme, _, supplied = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not supplied or not compare_digest(supplied, configured):
        raise HTTPException(401, detail={"code": "FINANCIAL_ADMIN_UNAUTHORIZED"},
                            headers={"WWW-Authenticate": "Bearer"})


def _admit_build(dataset: str, force: bool) -> None:
    global _pending_builds
    settings = get_settings()
    now = monotonic()
    with _admission_lock:
        if _pending_builds >= max(1, settings.financial_index_max_pending_builds):
            raise HTTPException(429, detail={"code": "BUILD_QUEUE_FULL"})
        if force and now - _last_forced_build.get(dataset, float("-inf")) < max(
                0., settings.financial_index_force_rebuild_cooldown_seconds):
            raise HTTPException(429, detail={"code": "FORCE_REBUILD_COOLDOWN"})
        _pending_builds += 1
        if force:
            _last_forced_build[dataset] = now


def _release_build() -> None:
    global _pending_builds
    with _admission_lock:
        _pending_builds = max(0, _pending_builds - 1)


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
    model_config = ConfigDict(extra="forbid")

    dataset_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,80}$")
    source_dataset_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,80}$")
    manifest_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    per_filing_limit: int | None = Field(default=None, ge=1, le=10000)
    allow_partial: bool = False
    force_rebuild: bool = False


class SearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

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

    @field_validator("ticker")
    @classmethod
    def canonical_ticker(cls, value):
        if value is None:
            return value
        value = value.strip().upper()
        import re
        if not re.fullmatch(r"[A-Z0-9][A-Z0-9.-]{0,9}", value):
            raise ValueError("ticker must be a canonical market symbol")
        return value

    @field_validator("fiscal_period")
    @classmethod
    def canonical_period(cls, value):
        if value is None:
            return value
        value = value.strip().upper()
        if value not in {"FY", "Q1", "Q2", "Q3", "Q4", "H1", "H2"}:
            raise ValueError("unsupported fiscal period")
        return value

    @field_validator("filing_ids")
    @classmethod
    def canonical_filing_ids(cls, values):
        import re
        pattern = re.compile(r"^sec:[0-9]{10}:[0-9]{10}-[0-9]{2}-[0-9]{6}$")
        if len(values) != len(set(values)) or any(not pattern.fullmatch(value) for value in values):
            raise ValueError("filing_ids must be unique canonical SEC identities")
        return values

    @field_validator("expected_manifests")
    @classmethod
    def canonical_manifest_ids(cls, values):
        import re
        if values is not None and (len(values) != len(set(values)) or any(
                not re.fullmatch(r"[0-9a-f]{64}", value) for value in values)):
            raise ValueError("expected_manifests must be unique SHA-256 identities")
        return values


class ActivateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dataset_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,80}$")
    generation: str = Field(pattern=r"^[0-9a-f]{64}$")


class ProtectRequest(ActivateRequest):
    kind: Literal["pin", "evaluation"]
    reference: str = Field(pattern=r"^[A-Za-z0-9_.:/-]{1,160}$")
    remove: bool = False


class CleanupRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    generations: list[str] = Field(min_length=1, max_length=20)
    apply: bool = False

    @field_validator("generations")
    @classmethod
    def canonical_generations(cls, values):
        import re
        if len(values) != len(set(values)) or any(not re.fullmatch(r"[0-9a-f]{64}", value) for value in values):
            raise ValueError("generations must be unique SHA-256 identities")
        return values


@router.get("/datasets")
def indexed_datasets():
    return {"datasets": get_index().describe()}


@router.get("/retention")
def retention_inventory():
    return get_index().retention_inventory()


def run_build(dataset, generation):
    try:
        get_index().build(dataset, generation)
    except Exception:
        logger.exception("Financial index generation build failed generation=%s", generation)
    finally:
        _release_build()


@router.post("/build", status_code=202, dependencies=[Depends(require_financial_admin)])
def build_index(request: BuildRequest, background_tasks: BackgroundTasks):
    admitted = False
    try:
        _admit_build(request.dataset_id, request.force_rebuild)
        admitted = True
        generation = get_index().plan(request.dataset_id, [{
            "root": str(get_settings().financial_corpus_dir), "dataset_id": request.source_dataset_id,
            "manifest_hash": request.manifest_hash, "per_filing_limit": request.per_filing_limit,
            "allow_partial": request.allow_partial}], force_rebuild=request.force_rebuild)
        background_tasks.add_task(run_build, request.dataset_id, generation)
        return {"dataset_id": request.dataset_id, "generation": generation, "state": "BUILD_QUEUED"}
    except ValueError as exc:
        if admitted:
            _release_build()
        raise HTTPException(409, detail={"code": _safe_code(exc, "INDEX_BUILD_CONFLICT")}) from exc
    except HTTPException:
        if admitted:
            _release_build()
        raise
    except Exception as exc:
        if admitted:
            _release_build()
        logger.exception("Financial index build planning failed")
        raise HTTPException(503, detail={"code": "INDEX_BUILD_UNAVAILABLE"}) from exc


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
        raise HTTPException(409, detail={"code": _safe_code(exc, "INDEX_SEARCH_CONFLICT")}) from exc
    except Exception as exc:
        logger.exception("Financial index search failed")
        raise HTTPException(503, detail={"code": "INDEX_SEARCH_UNAVAILABLE"}) from exc


@router.post("/activate", dependencies=[Depends(require_financial_admin)])
def activate_generation(request: ActivateRequest):
    try:
        get_index().activate(request.dataset_id, request.generation)
        return {"dataset_id": request.dataset_id, "generation": request.generation, "state": "READY"}
    except Exception as exc:
        logger.warning("Financial index activation rejected dataset=%s generation=%s",
                       request.dataset_id, request.generation)
        raise HTTPException(409, detail={"code": "GENERATION_ACTIVATION_FAILED"}) from exc


@router.post("/retention/protect", dependencies=[Depends(require_financial_admin)])
def protect_generation(request: ProtectRequest):
    try:
        if request.remove:
            get_index().unprotect_generation(
                request.dataset_id, request.generation, request.kind, request.reference)
        else:
            get_index().protect_generation(
                request.dataset_id, request.generation, request.kind, request.reference)
        return {"dataset_id": request.dataset_id, "generation": request.generation,
                "kind": request.kind, "reference": request.reference,
                "state": "REMOVED" if request.remove else "PROTECTED"}
    except Exception as exc:
        raise HTTPException(409, detail={"code": "GENERATION_PROTECTION_FAILED"}) from exc


@router.post("/retention/cleanup", dependencies=[Depends(require_financial_admin)])
def cleanup_generations(request: CleanupRequest):
    try:
        return get_index().cleanup_generations(request.generations, apply=request.apply)
    except ValueError as exc:
        raise HTTPException(409, detail={"code": _safe_code(exc, "GENERATION_CLEANUP_REJECTED")}) from exc
    except Exception as exc:
        logger.exception("Financial index cleanup failed")
        raise HTTPException(503, detail={"code": "GENERATION_CLEANUP_FAILED"}) from exc

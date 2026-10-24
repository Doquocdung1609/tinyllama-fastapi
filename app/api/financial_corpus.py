"""SEC corpus discovery, bounded ingestion, resume, manifest and evidence APIs."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

from app.config import get_settings
from app.financial_ingestion.pipeline import FinancialCorpusPipeline
from app.financial_ingestion.registry import FinancialRegistry
from app.financial_ingestion.schemas import FilingMetadata
from app.financial_ingestion.sec_client import (
    ALLOWED_FORMS, SECClient, SECConfigurationError, normalize_cik,
)

router = APIRouter(prefix="/financial-corpus", tags=["financial-corpus"])


class DiscoveryRequest(BaseModel):
    cik: str
    ticker: str | None = Field(default=None, max_length=16)
    forms: list[Literal["10-K", "10-Q", "10-K/A", "10-Q/A"]] = Field(
        default_factory=lambda: ["10-K", "10-Q", "10-K/A", "10-Q/A"])
    date_from: str | None = None
    date_to: str | None = None
    limit: int = Field(default=10, ge=1, le=200)
    dry_run: bool = False


class JobCreateRequest(BaseModel):
    dataset_id: str = Field(min_length=1, max_length=80)
    filings: list[FilingMetadata] = Field(min_length=1, max_length=200)
    dry_run: bool = False
    start: bool = True


def registry() -> FinancialRegistry:
    return FinancialRegistry(get_settings().financial_registry_db)


def local_pipeline() -> FinancialCorpusPipeline:
    return FinancialCorpusPipeline(registry=registry())


def live_pipeline() -> FinancialCorpusPipeline:
    settings = get_settings()
    client = SECClient(settings.sec_user_agent,
                       requests_per_second=settings.sec_requests_per_second,
                       timeout_seconds=settings.sec_timeout_seconds,
                       max_retries=settings.sec_max_retries)
    return FinancialCorpusPipeline(registry=registry(), client=client)


def initialize_financial_registry() -> dict:
    return registry().recover_interrupted()


@router.post("/discover")
def discover_filings(request: DiscoveryRequest):
    try:
        cik = normalize_cik(request.cik)
        url = f"https://data.sec.gov/submissions/CIK{cik}.json"
        if request.dry_run:
            return {"status": "DRY_RUN", "network_requests": 0,
                    "planned_request": {"url": url, "forms": request.forms,
                                        "date_from": request.date_from,
                                        "date_to": request.date_to, "limit": request.limit}}
        pipeline = live_pipeline()
        filings = pipeline.client.discover(
            cik, ticker=request.ticker, forms=request.forms,
            date_from=request.date_from, date_to=request.date_to, limit=request.limit)
        return {"status": "DISCOVERED", "count": len(filings),
                "filings": [item.model_dump(mode="json") for item in filings]}
    except SECConfigurationError as exc:
        raise HTTPException(503, detail={"code": "SEC_USER_AGENT_REQUIRED", "message": str(exc)}) from exc
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(502, detail={"code": "SEC_SOURCE_UNAVAILABLE", "message": str(exc)}) from exc


@router.post("/jobs", status_code=201)
def create_ingestion_job(request: JobCreateRequest, background_tasks: BackgroundTasks):
    try:
        pipeline = local_pipeline() if request.dry_run else live_pipeline()
        job = pipeline.create_job(request.dataset_id, request.filings, dry_run=request.dry_run)
        if request.start and not request.dry_run:
            background_tasks.add_task(pipeline.run_job, job.job_id)
        return job.model_dump(mode="json")
    except SECConfigurationError as exc:
        raise HTTPException(503, detail={"code": "SEC_USER_AGENT_REQUIRED", "message": str(exc)}) from exc
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc)) from exc


@router.get("/jobs/{job_id}")
def ingestion_job_status(job_id: str):
    job = registry().get_job(job_id)
    if not job:
        raise HTTPException(404, detail={"code": "JOB_NOT_FOUND"})
    return job.model_dump(mode="json")


@router.post("/jobs/{job_id}/resume")
def resume_ingestion_job(job_id: str, background_tasks: BackgroundTasks):
    try:
        pipeline = live_pipeline()
        job = pipeline.registry.get_job(job_id)
        if not job:
            raise HTTPException(404, detail={"code": "JOB_NOT_FOUND"})
        if job.dry_run:
            raise HTTPException(409, detail={"code": "DRY_RUN_CANNOT_RESUME"})
        background_tasks.add_task(pipeline.run_job, job_id)
        return {"job_id": job_id, "status": "RESUME_QUEUED", "next_index": job.next_index}
    except SECConfigurationError as exc:
        raise HTTPException(503, detail={"code": "SEC_USER_AGENT_REQUIRED", "message": str(exc)}) from exc


@router.get("/filings")
def list_filings(dataset_id: str | None = None):
    rows = registry().list_filings(dataset_id)
    result = []
    for row in rows:
        metadata = FilingMetadata.model_validate_json(row.pop("metadata_json")).model_dump(mode="json")
        result.append({**row, "metadata": metadata})
    return result


@router.get("/filings/{filing_id:path}")
def filing_status(filing_id: str):
    row = registry().get_filing(filing_id)
    if not row:
        raise HTTPException(404, detail={"code": "DOCUMENT_NOT_FOUND"})
    row["metadata"] = FilingMetadata.model_validate_json(row.pop("metadata_json")).model_dump(mode="json")
    return row


@router.post("/manifests/{dataset_id}")
def create_manifest(dataset_id: str):
    try:
        return local_pipeline().create_manifest(dataset_id).model_dump(mode="json")
    except ValueError as exc:
        raise HTTPException(404, detail=str(exc)) from exc


@router.get("/manifests")
def list_manifests(dataset_id: str | None = None):
    return registry().manifests(dataset_id)


@router.get("/evidence/{chunk_id}")
def source_evidence(chunk_id: str):
    try:
        result = local_pipeline().evidence(chunk_id)
    except ValueError as exc:
        raise HTTPException(404, detail={"code": "DOCUMENT_NOT_FOUND", "message": str(exc)}) from exc
    if result["status"] == "SOURCE_UNAVAILABLE":
        raise HTTPException(410, detail={"code": "SOURCE_UNAVAILABLE", "result": result})
    if result["status"] != "VERIFIED":
        raise HTTPException(409, detail={"code": result["status"], "result": result})
    return result


@router.get("/quality/{filing_id:path}")
def extraction_quality(filing_id: str):
    try:
        return local_pipeline().extraction_quality(filing_id)
    except LookupError as exc:
        raise HTTPException(404, detail={"code": "DOCUMENT_NOT_FOUND"}) from exc
    except FileNotFoundError as exc:
        raise HTTPException(410, detail={"code": "STRUCTURED_SOURCE_UNAVAILABLE"}) from exc
    except ValueError as exc:
        raise HTTPException(409, detail={"code": "INVALID_STRUCTURED_SNAPSHOT"}) from exc

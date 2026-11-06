"""Local authenticated product endpoints for user-owned PDFs."""
from functools import lru_cache
import hmac
import os
from pathlib import Path
from threading import Thread, RLock

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field

from app.config import ROOT_DIR
from app.product.workspace import MAX_PDF_BYTES, PdfWorkspace
from app.product.sec_search import SecResearchIndex


router = APIRouter(prefix="/studio", tags=["financial-studio"])
_factory_lock = RLock()


@lru_cache(maxsize=1)
def _workspace_cached():
    root = Path(os.getenv("STUDIO_WORKSPACE_DIR", str(ROOT_DIR / "studio_workspace")))
    if (root/'ocr-financial-v2.json').is_file():
        from app.product.ocr_financial_workspace import FinancialOcrWorkspace
        return FinancialOcrWorkspace(root)
    if (root/'search-v3r2.json').is_file():
        from app.product.controlled_workspace import ControlledPdfWorkspace
        return ControlledPdfWorkspace(root)
    if (root/'derived-generation.json').is_file():
        from app.product.derived_workspace import DerivedPdfWorkspace
        return DerivedPdfWorkspace(root)
    return PdfWorkspace(root)


@lru_cache(maxsize=1)
def _sec_cached():
    from app.product.local_config import sec_roots
    configured=sec_roots()
    root = configured['STUDIO_SEC_RESEARCH_ROOT']
    vector_root = configured['STUDIO_SEC_VECTOR_ROOT']
    qa_root = configured['TOPIC3_RESEARCH_ROOT']
    if not root or not vector_root or not qa_root:
        raise ValueError("SEC_SHARED_SOURCE_ROOTS_NOT_CONFIGURED")
    return SecResearchIndex(Path(root), Path(vector_root), Path(qa_root))


def workspace():
    with _factory_lock:
        return _workspace_cached()


def sec_index():
    from app.product.sec_library import active
    if active.get() is not None:return active.get()
    with _factory_lock:
        return _sec_cached()


workspace.cache_info = _workspace_cached.cache_info
workspace.cache_clear = _workspace_cached.cache_clear
sec_index.cache_info = _sec_cached.cache_info
sec_index.cache_clear = _sec_cached.cache_clear


def require_studio_token(authorization: str | None = Header(default=None)):
    configured = os.getenv("STUDIO_API_TOKEN", "")
    if len(configured) < 16:
        raise HTTPException(503, detail={"code": "STUDIO_TOKEN_NOT_CONFIGURED"})
    if not hmac.compare_digest(authorization or "", "Bearer " + configured):
        raise HTTPException(401, detail={"code": "STUDIO_UNAUTHORIZED"},
                            headers={"WWW-Authenticate": "Bearer"})


def _error(exc):
    code = str(exc)
    return code if code.isupper() and code.replace("_", "").isalnum() else "STUDIO_OPERATION_FAILED"


class SearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=2, max_length=2000)
    mode: str = Field(pattern="^(bm25|dense|hybrid)$")
    top_k: int = Field(default=5, ge=1, le=20)
    document_ids: list[str] = Field(default_factory=list, max_length=100)


class SecSearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=2, max_length=2000)
    mode: str = Field(pattern="^(bm25|dense|hybrid)$")
    top_k: int = Field(default=5, ge=1, le=20)
    ticker: str = Field(default="", max_length=20)
    report_period: str = Field(default="", max_length=20)


@router.get("/health")
def health():
    try:
        return workspace().health()
    except Exception:
        return {"workspace": "UNAVAILABLE", "ready_documents": 0, "total_documents": 0}


@router.get("/sec/catalog", dependencies=[Depends(require_studio_token)])
def sec_catalog():
    try:
        from app.product.sec_library import catalog
        return catalog()
    except Exception as exc:
        return {"status": "UNAVAILABLE", "reason": _error(exc), "filings": []}


@router.post("/sec/search", dependencies=[Depends(require_studio_token)])
def sec_search(payload: SecSearchRequest):
    try:
        return sec_index().search(payload.query, payload.mode, payload.top_k,
                                  payload.ticker, payload.report_period)
    except ValueError as exc:
        raise HTTPException(409, detail={"code": _error(exc)}) from exc
    except Exception as exc:
        raise HTTPException(503, detail={"code": _error(exc)}) from exc


@router.get("/documents", dependencies=[Depends(require_studio_token)])
def documents():
    from app.product.financial_understanding import document_profile
    w=workspace();documents=[]
    for original in w.list_documents():
        doc=dict(original)
        if doc['status']=='READY':
            w.source_file(doc['id'])
            profile=document_profile(w,doc)
            doc['display_metadata']=profile
            if len(profile['identities'])==1:
                doc['issuer_display_original']=doc.get('issuer','');doc['issuer']=profile['identities'][0]
            if not doc.get('report_period') and profile['report_year']:doc['report_period']=profile['report_year']
        documents.append(doc)
    return {'documents':documents}


@router.post("/documents", status_code=202, dependencies=[Depends(require_studio_token)])
async def upload_document(file: UploadFile = File(...), issuer: str = Form(""),
                          document_type: str = Form("PDF"), report_period: str = Form("")):
    if file.content_type != "application/pdf":
        raise HTTPException(415, detail={"code": "PDF_MIME_REQUIRED"})
    data = await file.read(MAX_PDF_BYTES + 1)
    await file.close()
    try:
        item = workspace().add_pdf(file.filename or "document.pdf", data, issuer,
                                   document_type, report_period)
    except ValueError as exc:
        raise HTTPException(422, detail={"code": _error(exc)}) from exc
    except RuntimeError as exc:
        raise HTTPException(507, detail={"code": _error(exc)}) from exc
    if not item.get("duplicate") and item["status"] == "UPLOADED":
        from app.product.search_preparation import process_and_prepare
        Thread(target=process_and_prepare, args=(workspace(),item["id"]), daemon=True).start()
    return item


@router.get("/documents/{document_id}", dependencies=[Depends(require_studio_token)])
def document(document_id: str):
    item = workspace().document(document_id)
    if item is None:
        raise HTTPException(404, detail={"code": "DOCUMENT_NOT_FOUND"})
    return item


@router.get("/documents/{document_id}/first-chunk", dependencies=[Depends(require_studio_token)])
def first_chunk(document_id: str):
    try:
        return workspace().first_chunk(document_id)
    except ValueError as exc:
        raise HTTPException(409, detail={"code": _error(exc)}) from exc


@router.post("/documents/{document_id}/retry", dependencies=[Depends(require_studio_token)])
def retry(document_id: str):
    item = workspace().document(document_id)
    if item is None:
        raise HTTPException(404, detail={"code": "DOCUMENT_NOT_FOUND"})
    if item["status"] not in {"FAILED", "INTERRUPTED"}:
        raise HTTPException(409, detail={"code": "DOCUMENT_RETRY_NOT_ALLOWED"})
    workspace()._stage(document_id, "RETRY_QUEUED", "RETRY_QUEUED")
    from app.product.search_preparation import process_and_prepare
    Thread(target=process_and_prepare, args=(workspace(),document_id), daemon=True).start()
    return {"document_id": document_id, "status": "RETRY_QUEUED"}


@router.delete("/documents/{document_id}", dependencies=[Depends(require_studio_token)])
def delete(document_id: str, confirm: str = ""):
    if confirm != document_id:
        raise HTTPException(409, detail={"code": "DOCUMENT_DELETE_CONFIRMATION_REQUIRED"})
    try:
        if not workspace().delete(document_id):
            raise HTTPException(404, detail={"code": "DOCUMENT_NOT_FOUND"})
        if (workspace().root/'derived-generation.json').exists():
            from app.product.search_preparation import preparation
            preparation(workspace()).schedule(invalidate=getattr(workspace(),'search_candidate_version',None) in {'V3R2','V3R3'})
    except ValueError as exc:
        raise HTTPException(409, detail={"code": _error(exc)}) from exc
    return {"deleted": True, "document_id": document_id}


@router.post("/search", dependencies=[Depends(require_studio_token)])
def search(payload: SearchRequest):
    try:
        return workspace().search(payload.query, payload.mode, payload.top_k, payload.document_ids)
    except ValueError as exc:
        raise HTTPException(409, detail={"code": _error(exc)}) from exc
    except Exception as exc:
        raise HTTPException(503, detail={"code": _error(exc)}) from exc


@router.get("/documents/{document_id}/pages/{page_number}/highlight",
            dependencies=[Depends(require_studio_token)])
def highlight(document_id: str, page_number: int, chunk_id: str, phrase: str = ""):
    try:
        png, status = workspace().page_image(document_id, page_number, [chunk_id], phrase)
    except ValueError as exc:
        raise HTTPException(409, detail={"code": _error(exc)}) from exc
    return Response(png, media_type="image/png", headers={"X-Highlight-Status": status})


from app.product.sec_library import router as sec_library_router
router.include_router(sec_library_router(require_studio_token))

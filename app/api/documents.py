"""PDF upload and document library endpoints."""
from pathlib import Path
from uuid import uuid4
from hashlib import sha256
import logging
import aiofiles
from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from app.config import get_settings
from app.services import rag_service

router = APIRouter(prefix="/documents", tags=["documents"])
logger = logging.getLogger(__name__)


@router.post("/upload")
async def upload_pdf(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    settings = get_settings()
    if file.content_type != "application/pdf" or Path(file.filename or "").suffix.lower() != ".pdf":
        raise HTTPException(415, "Tệp phải có định dạng PDF và phần mở rộng .pdf.")
    settings.prepare_dirs()
    safe_name = Path(file.filename or "document.pdf").name
    temporary_id = uuid4().hex
    target = settings.upload_dir / f".{temporary_id}.uploading"
    size = 0
    digest = sha256()
    try:
        async with aiofiles.open(target, "wb") as destination:
            while block := await file.read(1024 * 1024):
                size += len(block)
                if size > settings.max_upload_mb * 1024 * 1024:
                    target.unlink(missing_ok=True)
                    raise HTTPException(413, f"Dung lượng PDF vượt quá {settings.max_upload_mb} MB.")
                await destination.write(block)
                digest.update(block)
    finally:
        await file.close()
    content_hash = digest.hexdigest()
    duplicate = rag_service.find_document_by_hash(content_hash)
    if duplicate:
        existing_path = Path(duplicate.get("path") or "")
        if duplicate.get("status") == "FAILED":
            if existing_path and not existing_path.exists():
                existing_path.parent.mkdir(parents=True, exist_ok=True)
                target.replace(existing_path)
            else:
                target.unlink(missing_ok=True)
            background_tasks.add_task(rag_service.process_document, duplicate["document_id"])
            return {**duplicate, "size_bytes": size, "duplicate": True, "status": "PROCESSING",
                    "message": "PDF trùng nội dung; đang thử xử lý lại bản ghi đã lỗi."}
        target.unlink(missing_ok=True)
        return {**duplicate, "size_bytes": size, "duplicate": True,
                "message": "PDF trùng nội dung; dùng lại index hiện có."}
    doc_id = content_hash[:32]
    final_target = settings.upload_dir / f"{doc_id}_{safe_name}"
    target.replace(final_target)
    doc = rag_service.register_document(doc_id, safe_name, str(final_target), content_hash)
    logger.info("pdf upload accepted document_id=%s filename=%s size_bytes=%d", doc_id, safe_name, size)
    background_tasks.add_task(rag_service.process_document, doc_id)
    return {**doc, "size_bytes": size, "status": "UPLOADED", "message": "Đã nhận PDF; xử lý bắt đầu ở nền."}


@router.get("")
def list_documents():
    return rag_service.documents()


@router.get("/{document_id}")
def document_details(document_id: str):
    doc = rag_service.get_document(document_id)
    if not doc:
        raise HTTPException(404, "Không tìm thấy tài liệu.")
    return doc


@router.post("/{document_id}/process")
def process_again(document_id: str, background_tasks: BackgroundTasks):
    doc = rag_service.get_document(document_id)
    if not doc:
        raise HTTPException(404, "Không tìm thấy tài liệu.")
    background_tasks.add_task(rag_service.process_document, document_id)
    return {"document_id": document_id, "status": "PROCESSING"}


@router.get("/{document_id}/chunks")
def get_chunks(document_id: str):
    if not rag_service.get_document(document_id):
        raise HTTPException(404, "Không tìm thấy tài liệu.")
    return rag_service.chunks_for(document_id)


@router.get("/{document_id}/preview")
def preview_document_chunks(document_id: str, chunk_size: int = 800, chunk_overlap: int = 120):
    doc = rag_service.get_document(document_id)
    if not doc:
        raise HTTPException(404, "Không tìm thấy tài liệu.")
    try:
        pages, chunks = rag_service.preview_chunks(doc["path"], document_id, doc["filename"], chunk_size, chunk_overlap)
        return {"pages": pages, "chunks": chunks}
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/{document_id}/pages/{page_number}")
def inspect_document_page(document_id: str, page_number: int):
    if not rag_service.get_document(document_id):
        raise HTTPException(404, "Không tìm thấy tài liệu.")
    result = rag_service.page_inspection(document_id, page_number)
    if result is None:
        raise HTTPException(404, "Không tìm thấy dữ liệu trang đã xử lý.")
    return result


@router.get("/{document_id}/pages/{page_number}/preview")
def preview_document_page(document_id: str, page_number: int):
    try:
        path = rag_service.page_preview(document_id, page_number)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    if path is None:
        raise HTTPException(404, "Không tìm thấy tài liệu.")
    return FileResponse(path, media_type="image/png", filename=path.name)


@router.delete("/{document_id}")
def delete_document(document_id: str):
    if not rag_service.remove_document(document_id):
        raise HTTPException(404, "Không tìm thấy tài liệu.")
    return {"deleted": True, "document_id": document_id}

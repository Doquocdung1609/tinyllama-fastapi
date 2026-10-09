"""Qdrant collection status and maintenance endpoints."""
from fastapi import APIRouter, HTTPException
from app.services import qdrant_service

router = APIRouter(prefix="/qdrant", tags=["qdrant"])


@router.get("/status")
def status():
    return qdrant_service.collection_status()


@router.delete("/collection")
def clear_collection():
    try:
        qdrant_service.clear_collection()
        return {"cleared": True}
    except Exception as exc:
        raise HTTPException(503, f"Không thể xóa Qdrant collection: {exc}") from exc

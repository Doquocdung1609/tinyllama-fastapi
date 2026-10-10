"""Semantic retrieval and grounded answer endpoint."""
from fastapi import APIRouter, HTTPException
from app.config import get_settings
from app.models import RAGRequest
from app.services.rag_service import query

router = APIRouter(prefix="/rag", tags=["rag"])


@router.post("/query")
def rag_query(request: RAGRequest):
    settings = get_settings()
    try:
        return query(request.question, request.top_k, request.score_threshold,
                     request.document_id, request.generate_answer, request.model)
    except Exception as exc:
        raise HTTPException(503, f"RAG chưa sẵn sàng: {exc}") from exc

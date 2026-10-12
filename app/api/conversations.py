"""Persistent document-chat API."""
from fastapi import APIRouter, HTTPException

from app.models import ConversationCreate, ConversationMessageCreate, ConversationUpdate
from app.services import conversation_service


router = APIRouter(prefix="/conversations", tags=["conversations"])


def _error(exc: Exception) -> HTTPException:
    if isinstance(exc, conversation_service.ConversationNotFoundError):
        return HTTPException(404, str(exc))
    if isinstance(exc, conversation_service.DocumentScopeError):
        return HTTPException(409, str(exc))
    return HTTPException(500, str(exc))


@router.post("", status_code=201)
def create_conversation(request: ConversationCreate):
    try:
        return conversation_service.create_conversation(request.active_document_ids, request.title, request.settings)
    except Exception as exc:
        raise _error(exc) from exc


@router.get("")
def list_conversations():
    return conversation_service.list_conversations()


@router.get("/{conversation_id}")
def get_conversation(conversation_id: str):
    try:
        return conversation_service.get_conversation(conversation_id, include_messages=True)
    except Exception as exc:
        raise _error(exc) from exc


@router.patch("/{conversation_id}")
def update_conversation(conversation_id: str, request: ConversationUpdate):
    try:
        return conversation_service.update_conversation(conversation_id, **request.model_dump(exclude_none=True))
    except Exception as exc:
        raise _error(exc) from exc


@router.delete("/{conversation_id}", status_code=204)
def delete_conversation(conversation_id: str):
    try:
        conversation_service.delete_conversation(conversation_id)
    except Exception as exc:
        raise _error(exc) from exc


@router.get("/{conversation_id}/messages")
def list_messages(conversation_id: str, limit: int = 100):
    try:
        return conversation_service.list_messages(conversation_id, limit)
    except Exception as exc:
        raise _error(exc) from exc


@router.post("/{conversation_id}/messages")
def post_message(conversation_id: str, request: ConversationMessageCreate):
    try:
        return conversation_service.post_message(conversation_id, request.content, top_k=request.top_k,
            score_threshold=request.score_threshold, model=request.model, generate_answer=request.generate_answer)
    except Exception as exc:
        raise _error(exc) from exc

import pytest
from pydantic import ValidationError
from app.models import ChatRequest, RAGRequest


def test_chat_request_bounds():
    assert ChatRequest(message="Hi").temperature == .7
    with pytest.raises(ValidationError):
        ChatRequest(message="Hi", temperature=5)


def test_rag_defaults():
    req = RAGRequest(question="Where?")
    assert req.top_k == 3
    assert req.score_threshold == .55

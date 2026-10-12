from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from app.config import get_settings
from app.services import conversation_service, rag_service
from main import app


DOC_A = "a" * 32
DOC_B = "b" * 32


@pytest.fixture()
def conversation_env(tmp_path, monkeypatch):
    old_path = get_settings().conversation_db
    get_settings().conversation_db = tmp_path / "conversations.sqlite3"
    documents = {
        DOC_A: {"document_id": DOC_A, "filename": "bank-a.pdf", "status": "READY"},
        DOC_B: {"document_id": DOC_B, "filename": "bank-b.pdf", "status": "READY"},
    }
    monkeypatch.setattr(rag_service, "get_document", lambda document_id: documents.get(document_id))
    conversation_service.init_database()
    yield documents
    get_settings().conversation_db = old_path


def _rag_result(question, top_k, threshold, scope, generate_answer, model):
    page = 3 if "2024" in question else 4
    return {
        "answer": "Doanh thu là 125 tỷ đồng. [bank-a.pdf, trang 3].",
        "model": model or "qwen2.5:3b",
        "supporting_sources": [{"evidence_id": "E1", "chunk_id": "cell-revenue",
                                 "document_id": DOC_A, "filename": "bank-a.pdf", "page": page,
                                 "source_id": "table:p3:t1", "modality": "table", "bbox": [1, 2, 3, 4]}],
        "selected_evidence": [{"chunk_id": "cell-revenue", "document_id": DOC_A, "page": page,
                               "source_id": "table:p3:t1", "modality": "table"}],
        "calculation_validation": None,
        "citation_validation": {"citation_valid": True},
        "evidence_selection": {"context_token_estimate": 50},
        "timings": {"total_ms": 12.5},
    }


def test_conversation_persists_messages_and_resolves_followup(conversation_env, monkeypatch):
    monkeypatch.setattr(rag_service, "query", _rag_result)
    conversation = conversation_service.create_conversation([DOC_A])

    first = conversation_service.post_message(conversation["conversation_id"], "Doanh thu năm 2025 là bao nhiêu?")
    second = conversation_service.post_message(conversation["conversation_id"], "So với năm trước tăng bao nhiêu phần trăm?")
    restored = conversation_service.get_conversation(conversation["conversation_id"], include_messages=True)

    assert first["assistant_message"]["citations"][0]["chunk_id"] == "cell-revenue"
    assert "năm trước: 2024" in second["resolution"]["resolved_question"]
    assert "Kỳ đang nói đến: 2025" in second["resolution"]["resolved_question"]
    assert len(restored["messages"]) == 4
    assert restored["active_document_ids"] == [DOC_A]


def test_conversation_scope_is_isolated(conversation_env, monkeypatch):
    scopes = []
    def capture(*args):
        scopes.append(args[3])
        return _rag_result(*args)
    monkeypatch.setattr(rag_service, "query", capture)
    one = conversation_service.create_conversation([DOC_A])
    two = conversation_service.create_conversation([DOC_B])

    conversation_service.post_message(one["conversation_id"], "Doanh thu?")
    conversation_service.post_message(two["conversation_id"], "Lợi nhuận?")

    assert scopes == [[DOC_A], [DOC_B]]
    assert conversation_service.get_conversation(one["conversation_id"])["active_context"]["metric"] == "doanh thu"
    assert conversation_service.get_conversation(two["conversation_id"])["active_context"]["metric"] == "lợi nhuận"


def test_missing_document_and_ambiguous_followup_are_transparent(conversation_env, monkeypatch):
    monkeypatch.setattr(rag_service, "query", _rag_result)
    multi = conversation_service.create_conversation([DOC_A, DOC_B])
    ambiguous = conversation_service.post_message(multi["conversation_id"], "Thế còn ngân hàng còn lại?")
    assert ambiguous["assistant_message"]["processing_status"] == "NEEDS_CLARIFICATION"
    assert "ngân hàng nào" in ambiguous["assistant_message"]["content"]

    removed = conversation_service.create_conversation([DOC_A])
    conversation_env.pop(DOC_A)
    with pytest.raises(conversation_service.DocumentScopeError, match="không còn tồn tại"):
        conversation_service.post_message(removed["conversation_id"], "Doanh thu?")


def test_conversation_api_crud_and_validation(conversation_env, monkeypatch):
    monkeypatch.setattr(rag_service, "query", _rag_result)
    client = TestClient(app)
    created = client.post("/conversations", json={"active_document_ids": [DOC_A]} )
    assert created.status_code == 201
    conversation_id = created.json()["conversation_id"]
    answered = client.post(f"/conversations/{conversation_id}/messages", json={"content": "Doanh thu 2025?"})
    assert answered.status_code == 200
    assert answered.json()["assistant_message"]["processing_status"] == "COMPLETED"
    restored = client.get(f"/conversations/{conversation_id}").json()
    assert len(restored["messages"]) == 2
    assert client.delete(f"/conversations/{conversation_id}").status_code == 204
    assert client.get(f"/conversations/{conversation_id}").status_code == 404
    assert client.post("/conversations", json={"active_document_ids": ["../secret"]}).status_code == 409


def test_explicit_year_switch_updates_followup_context(conversation_env, monkeypatch):
    monkeypatch.setattr(rag_service, "query", _rag_result)
    conversation = conversation_service.create_conversation([DOC_A])
    conversation_service.post_message(conversation["conversation_id"], "Doanh thu năm 2024?")
    conversation_service.post_message(conversation["conversation_id"], "Chuyển sang năm 2025.")
    followup = conversation_service.post_message(conversation["conversation_id"], "Chỉ tiêu đó thế nào?")
    assert "2025" in followup["resolution"]["resolved_question"]
    assert "2024" not in followup["resolution"]["resolved_question"]


def test_prior_year_followup_carries_metric_and_correction_preserves_claim_for_verification(conversation_env, monkeypatch):
    monkeypatch.setattr(rag_service, "query", _rag_result)
    conversation = conversation_service.create_conversation([DOC_A])
    conversation_service.post_message(conversation["conversation_id"], "Doanh thu năm 2025 là bao nhiêu?")
    followup = conversation_service.post_message(conversation["conversation_id"], "So với năm trước tăng bao nhiêu phần trăm?")
    assert "Chỉ tiêu đang nói đến: doanh thu" in followup["resolution"]["resolved_question"]

    conversation_service.post_message(conversation["conversation_id"], "Lợi nhuận năm 2024 là 15 triệu đồng đúng không?")
    correction = conversation_service.post_message(conversation["conversation_id"], "Hãy sửa câu trả lời trước.")
    resolved = correction["resolution"]["resolved_question"]
    assert "15 triệu đồng" in resolved
    assert "nguyên khẳng định trước" in resolved


def test_explicit_page_survives_uncited_answer_for_ordinal_table_followup(conversation_env, monkeypatch):
    def no_citation(*args):
        result = _rag_result(*args)
        result.update({"answer": "Tài liệu chưa cung cấp đủ thông tin.",
                       "supporting_sources": [], "selected_evidence": []})
        return result

    monkeypatch.setattr(rag_service, "query", no_citation)
    conversation = conversation_service.create_conversation([DOC_A])
    conversation_service.post_message(conversation["conversation_id"], "Trang 1 có các bảng nào?")
    followup = conversation_service.post_message(conversation["conversation_id"],
                                                  "Giải thích bảng thứ hai trên trang đó.")
    assert followup["resolution"]["uncertainty"] is None
    assert "Trang đã trích dẫn gần nhất: 1" in followup["resolution"]["resolved_question"]
    assert "table:p1:t2" in followup["resolution"]["resolved_question"]

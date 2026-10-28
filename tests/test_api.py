"""Product route isolation and retained document compatibility."""
from fastapi.testclient import TestClient

from main import app
from app.config import get_settings
from app.services import rag_service


def test_health_and_home():
    client = TestClient(app)
    assert client.get("/health").json()["status"] == "ok"
    assert client.get("/").json()["model"] == get_settings().ollama_model


def test_pdf_upload_rejects_wrong_extension():
    response = TestClient(app).post("/documents/upload", files={"file": ("notes.txt", b"not pdf", "text/plain")})
    assert response.status_code == 415


def test_duplicate_failed_pdf_is_reprocessed(tmp_path, monkeypatch):
    settings = get_settings()
    old_upload_dir = settings.upload_dir
    settings.upload_dir = tmp_path
    existing = tmp_path / "existing.pdf"
    existing.write_bytes(b"%PDF-1.4 failed fixture")
    failed = {"document_id": "a" * 32, "filename": "failed.pdf", "path": str(existing),
              "status": "FAILED", "content_hash": "ignored"}
    calls = []
    monkeypatch.setattr(rag_service, "find_document_by_hash", lambda value: failed)
    monkeypatch.setattr(rag_service, "process_document", lambda document_id: calls.append(document_id))
    try:
        response = TestClient(app).post(
            "/documents/upload", files={"file": ("failed.pdf", b"%PDF-1.4 failed fixture", "application/pdf")})
    finally:
        settings.upload_dir = old_upload_dir
    assert response.status_code == 200
    assert response.json()["status"] == "PROCESSING"
    assert response.json()["duplicate"] is True
    assert calls == ["a" * 32]


def test_unrelated_media_and_general_chat_routes_are_absent():
    client = TestClient(app)
    for route in ("/chat", "/chat/stream", "/tts/generate", "/image/generate",
                  "/video/generate", "/video/capabilities", "/generate"):
        assert client.post(route, json={}).status_code == 404
    for path in ("/audio/example.wav", "/images/example.png", "/videos/example.mp4"):
        assert client.get(path).status_code == 404


def test_grounded_rag_route_remains_available():
    assert TestClient(app).post("/rag/query", json={"question": ""}).status_code == 422

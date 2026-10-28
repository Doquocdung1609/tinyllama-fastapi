"""Product API is default deny and validates requests before any index access."""
from fastapi.testclient import TestClient

from main import app


def test_studio_routes_require_explicit_token(monkeypatch):
    client = TestClient(app)
    monkeypatch.delenv("STUDIO_API_TOKEN", raising=False)
    assert client.get("/studio/documents").status_code == 503
    monkeypatch.setenv("STUDIO_API_TOKEN", "fixture-token-at-least-sixteen-chars")
    assert client.get("/studio/documents").status_code == 401
    assert client.post("/studio/sec/search", json={"query": "total assets", "mode": "bm25"}).status_code == 401
    assert client.get("/studio/sec/catalog", headers={"Authorization": "Bearer wrong"}).status_code == 401


def test_studio_search_rejects_invalid_input_before_access(monkeypatch):
    monkeypatch.setenv("STUDIO_API_TOKEN", "fixture-token-at-least-sixteen-chars")
    client = TestClient(app)
    headers = {"Authorization": "Bearer fixture-token-at-least-sixteen-chars"}
    assert client.post("/studio/search", headers=headers,
                       json={"query": "x" * 2001, "mode": "bm25"}).status_code == 422
    assert client.post("/studio/search", headers=headers,
                       json={"query": "total assets", "mode": "invented"}).status_code == 422
    assert client.post("/studio/sec/search", headers=headers,
                       json={"query": "total assets", "mode": "bm25", "unknown": True}).status_code == 422

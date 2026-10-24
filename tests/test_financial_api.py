from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.api import financial

app = FastAPI()
app.include_router(financial.router)


def test_api_schema_rejects_missing_scope():
    assert TestClient(app).post("/financial/search", json={"query": "net income"}).status_code == 422


def test_api_exposes_retrieval_methods_and_source_scores(monkeypatch):
    monkeypatch.setattr(financial, "search", lambda *args: {
        "method": args[2], "results": [{"chunk_id": "c1", "page": 3, "bm25_score": 2.1}]})
    response = TestClient(app).post("/financial/search", json={
        "query": "operating cash flow", "document_ids": ["a1"], "method": "bm25"})
    assert response.status_code == 200
    assert response.json()["results"][0]["bm25_score"] == 2.1


def test_api_does_not_fake_reranking(monkeypatch):
    def unavailable(*args):
        raise RuntimeError("Cross-Encoder unavailable")
    monkeypatch.setattr(financial, "search", unavailable)
    response = TestClient(app).post("/financial/search", json={
        "query": "revenue 2024", "document_ids": ["a1"], "method": "hybrid_rerank"})
    assert response.status_code == 503


def test_api_rejects_inconsistent_top_k():
    response = TestClient(app).post("/financial/search", json={
        "query": "revenue 2024", "document_ids": ["a1"], "top_k": 5, "candidate_limit": 2})
    assert response.status_code == 422

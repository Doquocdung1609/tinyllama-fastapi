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


def test_api_rejects_whitespace_query_and_scope():
    client = TestClient(app)
    assert client.post("/financial/search", json={
        "query": "  ", "document_ids": ["a1"]}).status_code == 422
    assert client.post("/financial/search", json={
        "query": "revenue", "document_ids": ["  "]}).status_code == 422


def test_api_distinguishes_missing_registered_and_partial_scope(monkeypatch):
    def no_chunks(*args):
        raise ValueError("No indexed chunks found in the selected document scope")
    monkeypatch.setattr(financial, "search", no_chunks)
    client = TestClient(app)

    monkeypatch.setattr(financial, "_unavailable_scope_detail", lambda ids: (
        404, {"code": "DOCUMENT_NOT_FOUND", "document_ids": ids}))
    missing = client.post("/financial/search", json={
        "query": "revenue", "document_ids": ["missing"]})
    assert missing.status_code == 404
    assert missing.json()["detail"]["code"] == "DOCUMENT_NOT_FOUND"

    monkeypatch.setattr(financial, "_unavailable_scope_detail", lambda ids: (
        409, {"code": "PARTIAL_INGESTION", "document_ids": ids}))
    partial = client.post("/financial/search", json={
        "query": "revenue", "document_ids": ["sec:partial"]})
    assert partial.status_code == 409
    assert partial.json()["detail"]["code"] == "PARTIAL_INGESTION"


def test_api_distinguishes_metadata_unavailable(monkeypatch):
    def missing_metadata(*args):
        raise ValueError("Metadata unavailable for selected document scope: fiscal_year,ticker")
    monkeypatch.setattr(financial, "search", missing_metadata)
    response = TestClient(app).post("/financial/search", json={
        "query": "revenue", "document_ids": ["a1"], "ticker": "ABC"})
    assert response.status_code == 409
    assert response.json()["detail"] == {
        "code": "METADATA_UNAVAILABLE", "fields": ["fiscal_year", "ticker"]}

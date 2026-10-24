from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import financial_corpus
from app.financial_ingestion.sec_client import SECConfigurationError


app = FastAPI()
app.include_router(financial_corpus.router)
client = TestClient(app)


def test_discovery_dry_run_performs_no_network_request():
    response = client.post("/financial-corpus/discover", json={
        "cik": "123456", "forms": ["10-K"], "limit": 2, "dry_run": True})
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "DRY_RUN"
    assert payload["network_requests"] == 0
    assert payload["planned_request"]["url"].endswith("CIK0000123456.json")


def test_live_discovery_reports_missing_sec_identity(monkeypatch):
    def blocked():
        raise SECConfigurationError("SEC_USER_AGENT must identify the application")
    monkeypatch.setattr(financial_corpus, "live_pipeline", blocked)
    response = client.post("/financial-corpus/discover", json={
        "cik": "123456", "forms": ["10-K"], "limit": 1})
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "SEC_USER_AGENT_REQUIRED"


def test_discovery_rejects_unsupported_or_invalid_scope():
    assert client.post("/financial-corpus/discover", json={
        "cik": "not-a-cik", "dry_run": True}).status_code == 422
    assert client.post("/financial-corpus/discover", json={
        "cik": "123456", "forms": ["8-K"], "dry_run": True}).status_code == 422

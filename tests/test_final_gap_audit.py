import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import financial_corpus
from app.financial_ingestion.schemas import DocumentStatus
from app.services.ollama_service import _chat_prompt
from test_financial_ingestion import filing, pipeline


@pytest.mark.parametrize("status", [DocumentStatus.READY, DocumentStatus.PARTIAL_EXTRACTION])
def test_quality_diagnostic_does_not_claim_financial_completeness_or_mutate_status(tmp_path, status):
    service, _ = pipeline(tmp_path)
    item = filing()
    service.ingest_one("quality-a", item)
    row = service.registry.get_filing(item.filing_id)
    # The diagnostic reads the actual stored status, including conservative partial.
    item.document_status = status
    service.registry.upsert_filing("quality-a", item)
    manifest = service.create_manifest("quality-a")
    before = {key: Path(row[key]).read_bytes() for key in ("raw_path", "structured_path", "chunks_path")}
    report = service.extraction_quality(item.filing_id)
    assert report["document_status"] == status.value
    assert report["financial_completeness"] == "NOT_ASSESSED"
    assert report["table_count"] == 1
    assert report["tables"][0]["numeric_fact_count"] == 1
    assert service.registry.get_filing(item.filing_id)["status"] == status.value
    assert service.create_manifest("quality-a").manifest_hash == manifest.manifest_hash
    for key, content in before.items():
        assert Path(row[key]).read_bytes() == content


def test_quality_api_missing_and_existing_snapshots(tmp_path, monkeypatch):
    service, _ = pipeline(tmp_path)
    item = filing()
    service.ingest_one("quality-api", item)
    monkeypatch.setattr(financial_corpus, "local_pipeline", lambda: service)
    app = FastAPI()
    app.include_router(financial_corpus.router)
    with TestClient(app) as client:
        response = client.get(f"/financial-corpus/quality/{item.filing_id}")
        assert response.status_code == 200
        assert response.json()["financial_completeness"] == "NOT_ASSESSED"
        assert client.get("/financial-corpus/quality/missing").status_code == 404
        row = service.registry.get_filing(item.filing_id)
        Path(row["structured_path"]).unlink()
        assert client.get(f"/financial-corpus/quality/{item.filing_id}").status_code == 410


def test_historical_files_and_manifests_persist_but_active_evidence_lookup_is_limited(tmp_path, monkeypatch):
    service, _ = pipeline(tmp_path)
    item = filing()
    service.ingest_one("history-a", item)
    original_row = service.registry.get_filing(item.filing_id)
    archived_path = Path(original_row["chunks_path"])
    archived_bytes = archived_path.read_bytes()
    old_chunk = json.loads(archived_bytes.splitlines()[0])
    old_manifest = service.create_manifest("history-a")
    monkeypatch.setattr("app.financial_ingestion.pipeline.PARSER_VERSION", "sec-html-gap-test-next")
    service.ingest_one("history-a", filing())
    new_manifest = service.create_manifest("history-a")
    assert old_manifest.snapshot_version != new_manifest.snapshot_version
    assert archived_path.read_bytes() == archived_bytes
    assert service.registry.get_chunk(old_chunk["chunk_id"]) is None
    assert len(service.registry.manifests("history-a")) == 2
    monkeypatch.setattr(financial_corpus, "local_pipeline", lambda: service)
    app = FastAPI()
    app.include_router(financial_corpus.router)
    with TestClient(app) as client:
        assert client.get("/financial-corpus/evidence/" + old_chunk["chunk_id"]).status_code == 404


def test_financial_general_chat_prompt_is_ungrounded_and_preserves_original_question():
    question = "Explain the purpose of a balance sheet in one sentence."
    prompt = _chat_prompt(question, [])
    assert prompt.endswith("User: " + question + "\nAssistant:")
    assert "Vietnamese" in prompt
    assert "[E1]" not in prompt and "SEC" not in prompt
    assert "balance sheet" in prompt
    assert "income statement" not in prompt

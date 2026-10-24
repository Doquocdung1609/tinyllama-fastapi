import pytest

from app.financial_ingestion.sec_client import filing_source_url
from test_financial_ingestion import filing, pipeline


@pytest.mark.parametrize("filename", ["/report.htm", "../report.htm", "C:report.htm",
    "report.htm:stream", "report.htm?x=1", "report.htm#part", ".", "..", "NUL.htm",
    "CON", "report.", " report.htm", "report.htm "])
def test_archive_filename_rejects_filesystem_and_url_ambiguity(filename):
    with pytest.raises(ValueError):
        filing_source_url("123456", "0000123456-24-000001", filename)


@pytest.mark.parametrize("field,value", [("cik", "../../123456"),
    ("cik", "0000123456/../other"), ("accession_number", "../0000123456-24-000001")])
def test_noncanonical_metadata_rejected_before_download_or_registry_mutation(tmp_path, field, value):
    service, client = pipeline(tmp_path)
    item = filing()
    setattr(item, field, value)
    item.filing_id = f"sec:{item.cik}:{item.accession_number}"
    with pytest.raises(ValueError):
        service.ingest_one("safe", item)
    assert client.download_calls == 0
    assert service.registry.list_filings() == []


@pytest.mark.parametrize("dataset", ["../escape", "/absolute", "C:drive", "", "a" * 81])
def test_dataset_path_validation_applies_to_direct_ingestion_and_manifest(tmp_path, dataset):
    service, client = pipeline(tmp_path)
    with pytest.raises(ValueError):
        service.ingest_one(dataset, filing())
    with pytest.raises(ValueError):
        service.create_manifest(dataset)
    assert client.download_calls == 0


def test_job_api_rejects_noncanonical_paths_before_writing(tmp_path, monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.api import financial_corpus
    service, source = pipeline(tmp_path)
    monkeypatch.setattr(financial_corpus, "local_pipeline", lambda: service)
    item = filing()
    item.cik = "../../123456"
    item.filing_id = f"sec:{item.cik}:{item.accession_number}"
    app = FastAPI()
    app.include_router(financial_corpus.router)
    with TestClient(app) as client:
        response = client.post("/financial-corpus/jobs", json={
            "dataset_id": "safe", "filings": [item.model_dump(mode="json")], "dry_run": True})
    assert response.status_code == 422
    assert service.registry.list_filings() == []
    assert source.download_calls == 0

from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

from app.financial_ingestion import INGESTION_VERSION, PARSER_VERSION
from app.financial_ingestion.pipeline import FinancialCorpusPipeline
from app.financial_ingestion.registry import FinancialRegistry
from app.financial_ingestion.schemas import DocumentStatus, FilingMetadata
from app.financial_ingestion.sec_client import DownloadResult

FIXTURE = Path(__file__).parent / "fixtures" / "sec" / "filing_sample.htm"


class FixtureClient:
    def __init__(self):
        self.download_calls = 0

    def download(self, url, target, **kwargs):
        self.download_calls += 1
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(FIXTURE.read_bytes())
        return DownloadResult(
            target, datetime.now(timezone.utc).isoformat(), 200, '"fixture-etag"',
            "Mon, 01 Jan 2024 00:00:00 GMT", "text/html", target.stat().st_size)


class FlakyFixtureClient(FixtureClient):
    def __init__(self):
        super().__init__()
        self.failed_once = False

    def download(self, url, target, **kwargs):
        if not self.failed_once:
            self.failed_once = True
            self.download_calls += 1
            raise ConnectionError("synthetic one-time connection failure")
        return super().download(url, target, **kwargs)


class MutableFixtureClient(FixtureClient):
    def __init__(self, content):
        super().__init__()
        self.content = content

    def download(self, url, target, **kwargs):
        self.download_calls += 1
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(self.content)
        return DownloadResult(
            target, datetime.now(timezone.utc).isoformat(), 200, '"mutable"',
            None, "text/html", target.stat().st_size)


def filing(accession="0000123456-24-000001", form="10-K", primary="example-20231231x10k.htm"):
    return FilingMetadata(
        filing_id=f"sec:0000123456:{accession}", company_name="Example Financial Corporation",
        cik="0000123456", ticker="EXM", form_type=form, accession_number=accession,
        filing_date="2024-03-01" if form == "10-K" else "2024-03-15",
        report_date="2023-12-31", primary_document=primary,
        source_url=(f"https://www.sec.gov/Archives/edgar/data/123456/"
                    f"{accession.replace('-', '')}/{primary}"),
        parser_version=PARSER_VERSION, ingestion_version=INGESTION_VERSION,
        unknown_reasons={"fiscal_year": "pending", "fiscal_period": "pending"},
    )


def pipeline(tmp_path):
    registry = FinancialRegistry(tmp_path / "registry.sqlite3")
    client = FixtureClient()
    return FinancialCorpusPipeline(root=tmp_path / "corpus", registry=registry,
                                   client=client), client


def test_end_to_end_fixture_ingestion_idempotency_manifest_and_lineage(tmp_path):
    service, client = pipeline(tmp_path)
    metadata = filing()
    first = service.ingest_one("dataset-a", metadata)
    second = service.ingest_one("dataset-a", filing())
    assert first["status"] == "READY"
    assert first["tables"] == 1 and first["chunk_count"] >= 5
    assert second["idempotent_reuse"] is True
    assert client.download_calls == 1
    row = service.registry.get_filing(metadata.filing_id)
    assert row["raw_hash"] == sha256(FIXTURE.read_bytes()).hexdigest()
    assert Path(row["raw_path"]).parent.name == row["raw_hash"]
    assert Path(row["raw_path"]).read_bytes() == FIXTURE.read_bytes()
    assert row["normalized_hash"]
    chunk_row = next(item for item in service.registry.connect().execute(
        "SELECT chunk_id FROM chunks WHERE filing_id=? ORDER BY chunk_id", (metadata.filing_id,)))
    evidence = service.evidence(chunk_row["chunk_id"])
    assert evidence["status"] == "VERIFIED"
    assert evidence["source_chain"]["accession_number"] == metadata.accession_number
    assert evidence["source_chain"]["source_url"] == metadata.source_url
    manifest_a = service.create_manifest("dataset-a")
    manifest_b = service.create_manifest("dataset-a")
    assert manifest_a.manifest_hash == manifest_b.manifest_hash
    assert manifest_a.snapshot_version == manifest_b.snapshot_version
    assert manifest_a.document_count == 1


def test_amendment_is_separate_version_and_links_to_base(tmp_path):
    service, _ = pipeline(tmp_path)
    base = filing()
    amendment = filing("0000123456-24-000002", "10-K/A", "example-20231231x10ka.htm")
    service.ingest_one("dataset-a", base)
    service.ingest_one("dataset-a", amendment)
    row = service.registry.get_filing(amendment.filing_id)
    saved = FilingMetadata.model_validate_json(row["metadata_json"])
    assert saved.amendment_of == base.filing_id
    assert saved.filing_id != base.filing_id
    assert len(service.registry.list_filings("dataset-a")) == 2


def test_job_checkpoint_resume_and_recovery(tmp_path):
    service, client = pipeline(tmp_path)
    items = [filing(), filing("0000123456-24-000002", "10-K/A", "example-20231231x10ka.htm")]
    job = service.create_job("dataset-a", items)
    interrupted = service.run_job(job.job_id, stop_after=1)
    assert interrupted.status == "INTERRUPTED" and interrupted.next_index == 1
    resumed = service.run_job(job.job_id)
    assert resumed.status == "COMPLETED" and len(resumed.completed) == 2
    assert client.download_calls == 2

    third = filing("0000123456-24-000004", "10-Q", "example-20240331x10q.htm")
    third.document_status = DocumentStatus.PARSING
    service.registry.upsert_filing("dataset-a", third)
    another = service.create_job("dataset-a", [third])
    another.status = "RUNNING"
    service.registry.update_job(another)
    recovered = service.registry.recover_interrupted()
    assert recovered == {"filings": 1, "jobs": 1}
    assert service.registry.get_filing(third.filing_id)["status"] == "INTERRUPTED"
    assert service.registry.get_job(another.job_id).status == "INTERRUPTED"


def test_tampered_raw_source_invalidates_lineage(tmp_path):
    service, _ = pipeline(tmp_path)
    metadata = filing()
    service.ingest_one("dataset-a", metadata)
    chunk_id = service.registry.connect().execute(
        "SELECT chunk_id FROM chunks WHERE filing_id=? LIMIT 1", (metadata.filing_id,)).fetchone()[0]
    row = service.registry.get_filing(metadata.filing_id)
    Path(row["raw_path"]).write_bytes(b"<html><body>tampered</body></html>")
    assert service.evidence(chunk_id)["status"] == "INVALID_RAW_HASH"


def test_failed_job_item_is_retried_without_duplicate_rows(tmp_path):
    registry = FinancialRegistry(tmp_path / "registry.sqlite3")
    client = FlakyFixtureClient()
    service = FinancialCorpusPipeline(root=tmp_path / "corpus", registry=registry,
                                      client=client)
    metadata = filing()
    job = service.create_job("dataset-a", [metadata])
    failed = service.run_job(job.job_id)
    assert failed.status == "COMPLETED_WITH_ERRORS"
    assert metadata.filing_id in failed.failed

    resumed = service.run_job(job.job_id)
    assert resumed.status == "COMPLETED"
    assert resumed.failed == {}
    assert resumed.completed == [metadata.filing_id]
    assert len(service.registry.list_filings("dataset-a")) == 1
    assert service.registry.connect().execute(
        "SELECT COUNT(*) FROM chunks WHERE filing_id=?", (metadata.filing_id,)
    ).fetchone()[0] > 0


def test_forced_revision_preserves_raw_and_processed_versions(tmp_path):
    registry = FinancialRegistry(tmp_path / "registry.sqlite3")
    client = MutableFixtureClient(FIXTURE.read_bytes())
    service = FinancialCorpusPipeline(root=tmp_path / "corpus", registry=registry,
                                      client=client)
    metadata = filing()
    first = service.ingest_one("dataset-a", metadata)
    first_row = registry.get_filing(metadata.filing_id)
    first_raw = Path(first_row["raw_path"])
    first_chunks = Path(first_row["chunks_path"])
    first_ids = {row[0] for row in registry.connect().execute(
        "SELECT chunk_id FROM chunks WHERE filing_id=?", (metadata.filing_id,))}

    client.content = FIXTURE.read_bytes().replace(
        b"Revenue increased", b"Revenue increased materially", 1)
    second = service.ingest_one("dataset-a", filing(), force=True)
    second_row = registry.get_filing(metadata.filing_id)
    second_ids = {row[0] for row in registry.connect().execute(
        "SELECT chunk_id FROM chunks WHERE filing_id=?", (metadata.filing_id,))}

    assert first["raw_hash"] != second["raw_hash"]
    assert first_raw.is_file() and Path(second_row["raw_path"]).is_file()
    assert first_chunks.is_file() and Path(second_row["chunks_path"]).is_file()
    assert first_ids.isdisjoint(second_ids)


def test_job_rejects_source_identity_mismatch_before_network(tmp_path):
    service, client = pipeline(tmp_path)
    metadata = filing()
    metadata.source_url = metadata.source_url.replace("/123456/", "/999999/")
    try:
        service.create_job("dataset-a", [metadata])
        assert False, "source identity mismatch must be rejected"
    except ValueError as exc:
        assert "source_url does not match" in str(exc)
    assert client.download_calls == 0
    assert service.registry.list_filings("dataset-a") == []

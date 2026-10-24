import json
from pathlib import Path

import pytest
import requests

from app.financial_ingestion.sec_client import (
    SECClient, SECConfigurationError, filing_source_url, normalize_accession,
    normalize_cik, validate_sec_url, validate_user_agent,
)

FIXTURES = Path(__file__).parent / "fixtures" / "sec"


class FakeResponse:
    status_code = 200
    headers = {"Content-Type": "application/json"}

    def __init__(self, payload):
        self.payload = payload
        self.url = "https://data.sec.gov/submissions/CIK0000123456.json"

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return FakeResponse(self.payload)


def test_sec_identifiers_and_url_are_canonical():
    assert normalize_cik("123456") == "0000123456"
    assert normalize_accession("000012345624000001") == "0000123456-24-000001"
    assert filing_source_url("123456", "0000123456-24-000001", "report.htm") == (
        "https://www.sec.gov/Archives/edgar/data/123456/000012345624000001/report.htm")
    with pytest.raises(ValueError):
        filing_source_url("123456", "0000123456-24-000001", "../report.htm")
    assert validate_sec_url("https://www.sec.gov/Archives/example.htm")
    with pytest.raises(ValueError):
        validate_sec_url("https://example.com/redirected")


def test_user_agent_requires_real_contact_shape():
    with pytest.raises(SECConfigurationError):
        validate_user_agent("tinyllama")
    assert validate_user_agent("TinyLlamaResearch researcher@example.edu") == (
        "TinyLlamaResearch researcher@example.edu")


def test_discovery_preserves_source_metadata_and_filters_forms():
    payload = json.loads((FIXTURES / "submissions_sample.json").read_text(encoding="utf-8"))
    session = FakeSession(payload)
    client = SECClient("TinyLlamaResearch researcher@example.edu", requests_per_second=10,
                       max_retries=0, session=session)
    filings = client.discover("123456", ticker="EXM", forms=["10-K", "10-K/A"], limit=5)
    assert [item.form_type for item in filings] == ["10-K/A", "10-K"]
    assert filings[0].cik == "0000123456"
    assert filings[0].ticker == "EXM"
    assert filings[0].accession_number == "0000123456-24-000002"
    assert filings[0].fiscal_year is None
    assert "fiscal_year" in filings[0].unknown_reasons
    assert session.calls[0][1]["headers"]["User-Agent"].endswith("@example.edu")


def test_discovery_date_limit_is_deterministic():
    payload = json.loads((FIXTURES / "submissions_sample.json").read_text(encoding="utf-8"))
    client = SECClient("TinyLlamaResearch researcher@example.edu", requests_per_second=10,
                       max_retries=0, session=FakeSession(payload))
    filings = client.discover("123456", forms=["10-K"], date_from="2024-03-01",
                              date_to="2024-03-01", limit=1)
    assert len(filings) == 1
    assert filings[0].filing_date == "2024-03-01"


class SequenceSession:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        value = next(self.responses)
        if isinstance(value, Exception):
            raise value
        value.url = url
        return value


class DownloadResponse:
    def __init__(self, status, body=b"", headers=None):
        self.status_code = status
        self.body = body
        self.headers = headers or {}
        self.url = ""

    def iter_content(self, chunk_size):
        yield self.body


def test_connector_retries_retryable_failures_and_sends_conditional_headers(monkeypatch, tmp_path):
    session = SequenceSession([
        requests.ConnectionError("temporary"),
        DownloadResponse(429, headers={"Retry-After": "0"}),
        DownloadResponse(200, b"<html>ok</html>", {"ETag": '"v2"'}),
    ])
    client = SECClient("TinyLlamaResearch researcher@example.edu", requests_per_second=10,
                       max_retries=2, session=session)
    monkeypatch.setattr(client.rate_limiter, "wait", lambda: None)
    monkeypatch.setattr("app.financial_ingestion.sec_client.time.sleep", lambda _: None)
    result = client.download(
        "https://www.sec.gov/Archives/edgar/data/1/filing.htm", tmp_path / "filing.htm",
        etag='"v1"', last_modified="Mon, 01 Jan 2024 00:00:00 GMT")
    assert result.path.read_bytes() == b"<html>ok</html>"
    assert result.etag == '"v2"'
    assert len(session.calls) == 3
    assert session.calls[-1][1]["headers"]["If-None-Match"] == '"v1"'


def test_connector_reuses_cached_raw_on_304(monkeypatch, tmp_path):
    cached = tmp_path / "immutable" / "filing.htm"
    cached.parent.mkdir()
    cached.write_bytes(b"<html>cached</html>")
    session = SequenceSession([DownloadResponse(304, headers={"Content-Type": "text/html"})])
    client = SECClient("TinyLlamaResearch researcher@example.edu", requests_per_second=10,
                       max_retries=0, session=session)
    monkeypatch.setattr(client.rate_limiter, "wait", lambda: None)
    result = client.download(
        "https://www.sec.gov/Archives/edgar/data/1/filing.htm", tmp_path / "incoming.htm",
        etag='"v1"', cached_path=cached)
    assert result.not_modified is True
    assert result.path == cached
    assert result.path.read_bytes() == b"<html>cached</html>"

"""SEC EDGAR connector with explicit identity, bounded retries and rate control."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import email.utils
import json
import logging
from pathlib import Path
import random
import re
from threading import Lock
import time
from typing import Any, Iterable
from urllib.parse import urlparse

import requests

from app.financial_ingestion import INGESTION_VERSION, PARSER_VERSION
from app.financial_ingestion.schemas import FilingMetadata

logger = logging.getLogger(__name__)
SEC_DATA_BASE = "https://data.sec.gov"
SEC_ARCHIVE_BASE = "https://www.sec.gov/Archives/edgar/data"
ALLOWED_FORMS = {"10-K", "10-Q", "10-K/A", "10-Q/A"}
SEC_HOSTS = {"www.sec.gov", "data.sec.gov"}


class SECConfigurationError(RuntimeError):
    pass


class SECRequestError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None,
                 retryable: bool = False):
        super().__init__(message)
        self.status_code = status_code
        self.retryable = retryable


def normalize_cik(value: str | int) -> str:
    text = re.sub(r"\D", "", str(value))
    if not text or len(text) > 10:
        raise ValueError("CIK must contain 1 to 10 digits")
    return text.zfill(10)


def normalize_accession(value: str) -> str:
    digits = re.sub(r"\D", "", value)
    if len(digits) != 18:
        raise ValueError("SEC accession number must contain 18 digits")
    return f"{digits[:10]}-{digits[10:12]}-{digits[12:]}"


def validate_user_agent(value: str) -> str:
    value = value.strip()
    if len(value) < 12 or not re.search(r"\b[^\s@]+@[^\s@]+\.[^\s@]+\b", value):
        raise SECConfigurationError(
            "SEC_USER_AGENT must identify the application and contain a valid contact email")
    return value


def filing_source_url(cik: str, accession_number: str, primary_document: str) -> str:
    cik_number = str(int(normalize_cik(cik)))
    accession_digits = normalize_accession(accession_number).replace("-", "")
    document = primary_document.strip().lstrip("/")
    if not document or "/" in document or "\\" in document:
        raise ValueError("primary_document must be a single SEC archive filename")
    return f"{SEC_ARCHIVE_BASE}/{cik_number}/{accession_digits}/{document}"


def validate_sec_url(url: str) -> str:
    parsed = urlparse(url)
    if (parsed.scheme != "https" or parsed.hostname not in SEC_HOSTS or
            parsed.username or parsed.password or parsed.port not in {None, 443}):
        raise ValueError(
            "SEC connector only permits HTTPS URLs on www.sec.gov or data.sec.gov")
    return url


class RateLimiter:
    def __init__(self, requests_per_second: float):
        if not 0 < requests_per_second <= 10:
            raise ValueError("SEC rate must be greater than 0 and no more than 10 requests/second")
        self._interval = 1.0 / requests_per_second
        self._lock = Lock()
        self._last_request = 0.0

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            remaining = self._interval - (now - self._last_request)
            if remaining > 0:
                time.sleep(remaining)
            self._last_request = time.monotonic()


@dataclass
class DownloadResult:
    path: Path
    retrieved_at: str
    status_code: int
    etag: str | None
    last_modified: str | None
    content_type: str | None
    content_length: int
    not_modified: bool = False
    final_url: str | None = None

    def response_metadata(self) -> dict[str, Any]:
        return {
            "status_code": self.status_code,
            "etag": self.etag,
            "last_modified": self.last_modified,
            "content_type": self.content_type,
            "content_length": self.content_length,
            "not_modified": self.not_modified,
            "final_url": self.final_url,
        }


class SECClient:
    def __init__(self, user_agent: str, *, requests_per_second: float = 6.0,
                 timeout_seconds: float = 30.0, max_retries: int = 3,
                 session: requests.Session | None = None):
        self.user_agent = validate_user_agent(user_agent)
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.session = session or requests.Session()
        self.rate_limiter = RateLimiter(requests_per_second)

    @property
    def headers(self) -> dict[str, str]:
        return {"User-Agent": self.user_agent, "Accept-Encoding": "gzip, deflate",
                "Accept": "application/json,text/html,application/xhtml+xml,*/*;q=0.8"}

    def _request(self, url: str, *, stream: bool = False,
                 conditional: dict[str, str] | None = None):
        validate_sec_url(url)
        headers = {**self.headers, **(conditional or {})}
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            self.rate_limiter.wait()
            try:
                response = self.session.get(url, headers=headers, timeout=self.timeout_seconds,
                                            stream=stream, allow_redirects=True)
            except requests.RequestException as exc:
                last_error = exc
                retryable = True
                status = None
            else:
                status = response.status_code
                final_url = getattr(response, "url", url) or url
                try:
                    validate_sec_url(final_url)
                except ValueError as exc:
                    raise SECRequestError(
                        f"SEC request redirected outside approved hosts: {final_url}") from exc
                if status in {200, 304}:
                    return response
                if status == 404:
                    raise SECRequestError(f"SEC resource not found: {url}", status_code=404)
                if status == 403:
                    raise SECRequestError(
                        "SEC returned 403. Verify User-Agent/contact and reduce request rate.",
                        status_code=403)
                retryable = status == 429 or 500 <= status < 600
                last_error = SECRequestError(f"SEC request failed with HTTP {status}: {url}",
                                             status_code=status, retryable=retryable)
                if not retryable:
                    raise last_error
            if attempt >= self.max_retries:
                break
            retry_after = None
            if status is not None and 'response' in locals():
                header = response.headers.get("Retry-After")
                if header:
                    try:
                        retry_after = float(header)
                    except ValueError:
                        parsed = email.utils.parsedate_to_datetime(header)
                        retry_after = max(0., parsed.timestamp() - time.time()) if parsed else None
            delay = retry_after if retry_after is not None else min(16., 2 ** attempt + random.uniform(0, .5))
            logger.warning("SEC retry attempt=%d delay=%.2f url=%s", attempt + 1, delay, url)
            time.sleep(delay)
        raise SECRequestError(f"SEC request exhausted retries: {url}: {last_error}",
                              status_code=getattr(last_error, "status_code", None), retryable=True)

    def get_json(self, url: str) -> dict[str, Any]:
        response = self._request(url)
        try:
            return response.json()
        except (ValueError, json.JSONDecodeError) as exc:
            raise SECRequestError(f"SEC returned invalid JSON: {url}") from exc

    def discover(self, cik: str, *, ticker: str | None = None,
                 forms: Iterable[str] = ALLOWED_FORMS, date_from: str | None = None,
                 date_to: str | None = None, limit: int = 20) -> list[FilingMetadata]:
        if not 1 <= limit <= 200:
            raise ValueError("limit must be between 1 and 200")
        cik = normalize_cik(cik)
        allowed = {form.upper() for form in forms}
        unsupported = allowed - ALLOWED_FORMS
        if unsupported:
            raise ValueError(f"Unsupported SEC forms: {sorted(unsupported)}")
        payload = self.get_json(f"{SEC_DATA_BASE}/submissions/CIK{cik}.json")
        company_name = str(payload.get("name") or "").strip()
        if not company_name:
            raise SECRequestError("SEC submissions response omitted company name")
        recent = payload.get("filings", {}).get("recent", {})
        required = ("accessionNumber", "filingDate", "reportDate", "form", "primaryDocument")
        if not all(isinstance(recent.get(key), list) for key in required):
            raise SECRequestError("SEC submissions response omitted required recent-filing arrays")
        count = min(len(recent[key]) for key in required)
        results = []
        for index in range(count):
            form_type = str(recent["form"][index]).upper()
            filing_date = str(recent["filingDate"][index] or "") or None
            if form_type not in allowed or (date_from and (not filing_date or filing_date < date_from)) \
                    or (date_to and (not filing_date or filing_date > date_to)):
                continue
            accession = normalize_accession(str(recent["accessionNumber"][index]))
            primary_document = str(recent["primaryDocument"][index]).strip()
            source_url = filing_source_url(cik, accession, primary_document)
            report_date = str(recent["reportDate"][index] or "") or None
            unknown = {}
            if not ticker:
                unknown["ticker"] = "Ticker was not supplied or source-mapped; CIK remains canonical."
            unknown["fiscal_year"] = "Not inferred from report date; parser may obtain an explicit iXBRL fact."
            unknown["fiscal_period"] = "Parser may obtain an explicit iXBRL DocumentFiscalPeriodFocus fact."
            filing_id = f"sec:{cik}:{accession}"
            results.append(FilingMetadata(
                filing_id=filing_id, company_name=company_name, cik=cik,
                ticker=ticker.upper() if ticker else None, form_type=form_type,
                accession_number=accession, filing_date=filing_date,
                report_date=report_date, primary_document=primary_document,
                source_url=source_url, parser_version=PARSER_VERSION,
                ingestion_version=INGESTION_VERSION, unknown_reasons=unknown,
            ))
            if len(results) >= limit:
                break
        return results

    def download(self, url: str, target: Path, *, etag: str | None = None,
                 last_modified: str | None = None, cached_path: Path | None = None,
                 max_bytes: int = 100 * 1024 * 1024) -> DownloadResult:
        target.parent.mkdir(parents=True, exist_ok=True)
        conditional = {}
        if etag:
            conditional["If-None-Match"] = etag
        if last_modified:
            conditional["If-Modified-Since"] = last_modified
        response = self._request(url, stream=True, conditional=conditional)
        retrieved_at = datetime.now(timezone.utc).isoformat()
        if response.status_code == 304:
            reusable = cached_path if cached_path and cached_path.is_file() else target
            if not reusable.exists():
                raise SECRequestError("SEC returned 304 but no cached raw file exists")
            return DownloadResult(reusable, retrieved_at, 304, etag, last_modified,
                                  response.headers.get("Content-Type"), reusable.stat().st_size,
                                  True, getattr(response, "url", url))
        content_type = (response.headers.get("Content-Type") or "").lower()
        temporary = target.with_suffix(target.suffix + ".download")
        size = 0
        try:
            with temporary.open("wb") as stream:
                for block in response.iter_content(chunk_size=1024 * 1024):
                    if not block:
                        continue
                    size += len(block)
                    if size > max_bytes:
                        raise SECRequestError(f"SEC filing exceeds configured {max_bytes} byte limit")
                    stream.write(block)
            if size == 0:
                raise SECRequestError("SEC filing response was empty")
            temporary.replace(target)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
        return DownloadResult(target, retrieved_at, response.status_code,
                              response.headers.get("ETag"), response.headers.get("Last-Modified"),
                              content_type or None, size, False,
                              getattr(response, "url", url))

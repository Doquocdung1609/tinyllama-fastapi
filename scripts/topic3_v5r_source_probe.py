"""Download a bounded set of official SEC HTML for source-first review."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import sys
import zipfile
from pathlib import Path

from topic3_v5r_restore import REPO, SOURCE

sys.path.insert(0, str(REPO))
from app.config import get_settings
from app.financial_ingestion.sec_client import SECClient


ACCESSIONS = {"0001018724-25-000004", "0001326801-25-000017",
              "0001628280-24-002390", "0000320193-24-000123"}
OUT = REPO / "tmp/topic3_v5r/sec_html"
REPORT = REPO / "docs/topic3_v5/recovery_live/official_source_manifest.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    settings = get_settings()
    client = SECClient(settings.sec_user_agent, requests_per_second=1, timeout_seconds=30, max_retries=1)
    with zipfile.ZipFile(SOURCE) as z:
        audit = list(csv.DictReader(io.StringIO(z.read("audit/p7g_fiscal_metadata_audit.csv").decode("utf-8-sig"))))
    OUT.mkdir(parents=True, exist_ok=True)
    results = []
    for row in audit:
        if row["accession"] not in ACCESSIONS:
            continue
        path = OUT / f"{row['accession']}.html"
        if path.exists():
            status = "REUSED_IMMUTABLE_LOCAL"
        else:
            client.download(row["source_url"], path)
            status = "DOWNLOADED_OFFICIAL_SEC"
        results.append({"accession": row["accession"], "url": row["source_url"],
                        "sec_report_date": row["sec_report_date"], "bytes": path.stat().st_size,
                        "sha256": sha(path), "status": status})
        print(row["accession"], status, path.stat().st_size, flush=True)
    if len(results) != len(ACCESSIONS):
        raise ValueError("Missing requested official source")
    REPORT.write_text(json.dumps({"contact_user_agent_configured": True, "max_requests_per_second": 1,
                                  "sources": results}, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

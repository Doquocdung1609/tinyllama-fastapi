"""Fetch missing review sources from official SEC at one request per second."""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.config import get_settings  # noqa: E402
from app.financial_ingestion.sec_client import SECClient  # noqa: E402

QUEUE = ROOT / "docs/topic3_v5/recovery_live/holdout_30_review_queue.csv"
SNAPSHOTS = ROOT / "tmp/topic3_v5r/sec_html"
OUT = ROOT / "docs/topic3_v6/V6_SOURCE_SNAPSHOT_MANIFEST.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    rows = list(csv.DictReader(QUEUE.open(encoding="utf-8", newline="")))
    sources = {r["source_accession"]: r["source_url"] for r in rows}
    assert len(rows) == 30 and len(sources) == 13
    settings = get_settings()
    client = SECClient(settings.sec_user_agent, requests_per_second=1, timeout_seconds=30, max_retries=1)
    SNAPSHOTS.mkdir(parents=True, exist_ok=True)
    entries = []
    for accession, url in sorted(sources.items()):
        path = SNAPSHOTS / f"{accession}.html"
        if path.is_file():
            action = "REUSED_LOCAL_SNAPSHOT"
        else:
            client.download(url, path)
            action = "FETCHED_OFFICIAL_SEC"
        entries.append({"accession": accession, "url": url, "sha256": sha(path),
                        "bytes": path.stat().st_size, "action": action})
        print(accession, action, path.stat().st_size, flush=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"status": "OFFICIAL_SEC_SOURCE_SNAPSHOTS",
                               "max_requests_per_second": 1, "contact_user_agent_configured": True,
                               "files_committed": False, "sources": entries}, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

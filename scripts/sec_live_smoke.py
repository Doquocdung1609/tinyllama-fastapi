"""Bounded live SEC smoke test; never contacts SEC without a valid User-Agent."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings
from app.financial_ingestion.pipeline import FinancialCorpusPipeline
from app.financial_ingestion.registry import FinancialRegistry
from app.financial_ingestion.sec_client import SECClient, SECConfigurationError


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cik", default="0000320193")
    parser.add_argument("--ticker", default="AAPL")
    parser.add_argument("--dataset-id", default="sec-live-smoke")
    parser.add_argument("--limit", type=int, default=1, choices=range(1, 4))
    args = parser.parse_args()
    settings = get_settings()
    try:
        client = SECClient(settings.sec_user_agent,
                           requests_per_second=settings.sec_requests_per_second,
                           timeout_seconds=settings.sec_timeout_seconds,
                           max_retries=settings.sec_max_retries)
    except SECConfigurationError as exc:
        print(json.dumps({"status": "BLOCKED_EXTERNAL_SOURCE", "network_requests": 0,
                          "reason": str(exc)}, indent=2))
        return 2
    registry = FinancialRegistry(settings.financial_registry_db)
    pipeline = FinancialCorpusPipeline(registry=registry, client=client)
    filings = client.discover(args.cik, ticker=args.ticker, forms=["10-K", "10-Q"],
                              limit=args.limit)
    job = pipeline.create_job(args.dataset_id, filings)
    completed = pipeline.run_job(job.job_id)
    manifest = pipeline.create_manifest(args.dataset_id)
    rows = registry.list_filings(args.dataset_id)
    print(json.dumps({"status": completed.status, "job": completed.model_dump(mode="json"),
                      "manifest": manifest.model_dump(mode="json"),
                      "filings": rows}, ensure_ascii=False, indent=2))
    return 0 if completed.status == "COMPLETED" else 1


if __name__ == "__main__":
    raise SystemExit(main())

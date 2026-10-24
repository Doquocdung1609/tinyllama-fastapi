"""CLI for bounded SEC discovery, ingestion, resume, manifests and evidence."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings
from app.financial_ingestion.pipeline import FinancialCorpusPipeline
from app.financial_ingestion.registry import FinancialRegistry
from app.financial_ingestion.sec_client import ALLOWED_FORMS, SECConfigurationError, SECClient, normalize_cik


def emit(value) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, default=str))


def clients():
    settings = get_settings()
    registry = FinancialRegistry(settings.financial_registry_db)
    client = SECClient(settings.sec_user_agent,
                       requests_per_second=settings.sec_requests_per_second,
                       timeout_seconds=settings.sec_timeout_seconds,
                       max_retries=settings.sec_max_retries)
    return client, FinancialCorpusPipeline(registry=registry, client=client)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    discover = commands.add_parser("discover")
    discover.add_argument("--cik", required=True)
    discover.add_argument("--ticker")
    discover.add_argument("--forms", nargs="+", choices=sorted(ALLOWED_FORMS), default=sorted(ALLOWED_FORMS))
    discover.add_argument("--date-from")
    discover.add_argument("--date-to")
    discover.add_argument("--limit", type=int, default=10)
    discover.add_argument("--dry-run", action="store_true")

    ingest = commands.add_parser("ingest")
    ingest.add_argument("--dataset-id", required=True)
    ingest.add_argument("--cik", required=True)
    ingest.add_argument("--ticker")
    ingest.add_argument("--forms", nargs="+", choices=sorted(ALLOWED_FORMS), default=sorted(ALLOWED_FORMS))
    ingest.add_argument("--date-from")
    ingest.add_argument("--date-to")
    ingest.add_argument("--limit", type=int, default=3)
    ingest.add_argument("--dry-run", action="store_true")

    status = commands.add_parser("status")
    status.add_argument("--job-id")
    status.add_argument("--dataset-id")
    resume = commands.add_parser("resume")
    resume.add_argument("--job-id", required=True)
    manifest = commands.add_parser("manifest")
    manifest.add_argument("--dataset-id", required=True)
    evidence = commands.add_parser("evidence")
    evidence.add_argument("--chunk-id", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    settings = get_settings()
    registry = FinancialRegistry(settings.financial_registry_db)
    local = FinancialCorpusPipeline(registry=registry)
    try:
        if args.command in {"discover", "ingest"} and args.dry_run:
            cik = normalize_cik(args.cik)
            emit({"status": "DRY_RUN", "network_requests": 0,
                  "planned_request": {"url": f"https://data.sec.gov/submissions/CIK{cik}.json",
                                      "forms": args.forms, "date_from": args.date_from,
                                      "date_to": args.date_to, "limit": args.limit},
                  "next": "Configure SEC_USER_AGENT with application name and real contact email."})
            return 0
        if args.command == "status":
            if args.job_id:
                job = registry.get_job(args.job_id)
                if not job:
                    raise ValueError("Job not found")
                emit(job.model_dump(mode="json"))
            else:
                emit(registry.list_filings(args.dataset_id))
            return 0
        if args.command == "manifest":
            emit(local.create_manifest(args.dataset_id).model_dump(mode="json"))
            return 0
        if args.command == "evidence":
            emit(local.evidence(args.chunk_id))
            return 0

        client, pipeline = clients()
        if args.command == "discover":
            filings = client.discover(args.cik, ticker=args.ticker, forms=args.forms,
                                      date_from=args.date_from, date_to=args.date_to,
                                      limit=args.limit)
            emit({"status": "DISCOVERED", "filings": [item.model_dump(mode="json") for item in filings]})
            return 0
        if args.command == "ingest":
            filings = client.discover(args.cik, ticker=args.ticker, forms=args.forms,
                                      date_from=args.date_from, date_to=args.date_to,
                                      limit=args.limit)
            job = pipeline.create_job(args.dataset_id, filings)
            emit(pipeline.run_job(job.job_id).model_dump(mode="json"))
            return 0
        if args.command == "resume":
            emit(pipeline.run_job(args.job_id).model_dump(mode="json"))
            return 0
    except SECConfigurationError as exc:
        emit({"status": "BLOCKED_EXTERNAL_SOURCE", "reason": str(exc)})
        return 2
    except Exception as exc:
        emit({"status": "FAILED", "reason": str(exc)})
        return 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

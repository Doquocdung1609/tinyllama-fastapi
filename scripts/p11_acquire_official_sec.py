"""Acquire only preregistered official SEC filings into a new owned P11 root.

The caller supplies an existing private .env file. Its contact identity is never
printed, committed, or serialized. Access denial stops the fixed request plan.
"""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil

from dotenv import dotenv_values

from app.financial_ingestion.sec_client import SECClient, SECRequestError


OWNER = "TOPIC3_P11_NEW_SEC_RESEARCH_DATASET_AND_DEV_EVALUATION_AUTHORIZED"
PROTOCOL = (Path(__file__).resolve().parents[1] /
            "docs/topic3/milestone_d/recovery/p11/p11_partition_manifest.json")


def atomic_json(path, value):
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    tmp.replace(path)


def owned_root(root, protocol_hash):
    root = root.resolve()
    if root.name != "t3-p11-new-sec-20261027-v1" or root.parent.name != "research":
        raise ValueError("EXPLICIT_P11_ISOLATED_RESEARCH_ROOT_REQUIRED")
    marker = root / "ownership.json"
    if root.exists():
        if not marker.is_file():
            raise ValueError("EXISTING_UNOWNED_ROOT")
        owned = json.loads(marker.read_text(encoding="utf-8"))
        if owned != {"owner": OWNER, "protocol_sha256": protocol_hash}:
            raise ValueError("RESEARCH_ROOT_IDENTITY_CONFLICT")
    else:
        if shutil.disk_usage(root.parent).free < 1_073_741_824:
            raise RuntimeError("INSUFFICIENT_FREE_RESEARCH_STORAGE")
        root.mkdir()
        atomic_json(marker, {"owner": OWNER, "protocol_sha256": protocol_hash})
    return root


def file_hash(path):
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def acquire(root, env_file, output):
    protocol_bytes = PROTOCOL.read_bytes()
    protocol_hash = sha256(protocol_bytes).hexdigest()
    plan = json.loads(protocol_bytes)
    root = owned_root(root, protocol_hash)
    user_agent = (dotenv_values(env_file).get("SEC_USER_AGENT") or "").strip()
    client = SECClient(user_agent, requests_per_second=1, timeout_seconds=30,
                       max_retries=0)
    local_progress = root / "acquisition.json"
    report = json.loads(local_progress.read_text(encoding="utf-8")) if local_progress.exists() else {
        "schema_version": "topic3-p11-official-sec-acquisition/v1",
        "protocol_sha256": protocol_hash,
        "source": "official_sec_submissions_and_primary_archive_bytes",
        "records": [], "status": "IN_PROGRESS", "contact_identity_recorded": False,
    }
    if report["protocol_sha256"] != protocol_hash or report["contact_identity_recorded"]:
        raise ValueError("ACQUISITION_PROTOCOL_IDENTITY_CONFLICT")
    existing = {row["ticker"]: row for row in report["records"]}
    total = sum(row.get("source_bytes", 0) for row in existing.values()
                if row.get("status") == "ACQUIRED_OFFICIAL_SOURCE")
    if total > plan["limits"]["max_total_raw_bytes"]:
        raise ValueError("AGGREGATE_SOURCE_BUDGET_EXCEEDED")
    stopped = False
    try:
        for partition, entries in plan["partitions"].items():
            for item in entries:
                ticker = item["ticker"]
                prior = existing.get(ticker)
                if prior is not None:
                    if prior.get("status") == "ACQUIRED_OFFICIAL_SOURCE":
                        raw = root / prior["relative_path"]
                        if (not raw.is_file() or file_hash(raw) != prior["raw_sha256"]
                            or prior["cik"] != item["cik"] or prior["partition"] != partition):
                            raise ValueError("EXISTING_SOURCE_IDENTITY_CONFLICT")
                    continue
                if stopped:
                    row = {"ticker": ticker, "cik": item["cik"],
                           "partition": partition, "requested_form": item["requested_form"],
                           "status": "NOT_ATTEMPTED_AFTER_ACCESS_DENIAL"}
                else:
                    row = {"ticker": ticker, "cik": item["cik"],
                           "partition": partition, "requested_form": item["requested_form"]}
                    try:
                        matches = client.discover(item["cik"], ticker=ticker,
                            forms=[item["requested_form"]],
                            date_to=plan["selection_date_utc"], limit=1)
                        if not matches:
                            row["status"] = "NO_ELIGIBLE_OFFICIAL_FILING"
                        else:
                            metadata = matches[0]
                            row["metadata"] = metadata.model_dump(mode="json")
                            target = (root / "raw" / item["cik"] /
                                      metadata.accession_number / metadata.primary_document)
                            if target.exists():
                                raise ValueError("UNREGISTERED_EXISTING_SOURCE_REFUSED")
                            if shutil.disk_usage(root).free < plan["limits"]["min_free_disk_bytes"]:
                                raise RuntimeError("INSUFFICIENT_FREE_RESEARCH_STORAGE")
                            result = client.download(metadata.source_url, target,
                                max_bytes=plan["limits"]["max_bytes_per_filing"])
                            total += result.content_length
                            if total > plan["limits"]["max_total_raw_bytes"]:
                                target.unlink(missing_ok=True)
                                raise RuntimeError("AGGREGATE_SOURCE_BUDGET_EXCEEDED")
                            row.update(status="ACQUIRED_OFFICIAL_SOURCE",
                                raw_sha256=file_hash(target), source_bytes=result.content_length,
                                relative_path=target.relative_to(root).as_posix(),
                                retrieved_at=result.retrieved_at,
                                response=result.response_metadata(),
                                parser_status="NOT_RUN")
                    except SECRequestError as exc:
                        row["status"] = "OFFICIAL_SOURCE_REQUEST_FAILED"
                        row["http_status"] = exc.status_code
                        row["error_type"] = type(exc).__name__
                        row["reason"] = ("SOURCE_BYTES_BUDGET_EXCEEDED"
                                         if "exceeds configured" in str(exc) else "SEC_REQUEST_FAILED")
                        if exc.status_code in {403, 429}:
                            stopped = True
                    except RuntimeError as exc:
                        row["status"] = str(exc)
                        stopped = True
                report["records"].append(row)
                existing[ticker] = row
                atomic_json(local_progress, report)
                atomic_json(output, report)
    finally:
        client.session.close()
    report["status"] = ("BLOCKED_ACCESS_DENIAL" if stopped else
                        "BOUNDED_ACQUISITION_FINISHED")
    report["completed_at_utc"] = datetime.now(timezone.utc).isoformat()
    report["acquired_count"] = sum(r["status"] == "ACQUIRED_OFFICIAL_SOURCE"
                                    for r in report["records"])
    report["total_raw_bytes"] = total
    atomic_json(local_progress, report)
    atomic_json(output, report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = acquire(args.root, args.env_file, args.output)
    print(json.dumps({"status": result["status"],
                      "acquired_count": result["acquired_count"],
                      "total_raw_bytes": result["total_raw_bytes"],
                      "record_statuses": {r["ticker"]: r["status"]
                                          for r in result["records"]}}))

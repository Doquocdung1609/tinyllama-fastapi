"""Bounded canonical parsing of preselected P11 development/validation SEC bytes."""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
from time import monotonic, sleep

import psutil

from app.financial_ingestion.chunker import chunk_filing
from app.financial_ingestion.html_parser import normalized_filing_text, parse_sec_html
from app.financial_ingestion.schemas import DocumentStatus, FilingMetadata
from app.financial_ingestion.pipeline import validate_metadata_identity
from scripts.p11_acquire_official_sec import OWNER, file_hash


def atomic_bytes(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("wb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def parse_worker(root, ticker):
    owned = json.loads((root / "ownership.json").read_text(encoding="utf-8"))
    if owned.get("owner") != OWNER:
        raise ValueError("P11_SOURCE_OWNERSHIP_REQUIRED")
    registry = json.loads((root / "acquisition.json").read_text(encoding="utf-8"))
    item = next((r for r in registry["records"] if r["ticker"] == ticker), None)
    if (item is None or item["partition"] not in {"development", "validation"}
        or item["status"] != "ACQUIRED_OFFICIAL_SOURCE"):
        raise ValueError("P11_SOURCE_NOT_ELIGIBLE_FOR_PARSING")
    raw_path = (root / item["relative_path"]).resolve(strict=True)
    if not raw_path.is_relative_to(root) or file_hash(raw_path) != item["raw_sha256"]:
        raise ValueError("P11_RAW_SOURCE_IDENTITY_MISMATCH")
    metadata = FilingMetadata.model_validate(item["metadata"])
    validate_metadata_identity(metadata)
    if metadata.cik != item["cik"] or metadata.ticker != ticker:
        raise ValueError("P11_FILING_MEMBERSHIP_MISMATCH")
    metadata.raw_content_hash = item["raw_sha256"]
    metadata.retrieved_at = item["retrieved_at"]
    metadata.response_metadata = item["response"]
    raw = raw_path.read_bytes()
    structured = parse_sec_html(raw, metadata)
    normalized = normalized_filing_text(structured)
    metadata.normalized_content_hash = sha256(normalized.encode("utf-8")).hexdigest()
    metadata.document_status = (DocumentStatus.PARTIAL_EXTRACTION
                                if structured.parser_warnings else DocumentStatus.READY)
    chunks = chunk_filing(structured)
    if not chunks or len({c.chunk_id for c in chunks}) != len(chunks):
        raise ValueError("EMPTY_OR_DUPLICATE_CANONICAL_CHUNKS")
    folder = root / "derived" / ticker
    structured_data = structured.model_dump_json().encode("utf-8")
    chunk_data = ("\n".join(c.model_dump_json() for c in chunks) + "\n").encode("utf-8")
    atomic_bytes(folder / "structured.json", structured_data)
    atomic_bytes(folder / "chunks.jsonl", chunk_data)
    membership = sha256(json.dumps(sorted(c.chunk_id for c in chunks),
                                   separators=(",", ":")).encode()).hexdigest()
    result = {"ticker": ticker, "partition": item["partition"],
              "cik": item["cik"], "accession": metadata.accession_number,
              "raw_sha256": item["raw_sha256"], "source_url": metadata.source_url,
              "parser_version": metadata.parser_version,
              "chunker_version": chunks[0].metadata["chunker_version"],
              "structured_sha256": sha256(structured_data).hexdigest(),
              "chunks_sha256": sha256(chunk_data).hexdigest(),
              "membership_sha256": membership,
              "parent_count": len(chunks), "table_count": len(structured.tables),
              "element_count": len(structured.elements),
              "parser_warnings": structured.parser_warnings,
              "document_status": metadata.document_status.value,
              "structured_path": (folder / "structured.json").relative_to(root).as_posix(),
              "chunks_path": (folder / "chunks.jsonl").relative_to(root).as_posix(),
              "worker_peak_working_set_bytes": psutil.Process().memory_info().peak_wset}
    atomic_bytes(folder / "parse_manifest.json", (json.dumps(result, indent=2) + "\n").encode())
    return result


def supervised_parse(root, ticker, max_seconds=180):
    root = root.resolve(strict=True)
    process = subprocess.Popen([sys.executable, "-m", "scripts.p11_parse_owned",
                                "--worker", "--root", str(root), "--ticker", ticker],
                               stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    child = psutil.Process(process.pid)
    start = monotonic()
    peak = 0
    reason = None
    while process.poll() is None:
        try:
            family = [child, *child.children(recursive=True)]
            peak = max(peak, sum(member.memory_info().rss for member in family
                                 if member.is_running()))
        except psutil.NoSuchProcess:
            break
        if peak > 1_100_000_000 or psutil.virtual_memory().available < 200_000_000:
            reason = "P11_ACTUAL_MEMORY_GUARD"
        elif monotonic() - start > max_seconds:
            reason = "P11_PARSE_TIMEOUT"
        if reason:
            for member in reversed([child, *child.children(recursive=True)]):
                try:
                    member.kill()
                except psutil.NoSuchProcess:
                    pass
            break
        sleep(0.1)
    _, stderr = process.communicate()
    if reason:
        return {"ticker": ticker, "status": reason, "peak_process_family_rss_bytes": peak}
    if process.returncode:
        return {"ticker": ticker, "status": "PARSER_FAILED",
                "peak_process_family_rss_bytes": peak,
                "error_tail": stderr.decode("utf-8", errors="replace")[-500:]}
    result = json.loads((root / "derived" / ticker / "parse_manifest.json").read_text())
    return {**result, "status": "PARSED_CANONICAL", "peak_process_family_rss_bytes": peak,
            "wall_seconds": round(monotonic() - start, 3)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--worker", action="store_true")
    args = parser.parse_args()
    if args.worker:
        parse_worker(args.root.resolve(strict=True), args.ticker)
    else:
        print(json.dumps(supervised_parse(args.root, args.ticker)))

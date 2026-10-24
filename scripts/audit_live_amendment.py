"""Bounded SEC amendment/original audit in a dedicated, persistent test root."""
from __future__ import annotations

import argparse
from datetime import date
from hashlib import sha256
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bs4 import BeautifulSoup
from app.config import get_settings
from app.financial_ingestion.pipeline import FinancialCorpusPipeline
from app.financial_ingestion.registry import FinancialRegistry
from app.financial_ingestion.schemas import FilingMetadata
from app.financial_ingestion.sec_client import SECClient


def audit(root: Path, output: Path) -> dict:
    client = SECClient(get_settings().sec_user_agent, requests_per_second=1,
                       timeout_seconds=25, max_retries=1)
    amendments = client.discover("1318605", ticker="TSLA", forms=["10-K/A", "10-Q/A"], limit=1)
    if not amendments:
        raise ValueError("LIVE_AMENDMENT_NOT_TESTED: no recent Tesla amendment discovered")
    amendment = amendments[0]
    originals = client.discover("1318605", ticker="TSLA",
                                forms=[amendment.form_type.removesuffix("/A")], limit=20)
    matches = [item for item in originals if item.report_date == amendment.report_date
               and item.filing_date <= amendment.filing_date]
    if not matches:
        raise ValueError("LIVE_AMENDMENT_NOT_TESTED: original not in recent bounded discovery")
    original = max(matches, key=lambda item: item.filing_date)
    registry = FinancialRegistry(root / "registry.sqlite3")
    service = FinancialCorpusPipeline(root=root, registry=registry, client=client)
    dataset = "gap-audit-real-amendment"
    print(f"Original {original.accession_number}; amendment {amendment.accession_number}", flush=True)
    first = service.ingest_one(dataset, original)
    first_row = registry.get_filing(original.filing_id)
    old_manifest = service.create_manifest(dataset)
    # On a repeated audit, recover the original-only historical manifest rather
    # than pretending the registry has been reset to one filing.
    if old_manifest.document_count != 1:
        from app.financial_ingestion.schemas import DatasetManifest
        candidates = [DatasetManifest.model_validate_json(Path(row["path"]).read_text("utf-8"))
                      for row in registry.manifests(dataset)]
        old_manifest = next((item for item in candidates if item.filing_ids == [original.filing_id]), None)
        if old_manifest is None:
            raise ValueError("Original-only historical manifest missing; use a new isolated audit root")
    manifest_path = root / "manifests" / dataset / f"{old_manifest.snapshot_version}.json"
    manifest_bytes = manifest_path.read_bytes()
    original_raw = Path(first_row["raw_path"])
    original_bytes = original_raw.read_bytes()
    second = service.ingest_one(dataset, amendment)
    amendment_row = registry.get_filing(amendment.filing_id)
    saved = FilingMetadata.model_validate_json(amendment_row["metadata_json"])
    assert saved.amendment_of == original.filing_id
    assert saved.filing_id != original.filing_id
    assert original_raw.read_bytes() == original_bytes
    assert manifest_path.read_bytes() == manifest_bytes
    final_manifest = service.create_manifest(dataset)
    assert final_manifest.document_count == 2
    assert final_manifest.snapshot_version != old_manifest.snapshot_version
    final_counts = {row["filing_id"]: row["chunk_count"] for row in registry.list_filings(dataset)}
    repeat = [service.ingest_one(dataset, item) for item in (original, saved)]
    assert all(item["idempotent_reuse"] for item in repeat)
    assert final_counts == {row["filing_id"]: row["chunk_count"] for row in registry.list_filings(dataset)}
    assert service.create_manifest(dataset).manifest_hash == final_manifest.manifest_hash
    amendment_text = BeautifulSoup(Path(amendment_row["raw_path"]).read_bytes(), "html.parser").get_text(" ", strip=True)
    start = amendment_text.upper().find("EXPLANATORY NOTE")
    note = amendment_text[start:start + 4000] if start >= 0 else None
    note_normalized = " ".join((note or "").split())
    def written_date(value):
        parsed = date.fromisoformat(value)
        return f"{parsed:%B} {parsed.day}, {parsed.year}"
    assert written_date(original.filing_date) in note_normalized
    assert "Original Form" in note_normalized and written_date(original.report_date) in note_normalized
    result = {"status": "LIVE_PAIR_INGESTED", "original_result": first,
              "amendment_result": second, "original": json.loads(first_row["metadata_json"]),
              "amendment": saved.model_dump(mode="json"), "explanatory_note": note,
              "original_raw_hash_rechecked": sha256(original_bytes).hexdigest(),
              "amendment_raw_hash_rechecked": sha256(Path(amendment_row["raw_path"]).read_bytes()).hexdigest(),
              "original_manifest": old_manifest.model_dump(mode="json"),
              "final_manifest": final_manifest.model_dump(mode="json"),
              "checks": {"separate_identities": True, "registry_relationship": True,
                         "relationship_supported_by_explanatory_note": True,
                         "raw_original_unchanged": True, "original_manifest_unchanged": True,
                         "idempotent_both": True, "two_registry_records": len(final_counts) == 2},
              "scope": "Identity/lineage/immutability; not a full Tesla financial extraction acceptance."}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.root, args.output)
    print(json.dumps(result["checks"]))

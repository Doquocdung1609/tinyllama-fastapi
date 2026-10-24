"""Read-only, pinned-source final gap and historical artifact integrity audit."""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bs4 import BeautifulSoup
from app.financial_ingestion.pipeline import FinancialCorpusPipeline
from app.financial_ingestion.registry import FinancialRegistry
from app.financial_ingestion.schemas import DatasetManifest, StructuredFiling
from app.financial_ingestion.html_parser import normalized_filing_text


def audit(root: Path, output: Path) -> dict:
    decisions = json.loads((Path(__file__).resolve().parents[1] / "docs/topic3/MILESTONE_B_TABLE_GAP_CLASSIFICATION.json").read_text("utf-8"))
    registry = FinancialRegistry(root / "registry.sqlite3")
    service = FinancialCorpusPipeline(root=root, registry=registry)
    row = registry.get_filing("sec:0000320193:0000320193-26-000020")
    if row is None:
        raise ValueError("Pinned Apple filing is not present in this isolated root")
    raw = Path(row["raw_path"]).read_bytes()
    assert sha256(raw).hexdigest() == decisions["source_raw_sha256"]
    parsed = StructuredFiling.model_validate_json(Path(row["structured_path"]).read_text("utf-8"))
    assert sha256(normalized_filing_text(parsed).encode()).hexdigest() == row["normalized_hash"]
    source_tables = BeautifulSoup(raw, "html.parser").find_all("table")
    table_reviews = []
    for decision in decisions["tables"]:
        table = parsed.tables[decision["index"]]
        source = source_tables[decision["index"]]
        assert table.table_id == decision["table_id"]
        assert table.source_location.structural_path == decision["source_locator"]
        table_reviews.append({**decision, "source_text": source.get_text(" ", strip=True),
                              "extraction_status_unchanged": table.extraction_status,
                              "numeric_ix_fact_count": sum(len(cell.numeric_facts) for cell in table.cells)})
    historical_manifests = []
    historical_raw_files = set()
    for path in root.parent.glob("*/manifests/**/*.json"):
        manifest = DatasetManifest.model_validate_json(path.read_text("utf-8"))
        assert manifest.content_hash() == manifest.manifest_hash
        corpus_root = path.parents[2]
        for filing_id, expected_hash in manifest.raw_hashes.items():
            _, cik, accession = filing_id.split(":")
            candidates = list((corpus_root / "raw" / cik / accession / expected_hash).glob("*"))
            verified = [candidate for candidate in candidates if candidate.is_file()
                        and sha256(candidate.read_bytes()).hexdigest() == expected_hash]
            assert verified, f"Missing/corrupt historical raw for {filing_id}"
            historical_raw_files.update(str(candidate) for candidate in verified)
            derived = []
            for structured_path in (corpus_root / "structured").rglob("*.json"):
                saved = json.loads(structured_path.read_text("utf-8"))
                metadata = saved["metadata"]
                if (metadata["filing_id"] == filing_id and metadata["parser_version"] == manifest.parser_version
                        and metadata.get("normalized_content_hash") == manifest.normalized_hashes.get(filing_id)):
                    relative = structured_path.relative_to(corpus_root / "structured")
                    chunks_path = corpus_root / "chunks" / relative.with_suffix(".jsonl")
                    assert chunks_path.is_file()
                    assert len(chunks_path.read_text("utf-8").splitlines()) == manifest.chunk_counts[filing_id]
                    derived.append(str(structured_path))
            assert derived, f"Historical derived files unavailable for {filing_id}"
        historical_manifests.append({"path": str(path), "manifest_hash": manifest.manifest_hash,
                                     "snapshot_version": manifest.snapshot_version})
    result = {"scope": "Manual classifications pinned to exact raw bytes; not generalized to other filings.",
              "table_reviews": table_reviews, "quality_diagnostic": service.extraction_quality(row["filing_id"]),
              "historical_manifests_hash_checked": historical_manifests,
              "historical_raw_files_hash_checked": sorted(historical_raw_files),
              "historical_derived_check_scope": "Files present, version/normalized-hash metadata and row counts match manifests. Old parser code is not replayed; this does not re-certify every old chunk.",
              "historical_lookup_contract": "Manifest inventory exposes paths; archived files persist. Registry chunk lookup and evidence API serve only the active derived revision.",
              "whole_document_status_unchanged": registry.get_filing(row["filing_id"])["status"]}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.root, args.output)
    print(json.dumps({"tables_reviewed": len(result["table_reviews"]),
                      "historical_manifests_valid": len(result["historical_manifests_hash_checked"]),
                      "whole_document_status": result["whole_document_status_unchanged"]}))

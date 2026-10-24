"""Read immutable B manifests/artifacts without mutating the ingestion registry."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import sqlite3

from app.financial_ingestion import PARSER_VERSION, CHUNKER_VERSION
from app.financial_ingestion.chunker import chunk_filing
from app.financial_ingestion.html_parser import parse_sec_html, normalized_filing_text
from app.financial_ingestion.schemas import DatasetManifest, StructuredFiling, FinancialChunk
from app.financial_ingestion.pipeline import validate_metadata_identity


def digest_file(path: Path) -> str:
    with path.open("rb") as stream:
        import hashlib
        return hashlib.file_digest(stream, "sha256").hexdigest()


def canonical(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def registered_path(root: Path, value: str) -> Path:
    root = root.resolve()
    candidate = Path(value).resolve()
    if candidate.is_relative_to(root):
        return candidate
    parts = Path(value).parts
    for name in ("raw", "structured", "chunks", "manifests"):
        if name in parts:
            candidate = root.joinpath(*parts[parts.index(name):]).resolve()
            if candidate.is_relative_to(root):
                return candidate
    raise ValueError("Registered artifact path is outside its corpus root")


def resolve_sources(specs: list[dict]) -> list[dict]:
    sources = []
    if not specs or len(specs) > 8:
        raise ValueError("Use one to eight explicit source manifests")
    for spec in specs:
        root = Path(spec["root"]).resolve()
        db = root / "registry.sqlite3"
        if not db.is_file():
            raise ValueError("Source registry does not exist")
        with sqlite3.connect(db.as_uri() + "?mode=ro", uri=True) as connection:
            row = connection.execute("SELECT path FROM manifests WHERE manifest_hash=? AND dataset_id=?",
                                     (spec["manifest_hash"], spec["dataset_id"])).fetchone()
        if row is None:
            raise ValueError("Requested immutable manifest is not registered")
        path = registered_path(root, row[0])
        manifest = DatasetManifest.model_validate_json(path.read_text("utf-8"))
        if manifest.manifest_hash != spec["manifest_hash"] or manifest.content_hash() != manifest.manifest_hash:
            raise ValueError("SOURCE_MANIFEST_MISMATCH")
        if manifest.parser_version != PARSER_VERSION or manifest.chunker_version != CHUNKER_VERSION:
            raise ValueError("Unsupported source parser/chunker; do not silently reinterpret historical output")
        if manifest.failed_documents:
            raise ValueError("Cannot index a manifest with failed documents")
        if manifest.partial_documents and not spec.get("allow_partial", False):
            raise ValueError("Source has partial documents; explicit pilot opt-in is required")
        limit = spec.get("per_filing_limit")
        if limit is not None and (isinstance(limit, bool) or not 1 <= limit <= 100000):
            raise ValueError("Invalid per-filing subset limit")
        sources.append({"root": str(root), "manifest_path": str(path),
                        "manifest": manifest.model_dump(mode="json"),
                        "per_filing_limit": limit, "allow_partial": bool(spec.get("allow_partial", False))})
    return sorted(sources, key=lambda item: (item["manifest"]["manifest_hash"], item["root"]))


def iter_documents(sources: list[dict]):
    for source in sources:
        root = Path(source["root"])
        manifest = source["manifest"]
        for filing_id in sorted(manifest["filing_ids"]):
            raw_hash = manifest["raw_hashes"].get(filing_id)
            normalized_hash = manifest["normalized_hashes"].get(filing_id)
            if not raw_hash or not normalized_hash:
                raise ValueError("Manifest has an incomplete source member")
            key = sha256(filing_id.encode()).hexdigest()[:24]
            candidates = []
            for path in (root / "structured" / key).rglob("*.json"):
                saved = StructuredFiling.model_validate_json(path.read_text("utf-8"))
                if (saved.metadata.raw_content_hash == raw_hash
                        and saved.metadata.normalized_content_hash == normalized_hash
                        and saved.metadata.parser_version == manifest["parser_version"]):
                    candidates.append((path, saved))
            if len(candidates) != 1:
                raise ValueError("Source structured revision is missing or ambiguous")
            structured_path, saved = candidates[0]
            validate_metadata_identity(saved.metadata)
            raw_path = root / "raw" / saved.metadata.cik / saved.metadata.accession_number / raw_hash / saved.metadata.primary_document
            relative = structured_path.relative_to(root / "structured")
            chunks_path = root / "chunks" / relative.with_suffix(".jsonl")
            frozen = {"raw_path": str(raw_path), "structured_path": str(structured_path),
                      "chunks_path": str(chunks_path), "raw_hash": raw_hash,
                      "structured_hash": digest_file(structured_path), "chunks_hash": digest_file(chunks_path),
                      "normalized_hash": normalized_hash, "manifest_hash": manifest["manifest_hash"],
                      "source_dataset_id": manifest["dataset_id"]}
            expected = verified_source(frozen)
            expected_count = manifest["chunk_counts"][filing_id]
            if len(expected) != expected_count:
                raise ValueError("Source chunk count does not match manifest")
            limit = source["per_filing_limit"]
            count = min(expected_count, limit) if limit else expected_count
            selected = {round(index * (expected_count - 1) / (count - 1)) for index in range(count)} if count > 1 else {0}
            seen = set()
            with chunks_path.open(encoding="utf-8") as stream:
                for ordinal, line in enumerate(stream):
                    chunk = FinancialChunk.model_validate_json(line)
                    if chunk.chunk_id in seen or chunk.chunk_id not in expected:
                        raise ValueError("Duplicate/unexpected source chunk")
                    if chunk.model_dump() != expected[chunk.chunk_id].model_dump():
                        raise ValueError("Source chunk context is inconsistent with disclosure")
                    seen.add(chunk.chunk_id)
                    if ordinal in selected:
                        yield {"chunk": chunk.model_dump(mode="json"), "source": frozen}
            if seen != set(expected):
                raise ValueError("Source chunk membership is incomplete")


def verified_source(frozen: dict) -> dict[str, FinancialChunk]:
    raw_path = Path(frozen["raw_path"])
    structured_path = Path(frozen["structured_path"])
    if digest_file(raw_path) != frozen["raw_hash"] or digest_file(structured_path) != frozen["structured_hash"]:
        raise ValueError("SOURCE_ARTIFACT_HASH_MISMATCH")
    if digest_file(Path(frozen["chunks_path"])) != frozen["chunks_hash"]:
        raise ValueError("SOURCE_CHUNKS_HASH_MISMATCH")
    saved = StructuredFiling.model_validate_json(structured_path.read_text("utf-8"))
    if saved.metadata.parser_version != PARSER_VERSION:
        raise ValueError("SOURCE_PARSER_VERSION_MISMATCH")
    parsed = parse_sec_html(raw_path.read_bytes(), saved.metadata.model_copy(deep=True))
    if sha256(normalized_filing_text(parsed).encode()).hexdigest() != frozen["normalized_hash"]:
        raise ValueError("SOURCE_NORMALIZED_HASH_MISMATCH")
    return {chunk.chunk_id: chunk for chunk in chunk_filing(parsed)}

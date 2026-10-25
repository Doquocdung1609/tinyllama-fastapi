"""Read immutable B manifests/artifacts without mutating the ingestion registry."""
from __future__ import annotations

from collections import OrderedDict
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
from threading import Event, Lock

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


class ProvenanceCache:
    """Bounded single-flight cache for parse/rechunk work, never for hash trust."""

    def __init__(self, max_entries: int = 8, max_bytes: int = 128 * 1024 * 1024):
        self.max_entries = max(0, max_entries)
        self.max_bytes = max(0, max_bytes)
        self._entries = OrderedDict()
        self._bytes = 0
        self._inflight: dict[tuple, Event] = {}
        self._lock = Lock()
        self._stats = {"hits": 0, "misses": 0, "evictions": 0, "waits": 0,
                       "invalidations": 0}

    def get_or_load(self, key: tuple, loader):
        if not self.max_entries or not self.max_bytes:
            with self._lock:
                self._stats["misses"] += 1
            return loader()
        while True:
            with self._lock:
                found = self._entries.pop(key, None)
                if found is not None:
                    self._entries[key] = found
                    self._stats["hits"] += 1
                    return found[0]
                event = self._inflight.get(key)
                if event is None:
                    event = self._inflight[key] = Event()
                    self._stats["misses"] += 1
                    owner = True
                else:
                    self._stats["waits"] += 1
                    owner = False
            if owner:
                break
            event.wait()
        try:
            value = loader()
            size = sum(len(chunk.model_dump_json()) for chunk in value.values())
            with self._lock:
                if size <= self.max_bytes:
                    self._entries[key] = (value, size)
                    self._bytes += size
                    while len(self._entries) > self.max_entries or self._bytes > self.max_bytes:
                        _, (_, removed) = self._entries.popitem(last=False)
                        self._bytes -= removed
                        self._stats["evictions"] += 1
            return value
        finally:
            with self._lock:
                self._inflight.pop(key).set()

    def invalidate_generation(self, generation: str):
        with self._lock:
            keys = [key for key in self._entries if key[0] == generation]
            for key in keys:
                _, size = self._entries.pop(key)
                self._bytes -= size
            if keys:
                self._stats["invalidations"] += len(keys)

    def clear(self):
        with self._lock:
            count = len(self._entries)
            self._entries.clear()
            self._bytes = 0
            if count:
                self._stats["invalidations"] += count

    def diagnostics(self) -> dict:
        with self._lock:
            return {**self._stats, "entries": len(self._entries), "bytes": self._bytes,
                    "max_entries": self.max_entries, "max_bytes": self.max_bytes}


def _verified_bytes(path: Path, expected_hash: str) -> bytes:
    """Hash the exact bytes used by the request, closing the hash/read TOCTOU gap."""
    with path.open("rb") as stream:
        data = stream.read()
    if sha256(data).hexdigest() != expected_hash:
        raise ValueError("SOURCE_ARTIFACT_HASH_MISMATCH")
    return data


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
            frozen = {"filing_id": filing_id, "raw_path": str(raw_path), "structured_path": str(structured_path),
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


def verified_source(frozen: dict, *, cache: ProvenanceCache | None = None,
                    generation: str = "unscoped") -> dict[str, FinancialChunk]:
    raw_path = Path(frozen["raw_path"])
    structured_path = Path(frozen["structured_path"])
    try:
        raw = _verified_bytes(raw_path, frozen["raw_hash"])
        structured = _verified_bytes(structured_path, frozen["structured_hash"])
        chunks_path = Path(frozen["chunks_path"])
        _verified_bytes(chunks_path, frozen["chunks_hash"])
        # Detect replacement or in-place modification while the verification
        # snapshot was being assembled. Parsing uses the already hashed bytes.
        if (digest_file(raw_path) != frozen["raw_hash"] or
                digest_file(structured_path) != frozen["structured_hash"] or
                digest_file(chunks_path) != frozen["chunks_hash"]):
            raise ValueError("SOURCE_CHANGED_DURING_VERIFICATION")
    except Exception:
        if cache is not None:
            cache.clear()
        raise
    key = (generation, frozen.get("filing_id"), frozen["raw_hash"], frozen["structured_hash"],
           frozen["chunks_hash"], frozen["normalized_hash"], frozen["manifest_hash"],
           PARSER_VERSION, CHUNKER_VERSION, "max_chars=1200;overlap=120")

    def load():
        saved = StructuredFiling.model_validate_json(structured)
        if saved.metadata.parser_version != PARSER_VERSION:
            raise ValueError("SOURCE_PARSER_VERSION_MISMATCH")
        parsed = parse_sec_html(raw, saved.metadata.model_copy(deep=True))
        if sha256(normalized_filing_text(parsed).encode()).hexdigest() != frozen["normalized_hash"]:
            raise ValueError("SOURCE_NORMALIZED_HASH_MISMATCH")
        return {chunk.chunk_id: chunk for chunk in chunk_filing(parsed)}

    return cache.get_or_load(key, load) if cache is not None else load()

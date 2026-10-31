"""Bounded author-parser SEC corpus from two pinned, public HTML snapshots.

Run with the isolated virtualenv containing the unmodified author package.
This does not fetch SEC data, modify the V3R3 workspace, or claim equivalence
to the author's unavailable 47-filing corpus.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from hybrid_search.chunking.chunker import DocumentChunker
from hybrid_search.config import AppConfig
from hybrid_search.ingestion.edgar_client import FilingMetadata
from hybrid_search.ingestion.pipeline import IngestionPipeline


ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "docs/topic3/01_REPRODUCTION"
AUTHOR = ROOT / "tmp/topic3/original-author"
SOURCES = [
    {
        "file": "pg-20260930.htm",
        "sha256": "1c60df5705b24abf1141221441e8a5f77e0233a9884a1927b84ce90ac74b7527",
        "ticker": "PG", "company_name": "PROCTER & GAMBLE Co", "cik": "0000080424",
        "form": "10-Q", "filing_date": "2026-10-22", "report_date": "2026-09-30",
        "accession_number": "0000080424-26-000256", "primary_document": "pg-20260930.htm",
        "fiscal_period": "Q1 FY2027",
        "document_url": "https://www.sec.gov/Archives/edgar/data/80424/000008042426000256/pg-20260930.htm",
    },
    {
        "file": "hd-20260802.htm",
        "sha256": "301a64049ae9e407c16d6b07b734614a1e64fa969acc3126f9e7a74023c9b614",
        "ticker": "HD", "company_name": "HOME DEPOT, INC.", "cik": "0000354950",
        "form": "10-Q", "filing_date": "2026-08-25", "report_date": "2026-08-02",
        "accession_number": "0001628280-26-058715", "primary_document": "hd-20260802.htm",
        "fiscal_period": "Q2 FY2026",
        "document_url": "https://www.sec.gov/Archives/edgar/data/354950/000162828026058715/hd-20260802.htm",
    },
]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=AUTHOR, text=True).strip()
    if commit != "16682dd42ca9cd4887ae74935cb3526dce580c49":
        raise SystemExit("AUTHOR_SOURCE_COMMIT_CHANGED")
    pipeline = IngestionPipeline(AppConfig())  # no network call is made
    chunker = DocumentChunker(chunk_size_tokens=500, chunk_overlap_tokens=100)
    docs = []
    source_record = []
    for item in SOURCES:
        path = HERE / "source" / item["file"]
        if sha(path) != item["sha256"]:
            raise SystemExit("SOURCE_HTML_HASH_CHANGED")
        metadata = FilingMetadata(**{k: v for k, v in item.items() if k not in {"file", "sha256"}})
        document = pipeline.process_filing_file(path, metadata)
        if document is None:
            raise SystemExit("AUTHOR_HTML_PARSE_FAILED")
        docs.append(document)
        source_record.append({"filename": item["file"], "sha256": item["sha256"], "url": item["document_url"], "document_id": document.document_id, "sections": len(document.sections)})
    chunks = chunker.chunk_documents(docs)
    output = HERE / "author_chunks.jsonl"
    with output.open("w", encoding="utf-8", newline="\n") as stream:
        for chunk in chunks:
            stream.write(chunk.model_dump_json(exclude_none=True) + "\n")
    manifest = {
        "status": "METHODOLOGICAL_REPLICATION_TWO_2026_SEC_FILINGS",
        "author_commit": commit,
        "parser": "EdgarHtmlParser+SectionExtractor+TextNormalizer",
        "chunker": {"chunk_size_tokens": 500, "chunk_overlap_tokens": 100},
        "sources": source_record,
        "chunk_count": len(chunks),
        "chunks_sha256": sha(output),
        "limitations": ["Different corpus and filing years from the author's 47 filings", "No independent qrels or author model weights locked yet", "SEC source extraction status in the product workspace is partial"],
    }
    (HERE / "CORPUS_MANIFEST.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"documents": len(docs), "chunks": len(chunks), "sections": [len(d.sections) for d in docs]}))


if __name__ == "__main__":
    main()

"""Read-only, source-preserving Topic 3 baseline inventory.

Run from the repository root after cloning the author's public repository to
tmp/topic3/original-author. No credentials or user-owned file contents are
written to the report.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
AUTHOR = ROOT / "tmp/topic3/original-author"
PAPER = Path.home() / "Downloads" / "Topic 3 - Hybrid Search.pdf"
SEC = ROOT / "tmp/studio-runtime/sec/p7-isolated-review-product-20261028/raw"
PDF = ROOT / "studio_workspace/search-v3r3-owner-20261030/files"


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def git(*args: str, cwd: Path = ROOT) -> str:
    return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()


def main() -> None:
    if not PAPER.is_file() or not AUTHOR.is_dir():
        raise SystemExit("PAPER_OR_AUTHOR_CLONE_MISSING")
    dataset = AUTHOR / "evaluation/golden_dataset.yaml"
    items = yaml.safe_load(dataset.read_text(encoding="utf-8"))["queries"]
    author_data = AUTHOR / "data"
    inventory = {
        "status": "P0_READ_ONLY_INVENTORY",
        "branch": git("branch", "--show-current"),
        "base_commit": git("rev-parse", "HEAD"),
        "paper": {"sha256": digest(PAPER), "bytes": PAPER.stat().st_size, "pages": 23, "text_layer": False},
        "author_repository": {
            "url": "https://github.com/satyam671/financial-hybrid-search-qdrant",
            "commit": git("rev-parse", "HEAD", cwd=AUTHOR),
            "golden_query_count": len(items),
            "golden_sha256": digest(dataset),
            "golden_fields": sorted({key for item in items for key in item}),
            "included_data_files": sorted(str(p.relative_to(author_data)).replace("\\", "/") for p in author_data.rglob("*") if p.is_file()),
            "raw_sec_corpus_included": any((author_data / "raw").rglob("*.htm")) if (author_data / "raw").exists() else False,
        },
        "local_isolated_sources": {
            "sec_raw": {str(p.relative_to(SEC)).replace("\\", "/"): digest(p) for p in sorted(SEC.rglob("*.htm"))} if SEC.exists() else {},
            "owner_pdf_count": len(list(PDF.glob("*.pdf"))) if PDF.exists() else 0,
            "owner_pdf_sha256": {p.name: digest(p) for p in sorted(PDF.glob("*.pdf"))} if PDF.exists() else {},
        },
        "v3r3_artifacts_sha256": {
            name: digest(ROOT / "docs/search_v3r3" / name)
            for name in ["PAIRED_PRECISION_FINAL.json", "AFTER_178_CEO_RECONSTRUCTED.json", "BASELINE_AUDIT.json"]
        },
        "equivalence": "EXACT_REPRODUCTION_NOT_ESTABLISHED",
    }
    output = ROOT / "docs/topic3/00_AUDIT/REPOSITORY_INVENTORY.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(items)} author queries; {len(inventory['local_isolated_sources']['sec_raw'])} SEC HTML; {inventory['local_isolated_sources']['owner_pdf_count']} owner PDFs")


if __name__ == "__main__":
    main()

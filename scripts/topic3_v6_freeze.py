"""Freeze V6 candidate code and evidence before any new label inspection."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/topic3_v6/V6_ALGORITHM_FREEZE_MANIFEST.json"
AUTHOR = ROOT / "tmp/topic3/original-author"


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    project = [
        "app/research_retrieval/faith_r.py",
        "app/research_retrieval/faith_r_live.py",
        "scripts/topic3_v5r_author_live.py",
        "scripts/topic3_v5r_ablation.py",
        "scripts/topic3_v5r_query_once.py",
    ]
    author = [
        "config/default.yaml", "src/hybrid_search/retrieval/engine.py",
        "src/hybrid_search/retrieval/bm25_retriever.py",
        "src/hybrid_search/retrieval/dense_retriever.py",
        "src/hybrid_search/retrieval/sparse_retriever.py",
        "src/hybrid_search/retrieval/bm25_dense_retriever.py",
        "src/hybrid_search/retrieval/sparse_dense_retriever.py",
        "src/hybrid_search/retrieval/reranker.py",
        "src/hybrid_search/retrieval/extractor.py",
        "src/hybrid_search/embeddings/bm25.py",
        "src/hybrid_search/embeddings/dense.py",
        "src/hybrid_search/embeddings/sparse.py",
    ]
    files = {str(Path("project") / name): digest(ROOT / name) for name in project}
    files.update({str(Path("author_16682dd") / name): digest(AUTHOR / name) for name in author})
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    author_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=AUTHOR, text=True).strip()
    if head != "571750b116dde37c9a1b39dcc95ec075c02f9950":
        raise ValueError(f"Unexpected V5R checkpoint: {head}")
    if author_head != "16682dd42ca9cd4887ae74935cb3526dce580c49":
        raise ValueError(f"Unexpected author checkpoint: {author_head}")
    manifest = {
        "status": "FROZEN_BEFORE_V6_NEW_OUTCOME_ACCESS",
        "frozen_utc": datetime.now(timezone.utc).isoformat(),
        "project_checkpoint": head, "author_commit": author_head,
        "corpus_sha256": "7c6852a8c68ed1c64194c2da9339fbb4719482949e5705596499db53114abb1f",
        "indexes": {"A": "P3D_RECOVERED_NOT_PROVEN_P3C", "B": "P7K_FISCAL_CORRECTED"},
        "methods": {
            "original": ["bm25", "dense", "sparse", "bm25_dense", "sparse_dense", "rerank"],
            "faith_r": ["A2", "A3", "A4", "A4R"],
        },
        "algorithm_parameters": {
            "dense_model": "BAAI/bge-small-en-v1.5", "bm25_model": "Qdrant/bm25",
            "sparse_model": "prithivida/Splade_PP_en_v1",
            "dense_dimensions": 384, "collection": "financial_docs",
            "original_default_prefetch": 50, "original_stage2_min_pool": 20,
            "original_stage2_coverage_weights": [0.70, 0.30],
            "original_stage2_score_weights": [0.15, 0.25, 0.10, 0.15, 0.10, 0.15, 0.10],
            "faith_r_default_budget": 10, "faith_r_allowed_budget": [1, 100],
            "faith_r_prefetch": "max(50,budget)",
            "a2": "issuer hard filter; one non-comparative fiscal year hard filter",
            "a3": "A2 plus same-corpus row sidecar; quota max(1,budget//4); deduplicate/fill",
            "a4": "A3 then lexicographic six-feature ordering; stable original-rank and chunk-id tie break",
            "a4r": "post-hoc seven-feature alignment on A3 pool; not independent development result",
            "a5": "A4 ranking plus UNVERIFIED; no verified numeric cell",
        },
        "code_sha256": files,
        "label_boundary": "P7L/F10 and A4R repair cases exposed development; V5R 30-question queue candidate pool only; no V6 human gold",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode()
    OUT.write_bytes(encoded)
    print(json.dumps({"path": str(OUT), "sha256": hashlib.sha256(encoded).hexdigest(),
                      "file_count": len(files)}))


if __name__ == "__main__":
    main()

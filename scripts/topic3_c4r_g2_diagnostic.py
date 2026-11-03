"""Post-exposure G2 A5 regression; never an independent benchmark."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys

from app.research_retrieval.faith_r_a5 import execute_a5


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(questions: Path, index_b: Path, source_manifest: Path,
        author_root: Path, cache: Path, output: Path) -> dict:
    if output.exists():
        raise FileExistsError("G2 post-exposure output already exists")
    if sha(questions) != "a92cdfb6a00744c3ea8bdae93b337d60919be52e65019b4f541b40235f4aa4ef":
        raise ValueError("Frozen G2 question bytes changed")
    with questions.open(encoding="utf-8-sig", newline="") as stream:
        items = list(csv.DictReader(stream))
    if len(items) != 94:
        raise ValueError("G2 count changed")
    os.environ.setdefault("FASTEMBED_CACHE_PATH", str(cache.resolve()))
    sys.path.insert(0, str(author_root.resolve() / "src"))
    from hybrid_search.retrieval.engine import SearchEngine
    from qdrant_client import QdrantClient
    sources = json.loads(source_manifest.read_text(encoding="utf-8"))
    report_dates = {s["accession"]: s["report_date"] for s in sources["sources"]}
    client = QdrantClient(path=str(index_b))
    try:
        if client.count("financial_docs", exact=True).count != 8670:
            raise ValueError("Index B changed")
        engine = SearchEngine(client=client)
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x", encoding="utf-8", newline="\n") as stream:
            for i, item in enumerate(items, 1):
                try:
                    result = execute_a5(engine, item["question"], budget=20,
                                        report_dates=report_dates, use_fallback=False)
                    record = {"query_id": item["question_id"], "status": result.status,
                              "query_plan": result.query_plan, "attempts": result.attempts,
                              "hits": [{"rank": h["rank"], "chunk_id": h["chunk_id"],
                                        "accession": h["accession_number"]} for h in result.hits],
                              "latency_ms": result.elapsed_ms, "error": None}
                except Exception as exc:
                    record = {"query_id": item["question_id"], "status": "ERROR",
                              "attempts": [], "hits": [], "error": f"{type(exc).__name__}:{exc}"}
                record.update({"schema": "c4r_g2_exposed_diagnostic/v1", "arm": "A5_BASE",
                               "index": "B", "not_independent": True,
                               "run_timestamp": datetime.now(timezone.utc).isoformat()})
                stream.write(json.dumps(record, ensure_ascii=False) + "\n")
                stream.flush()
                if i % 10 == 0:
                    print(f"G2 diagnostic {i}/94", flush=True)
    finally:
        client.close()
    return {"rows": len(items), "sha256": sha(output), "status": "POST_EXPOSURE_REGRESSION_DIAGNOSTIC"}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("questions", "index_b", "source_manifest", "author_root", "cache", "output"):
        p.add_argument("--" + name.replace("_", "-"), type=Path, required=True)
    print(json.dumps(run(**vars(p.parse_args())), indent=2))

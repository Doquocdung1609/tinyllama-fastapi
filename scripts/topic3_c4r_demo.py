"""One-query A5 + source-cited financial answer demo; no evaluation gold input."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

from app.research_retrieval.faith_r_a5 import execute_a5
from app.research_retrieval.financial_answer_v8 import SourceArchiveAnswererV8


def demo(question: str, index_b: Path, source_manifest: Path,
         author_root: Path, cache: Path) -> dict:
    os.environ.setdefault("FASTEMBED_CACHE_PATH", str(cache.resolve()))
    sys.path.insert(0, str(author_root.resolve() / "src"))
    from qdrant_client import QdrantClient
    from hybrid_search.retrieval.engine import SearchEngine
    client = QdrantClient(path=str(index_b))
    answerer = SourceArchiveAnswererV8(source_manifest)
    try:
        engine = SearchEngine(client=client)
        dates = {s["accession"]: s["report_date"] for s in answerer.sources.values()}
        result = execute_a5(engine, question, 20, report_dates=dates,
                            use_fallback=False)
        answer = answerer.answer(question, result.hits, "SOURCE_ENRICHED_V1")
        return {"schema": "c4r_live_demo_answer/v1", "question": question,
                "query_plan": result.query_plan, "retrieval_status": result.status,
                "attempts": result.attempts,
                "top5_original_chunks": [{"rank": h["rank"], "chunk_id": h["chunk_id"],
                                          "accession": h["accession_number"]}
                                         for h in result.hits[:5]],
                "answer_track": "SOURCE_ENRICHED_V1",
                "answer": answer.__dict__,
                "latency_ms": result.elapsed_ms,
                "not_original_chunk_exact_qrel": True,
                "evaluation_gold_read": False}
    finally:
        answerer.close()
        client.close()


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--question", required=True)
    for name in ("index_b", "source_manifest", "author_root", "cache"):
        p.add_argument("--" + name.replace("_", "-"), required=True, type=Path)
    # Windows PowerShell can give redirected Python stdout a legacy code page.
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(demo(**vars(p.parse_args())), ensure_ascii=False, indent=2))

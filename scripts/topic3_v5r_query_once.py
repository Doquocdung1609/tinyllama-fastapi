"""One bounded live research query for the opt-in Research Lab UI."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

from qdrant_client import QdrantClient

from topic3_v5r_author_live import REPO, WORK

sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tmp/topic3/original-author/src"))
from app.research_retrieval.faith_r_live import EvidenceSidecar, live_retrieve  # noqa: E402
from hybrid_search.retrieval.engine import SearchEngine  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", required=True)
    parser.add_argument("--arm", choices=("A0", "A1", "A2", "A3", "A4", "A4R", "A5"), required=True)
    args = parser.parse_args()
    if not 3 <= len(args.query) <= 300:
        raise ValueError("QUERY_LENGTH")
    os.environ.setdefault("FASTEMBED_CACHE_PATH", str(REPO / "tmp/topic3/model-cache"))
    index = "A" if args.arm == "A0" else "B"
    client = QdrantClient(path=str(WORK / index))
    try:
        if client.count("financial_docs", exact=True).count != 8670:
            raise ValueError("INDEX_COUNT_MISMATCH")
        engine = SearchEngine(client=client)
        start = time.perf_counter()
        if args.arm in {"A0", "A1"}:
            hits = [{"rank": i, "chunk_id": r.chunk_id, "ticker": r.ticker,
                     "fiscal_period": r.fiscal_period, "score": r.score, "text": r.text,
                     "source_url": r.source_url, "accession_number": r.document_id.split("_", 1)[-1],
                     "verification_status": "UNVERIFIED"}
                    for i, r in enumerate(engine.search(args.query, method="bm25_dense", k=10), 1)]
        else:
            sidecar = EvidenceSidecar(client) if args.arm in {"A3", "A4", "A4R", "A5"} else None
            hits = live_retrieve(engine, args.query, args.arm, 10, sidecar).hits
        output = {"status": "LIVE_EXECUTED", "experiment_id": "V5R_UI_ON_DEMAND",
                  "arm": args.arm, "index": index, "question": args.query,
                  "run_utc": datetime.now(timezone.utc).isoformat(),
                  "elapsed_ms": round((time.perf_counter() - start) * 1000, 2),
                  "method": "bm25_dense" if args.arm in {"A0", "A1", "A2"} else "bm25_dense_plus_same_corpus_sidecar",
                  "index_points": 8670,
                  "hits": [{**{k: h[k] for k in ("rank", "chunk_id", "ticker", "fiscal_period", "score", "source_url", "accession_number", "verification_status")},
                            "snippet": h["text"][:450]} for h in hits],
                  "limits": ["Index A is recovered P3D, not proven exact original P3C",
                             "Chunk relevance does not certify a financial cell or answer value"]}
        print(json.dumps(output, ensure_ascii=False))
    finally:
        client.close()


if __name__ == "__main__":
    main()

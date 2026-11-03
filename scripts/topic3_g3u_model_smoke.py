"""Non-G2 live engine smoke; print resource/count facts, never candidate ranks."""

import argparse
import json
import os
from pathlib import Path
import sys
import time


def run(author_root: Path, index_root: Path, model_cache: Path) -> dict:
    import psutil
    from qdrant_client import QdrantClient

    sys.path.insert(0, str(author_root / 'src'))
    os.environ.setdefault('FASTEMBED_CACHE_PATH', str(model_cache))
    from hybrid_search.retrieval.engine import SearchEngine

    client = QdrantClient(path=str(index_root / 'A'))
    process = psutil.Process()
    try:
        if client.count('financial_docs', exact=True).count != 8670:
            raise ValueError('Restored index count changed')
        engine = SearchEngine(client=client)
        query = 'Synthetic non-G2 test: what was the revenue of Acme Fictional Corp in 2031?'
        measurements = {}
        for method in ('bm25', 'dense', 'sparse', 'bm25_dense', 'sparse_dense', 'rerank'):
            start = time.perf_counter()
            hits = engine.search(query, method=method, k=20, prefetch_k=50)
            measurements[method] = {'count': len(hits), 'elapsed_ms': round((time.perf_counter()-start)*1000, 2),
                                    'process_rss_mib': round(process.memory_info().rss/1048576, 2)}
        return {'fixture': 'SYNTHETIC_NON_G2', 'index_count': 8670, 'methods': measurements,
                'candidate_ids_or_scores_exposed': False}
    finally:
        client.close()


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for n in ('author_root', 'index_root', 'model_cache'):
        p.add_argument('--'+n.replace('_','-'), type=Path, required=True)
    print(json.dumps(run(**vars(p.parse_args())), indent=2))

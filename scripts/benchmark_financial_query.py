"""Fixture-only D1 resolver benchmark. Does not open an index or a live service.

Run from repository root: python -m scripts.benchmark_financial_query
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys
from time import perf_counter
import tracemalloc

from app.financial_query import resolve_financial_query
from app.financial_query.contracts import CorpusCatalogV1


def distribution(values):
    ordered = sorted(values)
    return {'samples': len(values), 'p50_ms': statistics.median(values),
            'p95_ms_nearest_rank': ordered[max(0, (95 * len(values) + 99) // 100 - 1)]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repeats', type=int, default=25)
    parser.add_argument('--cold-processes', type=int, default=10)
    parser.add_argument('--cold-child', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not 1 <= args.repeats <= 100 or not 1 <= args.cold_processes <= 20:
        parser.error('Bounded repeats 1..100 and cold-processes 1..20 required')
    root = Path(__file__).resolve().parents[1]
    fixture = root / 'tests' / 'fixtures' / 'financial_query'
    catalog_bytes = (fixture / 'catalog.json').read_bytes()
    case_bytes = (fixture / 'cases.json').read_bytes()
    catalog = CorpusCatalogV1.model_validate_json(catalog_bytes)
    cases = json.loads(case_bytes)
    def resolve(case):
        start = perf_counter()
        result = resolve_financial_query(case['question'], case.get('filters', {}), catalog)
        elapsed = (perf_counter() - start) * 1000
        if result.status.value != case['status']:
            raise RuntimeError('Benchmark fixture correctness failed: ' + case['id'])
        return elapsed
    if args.cold_child:
        print(json.dumps({'first_resolver_ms': resolve(cases[0])}))
        return
    cold_wall, cold_request = [], []
    for _ in range(args.cold_processes):
        start = perf_counter()
        child = subprocess.run([sys.executable, '-m', 'scripts.benchmark_financial_query', '--cold-child'],
            cwd=root, check=True, capture_output=True, text=True, timeout=30)
        cold_wall.append((perf_counter() - start) * 1000)
        cold_request.append(json.loads(child.stdout)['first_resolver_ms'])
    for case in cases:
        resolve(case)
    timings = [resolve(case) for _ in range(args.repeats) for case in cases]
    # Trace allocations separately; instrumentation is not in warm timings.
    tracemalloc.start()
    for case in cases:
        resolve(case)
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    try:
        import psutil
        rss = psutil.Process(os.getpid()).memory_info().rss
    except ImportError:
        rss = None
    report = {
        'scope': 'D1 resolver only on synthetic metadata; no retrieval-quality claim',
        'python': platform.python_version(), 'os': platform.platform(), 'cpu': platform.processor(),
        'fixture': {'issuers': len(catalog.issuers), 'filings': len(catalog.filings), 'queries': len(cases),
            'catalog_sha256_canonical_lf': sha256(catalog_bytes.replace(b'\r\n', b'\n')).hexdigest(),
            'cases_sha256_canonical_lf': sha256(case_bytes.replace(b'\r\n', b'\n')).hexdigest()},
        'warm': distribution(timings), 'first_request_fresh_process_C01': distribution(cold_request),
        'fresh_process_wall_including_startup_imports_fixture_load_C01': distribution(cold_wall),
        'tracemalloc_one_sweep_bytes': {'current': current, 'peak': peak}, 'process_rss_bytes_after_run': rss,
        'notes': ['One warmup sweep; fixed case order; 25 repeats by default; no GPU used',
            'Fresh process is not a cold OS filesystem or CPU cache',
            'RSS includes Python/dependencies/catalog, not incremental per-query memory',
            'Do not compare resolver-only measurements with Milestone C end-to-end timings'],
    }
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()

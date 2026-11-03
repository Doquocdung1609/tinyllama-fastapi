"""Non-scoring V7B research wiring; sealed G2 metrics are deliberately unavailable."""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
import random
import statistics


ARMS = ('AUTHOR_A_BM25', 'AUTHOR_A_DENSE', 'AUTHOR_A_SPARSE',
        'AUTHOR_A_BM25_DENSE', 'AUTHOR_A_SPARSE_DENSE', 'AUTHOR_A_RERANK',
        'AUTHOR_B_BM25', 'AUTHOR_B_DENSE', 'AUTHOR_B_SPARSE',
        'AUTHOR_B_BM25_DENSE', 'AUTHOR_B_SPARSE_DENSE', 'AUTHOR_B_RERANK',
        'FAITH_R_A0', 'FAITH_R_A1', 'FAITH_R_A2', 'FAITH_R_A3',
        'FAITH_R_A4', 'FAITH_R_A4R')


def judged_bounds(ranked: list[str], qrels: dict[str, int | None], k: int) -> dict:
    """Descriptive judged-only share and 0/1 sensitivity, never corpus recall."""
    sample = ranked[:k]
    if not sample:
        raise ValueError('Empty synthetic rank list')
    judged = [qrels[cid] for cid in sample if qrels.get(cid) is not None]
    exact = sum(v == 2 for v in judged)
    unknown = len(sample) - len(judged)
    return {'assessed': len(judged), 'unknown': unknown,
            'judged_fraction': len(judged) / len(sample),
            'judged_only_exact_share': exact / len(judged) if judged else None,
            'pessimistic_exact_share': exact / len(sample),
            'optimistic_exact_share': (exact + unknown) / len(sample),
            'metric_scope': 'SYNTHETIC_ASSESSED_POOL_ONLY_NOT_CORPUS_RECALL'}


def paired_cluster_interval(rows: list[dict], cluster_key: str, seed: int,
                            replicates: int = 1000) -> dict:
    clusters = defaultdict(list)
    for row in rows:
        clusters[row[cluster_key]].append(row['delta'])
    names = sorted(clusters)
    if len(names) < 2:
        raise ValueError('At least two independent clusters needed')
    rng = random.Random(seed)
    draws = []
    for _ in range(replicates):
        sampled = [rng.choice(names) for _ in names]
        draws.append(statistics.mean(value for name in sampled for value in clusters[name]))
    draws.sort()
    return {'clusters': len(names), 'paired_mean_delta': statistics.mean(r['delta'] for r in rows),
            'bootstrap_95pct': [draws[int(.025 * replicates)], draws[int(.975 * replicates) - 1]],
            'seed': seed, 'replicates': replicates}


def synthetic() -> dict:
    ranks = ['c1', 'c2', 'c3', 'c4']
    qrels = {'c1': 2, 'c2': None, 'c3': 0, 'c4': 1}
    rows = [{'accession': f'a{i}', 'issuer': f'issuer{i//2}', 'delta': d}
            for i, d in enumerate((1, 0, -1, 1))]
    latency = [4.0, 5.0, 8.0, 12.0]
    return {'schema': 'g3u_v7b_synthetic_dry_run/v1',
            'fixture': 'SYNTHETIC_NON_G2_NON_SEALED',
            'arm_registry_count': len(ARMS),
            'judged_bounds_at_4': judged_bounds(ranks, qrels, 4),
            'filing_cluster': paired_cluster_interval(rows, 'accession', 20261103),
            'issuer_cluster_sensitivity': paired_cluster_interval(rows, 'issuer', 20261103),
            'latency_p50_ms': statistics.median(latency),
            'latency_p95_ms': sorted(latency)[int(.95 * (len(latency) - 1))],
            'missing_judgments_coerced_to_none': False,
            'negative_cases_reported_separately': True,
            'resource_fields': ['peak_process_rss_mib', 'vram_if_measurable',
                                'index_storage_bytes', 'errors'],
            'real_G2_score': 'NOT_RUN'}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--synthetic', action='store_true', required=True,
                        help='Only supported execution mode before sealed owner authorization')
    parser.parse_args()
    print(json.dumps(synthetic(), indent=2))


if __name__ == '__main__':
    main()

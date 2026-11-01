"""Read-only historical Topic 3 run explorer; never executes a live model."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2] / 'docs/topic3'
ARM_GROUP = {
    'R0_BM25': 'AUTHOR_METHOD_REPRODUCTION',
    'R1_DENSE': 'AUTHOR_METHOD_REPRODUCTION',
    'R2_SPLADE': 'AUTHOR_METHOD_REPRODUCTION',
    'R3_BM25_DENSE_RRF': 'AUTHOR_METHOD_REPRODUCTION',
    'R4_SPLADE_DENSE_RRF': 'AUTHOR_METHOD_REPRODUCTION',
    'R5_THREE_WAY_RRF': 'PROJECT_EXTENSION',
    'R6_AUTHOR_DETERMINISTIC_STAGE2': 'AUTHOR_CODE_DETERMINISTIC_NOT_NEURAL',
}


def _read(path: Path):
    raw = path.read_bytes()
    return json.loads(raw), hashlib.sha256(raw).hexdigest()


def historical_experiment() -> dict:
    baseline, baseline_hash = _read(ROOT / '01_REPRODUCTION/RETRIEVAL_RESULTS.json')
    structure, structure_hash = _read(ROOT / '03_IMPROVEMENTS/STRUCTURE_BM25_RESULTS.json')
    qrel_path = ROOT / '01_REPRODUCTION/PROVISIONAL_SOURCE_QRELS.jsonl'
    qrels = {q['id']: q for q in (json.loads(line) for line in qrel_path.read_text(encoding='utf-8').splitlines())}
    if baseline['qrels_sha256'] != hashlib.sha256(qrel_path.read_bytes()).hexdigest() or structure['qrels_sha256'] != baseline['qrels_sha256']:
        raise ValueError('TOPIC3_HISTORICAL_QRELS_CHANGED')
    chunks = {c['chunk_id']: c for c in (json.loads(line) for line in (ROOT / '01_REPRODUCTION/author_chunks.jsonl').read_text(encoding='utf-8').splitlines())}
    structural = {r['id']: r for r in structure['records']}
    questions = []
    for record in baseline['records']:
        q = qrels[record['id']]
        arms = []
        for name, run in record['arms'].items():
            target = next((hit['rank'] for hit in run['results'] if hit['chunk_id'] in record['expected_chunk_ids']), None)
            arms.append({'name': name, 'family': ARM_GROUP[name], 'target_rank_top10': target,
                         'query_ms': run['query_ms'],
                         'hits': [{**{k: h.get(k) for k in ('rank', 'chunk_id', 'score', 'ticker')},
                                   'snippet': chunks.get(h['chunk_id'], {}).get('text', '')[:260]}
                                  for h in run['results'][:3]]})
        s = structural[record['id']]
        arms.append({'name': 'I1_STRUCTURE_BM25', 'family': 'PROJECT_IMPROVEMENT_DIFFERENT_CHUNK_COUNT',
                     'target_rank_top10': s['target_rank_top10'], 'query_ms': s['query_ms'],
                     'hits': [{**{k: h.get(k) for k in ('rank', 'chunk_id', 'score', 'statement_title')}, 'snippet': ''}
                              for h in s['hits'][:3]]})
        questions.append({'id': q['id'], 'query': q['query'], 'ticker': q['ticker'],
                          'source_url': q.get('source_url'), 'source_sha256': q.get('source_sha256'),
                          'source_locator': q.get('source_locator'), 'answerable': q['answerable'],
                          'review_status': q['review_status'], 'arms': arms})
    return {'status': 'RECORDED_EXPERIMENT_NOT_LIVE', 'base_commit': 'b3eedef92824d4f48c8afe69ec40b4e1c197c3b1',
            'corpus': 'Two 2026 SEC 10-Q HTML snapshots; 121 author chunks versus 1241 structure chunks',
            'qrels_sha256': baseline['qrels_sha256'], 'baseline_results_sha256': baseline_hash,
            'structure_results_sha256': structure_hash, 'human_gold': False,
            'limits': ['Six exposed machine-prepared questions; four known row targets',
                       'Timing is local Qdrant query only; excludes embedding and browser',
                       'Original author 47-filing results are not reproduced',
                       'SPLADE and deterministic Stage-2 here are saved runs, not live calls'],
            'live_modes': ['PRODUCT_BM25', 'PRODUCT_DENSE', 'PRODUCT_HYBRID_RRF'],
            'unavailable_live_modes': ['AUTHOR_SPLADE', 'AUTHOR_DETERMINISTIC_STAGE2', 'STRUCTURE_BM25_RESEARCH_INDEX'],
            'questions': questions}

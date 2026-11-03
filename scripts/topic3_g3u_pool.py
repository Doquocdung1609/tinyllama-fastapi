"""One-shot original-chunk candidate pool; never computes G2 quality metrics."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import gc
import hashlib
import json
import os
from pathlib import Path
import random
import statistics
import sys
import time
import zipfile


AUTHOR = ('bm25', 'dense', 'sparse', 'bm25_dense', 'sparse_dense', 'rerank')
FAITH_A = ('A0',)
FAITH_B = ('A1', 'A2', 'A3', 'A4', 'A4R')
FORBIDDEN_BLIND_KEYS = {'arm', 'method', 'rank', 'score', 'raw_score', 'model',
                        'retrieval_method', 'candidate_rank', 'candidate_score'}
REGISTRY_SHA_V1 = '5c9e95a81d21548f9fa2166785cbaa5e2a3e604791b65cd7900252171d3a20ca'
REGISTRY_SHA_V2 = 'eddef050ac78b1184d4fa311ffbf1758ae7f458940483a412f8d69271aad1f76'


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical(obj: object) -> bytes:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':')).encode('utf-8')


def validate_registry(registry: Path, protocol: Path, question_file: Path) -> dict:
    registry_sha = sha(registry.read_bytes())
    if registry_sha not in {REGISTRY_SHA_V1, REGISTRY_SHA_V2}:
        raise ValueError('Locked G3U arm registry changed')
    rules = json.loads(registry.read_text(encoding='utf-8'))
    expected_protocol = (rules['protocol_v2_sha256'] if registry_sha == REGISTRY_SHA_V2
                         else rules['protocol_v1_sha256'])
    if (sha(protocol.read_bytes()) != expected_protocol or
            sha(question_file.read_bytes()) != rules['frozen_question_sha256'] or
            rules['output_pool_depth_per_arm'] != 20 or
            rules['author_stage2_internal_candidates_at_output_20'] != 60 or
            rules['final_scoring_authorized'] is not False):
        raise ValueError('Pool specification/protocol does not match freeze')
    if registry_sha == REGISTRY_SHA_V2:
        import importlib.metadata
        if (rules.get('pool_owner_approved') is not True or
                rules['prior_registry_v1_sha256'] != REGISTRY_SHA_V1 or
                rules['fastembed_runtime'] != importlib.metadata.version('fastembed') or
                rules['qdrant_client_runtime'] != importlib.metadata.version('qdrant-client')):
            raise ValueError('Approved v2 owner/runtime provenance mismatch')
    return rules


def native_stage2_budget(output_k: int) -> int:
    return max(output_k * 3, 20)


def assert_rrf_fidelity(declared: int, runtime_default: int) -> None:
    if declared != runtime_default:
        raise ValueError('POOL_NOT_RUN_PROTOCOL_CONFLICT: locked RRF constant differs '
                         'from native Qdrant FusionQuery default; versioned owner signoff required')


def blind_union(ranked: list[dict], chunks: dict[str, dict],
                questions: dict[str, str], sources: dict[str, dict], seed: int) -> list[dict]:
    """Strip every output signal before a judge sees one original chunk."""
    seen = set()
    blind = []
    for hit in ranked:
        qid, cid = hit['question_id'], hit['chunk_id']
        if qid not in questions or cid not in chunks:
            raise ValueError('Unknown question/original chunk in ranked pool')
        key = (qid, cid)
        if key in seen:
            continue
        seen.add(key)
        chunk = chunks[cid]
        acc = chunk['document_id'].split('_')[-1]
        source = sources[acc]
        body = chunk['text']
        blind.append({'schema': 'g3u_blind_original_chunk/v1',
                      'question_id': qid, 'question': questions[qid],
                      'chunk_id': cid, 'original_text': body,
                      'original_text_sha256': sha(body.encode('utf-8')),
                      'original_record_text_hash': chunk['text_hash'],
                      'chunk_accession': acc, 'chunk_issuer': chunk['ticker'],
                      'chunk_section': chunk.get('section'),
                      'source_url': source['source_url'],
                      'source_sha256': source['sha256'],
                      'human_decision': None, 'ai_qrel_proposal': None})
    random.Random(seed).shuffle(blind)
    if any(FORBIDDEN_BLIND_KEYS & set(item) for item in blind):
        raise ValueError('Method/rank/score leaked into blind pool')
    return blind


def frozen_inputs(corpus_zip: Path, question_file: Path, source_registry: Path,
                  c1_ledger: Path, rules: dict) -> tuple[dict, dict, dict]:
    with zipfile.ZipFile(corpus_zip) as archive:
        if archive.testzip() is not None:
            raise ValueError('Frozen corpus archive CRC changed')
        raw = archive.read('corpus/chunks_frozen.jsonl')
    if sha(raw) != rules['frozen_corpus_sha256']:
        raise ValueError('Frozen corpus hash changed')
    chunks = {r['chunk_id']: r for r in (json.loads(s) for s in raw.splitlines())}
    if len(chunks) != 8670:
        raise ValueError('Frozen chunk count changed')
    with question_file.open(encoding='utf-8-sig', newline='') as stream:
        rows = list(csv.DictReader(stream))
    questions = {r['question_id']: r['question'] for r in rows}
    if len(questions) != 94:
        raise ValueError('Frozen G2 question count changed')
    c1 = {r['question_id']: r for r in
          (json.loads(s) for s in c1_ledger.read_text(encoding='utf-8').splitlines())}
    if set(c1) != set(questions) or any(sha(questions[qid].encode('utf-8')) != c1[qid]['question_sha256']
                                     for qid in questions):
        raise ValueError('Question text/hash differs from frozen C1')
    source_data = json.loads(source_registry.read_text(encoding='utf-8'))
    sources = {r['accession']: r for r in source_data['sources']}
    if len(sources) != 47 or any(c['document_id'].split('_')[-1] not in sources for c in chunks.values()):
        raise ValueError('Source accession mapping incomplete')
    return chunks, questions, sources


def dry_run() -> dict:
    questions = {'Q1': 'Question about issuer A', 'Q2': 'Question about issuer B'}
    chunks = {
        'c1': {'chunk_id': 'c1', 'document_id': 'A_0001', 'ticker': 'A', 'section': 's',
               'text_hash': 'h1', 'text': 'issuer A row'},
        'c2': {'chunk_id': 'c2', 'document_id': 'B_0002', 'ticker': 'B', 'section': 's',
               'text_hash': 'h2', 'text': 'issuer B row'}}
    sources = {'0001': {'source_url': 'https://example.test/a', 'sha256': 'sa'},
               '0002': {'source_url': 'https://example.test/b', 'sha256': 'sb'}}
    ranked = [{'question_id': 'Q1', 'chunk_id': 'c2', 'arm': 'BM25', 'rank': 1, 'score': 9},
              {'question_id': 'Q1', 'chunk_id': 'c1', 'arm': 'BGE', 'rank': 2, 'score': .4},
              {'question_id': 'Q1', 'chunk_id': 'c2', 'arm': 'BGE', 'rank': 3, 'score': .2},
              {'question_id': 'Q2', 'chunk_id': 'c1', 'arm': 'BM25', 'rank': 1, 'score': 7}]
    a = blind_union(ranked, chunks, questions, sources, 17)
    b = blind_union(ranked, chunks, questions, sources, 17)
    if a != b or len(a) != 3 or not any(x['question_id']=='Q1' and x['chunk_accession']=='0002' for x in a):
        raise ValueError('Blind union/dedup/off-target fixture failed')
    return {'status': 'SYNTHETIC_NON_G2_PASS', 'pairs': len(a),
            'off_target_candidate_retained': True, 'method_rank_score_hidden': True,
            'author_stage2_internal_at_output_20': native_stage2_budget(20)}


def execute(args: argparse.Namespace) -> dict:
    if args.out.exists():
        raise FileExistsError('One-shot pool output already exists; refusing rerun')
    rules = validate_registry(args.registry, args.protocol, args.questions)
    from qdrant_client.hybrid.fusion import DEFAULT_RANKING_CONSTANT_K
    # Pinned author retrievers invoke FusionQuery(RRF) without an explicit k.
    # Its local runtime default, not config/default.yaml, is the executed k.
    assert_rrf_fidelity(rules['rrf_constant'], DEFAULT_RANKING_CONSTANT_K)
    if native_stage2_budget(20) != 60:
        raise ValueError('Author Stage-2 native budget changed')
    chunks, questions, sources = frozen_inputs(args.corpus_zip, args.questions,
                                                args.sources, args.c1_ledger, rules)
    import psutil
    free_ram = psutil.virtual_memory().available
    free_disk = psutil.disk_usage(str(args.out.parent)).free
    if free_ram < 2.5 * (1 << 30) or free_disk < 2 * (1 << 30):
        raise RuntimeError('POOL_NOT_RUN: bounded local RAM/disk guard')
    author_root = args.author_root.resolve()
    if not (author_root / 'src/hybrid_search/retrieval/engine.py').is_file():
        raise FileNotFoundError('Pinned author source absent')
    if sha((author_root / 'src/hybrid_search/retrieval/engine.py').read_bytes()) != rules['author_engine_sha256']:
        raise ValueError('Pinned author engine hash changed')
    if sha((author_root / 'src/hybrid_search/retrieval/reranker.py').read_bytes()) != rules['author_reranker_sha256']:
        raise ValueError('Pinned author reranker hash changed')
    os.environ.setdefault('FASTEMBED_CACHE_PATH', str(args.model_cache.resolve()))
    sys.path.insert(0, str(author_root / 'src'))
    from qdrant_client import QdrantClient
    from hybrid_search.retrieval.engine import SearchEngine
    from app.research_retrieval.faith_r_live import EvidenceSidecar, live_retrieve

    args.out.mkdir(parents=True)
    started = {'schema': 'g3u_one_shot_pool_started/v1', 'started_utc': datetime.now(timezone.utc).isoformat(),
               'registry_sha256': sha(args.registry.read_bytes()),
               'protocol_sha256': sha(args.protocol.read_bytes()),
               'question_count': 94, 'index_A_sha256': rules['index_sha256']['A'],
               'index_B_sha256': rules['index_sha256']['B'],
               'no_final_scoring': True}
    (args.out / 'RUN_STARTED.json').write_text(json.dumps(started, indent=2) + '\n', encoding='utf-8')
    ranked_path = args.out / 'G3U_RANKED_POOL_SEALED.jsonl'
    timing = []
    process = psutil.Process()
    peak_rss = 0
    total_runs = 0
    with ranked_path.open('x', encoding='utf-8') as stream:
        for index in ('A', 'B'):
            client = QdrantClient(path=str(args.index_root / index))
            try:
                if client.count('financial_docs', exact=True).count != 8670:
                    raise ValueError(f'Index {index} point count changed')
                engine = SearchEngine(client=client)
                sidecar = EvidenceSidecar(client) if index == 'B' else None
                arms = [('AUTHOR_' + method.upper(), method) for method in AUTHOR]
                arms += [('FAITH_R_' + arm, arm) for arm in (FAITH_A if index == 'A' else FAITH_B)]
                for qid in sorted(questions):
                    query = questions[qid]
                    for arm_id, method in arms:
                        begin = time.perf_counter()
                        if method in AUTHOR:
                            hits = engine.search(query, method=method, k=20, prefetch_k=50)
                            data = [(r.chunk_id, float(r.score), r.text) for r in hits]
                        elif method in ('A0', 'A1'):
                            hits = engine.search(query, method='bm25_dense', k=20, prefetch_k=50)
                            data = [(r.chunk_id, float(r.score), r.text) for r in hits]
                        else:
                            hits = live_retrieve(engine, query, method, 20, sidecar).hits
                            data = [(r['chunk_id'], float(r['score']), r['text']) for r in hits]
                        elapsed_ms = round((time.perf_counter() - begin) * 1000, 3)
                        if len(data) > 20 or len({c for c, _, _ in data}) != len(data):
                            raise ValueError('Invalid rank depth or duplicate original chunk')
                        for rank, (cid, score, body) in enumerate(data, 1):
                            if cid not in chunks or sha(body.encode('utf-8')) != sha(chunks[cid]['text'].encode('utf-8')):
                                raise ValueError('Ranked hit not identical to original frozen chunk')
                            record = {'schema': 'g3u_sealed_ranked_hit/v1', 'question_id': qid,
                                      'query_sha256': sha(query.encode('utf-8')),
                                      'chunk_id': cid, 'arm': arm_id, 'index': index,
                                      'rank': rank, 'raw_score': score,
                                      'elapsed_ms': elapsed_ms,
                                      'original_text_sha256': sha(body.encode('utf-8')),
                                      'author_stage2_internal_candidates': 60 if method == 'rerank' else None,
                                      'prefetch': 50}
                            stream.write(json.dumps(record, ensure_ascii=False) + '\n')
                        stream.flush()
                        timing.append(elapsed_ms)
                        total_runs += 1
                        peak_rss = max(peak_rss, process.memory_info().rss)
                    if int(qid[-5:-3]) % 10 == 0 and qid.endswith('_02'):
                        print(f'{index}: completed a ten-filing block', flush=True)
            finally:
                client.close()
                del client
                gc.collect()
    ranked = [json.loads(s) for s in ranked_path.read_text(encoding='utf-8').splitlines()]
    blind = blind_union(ranked, chunks, questions, sources, rules['blind_seed'])
    if len({r['question_id'] for r in ranked}) != 94 or total_runs != 94 * 18:
        raise ValueError('One-shot arm/question coverage incomplete')
    blind_path = args.out / 'G3U_BLIND_REVIEW_POOL.jsonl'
    blind_path.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in blind), encoding='utf-8')
    manifest = {'schema': 'g3u_one_shot_pool_manifest/v1', 'status': 'POOL_GENERATED_NOT_SCORED',
                'question_count': 94, 'arm_runs': total_runs, 'unique_blind_pairs': len(blind),
                'ranked_lines': len(ranked), 'ranked_sha256': sha(ranked_path.read_bytes()),
                'blind_sha256': sha(blind_path.read_bytes()),
                'registry_sha256': sha(args.registry.read_bytes()),
                'protocol_sha256': sha(args.protocol.read_bytes()),
                'peak_process_rss_mib': round(peak_rss / 1048576, 2),
                'latency_p50_ms': statistics.median(timing),
                'latency_p95_ms': sorted(timing)[int(.95 * (len(timing) - 1))],
                'index_A_source_sha256': rules['index_sha256']['A'],
                'index_B_source_sha256': rules['index_sha256']['B'],
                'blind_leakage': 'PASS_KEYS_AND_RANDOMIZED_ORDER',
                'final_G2_metrics': 'NOT_RUN'}
    (args.out / 'G3U_POOL_MANIFEST.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    return manifest


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dry-run', action='store_true')
    for name in ('registry', 'protocol', 'questions', 'corpus_zip', 'sources', 'c1_ledger',
                 'author_root', 'model_cache', 'index_root', 'out'):
        p.add_argument('--' + name.replace('_', '-'), type=Path)
    a = p.parse_args()
    print(json.dumps(dry_run() if a.dry_run else execute(a), indent=2))

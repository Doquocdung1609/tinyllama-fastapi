"""Structural audit of a sealed pool and blind qrels, without scoring rankings."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path

from scripts.topic3_g3u_pool import FORBIDDEN_BLIND_KEYS, sha
from scripts.topic3_g3u_review_tool import verify_events


def rows(path: Path) -> list[dict]:
    return [json.loads(s) for s in path.read_text(encoding='utf-8').splitlines() if s]


def run(pool_dir: Path, qrel_dir: Path, c1_ledger: Path,
        human_events: Path, out: Path) -> dict:
    if out.exists():
        raise FileExistsError(out)
    pool = json.loads((pool_dir / 'G3U_POOL_MANIFEST.json').read_text(encoding='utf-8'))
    ranked_path = pool_dir / 'G3U_RANKED_POOL_SEALED.jsonl'
    blind_path = pool_dir / 'G3U_BLIND_REVIEW_POOL.jsonl'
    if (pool['status'] != 'POOL_GENERATED_NOT_SCORED' or
            sha(ranked_path.read_bytes()) != pool['ranked_sha256'] or
            sha(blind_path.read_bytes()) != pool['blind_sha256']):
        raise ValueError('Sealed or blind pool hash/status changed')
    ranked, blind = rows(ranked_path), rows(blind_path)
    if len(ranked) != pool['ranked_lines'] or len(blind) != pool['unique_blind_pairs']:
        raise ValueError('Pool line count changed')
    rank_keys, union, arms = set(), set(), defaultdict(set)
    ranks_by_run = defaultdict(set)
    for r in ranked:
        key = (r['question_id'], r['arm'], r['index'], r['rank'])
        if key in rank_keys or not 1 <= r['rank'] <= 20:
            raise ValueError('Duplicate or invalid ranked slot')
        rank_keys.add(key)
        union.add((r['question_id'], r['chunk_id']))
        arms[r['question_id']].add((r['arm'], r['index']))
        ranks_by_run[(r['question_id'], r['arm'], r['index'])].add(r['rank'])
    expected_a = {('AUTHOR_' + x, 'A') for x in
                  ('BM25', 'DENSE', 'SPARSE', 'BM25_DENSE', 'SPARSE_DENSE', 'RERANK')}
    expected_b = {('AUTHOR_' + x, 'B') for x in
                  ('BM25', 'DENSE', 'SPARSE', 'BM25_DENSE', 'SPARSE_DENSE', 'RERANK')}
    expected_a.add(('FAITH_R_A0', 'A'))
    expected_b.update((('FAITH_R_' + x, 'B') for x in ('A1','A2','A3','A4','A4R')))
    expected = expected_a | expected_b
    if (len(arms) != 94 or pool['arm_runs'] != 94 * len(expected) or
            any(not observed <= expected for observed in arms.values()) or
            any(ranks != set(range(1, len(ranks)+1)) for ranks in ranks_by_run.values())):
        raise ValueError('One-shot arm/question/rank structure invalid')
    missing_run_rows = sum(len(expected - observed) for observed in arms.values())
    c1 = {r['question_id']: r for r in rows(c1_ledger)}
    if len(c1) != 94:
        raise ValueError('Original C1 question map incomplete')
    blind_keys = set()
    off_target = 0
    for b in blind:
        key = b['question_id'], b['chunk_id']
        if (key in blind_keys or FORBIDDEN_BLIND_KEYS & set(b) or
                sha(b['original_text'].encode('utf-8')) != b['original_text_sha256']):
            raise ValueError('Blind pool duplicate/leakage/text hash')
        blind_keys.add(key)
        off_target += b['chunk_accession'] != c1[b['question_id']]['accession']
    if blind_keys != union:
        raise ValueError('Blind pool omitted or invented ranked candidate')
    qrel_manifest = json.loads((qrel_dir / 'G3U_QREL_PREPARATION_MANIFEST.json').read_text(encoding='utf-8'))
    qrel_path = qrel_dir / 'G3U_AI_QREL_PROVISIONAL.jsonl'
    queue_path = qrel_dir / 'G3U_HUMAN_CHUNK_REVIEW_QUEUE.jsonl'
    if (sha(qrel_path.read_bytes()) != qrel_manifest['files']['ai']['sha256'] or
            sha(queue_path.read_bytes()) != qrel_manifest['files']['queue']['sha256']):
        raise ValueError('Qrel/queue hash changed')
    qrels, queue = rows(qrel_path), rows(queue_path)
    if len(qrels) != len(blind) or len(queue) != len(blind):
        raise ValueError('Qrel/queue coverage incomplete')
    qrel_keys = set()
    grade = Counter()
    for r in qrels:
        key = r['question_id'], r['chunk_id']
        if (key not in blind_keys or key in qrel_keys or
                r['grade'] not in {'PARTIAL', 'UNJUDGED'} or
                r['graded_value'] != (1 if r['grade'] == 'PARTIAL' else None) or
                r['human_certified'] is not False or r['rank_exposure'] is not False):
            raise ValueError('Provisional qrel identity/grade corrupted')
        qrel_keys.add(key)
        grade[r['grade']] += 1
    if qrel_keys != blind_keys or any(FORBIDDEN_BLIND_KEYS & set(r) for r in queue):
        raise ValueError('Blind queue/qrel mismatch or leakage')
    events = verify_events(human_events)
    result = {'schema': 'g3u_pool_qrel_structural_audit/v1',
              'status': 'PASS_WITH_UNLOGGED_ZERO_RESULT_ARMS' if missing_run_rows else 'PASS',
              'questions': 94, 'arm_runs': pool['arm_runs'],
              'arm_question_pairs_with_ranked_hits': len(ranks_by_run),
              'arm_question_pairs_without_ranked_hits': missing_run_rows,
              'zero_result_provenance_limit': 'Original runner asserted all 1692 executions but did not write individual zero-result run rows; absent hit rows cannot independently prove that the arm ran.',
              'ranked_lines': len(ranked), 'unique_blind_pairs': len(blind),
              'off_target_candidates_retained': off_target,
              'qrel_grades': dict(grade), 'exact': 0, 'none': 0,
              'human_event_count': len(events), 'final_G2_metrics': 'NOT_RUN',
              'ranked_sha256': pool['ranked_sha256'], 'blind_sha256': pool['blind_sha256'],
              'qrel_sha256': qrel_manifest['files']['ai']['sha256'],
              'human_queue_sha256': qrel_manifest['files']['queue']['sha256']}
    out.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for n in ('pool_dir', 'qrel_dir', 'c1_ledger', 'human_events', 'out'):
        p.add_argument('--'+n.replace('_','-'), type=Path, required=True)
    print(json.dumps(run(**vars(p.parse_args())), indent=2))

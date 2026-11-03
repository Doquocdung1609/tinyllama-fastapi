"""Verify source-only original-chunk queue without pretending it is ranked."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path

from scripts.topic3_g3u_pool import FORBIDDEN_BLIND_KEYS, sha
from scripts.topic3_g3u_review_tool import verify_events


def rows(path: Path) -> list[dict]:
    return [json.loads(s) for s in path.read_text(encoding='utf-8').splitlines() if s]


def run(source_dir: Path, qrel_dir: Path, c1_ledger: Path,
        human_events: Path, out: Path) -> dict:
    if out.exists():
        raise FileExistsError(out)
    source_manifest = json.loads((source_dir/'G3U_SOURCE_AUDIT_QUEUE_MANIFEST.json').read_text(encoding='utf-8'))
    qrel_manifest = json.loads((qrel_dir/'G3U_QREL_PREPARATION_MANIFEST.json').read_text(encoding='utf-8'))
    if (source_manifest['status'] != 'SOURCE_AUDIT_QUEUE_NOT_RANKED_POOL' or
            qrel_manifest['input_status'] != source_manifest['status'] or
            qrel_manifest['ranking_metrics'] != 'NOT_COMPUTED'):
        raise ValueError('Source-only queue mislabeled as a ranked pool')
    source_path = source_dir/'G3U_SOURCE_AUDIT_BLIND_POOL.jsonl'
    queue_path = qrel_dir/'G3U_HUMAN_CHUNK_REVIEW_QUEUE.jsonl'
    ai_path = qrel_dir/'G3U_AI_QREL_PROVISIONAL.jsonl'
    if (sha(source_path.read_bytes()) != source_manifest['blind_sha256'] or
            sha(queue_path.read_bytes()) != qrel_manifest['files']['queue']['sha256'] or
            sha(ai_path.read_bytes()) != qrel_manifest['files']['ai']['sha256']):
        raise ValueError('Source queue/qrel SHA-256 changed')
    c1 = {r['question_id']: r for r in rows(c1_ledger)}
    source, queue, ai = rows(source_path), rows(queue_path), rows(ai_path)
    if len(c1) != 94 or len(source) != len(queue) or len(source) != len(ai):
        raise ValueError('Source review cardinality changed')
    source_keys, queue_keys, ai_keys = set(), set(), set()
    grade = Counter()
    for r in source:
        key = (r['question_id'], r['chunk_id'])
        if (key in source_keys or FORBIDDEN_BLIND_KEYS & set(r) or
                r['chunk_accession'] != c1[r['question_id']]['accession'] or
                sha(r['original_text'].encode('utf-8')) != r['original_text_sha256']):
            raise ValueError('Source-only candidate identity/leakage invalid')
        source_keys.add(key)
    for r in queue:
        key = r['question_id'], r['chunk_id']
        if key in queue_keys or FORBIDDEN_BLIND_KEYS & set(r):
            raise ValueError('Human queue duplicated or not blind')
        queue_keys.add(key)
    for r in ai:
        key = r['question_id'], r['chunk_id']
        if (key in ai_keys or r['grade'] not in {'PARTIAL','UNJUDGED'} or
                r['graded_value'] != (1 if r['grade']=='PARTIAL' else None) or
                r['human_certified'] is not False):
            raise ValueError('AI source qrel grade invalid')
        ai_keys.add(key)
        grade[r['grade']] += 1
    if source_keys != queue_keys or source_keys != ai_keys or len(source_keys) != 17340:
        raise ValueError('Question/chunk pairs differ between source, AI and human queue')
    events = verify_events(human_events)
    result = {'schema': 'g3u_source_only_qrel_audit/v1', 'status': 'PASS',
              'questions': 94, 'source_only_pairs': len(source_keys),
              'qrel_grades': dict(grade), 'exact': 0, 'none': 0,
              'human_events': len(events), 'ranked_pool_pairs': 0,
              'off_target_retrieval_judgments': 0,
              'source_queue_sha256': source_manifest['blind_sha256'],
              'ai_qrel_sha256': qrel_manifest['files']['ai']['sha256'],
              'human_queue_sha256': qrel_manifest['files']['queue']['sha256'],
              'final_G2_metrics': 'NOT_RUN'}
    out.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    return result


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('source_dir','qrel_dir','c1_ledger','human_events','out'):
        p.add_argument('--'+n.replace('_','-'), type=Path, required=True)
    print(json.dumps(run(**vars(p.parse_args())), indent=2))

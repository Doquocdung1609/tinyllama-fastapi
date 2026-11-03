"""Publish hash-only G3U status; never copy private answers or ranked hits to Git."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def file_info(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(path)
    return {'sha256': sha(path), 'bytes': path.stat().st_size}


def run(risk: Path, amd: Path, revalidation: Path, partial_dir: Path,
        source_dir: Path, qrel_dir: Path, source_audit: Path, out: Path) -> dict:
    partial = json.loads((partial_dir / 'ABORTED_PROTOCOL_CONFLICT.json').read_text(encoding='utf-8'))
    sealed = partial_dir / 'G3U_RANKED_POOL_SEALED.jsonl'
    source = json.loads((source_dir/'G3U_SOURCE_AUDIT_QUEUE_MANIFEST.json').read_text(encoding='utf-8'))
    qrel = json.loads((qrel_dir/'G3U_QREL_PREPARATION_MANIFEST.json').read_text(encoding='utf-8'))
    audit = json.loads(source_audit.read_text(encoding='utf-8'))
    if (sha(sealed) != partial['sealed_partial_sha256'] or
            source['status'] != 'SOURCE_AUDIT_QUEUE_NOT_RANKED_POOL' or
            qrel['input_status'] != source['status'] or audit['status'] != 'PASS' or
            qrel['pairs'] != audit['source_only_pairs'] or
            qrel['grades'] != audit['qrel_grades']):
        raise ValueError('Private G3U status or hashes do not reconcile')
    files = {
        'risk_overlay': risk, 'amd_diagnosis': amd, 'g3t_revalidation': revalidation,
        'partial_run_started': partial_dir/'RUN_STARTED.json',
        'partial_sealed_ranked_log': sealed,
        'partial_abort_record': partial_dir/'ABORTED_PROTOCOL_CONFLICT.json',
        'source_audit_blind_queue': source_dir/'G3U_SOURCE_AUDIT_BLIND_POOL.jsonl',
        'source_audit_queue_manifest': source_dir/'G3U_SOURCE_AUDIT_QUEUE_MANIFEST.json',
        'source_only_ai_qrels': qrel_dir/'G3U_AI_QREL_PROVISIONAL.jsonl',
        'source_only_human_queue': qrel_dir/'G3U_HUMAN_CHUNK_REVIEW_QUEUE.jsonl',
        'source_only_challenge_queue': qrel_dir/'G3U_QREL_CHALLENGE_QUEUE.jsonl',
        'source_only_qrel_manifest': qrel_dir/'G3U_QREL_PREPARATION_MANIFEST.json',
        'source_only_validation': source_audit,
    }
    manifest = {'schema': 'g3u_private_hash_audit/v1',
                'location': 'OWNER_MACHINE_DOWNLOADS_OUTSIDE_GIT',
                'private_value_or_rank_bearing': True,
                'files': {name: {'filename': path.name, **file_info(path)} for name,path in files.items()},
                'full_ranked_pool': 'NOT_GENERATED',
                'partial_ranked_pool': 'ABORTED_PROTOCOL_CONFLICT',
                'human_events': 0}
    pool_status = {'schema': 'g3u_pool_status/v1',
                   'status': 'POOL_PARTIAL_ABORTED_PROTOCOL_CONFLICT',
                   'partial_ranked_lines': partial['sealed_partial_lines'],
                   'partial_question_arm_index_runs': partial['distinct_question_arm_index_runs'],
                   'expected_full_runs': partial['expected_full_runs'],
                   'complete_ranked_pool_pairs': 0,
                   'blind_mixed_arm_pool_pairs': 0,
                   'source_only_target_filing_pairs': source['unique_blind_pairs'],
                   'source_only_is_ranked_pool': False,
                   'per_hit_scores_inspected_by_coordinator': False,
                   'final_quality_metrics': 'NOT_RUN'}
    coverage = {'schema': 'g3u_qrel_coverage/v1',
                'questions': 94, 'source_only_original_chunk_pairs': qrel['pairs'],
                'source_only_grades': qrel['grades'],
                'ranked_blind_pool_pairs': 0,
                'ranked_pool_qrel_grades': {'EXACT': 0, 'PARTIAL': 0, 'NONE': 0, 'UNJUDGED': 0},
                'source_only_exact': 0, 'source_only_none': 0,
                'human_chunk_decisions': 0,
                'off_target_retrieval_coverage': 'NOT_ASSESSED',
                'retrieval_quality_scoring': 'BLOCKED'}
    out.mkdir(parents=True, exist_ok=True)
    for name, obj in [('G3U_PRIVATE_HASH_AUDIT.json', manifest),
                      ('G3U_POOL_STATUS.json', pool_status),
                      ('G3U_QREL_COVERAGE.json', coverage)]:
        path = out / name
        if path.exists():
            raise FileExistsError(path)
        path.write_text(json.dumps(obj, indent=2)+'\n', encoding='utf-8')
    return {'private_file_count': len(files),
            'private_manifest_sha256': sha(out/'G3U_PRIVATE_HASH_AUDIT.json'),
            'pool_status': pool_status['status'], 'source_only_pairs': qrel['pairs']}


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('risk','amd','revalidation','partial_dir','source_dir','qrel_dir','source_audit','out'):
        p.add_argument('--'+n.replace('_','-'), type=Path, required=True)
    print(json.dumps(run(**vars(p.parse_args())), indent=2))

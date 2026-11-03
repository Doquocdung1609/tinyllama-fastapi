"""Publish redacted approved-v2 pool/qrel facts after independent verification."""

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
    return {'filename': path.name, 'sha256': sha(path), 'bytes': path.stat().st_size}


def run(pool_dir: Path, qrel_dir: Path, verification: Path,
        partial_dir: Path, source_dir: Path, source_qrel_dir: Path,
        risk: Path, amd: Path, out: Path) -> dict:
    pool = json.loads((pool_dir/'G3U_POOL_MANIFEST.json').read_text(encoding='utf-8'))
    qrel = json.loads((qrel_dir/'G3U_QREL_PREPARATION_MANIFEST.json').read_text(encoding='utf-8'))
    verified = json.loads(verification.read_text(encoding='utf-8'))
    partial = json.loads((partial_dir/'ABORTED_PROTOCOL_CONFLICT.json').read_text(encoding='utf-8'))
    if (pool['status'] != 'POOL_GENERATED_NOT_SCORED' or pool['arm_runs'] != 1692 or
            qrel['input_status'] != pool['status'] or
            verified['status'] not in {'PASS','PASS_WITH_UNLOGGED_ZERO_RESULT_ARMS'} or
            verified['unique_blind_pairs'] != pool['unique_blind_pairs'] or
            qrel['pairs'] != pool['unique_blind_pairs'] or
            pool['registry_sha256'] != 'eddef050ac78b1184d4fa311ffbf1758ae7f458940483a412f8d69271aad1f76' or
            partial['status'] != 'PARTIAL_ABORTED_PROTOCOL_RRF_CONSTANT_MISMATCH'):
        raise ValueError('Approved v2 pool/qrel audit does not reconcile')
    files = {
        'approved_pool_started': pool_dir/'RUN_STARTED.json',
        'approved_sealed_ranked_log': pool_dir/'G3U_RANKED_POOL_SEALED.jsonl',
        'approved_blind_review_pool': pool_dir/'G3U_BLIND_REVIEW_POOL.jsonl',
        'approved_pool_manifest': pool_dir/'G3U_POOL_MANIFEST.json',
        'approved_ai_qrel': qrel_dir/'G3U_AI_QREL_PROVISIONAL.jsonl',
        'approved_human_queue': qrel_dir/'G3U_HUMAN_CHUNK_REVIEW_QUEUE.jsonl',
        'approved_challenge_queue': qrel_dir/'G3U_QREL_CHALLENGE_QUEUE.jsonl',
        'approved_qrel_manifest': qrel_dir/'G3U_QREL_PREPARATION_MANIFEST.json',
        'approved_structural_verification': verification,
        'aborted_partial_ranked_log': partial_dir/'G3U_RANKED_POOL_SEALED.jsonl',
        'aborted_partial_record': partial_dir/'ABORTED_PROTOCOL_CONFLICT.json',
        'source_only_blind_queue': source_dir/'G3U_SOURCE_AUDIT_BLIND_POOL.jsonl',
        'source_only_ai_qrel': source_qrel_dir/'G3U_AI_QREL_PROVISIONAL.jsonl',
        'risk_overlay': risk, 'amd_original_chunk_diagnosis': amd}
    details = {name: file_info(path) for name, path in files.items()}
    if (details['approved_sealed_ranked_log']['sha256'] != pool['ranked_sha256'] or
            details['approved_blind_review_pool']['sha256'] != pool['blind_sha256'] or
            details['approved_ai_qrel']['sha256'] != qrel['files']['ai']['sha256'] or
            details['approved_human_queue']['sha256'] != qrel['files']['queue']['sha256']):
        raise ValueError('Approved v2 private bytes differ from manifests')
    private = {'schema': 'g3u_private_hash_audit/v2',
               'location': 'OWNER_MACHINE_DOWNLOADS_OUTSIDE_GIT',
               'contains_private_rank_or_answer_values': True,
               'files': details, 'human_events': 0,
               'final_G2_scores': 'NOT_RUN'}
    public_pool = {'schema': 'g3u_approved_pool_status/v2',
                   'status': pool['status'], 'owner_approved_protocol': True,
                   'prior_partial_exposure': 'DISCLOSED_NOT_TUNED',
                   'question_count': 94, 'arm_runs': pool['arm_runs'],
                   'arm_question_pairs_without_ranked_hits': verified['arm_question_pairs_without_ranked_hits'],
                   'ranked_lines': pool['ranked_lines'],
                   'unique_blind_pairs': pool['unique_blind_pairs'],
                   'off_target_candidates_retained': verified['off_target_candidates_retained'],
                   'blind_leakage': verified['status'],
                   'ranked_sha256': pool['ranked_sha256'],
                   'blind_sha256': pool['blind_sha256'],
                   'registry_sha256': pool['registry_sha256'],
                   'protocol_sha256': pool['protocol_sha256'],
                   'peak_process_rss_mib': pool['peak_process_rss_mib'],
                   'latency_p50_ms': pool['latency_p50_ms'],
                   'latency_p95_ms': pool['latency_p95_ms'],
                   'final_quality_metrics': 'NOT_RUN'}
    public_qrel = {'schema': 'g3u_approved_pool_qrel_coverage/v2',
                   'question_count': qrel['question_count'],
                   'ranked_blind_pairs': qrel['pairs'],
                   'ai_provisional_grades': qrel['grades'],
                   'exact': 0, 'none': 0, 'human_chunk_events': 0,
                   'source_only_queue_pairs_separate': 17340,
                   'original_single_chunk': True,
                   'ranked_pool_complete_judgment': False,
                   'tier_A': 'BLOCKED_NO_EXACT_AND_INCOMPLETE_QRELS',
                   'tier_H': 'BLOCKED_NO_HUMAN_APPROVAL',
                   'final_G2_scoring': 'NOT_RUN'}
    out.mkdir(parents=True, exist_ok=True)
    for name, value in [('G3U_PRIVATE_HASH_AUDIT_V2_APPROVED.json', private),
                        ('G3U_POOL_STATUS_V2_APPROVED.json', public_pool),
                        ('G3U_RANKED_QREL_COVERAGE_V2_APPROVED.json', public_qrel)]:
        path = out/name
        if path.exists():
            raise FileExistsError(path)
        path.write_text(json.dumps(value, indent=2)+'\n', encoding='utf-8')
    return {'private_files': len(files), 'pool_pairs': pool['unique_blind_pairs'],
            'qrel_grades': qrel['grades'],
            'private_manifest_sha256': sha(out/'G3U_PRIVATE_HASH_AUDIT_V2_APPROVED.json')}


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('pool_dir','qrel_dir','verification','partial_dir','source_dir',
              'source_qrel_dir','risk','amd','out'):
        p.add_argument('--'+n.replace('_','-'), type=Path, required=True)
    print(json.dumps(run(**vars(p.parse_args())), indent=2))

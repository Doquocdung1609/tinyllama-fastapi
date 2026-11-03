"""Adversarial G3T integrity checks; fixtures never use sealed G2 rankings."""

import copy
import json
from pathlib import Path

import pytest

from scripts.topic3_g3t_validate import (
    synthetic_cluster_bootstrap,
    verify_ai_chain,
    verify_human_import,
)


def _ledger():
    from scripts.topic3_g3t_validate import canonical, sha

    records, previous = [], 'GENESIS'
    for i in range(94):
        body = {
            'question_id': f'fixture_{i:02d}',
            'previous_record_sha256': previous,
            'reviewer_type': 'AI_ASSISTED_SOURCE_FIRST',
            'human_approval_status': 'PENDING',
            'protocol_sha256': 'policy',
            'c1_ledger_sha256': 'c1',
        }
        record = {**body, 'record_sha256': sha(canonical(body))}
        records.append(record)
        previous = record['record_sha256']
    return records


def test_valid_ai_chain_and_tamper_rejected():
    records = _ledger()
    verify_ai_chain(records, 'policy', 'c1')
    tampered = copy.deepcopy(records)
    tampered[20]['human_approval_status'] = 'APPROVED'
    with pytest.raises(ValueError):
        verify_ai_chain(tampered, 'policy', 'c1')


def test_duplicate_or_missing_ai_questions_rejected():
    records = _ledger()
    with pytest.raises(ValueError):
        verify_ai_chain(records[:-1], 'policy', 'c1')
    duplicate = copy.deepcopy(records)
    duplicate[1]['question_id'] = duplicate[0]['question_id']
    with pytest.raises(ValueError):
        verify_ai_chain(duplicate, 'policy', 'c1')


def test_human_import_refuses_ai_path_and_forged_schema(tmp_path: Path):
    from scripts.topic3_v7a_g3s_review_tool import event_hash
    dataset = tmp_path / 'dataset.json'
    dataset.write_text(json.dumps({'records': [{'question_id': 'fixture_01'}]}), encoding='utf-8')
    ai = tmp_path / 'ai.jsonl'
    ai.write_text('', encoding='utf-8')
    with pytest.raises(ValueError):
        verify_human_import(ai, dataset, ai)

    from scripts.topic3_g3t_validate import sha
    body = {'question_id': 'fixture_01', 'event_id': 'forged', 'decision': 'APPROVE',
            'evidence_sha256': sha(dataset.read_bytes()), 'reviewer_type': 'AI_ASSISTED_SOURCE_FIRST',
            'previous_event_sha256': 'GENESIS'}
    events = tmp_path / 'human.jsonl'
    events.write_text(json.dumps({**body, 'event_sha256': event_hash(body)}) + '\n', encoding='utf-8')
    with pytest.raises(ValueError):
        verify_human_import(events, dataset, ai)


def test_synthetic_dry_run_is_deterministic_and_non_g2():
    a = synthetic_cluster_bootstrap()
    assert a == synthetic_cluster_bootstrap()
    assert a['fixture'].endswith('NOT_G2')
    assert a['mean'] == 0.625

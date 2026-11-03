"""G3U blind-pool and label-boundary adversarial fixtures."""

import copy
import hashlib
import json
from pathlib import Path
import zipfile

import pytest

from scripts.topic3_g3u_amd import classify_chunk_evidence, row_hit, value_hit
from scripts.topic3_g3u_pool import assert_rrf_fidelity, blind_union, dry_run, native_stage2_budget
from scripts.topic3_g3u_qrels import challenge_one_chunk
from scripts.topic3_g3u_review_tool import canonical, sha, validate, verify_events
from scripts.topic3_g3u_risk import strict_exact_candidates, verify_handoff
from scripts.topic3_g3u_v7b_harness import judged_bounds, synthetic


def test_stage2_native_budget_separate_from_depth20():
    assert native_stage2_budget(10) == 30
    assert native_stage2_budget(20) == 60
    with pytest.raises(ValueError, match='POOL_NOT_RUN_PROTOCOL_CONFLICT'):
        assert_rrf_fidelity(60, 2)


def test_amd_value_normalization_and_split_row_not_exact():
    assert value_hit('Data Center | $ 3,240', '3240')
    assert value_hit('Data Center | 3 240', '3240')
    assert not value_hit('Data Center | $ 13,240', '3240')
    assert not value_hit('Data Center only', '3240')
    assert row_hit('Segment Data Center revenue', 'Data Center')
    assert not row_hit('Data in one chunk, Center elsewhere', 'Data Center')
    filing = [{'section': 'Part II - Item 1A. Risk Factors'} for _ in range(3)]
    assert classify_chunk_evidence(filing, [0], [1], []) == 'CHUNK_SPLIT_EVIDENCE'
    assert classify_chunk_evidence(filing, [0], [0], [0]) == 'EVIDENCE_PRESENT_NEEDS_MANUAL_QREL'
    assert classify_chunk_evidence(filing, [0], [], []) == 'SOURCE_PRESENT_CORPUS_CHUNK_MISSING'


def test_strict_exact_holds_two_scope_conflicts():
    c1 = {qid: {'c1_outcome': 'SOURCE_FACT_VERIFIED_BUT_QUESTION_SCOPE_PENDING'}
          for qid in ('V7A_G2_12_02', 'V7A_G2_15_01')}
    c2 = [{'question_id': qid, 'technical_label': 'AI_SUPPORTED_EXACT'} for qid in c1]
    c2.append({'question_id': 'safe', 'technical_label': 'AI_SUPPORTED_EXACT'})
    assert strict_exact_candidates(c1, c2) == {'safe'}
    c1['V7A_G2_12_02']['c1_outcome'] = 'SOURCE_CELL_VERIFIED'
    with pytest.raises(ValueError):
        strict_exact_candidates(c1, c2)


def test_blind_union_retains_off_target_and_hides_output_signals():
    assert dry_run()['off_target_candidate_retained']
    chunks = {'x': {'document_id': 'A_001', 'text': 'one', 'text_hash': 'h',
                    'ticker': 'A', 'section': 's'}}
    source = {'001': {'source_url': 'https://example.test', 'sha256': 'source'}}
    rows = blind_union([{'question_id': 'q', 'chunk_id': 'x', 'arm': 'SPLADE',
                         'rank': 1, 'raw_score': 100}], chunks, {'q': 'query'}, source, 3)
    assert len(rows) == 1
    assert {'arm', 'rank', 'raw_score', 'method', 'model'}.isdisjoint(rows[0])
    with pytest.raises(ValueError):
        blind_union([{'question_id': 'q', 'chunk_id': 'unknown'}], chunks,
                    {'q': 'query'}, source, 3)


def test_row_value_signal_stays_partial_and_unknown_stays_unknown():
    chunk = {'original_text': 'Data Center | $3,240', 'chunk_accession': 'a'}
    source = {'accession': 'a', 'source_cells': [{'row': 'Data Center',
              'value_decimal': '3240', 'period': 'Three months 2025', 'scale': 'millions'}]}
    result = challenge_one_chunk(chunk, source)
    assert result['provisional_grade'] == 'PARTIAL'
    assert result['exact_claim'] is False and result['none_claim'] is False
    assert result['cell_checks'][0]['scale_text_present'] is False
    off = copy.copy(chunk)
    off['chunk_accession'] = 'b'
    assert challenge_one_chunk(off, source)['provisional_grade'] == 'UNJUDGED'


def test_human_review_rejects_ai_and_missing_ack():
    queue = {('q', 'x'): {'original_text_sha256': 'text'}}
    payload = {'question_id': 'q', 'chunk_id': 'x', 'queue_sha256': 'queue',
               'decision': 'EXACT', 'reviewer': 'Human',
               'reason': 'I checked every mandatory element in this original chunk.',
               'evidence_reference': 'https://example.test/source#x',
               'human_interaction_ack': False}
    with pytest.raises(ValueError):
        validate(payload, queue, 'queue')
    payload['human_interaction_ack'] = True
    payload['reviewer_type'] = 'AI_QREL_PROVISIONAL_DETERMINISTIC_RULES'
    with pytest.raises(ValueError):
        validate(payload, queue, 'queue')


def test_non_scoring_v7b_wiring_keeps_unknown_sensitivity():
    result = judged_bounds(['a', 'b'], {'a': 2, 'b': None}, 2)
    assert result['assessed'] == 1 and result['unknown'] == 1
    assert result['pessimistic_exact_share'] == .5
    assert result['optimistic_exact_share'] == 1.0
    assert synthetic()['real_G2_score'] == 'NOT_RUN'


def test_handoff_crc_member_hash_and_tamper(tmp_path: Path):
    manifest = {'files': {'C1': {}, 'C2': {}, 'C3': {}}}
    archive = tmp_path / 'handoff.zip'
    review = b'{"fixture":true}'
    with zipfile.ZipFile(archive, 'w') as out:
        for index in range(17):
            name = f'member_{index}.json'
            content = f'fixture-{index}'.encode()
            group = ('C1', 'C2', 'C3')[index % 3]
            manifest['files'][group][name] = {'bytes': len(content),
                                              'sha256': hashlib.sha256(content).hexdigest()}
            out.writestr(f'group/{name}', content)
        out.writestr('G3T_HUMAN_REVIEW_INPUT_20261103_V2.json', review)
    metadata = tmp_path / 'manifest.json'
    metadata.write_text(json.dumps(manifest), encoding='utf-8')
    assert verify_handoff(archive, metadata, hashlib.sha256(review).hexdigest())['entries'] == 18
    manifest['files']['C1']['member_0.json']['sha256'] = 'bad'
    metadata.write_text(json.dumps(manifest), encoding='utf-8')
    with pytest.raises(ValueError):
        verify_handoff(archive, metadata, hashlib.sha256(review).hexdigest())


def test_human_chunk_event_chain_rejects_tamper(tmp_path: Path):
    body = {'event_id': 'synthetic-fixture', 'previous_event_sha256': 'GENESIS',
            'reviewer_type': 'HUMAN_SELF_DECLARED', 'decision': 'PARTIAL'}
    event = {**body, 'event_sha256': sha(canonical(body))}
    path = tmp_path / 'events.jsonl'
    path.write_text(json.dumps(event) + '\n', encoding='utf-8')
    assert len(verify_events(path)) == 1
    event['decision'] = 'EXACT'
    path.write_text(json.dumps(event) + '\n', encoding='utf-8')
    with pytest.raises(ValueError):
        verify_events(path)

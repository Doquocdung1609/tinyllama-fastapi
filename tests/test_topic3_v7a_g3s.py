import hashlib
import json
from pathlib import Path
import zipfile

from lxml import html
import pytest

from scripts.topic3_v7a_g3s_attest import attest
from scripts.topic3_v7a_g3s_evidence import (
    choose_candidate, currency_compatible, source_cell_candidates,
    typed_ai_cells,
)
from scripts.topic3_v7a_g3s_review_tool import (
    append_event, release_preview, verify_events,
)
from scripts.topic3_v7a_g3s_sources import index_identity


def test_sec_6k_index_identity_and_wrong_primary():
    index = b'<html><body>Form 6-K - Foreign private issuer SEC Accession No. 0001046179-25-000140 '
    index += b'tsmcazagm20251219_6k.htm</body></html>'
    good = index_identity(index, '0001046179-25-000140', 'tsmcazagm20251219_6k.htm', '6-K')
    assert all(good[k] for k in ('form_matches', 'accession_present', 'primary_filename_present'))
    assert not index_identity(index, '0001046179-25-000140', 'other.htm', '6-K')['primary_filename_present']


def test_typed_comparative_cells_reject_year_swap_and_scale_change():
    a = [{'column_header': 'FY ended 2025-12-31', 'exact_value': '100', 'currency': 'USD', 'scale': 'millions'},
         {'column_header': 'FY ended 2024-12-31', 'exact_value': '90', 'currency': 'USD', 'scale': 'millions'}]
    b = [{'period_label': 'FY2025', 'numeric_value': 100, 'currency': 'USD', 'scale': 1000000},
         {'period_label': 'FY2024', 'numeric_value': 90, 'currency': 'USD', 'scale': 1000000}]
    assert typed_ai_cells(a, b)[0] == 'FULL_AI_CELL_MAPPING'
    assert typed_ai_cells(a, [{**b[0], 'numeric_value': 90}, {**b[1], 'numeric_value': 100}])[0] == 'VALUE_PERIOD_OR_CURRENCY_CONFLICT'
    assert typed_ai_cells(a, [{**b[0], 'scale': 1000}, b[1]])[0] == 'VALUE_PERIOD_OR_CURRENCY_CONFLICT'
    assert typed_ai_cells(a[:1], b)[0] == 'A2_HAS_ADDITIONAL_CELLS'
    assert currency_compatible('percent of total net revenue', 'NOT_APPLICABLE', 'percent')


def test_source_cell_grid_distinguishes_three_months_from_nine_months():
    source = html.fromstring('''<html><body><table>
      <tr><th></th><th colspan="2">Three Months Ended</th><th colspan="2">Nine Months Ended</th></tr>
      <tr><th></th><th>2025</th><th>2024</th><th>2025</th><th>2024</th></tr>
      <tr><td>Research and development</td><td>8,198</td><td>7,653</td><td>23,659</td><td>21,454</td></tr>
      </table></body></html>''')
    cell = {'row_label': 'Research and development',
            'column_header': 'Three months ended 2025-03-31', 'exact_value': '8,198'}
    candidates = source_cell_candidates(source, cell)
    assert choose_candidate(candidates)[0] == 'SOURCE_CELL_REVALIDATED'
    assert candidates[0]['year_column_bound'] and candidates[0]['duration_column_bound']
    assert source_cell_candidates(source, {**cell, 'exact_value': '23,659'})[0]['duration_column_bound'] is False


def test_detached_attestation_preserves_stale_self_hash_warning(tmp_path: Path):
    path = tmp_path / 'agent2.zip'
    data = b'example evidence'
    manifest = {'artifact_sha256': {'data.csv': hashlib.sha256(data).hexdigest(),
                                    'AGENT2_G3_POST_SOURCE_FREEZE_MANIFEST.json': '0' * 64,
                                    'SHA256SUMS.txt': '1' * 64}}
    manifest_bytes = json.dumps(manifest).encode()
    sums = (hashlib.sha256(data).hexdigest() + '  data.csv\n' +
            hashlib.sha256(manifest_bytes).hexdigest() + '  AGENT2_G3_POST_SOURCE_FREEZE_MANIFEST.json\n').encode()
    with zipfile.ZipFile(path, 'w') as z:
        z.writestr('data.csv', data)
        z.writestr('AGENT2_G3_POST_SOURCE_FREEZE_MANIFEST.json', manifest_bytes)
        z.writestr('SHA256SUMS.txt', sums)
    result = attest(path)
    assert result['zip_crc'] == 'PASS'
    assert len(result['self_reference_warnings']) == 2
    assert result['verified_data_member_sha256']['data.csv'] == hashlib.sha256(data).hexdigest()


def test_human_event_chain_and_release_preview_do_not_auto_approve(tmp_path: Path):
    dataset = {'evidence_sha256': 'a' * 64, 'records': [
        {'question_id': 'q1', 'accession': 'accession', 'source_sha256': 'b' * 64,
         'question_validity_flag': '', 'source_evidence_level': 'SOURCE_CELL_REVALIDATED',
         'candidate_cells': [{'value_as_printed': '100'}]},
        {'question_id': 'q2', 'accession': 'accession2', 'source_sha256': 'c' * 64,
         'question_validity_flag': 'REVIEW_WORDING', 'source_evidence_level': 'UNRESOLVED',
         'candidate_cells': []},
        {'question_id': 'q3', 'accession': 'accession3', 'source_sha256': 'd' * 64,
         'question_validity_flag': '', 'source_evidence_level': 'SOURCE_EVIDENCE_PARTIAL_REVIEW_REQUIRED',
         'candidate_cells': []}]}
    path = tmp_path / 'synthetic_events.jsonl'
    assert release_preview(dataset, path)['approved_count'] == 0
    payload = {'question_id': 'q1', 'decision': 'APPROVE', 'reviewer': 'Fixture Reviewer',
               'explanation': 'Synthetic source cell checked', 'evidence_reference': 'xpath=/html/body/table/tr[2]',
               'evidence_sha256': 'a' * 64, 'human_interaction_ack': True}
    append_event(path, payload, dataset)
    assert len(verify_events(path)) == 1
    assert release_preview(dataset, path)['approved_count'] == 1
    append_event(path, {**payload, 'question_id': 'q3'}, dataset)
    preview = release_preview(dataset, path)
    assert preview['approved_count'] == 1
    assert preview['blocked'] == [{'question_id': 'q3', 'reason': 'STRUCTURED_SOURCE_EVIDENCE_REQUIRED',
                                   'event_sha256': verify_events(path)[-1]['event_sha256']}]
    with pytest.raises(ValueError):
        append_event(path, {**payload, 'question_id': 'q2', 'human_interaction_ack': False}, dataset)
    path.write_text(path.read_text().replace('Fixture Reviewer', 'Tampered Reviewer'))
    with pytest.raises(ValueError):
        verify_events(path)


def test_frozen_g2_and_v6_manifests_match_pinned_content():
    root = Path(__file__).resolve().parents[1]
    g2 = root / 'docs/topic3_v7a_g2/V7A_SEC47_PRIVATE_SOURCE_MANIFEST.csv'
    v6 = root / 'docs/topic3_v6/V6_ALGORITHM_FREEZE_MANIFEST.json'
    assert hashlib.sha256(g2.read_bytes()).hexdigest() == '46c0d0a0fed423ba373afab075b1952a6a0d3da85041c0f5b0f626585bbebaa6'
    assert json.loads(v6.read_text(encoding='utf-8'))['corpus_sha256'] == '7c6852a8c68ed1c64194c2da9339fbb4719482949e5705596499db53114abb1f'

"""Compare two frozen G3 AI ledgers without certifying gold or running retrieval.

Detailed per-question values are written only to a local coordinator directory.
The public summary contains counts and dispute IDs, not answer values.
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from decimal import Decimal, InvalidOperation
import hashlib
import io
import json
from pathlib import Path
import re
import zipfile


ROOT = Path(__file__).resolve().parents[1]
G2_PUBLIC = ROOT / 'docs/topic3_v7a_g2/V7A_SEC47_QUESTION_ONLY.csv'
G2_SOURCE = ROOT / 'docs/topic3_v7a_g2/V7A_SEC47_PRIVATE_SOURCE_MANIFEST.csv'
A1_LEDGER = 'AGENT1_G3_SECOND_PASS_SOURCE_EVIDENCE_LEDGER.jsonl'
A2_LEDGER = 'AGENT2_G3_HARDENED_VERIFICATION_LEDGER_V2.csv'
A2_CONTRACT = 'AGENT2_G3_FINANCIAL_EVIDENCE_CONTRACT_V2.csv'


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def csv_rows(data: bytes) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(data.decode('utf-8-sig'))))


def csv_bytes(rows: list[dict[str, object]]) -> bytes:
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode('utf-8')


def clean(s: object) -> str:
    return ' '.join(re.findall(r'[a-z0-9]+', str(s or '').lower()))


def decimal_value(value: object) -> Decimal | None:
    value = str(value or '').strip().replace(',', '')
    if value.startswith('(') and value.endswith(')'):
        value = '-' + value[1:-1]
    try:
        return Decimal(value)
    except InvalidOperation:
        return None


def values_a1(row: dict[str, object]) -> list[dict[str, object]]:
    cells = row.get('second_pass_cells') if row.get('G3_review_round') == 'SECOND_PASS' else row.get('cells')
    return cells if isinstance(cells, list) else []


def values_a2(row: dict[str, str]) -> list[dict[str, object]]:
    result = json.loads(row.get('numeric_cells_json') or '[]')
    return result if isinstance(result, list) else []


def value_relation(a: list[dict[str, object]], b: list[dict[str, object]]) -> str:
    va = {v for v in (decimal_value(x.get('exact_value')) for x in a) if v is not None}
    vb = {v for v in (decimal_value(x.get('numeric_value')) for x in b) if v is not None}
    if va and vb:
        if va == vb:
            return 'SAME_NUMERIC_TOKEN_SET_PERIOD_NOT_CERTIFIED'
        if va & vb:
            return 'PARTIAL_NUMERIC_TOKEN_OVERLAP'
        return 'DISJOINT_NUMERIC_TOKEN_SETS'
    if va or vb:
        return 'ONE_SIDED_STRUCTURED_NUMERIC'
    return 'NO_STRUCTURED_NUMERIC_COMPARISON'


def text_relation(a: object, b: object) -> str:
    ca, cb = clean(a), clean(b)
    if not ca or not cb:
        return 'INSUFFICIENT_TEXT'
    if ca == cb:
        return 'EXACT_NORMALIZED_TEXT'
    if ca in cb or cb in ca:
        return 'CONTAINMENT_REVIEW_SCOPE'
    return 'DIFFERENT_TEXT_REVIEW_REQUIRED'


def date_relation(a: object, b: object) -> str:
    da = set(re.findall(r'\d{4}-\d{2}-\d{2}', str(a or '')))
    db = set(re.findall(r'\d{4}-\d{2}-\d{2}', str(b or '')))
    if not da or not db:
        return 'PERIOD_DATE_UNCOMPARABLE'
    if da == db:
        return 'SAME_DATE_SET_DURATION_NOT_CERTIFIED'
    if da < db:
        return 'A2_HAS_EXTRA_DATES'
    if db < da:
        return 'A1_HAS_EXTRA_DATES'
    return 'PERIOD_DATE_CONFLICT'


def unit_relation(currency_a: object, scale_a: object, currency_b: object, scale_b: object) -> str:
    sa, sb = clean(scale_a), clean(scale_b)
    ca, cb = clean(currency_a), clean(currency_b)
    if not sa or not sb:
        return 'UNIT_NOT_COMPARABLE'
    if sa != sb:
        return 'SCALE_TEXT_DIFFERS'
    if ca == cb:
        return 'SAME_CURRENCY_AND_SCALE_TEXT'
    if sa in ('percent', 'percentage') and ('percent' in ca or not ca) and cb in ('not applicable', 'na', ''):
        return 'PERCENT_WITH_NO_CURRENCY_COMPATIBLE'
    return 'CURRENCY_TEXT_DIFFERS'


def status_a1(row: dict[str, object]) -> str:
    if row.get('G3_review_round') == 'SECOND_PASS':
        return str(row.get('second_pass_status'))
    decision = str(row.get('decision'))
    return 'AMBIGUOUS' if decision.startswith('AMBIGUOUS') else decision


def validate_zip(z: zipfile.ZipFile, expected_hashes: dict[str, str]) -> None:
    if z.testzip() is not None:
        raise ValueError('ZIP CRC failed')
    for name, expected in expected_hashes.items():
        if name not in z.namelist() or sha(z.read(name)) != expected:
            raise ValueError(f'Frozen output hash mismatch: {name}')


def compare(a1_path: Path, a2_path: Path, a1_first_path: Path,
            a2_round1_path: Path, source_manifest: Path, output_dir: Path) -> dict[str, object]:
    if output_dir.exists():
        raise FileExistsError(f'Refusing to overwrite private coordinator output: {output_dir}')
    g2 = {r['question_id']: r for r in csv_rows(G2_PUBLIC.read_bytes())}
    g2_source = {r['question_id']: r for r in csv_rows(G2_SOURCE.read_bytes())}
    source = json.loads(source_manifest.read_text(encoding='utf-8'))
    source_by_acc = {r['accession']: r for r in source['sources'] if r.get('identity_pass')}
    with zipfile.ZipFile(a1_path) as z1, zipfile.ZipFile(a2_path) as z2, \
            zipfile.ZipFile(a1_first_path) as z1_first, zipfile.ZipFile(a2_round1_path) as z2_round1:
        m1 = json.loads(z1.read('AGENT1_G3_SECOND_PASS_MANIFEST.json'))
        m2 = json.loads(z2.read('AGENT2_G3_EVIDENCE_FREEZE_MANIFEST_V2.json'))
        m1_first = json.loads(z1_first.read('AGENT1_G3_AUDIT_MANIFEST.json'))
        validate_zip(z1, m1['output_sha256'])
        validate_zip(z2, m2['output_sha256'])
        validate_zip(z1_first, m1_first['output_sha256'])
        if z2_round1.testzip() is not None:
            raise ValueError('Agent 2 round1 ZIP CRC failed')
        if sha(a1_first_path.read_bytes()) != m1['first_pass_zip_sha256']:
            raise ValueError('Agent 1 first-pass ZIP does not match second-pass manifest')
        if sha(a2_round1_path.read_bytes()) != m2['inputs_sha256']['G3_ROUND1_VERIFICATION_CHECKPOINT.zip']:
            raise ValueError('Agent 2 round1 ZIP does not match V2 manifest')
        if z2.read('immutable_round1/AGENT2_G3_94_VERIFICATION_LEDGER_ROUND1_UNMODIFIED.csv') != z2_round1.read('AGENT2_G3_94_VERIFICATION_LEDGER.csv'):
            raise ValueError('Agent 2 round1 ledger was not preserved byte-for-byte')
        if z2.read('immutable_round1/AGENT2_G3_FINANCIAL_CELL_EVIDENCE_ROUND1_UNMODIFIED.jsonl') != z2_round1.read('AGENT2_G3_FINANCIAL_CELL_EVIDENCE.jsonl'):
            raise ValueError('Agent 2 round1 evidence was not preserved byte-for-byte')
        expected_q = sha(G2_PUBLIC.read_bytes())
        if m1['question_only_sha256'] != expected_q or m2['inputs_sha256']['G2_QUESTION_ONLY.csv'] != expected_q:
            raise ValueError('Agents used different G2 question bytes')
        a1 = {r['question_id']: r for r in (json.loads(x) for x in z1.read(A1_LEDGER).decode('utf-8-sig').splitlines() if x.strip())}
        a1_first = {r['question_id']: r for r in (json.loads(x) for x in z1_first.read('AGENT1_G3_SOURCE_EVIDENCE_LEDGER.jsonl').decode('utf-8-sig').splitlines() if x.strip())}
        a2 = {r['question_id']: r for r in csv_rows(z2.read(A2_LEDGER))}
        contract = {r['question_id']: r for r in csv_rows(z2.read(A2_CONTRACT))}
    carried = [qid for qid, row in a1.items() if row['G3_review_round'] == 'FIRST_PASS_CARRIED_FORWARD_UNCHANGED']
    if len(carried) != 32 or set(a1_first) != set(a1):
        raise ValueError('Agent 1 carried-forward row set invalid')
    for qid in carried:
        for key in set(a1_first[qid]) & set(a1[qid]):
            if a1_first[qid][key] != a1[qid][key]:
                raise ValueError(f'Agent 1 first-pass evidence changed: {qid}/{key}')
    if not (len(g2) == len(g2_source) == 94):
        raise ValueError('G2 count invalid')
    if set(a1) != set(a2) or set(a1) != set(contract) or set(a1) != set(g2):
        raise ValueError('Question ID sets differ')
    rows: list[dict[str, object]] = []
    disputes: list[dict[str, object]] = []
    source_queue: list[dict[str, object]] = []
    for qid in sorted(g2):
        x, y, c, frozen = a1[qid], a2[qid], contract[qid], g2_source[qid]
        if x['question'] != g2[qid]['question'] or y['question'] != g2[qid]['question'] or c['question_frozen'] != g2[qid]['question']:
            raise ValueError(f'Frozen question text differs: {qid}')
        if x['accession_number'] != frozen['accession_number'] or y['source_accession'] != frozen['accession_number'] or c['source_accession'] != frozen['accession_number']:
            raise ValueError(f'Accession differs: {qid}')
        if x['source_url'] != frozen['source_url'] or y['source_url'] != frozen['source_url'] or c['source_url'] != frozen['source_url']:
            raise ValueError(f'Source URL differs: {qid}')
        s1, s2 = status_a1(x), y['decision']
        if s1 == 'SOURCE_UNAVAILABLE' or s2 == 'SOURCE_UNAVAILABLE':
            classification = 'SOURCE_UNAVAILABLE_IN_FROZEN_REVIEWS'
        elif s1 != s2:
            classification = 'DISAGREED_DECISION'
        elif s1 == 'AMBIGUOUS':
            classification = 'AMBIGUOUS_BOTH'
        elif s1 == 'SUPPORTED':
            classification = 'AGREED_SUPPORTED_DECISION_ONLY'
        else:
            classification = 'AGREED_OTHER_DECISION'
        ca, cb = values_a1(x), values_a2(c)
        value_check = value_relation(ca, cb)
        row_check = text_relation(' | '.join(str(v.get('row_label', '')) for v in ca) or x.get('metric_definition'), c.get('row'))
        metric_check = text_relation(x.get('metric_definition'), c.get('metric_definition'))
        statement_check = text_relation(x.get('statement_or_section'), c.get('statement'))
        period_check = date_relation(x.get('period_column'), c.get('column_period'))
        currency_check = text_relation(x.get('currency'), c.get('currency'))
        scale_check = text_relation(x.get('scale'), c.get('scale'))
        unit_check = unit_relation(x.get('currency'), x.get('scale'), c.get('currency'), c.get('scale'))
        raw_ready = frozen['accession_number'] in source_by_acc
        if classification == 'SOURCE_UNAVAILABLE_IN_FROZEN_REVIEWS':
            priority = 'RAW_SOURCE_REVIEW_REQUIRED' if raw_ready else 'SOURCE_ACQUISITION_REQUIRED'
        elif classification in ('DISAGREED_DECISION', 'AMBIGUOUS_BOTH'):
            priority = 'INDEPENDENT_DISPUTE_REVIEW_REQUIRED'
        elif value_check in ('PARTIAL_NUMERIC_TOKEN_OVERLAP', 'DISJOINT_NUMERIC_TOKEN_SETS', 'ONE_SIDED_STRUCTURED_NUMERIC'):
            priority = 'CELL_PERIOD_SCOPE_REVIEW_REQUIRED'
        else:
            priority = 'STANDARD_CELL_VALIDATION_REQUIRED'
        record = {'question_id': qid, 'accession': frozen['accession_number'], 'ticker': frozen['ticker'],
                  'agent1_round': x['G3_review_round'], 'agent1_decision': s1, 'agent2_decision': s2,
                  'classification': classification, 'source_raw_now_available': str(raw_ready),
                  'source_raw_sha256': source_by_acc[frozen['accession_number']]['sha256'] if raw_ready else '',
                  'metric_text_relation': metric_check, 'statement_text_relation': statement_check,
                  'row_text_relation': row_check, 'period_date_relation': period_check,
                  'numeric_token_relation': value_check, 'currency_text_relation': currency_check,
                  'scale_text_relation': scale_check, 'unit_compatibility': unit_check,
                  'review_priority': priority,
                  'agent1_metric': x.get('metric_definition') or '', 'agent2_metric': c.get('metric_definition') or '',
                  'agent1_statement': x.get('statement_or_section') or '', 'agent2_statement': c.get('statement') or '',
                  'agent1_rows': ' | '.join(str(v.get('row_label', '')) for v in ca), 'agent2_row': c.get('row') or '',
                  'agent1_period': x.get('period_column') or '', 'agent2_period': c.get('column_period') or '',
                  'agent1_values_json': json.dumps(ca, ensure_ascii=False, separators=(',', ':')),
                  'agent2_values_json': json.dumps(cb, ensure_ascii=False, separators=(',', ':')),
                  'agent1_currency': x.get('currency') or '', 'agent2_currency': c.get('currency') or '',
                  'agent1_scale': x.get('scale') or '', 'agent2_scale': c.get('scale') or '',
                  'agent1_scope': x.get('scope') or '', 'agent2_scope': c.get('accounting_scope') or '',
                  'agent1_locator': x.get('source_locator') or '', 'agent2_locator': c.get('exact_source_locator') or '',
                  'agent1_evidence': x.get('source_excerpt') or '', 'agent2_evidence': c.get('evidence_excerpt') or ''}
        rows.append(record)
        if priority in ('INDEPENDENT_DISPUTE_REVIEW_REQUIRED', 'CELL_PERIOD_SCOPE_REVIEW_REQUIRED'):
            disputes.append(record)
        elif priority == 'RAW_SOURCE_REVIEW_REQUIRED':
            source_queue.append(record)
    output_dir.mkdir(parents=True)
    (output_dir / 'V7A_G3_PRIVATE_94_FIELD_COMPARISON.csv').write_bytes(csv_bytes(rows))
    (output_dir / 'V7A_G3_PRIVATE_DISPUTE_PACKETS.json').write_text(json.dumps(disputes, indent=2, ensure_ascii=False) + '\n', encoding='utf-8', newline='\n')
    (output_dir / 'V7A_G3_PRIVATE_RAW_SOURCE_REVIEW_QUEUE.json').write_text(json.dumps(source_queue, indent=2, ensure_ascii=False) + '\n', encoding='utf-8', newline='\n')
    categories = Counter(r['classification'] for r in rows)
    numeric = Counter(r['numeric_token_relation'] for r in rows)
    priorities = Counter(r['review_priority'] for r in rows)
    summary = {'status': 'FROZEN_AI_LEDGER_COMPARISON_NOT_GOLD',
               'agent1_zip_sha256': sha(a1_path.read_bytes()), 'agent2_zip_sha256': sha(a2_path.read_bytes()),
               'agent1_first_pass_zip_sha256': sha(a1_first_path.read_bytes()),
               'agent2_round1_zip_sha256': sha(a2_round1_path.read_bytes()),
               'agent1_first_pass_carried_forward_rows_verified': len(carried),
               'agent2_round1_ledger_and_evidence_byte_identical': True,
               'g2_question_sha256': sha(G2_PUBLIC.read_bytes()), 'source_manifest_sha256': sha(source_manifest.read_bytes()),
               'questions': 94, 'classifications': dict(categories), 'numeric_token_relations': dict(numeric),
               'review_priorities': dict(priorities),
               'decision_dispute_ids': [r['question_id'] for r in rows if r['classification'] == 'DISAGREED_DECISION'],
               'shared_ambiguity_ids': [r['question_id'] for r in rows if r['classification'] == 'AMBIGUOUS_BOTH'],
               'partial_numeric_scope_ids': [r['question_id'] for r in rows if r['numeric_token_relation'] == 'PARTIAL_NUMERIC_TOKEN_OVERLAP'],
               'source_unavailable_ids': [r['question_id'] for r in rows if r['classification'] == 'SOURCE_UNAVAILABLE_IN_FROZEN_REVIEWS'],
               'limitations': ['Both AI freezes predate the nine raw HTML handoffs',
                               'Matching numeric tokens do not certify the same row, period, scale, scope or human gold']}
    summary['private_output_sha256'] = {p.name: sha(p.read_bytes()) for p in output_dir.iterdir() if p.is_file()}
    (output_dir / 'V7A_G3_COORDINATOR_SUMMARY.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8', newline='\n')
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--agent1-zip', type=Path, required=True)
    parser.add_argument('--agent2-zip', type=Path, required=True)
    parser.add_argument('--agent1-first-pass-zip', type=Path, required=True)
    parser.add_argument('--agent2-round1-zip', type=Path, required=True)
    parser.add_argument('--source-manifest', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    result = compare(args.agent1_zip, args.agent2_zip, args.agent1_first_pass_zip,
                     args.agent2_round1_zip, args.source_manifest, args.output_dir)
    print(json.dumps({k: v for k, v in result.items() if k not in ('source_unavailable_ids',)}, indent=2))

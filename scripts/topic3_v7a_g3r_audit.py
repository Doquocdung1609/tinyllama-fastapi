"""Additive, source-first G3R reconciliation. Detailed AI answers stay outside Git.

This tool never edits reviewer submissions or promotes AI agreement to human gold.
"""

from __future__ import annotations

import argparse
import csv
from decimal import Decimal, InvalidOperation
import hashlib
import io
import json
from pathlib import Path
import re
import zipfile
from collections import Counter

try:
    from scripts.topic3_v7a_g3_coordinator_compare import G2_PUBLIC, G2_SOURCE, csv_rows, sha
except ModuleNotFoundError:  # direct `python scripts/...py` invocation
    from topic3_v7a_g3_coordinator_compare import G2_PUBLIC, G2_SOURCE, csv_rows, sha


A1_DECISIONS = 'AGENT1_G3_POST_SOURCE_18_DECISIONS.csv'
A1_CELLS = 'AGENT1_G3_POST_SOURCE_FINANCIAL_CELLS.jsonl'
A2_DECISIONS = 'AGENT2_G3_POST_SOURCE_18_VERIFICATION.csv'
A2_EVIDENCE = 'AGENT2_G3_POST_SOURCE_CELL_EVIDENCE.jsonl'


def unique_rows(rows: list[dict], expected: set[str], label: str) -> dict[str, dict]:
    result = {r['question_id']: r for r in rows}
    if len(result) != len(rows) or set(result) != expected:
        raise ValueError(f'{label}: duplicate, missing or extra question IDs')
    return result


def decimal_value(raw: object) -> Decimal | None:
    value = str(raw or '').strip().replace(',', '')
    if value.startswith('(') and value.endswith(')'):
        value = '-' + value[1:-1]
    try:
        return Decimal(value)
    except InvalidOperation:
        return None


def normalize_unit(currency: str, scale: str) -> tuple[str, str]:
    money = {'USD': 'USD', 'US$': 'USD', 'TWD': 'TWD', 'NT$': 'TWD', 'NTD': 'TWD'}
    amount = {'millions': '1000000', 'million': '1000000', 'thousands': '1000',
              'thousand': '1000', 'billions': '1000000000', 'billion': '1000000000',
              'units': '1', 'unit': '1'}
    return money.get(currency.strip().upper(), currency.strip().upper()), amount.get(scale.strip().lower(), scale.strip().lower())


def negative_question_category(*, relevant_statement_inspected: bool,
                               target_line_present: bool | None,
                               question_scope_unambiguous: bool) -> str:
    """A keyword miss alone can never establish a source-supported negative."""
    if not question_scope_unambiguous:
        return 'AMBIGUOUS'
    if not relevant_statement_inspected or target_line_present is None:
        return 'SOURCE_INSUFFICIENT'
    return 'POSITIVE_SUPPORTED' if target_line_present else 'NEGATIVE_SUPPORTED'


def gold_release_eligible(record: dict) -> bool:
    """Only an explicit, attributable human review can enter a release subset."""
    return bool(record.get('human_decision') in {
        'POSITIVE_SUPPORTED', 'NEGATIVE_SUPPORTED', 'UNSUPPORTED_REQUEST',
        'AMBIGUOUS', 'SOURCE_INSUFFICIENT'} and
        record.get('human_explanation') and record.get('human_reviewer') and
        record.get('human_reviewed_utc') and record.get('source_url'))


def period_key(text: str) -> tuple[str, str]:
    value = text.lower()
    iso = re.findall(r'20\d\d-\d\d-\d\d', value)
    if iso:
        end = iso[-1]
    else:
        months = {m.lower(): f'{i:02d}' for i, m in enumerate(
            ('January', 'February', 'March', 'April', 'May', 'June', 'July',
             'August', 'September', 'October', 'November', 'December'), 1)}
        found = re.search(r'(' + '|'.join(months) + r')\s+(\d{1,2}),?\s+(20\d\d)', value, re.I)
        end = f'{found.group(3)}-{months[found.group(1).lower()]}-{int(found.group(2)):02d}' if found else ''
    duration = 'THREE_MONTHS' if re.search(r'three\s+months|3\s+months', value) else (
        'SIX_MONTHS' if re.search(r'six\s+months|6\s+months', value) else (
        'NINE_MONTHS' if re.search(r'nine\s+months|9\s+months', value) else (
        'YEAR' if re.search(r'year\s+ended|fiscal\s+year|fy20', value) else 'UNKNOWN')))
    return end, duration


def verify_archive(path: Path, manifest_name: str, file_hash_key: str) -> tuple[zipfile.ZipFile, dict, list[str]]:
    z = zipfile.ZipFile(path)
    if z.testzip() is not None:
        z.close()
        raise ValueError(f'CRC failed: {path}')
    manifest = json.loads(z.read(manifest_name))
    warnings = []
    for name, record in manifest[file_hash_key].items():
        expected = record['sha256'] if isinstance(record, dict) else record
        actual = sha(z.read(name))
        if expected != actual:
            if name in (manifest_name, 'SHA256SUMS.txt'):
                warnings.append(f'{name}: declared {expected}; actual {actual}')
            else:
                z.close()
                raise ValueError(f'Data-file SHA mismatch: {path.name}/{name}')
    if 'SHA256SUMS.txt' in z.namelist():
        for line in z.read('SHA256SUMS.txt').decode().splitlines():
            expected, name = line.split(None, 1)
            if sha(z.read(name.strip())) != expected:
                z.close()
                raise ValueError(f'SHA256SUMS mismatch: {name}')
    return z, manifest, warnings


def source_member_checks(z: zipfile.ZipFile, source: dict, qid: str, a1: dict, a2: dict) -> dict:
    raw = z.read(source['file'])
    expected = source['sha256']
    if sha(raw) != expected:
        raise ValueError(f'Raw SEC source SHA mismatch: {qid}')
    if a1['source_html_sha256'] != expected or a2['source_html_sha256'] != expected:
        raise ValueError(f'Reviewer source SHA mismatch: {qid}')
    if a1['source_url'] != source['original_sec_url'] or a2['source_url'] != source['original_sec_url']:
        raise ValueError(f'Reviewer source URL mismatch: {qid}')
    if a1['accession_number'] != source['accession'] or a2['accession'] != source['accession']:
        raise ValueError(f'Reviewer accession mismatch: {qid}')
    if (not source['identity_pass'] or source['form'] != a1['form_type'] or
            source['form'] != a2['form'] or source['cik'] != a1['cik'] or
            source['filing_index_crosscheck']['form_matches'] is not True or
            source['filing_index_crosscheck']['primary_filename_in_document_format_table'] is not True):
        raise ValueError(f'SEC filing-index/form/CIK identity mismatch: {qid}')
    if a2['source_zip_member'] != source['file']:
        raise ValueError(f'Reviewer ZIP member mismatch: {qid}')
    return {'question_id': qid, 'accession': source['accession'], 'source_sha256': expected,
            'source_member': source['file'], 'source_url': source['original_sec_url'],
            'source_bytes': len(raw), 'identity': 'PASS'}


def compare_numeric_cells(a1: dict, a2: dict, a1_cell: dict, source_bytes: bytes) -> tuple[str, str]:
    """Bind value to explicit row/column/period; report uncertainty conservatively."""
    one, two = decimal_value(a1['exact_value']), decimal_value(a2['value_exact_decimal'])
    if one is None or two is None:
        return 'INSUFFICIENT_EVIDENCE', 'Missing numeric value'
    if one != two:
        return 'PERIOD_OR_SCOPE_CONFLICT', f'Decimal values differ: {one} versus {two}'
    if normalize_unit(a1['currency'], a1['scale']) != normalize_unit(a2['currency'], a2['scale']):
        return 'PERIOD_OR_SCOPE_CONFLICT', 'Currency or unit multiplier differs'
    if period_key(a1['column_period']) != period_key(a2['column_period']):
        return 'PERIOD_OR_SCOPE_CONFLICT', 'Period end or duration differs'
    if a1['row_label'].strip().casefold() != a2['row_label'].strip().casefold():
        return 'PERIOD_OR_SCOPE_CONFLICT', 'Financial row label differs'
    try:
        from lxml import html  # optional audit-only dependency; never executes source scripts
    except ImportError:
        return 'INSUFFICIENT_EVIDENCE', 'lxml unavailable for source-cell XPath validation'
    root = html.fromstring(source_bytes)
    nodes = root.xpath(a1_cell['cell_xpath'])
    if len(nodes) != 1 or decimal_value(''.join(nodes[0].itertext())) != one:
        return 'SOURCE_LOCATOR_CONFLICT', 'Agent 1 cell XPath does not resolve to the declared value'
    nodes2 = root.xpath(a2['source_xpath'])
    if len(nodes2) != 1 or a2['row_label'].casefold() not in ' '.join(nodes2[0].itertext()).casefold():
        return 'SOURCE_LOCATOR_CONFLICT', 'Agent 2 row XPath does not resolve to the declared row'
    row = nodes[0].getparent()
    if row is None or a1['row_label'].casefold() not in ' '.join(row.itertext()).casefold():
        return 'SOURCE_LOCATOR_CONFLICT', 'Agent 1 cell XPath is outside the declared row'
    if row is not nodes2[0]:
        return 'SOURCE_LOCATOR_CONFLICT', 'Reviewer XPaths identify different source rows'
    tables = nodes[0].xpath('ancestor::table[1]')
    if len(tables) != 1:
        return 'INSUFFICIENT_EVIDENCE', 'Financial table ancestor absent'
    first_rows = tables[0].xpath('.//tr')[:5]
    header = ' '.join(' '.join(r.itertext()) for r in first_rows).lower()
    end, duration = period_key(a1['column_period'])
    if not end or end[:4] not in header:
        return 'INSUFFICIENT_EVIDENCE', 'Source table header does not establish requested year'
    if duration == 'THREE_MONTHS' and 'three months' not in header:
        return 'PERIOD_OR_SCOPE_CONFLICT', 'Source table header does not establish three-month duration'
    if duration == 'YEAR' and 'three months' in header and 'year ended' not in header:
        return 'PERIOD_OR_SCOPE_CONFLICT', 'Annual claim points to an interim table'
    if a1_cell['column_period'] != a1['column_period'] or a1_cell['value_as_printed'] != a1['exact_value']:
        return 'INSUFFICIENT_EVIDENCE', 'Agent 1 decision and cell contract differ'
    return 'EXACT_CELL_AGREEMENT', 'Same Decimal value, unit, row, period and source row; Agent 1 cell XPath resolves'


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError(f'No rows for {path}')
    with path.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(dict.fromkeys(k for row in rows for k in row)))
        writer.writeheader()
        writer.writerows(rows)


def audit(a1_path: Path, a2_path: Path, source_path: Path, prior_path: Path,
          input1_path: Path, input2_path: Path, out: Path) -> dict:
    if out.exists():
        raise FileExistsError(f'Refusing to overwrite prior audit: {out}')
    g2 = unique_rows(csv_rows(G2_PUBLIC.read_bytes()), set(r['question_id'] for r in csv_rows(G2_PUBLIC.read_bytes())), 'G2')
    source_g2 = unique_rows(csv_rows(G2_SOURCE.read_bytes()), set(g2), 'G2 source')
    if len(g2) != len(source_g2) or len(g2) != 94:
        raise ValueError('G2 must contain exactly 94 questions')
    prior_bytes = prior_path.read_bytes()
    prior = unique_rows(csv_rows(prior_bytes), set(g2), 'pre-recovery comparison')
    if Counter(r['classification'] for r in prior.values()) != Counter({
        'AGREED_SUPPORTED_DECISION_ONLY': 70, 'DISAGREED_DECISION': 5,
        'AMBIGUOUS_BOTH': 1, 'SOURCE_UNAVAILABLE_IN_FROZEN_REVIEWS': 18}):
        raise ValueError('Pre-recovery classification lock changed')
    z1, m1, w1 = verify_archive(a1_path, 'AGENT1_G3_POST_SOURCE_MANIFEST.json', 'files')
    z2, m2, w2 = verify_archive(a2_path, 'AGENT2_G3_POST_SOURCE_FREEZE_MANIFEST.json', 'artifact_sha256')
    input_ready_bytes = []
    for input_path, declared in ((input1_path, m1['input_primary_zip_sha256']),
                                 (input2_path, m2['immutable_inputs']['source_review_input_zip']['sha256'])):
        if sha(input_path.read_bytes()) != declared:
            raise ValueError(f'Reviewer input ZIP SHA mismatch: {input_path}')
        with zipfile.ZipFile(input_path) as zi:
            if zi.testzip() is not None or sha(zi.read('G3_SEC9_SOURCE_HANDOFF.zip')) != sha(source_path.read_bytes()):
                raise ValueError(f'Nested reviewer SEC input failed: {input_path}')
            ready = zi.read('SOURCE_READY_18.csv')
            input_ready_bytes.append(ready)
            if len(csv_rows(ready)) != 18:
                raise ValueError(f'Reviewer source-ready mapping count invalid: {input_path}')
            with zipfile.ZipFile(io.BytesIO(zi.read('G2_BLIND_QUESTION_INPUT.zip'))) as zq:
                if zq.testzip() is not None:
                    raise ValueError(f'Reviewer G2 question ZIP CRC failed: {input_path}')
                if sha(zq.read('QUESTION_ONLY.csv')) != sha(G2_PUBLIC.read_bytes()):
                    raise ValueError(f'Reviewer G2 question bytes differ: {input_path}')
    if input_ready_bytes[0] != input_ready_bytes[1]:
        raise ValueError('Blind reviewers received different 18-question source mappings')
    with z1, z2, zipfile.ZipFile(source_path) as zs:
        if zs.testzip() is not None:
            raise ValueError('Nested SEC source ZIP CRC failed')
        source_manifest = json.loads(zs.read('V7A_G3_SOURCE_ACQUISITION_MANIFEST.json'))
        sources = {s['accession']: s for s in source_manifest['sources']}
        if len(sources) != 9 or sha(source_path.read_bytes()) != m2['immutable_inputs']['source_handoff_inner_zip']['sha256']:
            raise ValueError('Nine-source package identity differs')
        for line in zs.read('SHA256SUMS.txt').decode().splitlines():
            expected, name = line.split(None, 1)
            if sha(zs.read(name.strip())) != expected:
                raise ValueError(f'SEC handoff member SHA failed: {name}')
        expected = {qid for qid, r in prior.items() if r['classification'] == 'SOURCE_UNAVAILABLE_IN_FROZEN_REVIEWS'}
        if set(r['question_id'] for r in csv_rows(input_ready_bytes[0])) != expected:
            raise ValueError('Blind reviewer 18-question mapping differs from frozen queue')
        a1 = unique_rows(csv_rows(z1.read(A1_DECISIONS)), expected, 'Agent 1 post-source')
        a2 = unique_rows(csv_rows(z2.read(A2_DECISIONS)), expected, 'Agent 2 post-source')
        a1_cells = {r['question_id']: r for r in (json.loads(x) for x in z1.read(A1_CELLS).decode().splitlines() if x.strip())}
        a2_evidence = unique_rows([json.loads(x) for x in z2.read(A2_EVIDENCE).decode().splitlines() if x.strip()], expected, 'Agent 2 evidence')
        if len(a1_cells) != 9:
            raise ValueError('Agent 1 numeric cell count differs from nine')
        if m1['frozen_g2_question_count'] != 94 or m2['immutable_inputs']['G2_question_only_csv']['sha256'] != sha(G2_PUBLIC.read_bytes()):
            raise ValueError('G2 question freeze mismatch')
        checks, merged, cells, review = [], [], [], []
        for qid in sorted(g2):
            old = prior[qid]
            if qid in expected:
                x, y, meta = a1[qid], a2[qid], source_g2[qid]
                if x['question_exact_g2'] != g2[qid]['question'] or y['question'] != g2[qid]['question']:
                    raise ValueError(f'Question wording changed: {qid}')
                for key1, key2 in [('accession_number', 'accession_number'), ('source_url', 'source_url'), ('form_type', 'form_type')]:
                    if x[key1] != meta[key2]:
                        raise ValueError(f'Agent 1 frozen identity mismatch: {qid}/{key1}')
                if y['accession'] != meta['accession_number'] or y['form'] != meta['form_type'] or y['report_date'] != meta['report_date']:
                    raise ValueError(f'Agent 2 frozen identity mismatch: {qid}')
                source = sources[meta['accession_number']]
                checks.append(source_member_checks(zs, source, qid, x, y))
                if y['review_decision'] != a2_evidence[qid]['review_decision']:
                    raise ValueError(f'Agent 2 cell contract decision mismatch: {qid}')
                cell_class = 'INSUFFICIENT_EVIDENCE'
                reason = 'Qualitative or unresolved decision; no numeric cell comparison'
                if qid in a1_cells:
                    cell_class, reason = compare_numeric_cells(x, y, a1_cells[qid], zs.read(source['file']))
                status = ('AGREED_SUPPORTED' if x['decision'] == y['review_decision'] == 'SUPPORTED' else
                          'AGREED_AMBIGUOUS' if x['decision'] == y['review_decision'] == 'AMBIGUOUS' else
                          'SEMANTICALLY_ALIGNED_UNRESOLVED' if x['decision'] == 'SOURCE_INSUFFICIENT' and y['review_decision'] == 'PARTIAL' else
                          'DISAGREED_DECISION')
                cells.append({'question_id': qid, 'classification': cell_class, 'reason': reason,
                              'agent1_value': x['exact_value'], 'agent2_value': y['value_exact_decimal'],
                              'agent1_period': x['column_period'], 'agent2_period': y['column_period'],
                              'agent1_row': x['row_label'], 'agent2_row': y['row_label'],
                              'agent1_cell_xpath': a1_cells.get(qid, {}).get('cell_xpath', ''),
                              'agent2_row_xpath': y['source_xpath'], 'source_sha256': source['sha256']})
                merged.append({**old, 'pass': 'POST_SOURCE_ADDITIVE', 'pre_recovery_classification': old['classification'],
                               'agent1_decision': x['decision'], 'agent2_decision': y['review_decision'],
                               'decision_relation': status, 'cell_relation': cell_class, 'source_sha256': source['sha256'],
                               'post_agent1_metric': x['metric_definition'], 'post_agent2_metric': y['metric_definition'],
                               'post_agent1_statement': x['statement_or_section'], 'post_agent2_statement': y['statement'],
                               'post_agent1_row': x['row_label'], 'post_agent2_row': y['row_label'],
                               'post_agent1_period': x['column_period'], 'post_agent2_period': y['column_period'],
                               'post_agent1_value': x['exact_value'], 'post_agent2_value': y['value_exact_decimal'],
                               'post_agent1_currency': x['currency'], 'post_agent2_currency': y['currency'],
                               'post_agent1_scale': x['scale'], 'post_agent2_scale': y['scale'],
                               'post_agent1_scope': x['accounting_scope'], 'post_agent2_scope': y['scope'],
                               'post_agent1_locator': x['source_locator'], 'post_agent2_locator': y['source_locator'],
                               'human_decision': '', 'review_required': 'YES'})
                review.append({'question_id': qid, 'question': g2[qid]['question'], 'accession': source['accession'],
                               'source_url': source['original_sec_url'], 'agent1_decision': x['decision'],
                               'agent2_decision': y['review_decision'], 'agent1_locator': x['source_locator'],
                               'agent2_locator': y['source_locator'], 'agent1_value': x['exact_value'],
                               'agent2_value': y['value_exact_decimal'], 'cell_relation': cell_class,
                               'review_reason': reason, 'human_decision': '', 'human_explanation': '',
                               'human_reviewer': '', 'human_reviewed_utc': ''})
            else:
                merged.append({**old, 'pass': 'PRE_RECOVERY_UNCHANGED',
                               'pre_recovery_classification': old['classification'],
                               'agent1_decision': old['agent1_decision'], 'agent2_decision': old['agent2_decision'],
                               'decision_relation': old['classification'], 'cell_relation': 'NOT_SOURCE_CERTIFIED',
                               'source_sha256': old['source_raw_sha256'], 'human_decision': '', 'review_required': 'YES'})
                review.append({'question_id': qid, 'question': g2[qid]['question'], 'accession': old['accession'],
                               'source_url': old['source_url'], 'agent1_decision': old['agent1_decision'],
                               'agent2_decision': old['agent2_decision'], 'agent1_locator': old['agent1_locator'],
                               'agent2_locator': old['agent2_locator'], 'agent1_value': old['agent1_values_json'],
                               'agent2_value': old['agent2_values_json'], 'cell_relation': 'NOT_SOURCE_CERTIFIED',
                               'review_reason': 'Frozen pre-recovery AI comparison; original source cell not independently rechecked in this pass',
                               'human_decision': '', 'human_explanation': '', 'human_reviewer': '', 'human_reviewed_utc': ''})
    out.mkdir(parents=True)
    write_csv(out / 'V7A_G3R_POST_SOURCE_AGENT1_VERIFICATION.csv', [a1[q] for q in sorted(a1)])
    write_csv(out / 'V7A_G3R_POST_SOURCE_AGENT2_VERIFICATION.csv', [a2[q] for q in sorted(a2)])
    write_csv(out / 'V7A_G3R_94_FIELD_RECONCILIATION.csv', merged)
    write_csv(out / 'V7A_G3R_HUMAN_ADJUDICATION_QUEUE.csv', review)
    triage = []
    for qid in sorted(g2):
        old = prior[qid]
        if old['classification'] != 'AGREED_SUPPORTED_DECISION_ONLY':
            continue
        spot = (old['numeric_token_relation'] == 'SAME_NUMERIC_TOKEN_SET_PERIOD_NOT_CERTIFIED'
                and old['period_date_relation'] == 'SAME_DATE_SET_DURATION_NOT_CERTIFIED'
                and old['unit_compatibility'] == 'SAME_CURRENCY_AND_SCALE_TEXT'
                and all(old[key] != 'DIFFERENT_TEXT_REVIEW_REQUIRED' for key in
                        ('row_text_relation', 'metric_text_relation', 'statement_text_relation')))
        triage.append({'question_id': qid, 'triage': 'SPOT_CHECK_CANDIDATE' if spot else 'FULL_MANUAL_SOURCE_REVIEW',
                       'source_cell_certified': 'NO', 'numeric_token_relation': old['numeric_token_relation'],
                       'row_text_relation': old['row_text_relation'], 'period_date_relation': old['period_date_relation'],
                       'unit_compatibility': old['unit_compatibility']})
    write_csv(out / 'V7A_G3R_PRIOR70_REVIEW_TRIAGE.csv', triage)
    (out / 'V7A_G3R_FINANCIAL_CELL_COMPARISON.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in cells), encoding='utf-8')
    counts = {'agent1': dict(Counter(r['decision'] for r in a1.values())),
              'agent2': dict(Counter(r['review_decision'] for r in a2.values())),
              'post_source_decision_relation': dict(Counter(r['decision_relation'] for r in merged if r['pass'] == 'POST_SOURCE_ADDITIVE')),
              'post_source_cell_relation': dict(Counter(r['classification'] for r in cells)),
              'prior70_triage': dict(Counter(r['triage'] for r in triage)),
              'all_94_human_pending': len(review)}
    lock = {'pre_recovery_sha256': sha(prior_bytes), 'classifications': dict(Counter(r['classification'] for r in prior.values())),
            'question_only_sha256': sha(G2_PUBLIC.read_bytes()), 'frozen_question_count': 94}
    (out / 'V7A_G3R_PRE_RECOVERY_COMPARISON_LOCK.json').write_text(json.dumps(lock, indent=2) + '\n', encoding='utf-8')
    integrity = {'agent1_post_zip_sha256': sha(a1_path.read_bytes()), 'agent2_post_zip_sha256': sha(a2_path.read_bytes()),
                 'source_zip_sha256': sha(source_path.read_bytes()), 'source_accessions': len(sources),
                 'source_questions_verified': len(checks), 'agent1_manifest_warnings': w1,
                 'agent2_manifest_warnings': w2, 'counts': counts,
                 'private_output_sha256': {p.name: sha(p.read_bytes()) for p in out.iterdir() if p.is_file()}}
    (out / 'V7A_G3R_INPUT_INTEGRITY.json').write_text(json.dumps(integrity, indent=2) + '\n', encoding='utf-8')
    return integrity


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('agent1', 'agent2', 'source', 'prior', 'input1', 'input2', 'out'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.agent1, args.agent2, args.source, args.prior,
                           args.input1, args.input2, args.out), indent=2))

"""Verify G3T handoff and create a prospective strict-label risk overlay."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import zipfile

from lxml import html

from scripts.topic3_g3t_validate import verify_ai_chain
from scripts.topic3_v7a_g3s_evidence import SourceStore, norm


HOLD = {'V7A_G2_12_02', 'V7A_G2_15_01'}
SAMPLE_STEP = 7


def strict_exact_candidates(c1: dict[str, dict], c2: list[dict]) -> set[str]:
    exact = {r['question_id'] for r in c2 if r['technical_label'] == 'AI_SUPPORTED_EXACT'}
    if not HOLD <= exact or any(c1[qid]['c1_outcome'] !=
                                 'SOURCE_FACT_VERIFIED_BUT_QUESTION_SCOPE_PENDING' for qid in HOLD):
        raise ValueError('Frozen C1/C2 comparative-scope contradiction changed')
    return exact - HOLD


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def records(path: Path) -> list[dict]:
    return [json.loads(s) for s in path.read_text(encoding='utf-8').splitlines() if s]


def verify_handoff(archive: Path, manifest: Path, review_sha: str) -> dict:
    metadata = json.loads(manifest.read_text(encoding='utf-8'))
    expected = {filename: info for group in metadata['files'].values()
                for filename, info in group.items()}
    with zipfile.ZipFile(archive) as package:
        if package.testzip() is not None or len(package.namelist()) != 18:
            raise ValueError('G3T private handoff CRC/count failed')
        for filename, info in expected.items():
            paths = [name for name in package.namelist() if name.endswith('/' + filename)]
            if len(paths) != 1:
                raise ValueError(f'Missing/duplicate G3T member: {filename}')
            raw = package.read(paths[0])
            if len(raw) != info['bytes'] or sha(raw) != info['sha256']:
                raise ValueError(f'G3T handoff member hash changed: {filename}')
        review = [name for name in package.namelist()
                  if name.endswith('G3T_HUMAN_REVIEW_INPUT_20261103_V2.json')]
        if len(review) != 1 or sha(package.read(review[0])) != review_sha:
            raise ValueError('Human review input hash changed')
    return {'zip_sha256': sha(archive.read_bytes()), 'entries': 18,
            'manifest_members_verified': len(expected), 'review_input_verified': True,
            'zip_crc': 'PASS'}


def audit_sample(c1: list[dict], store: SourceStore) -> list[dict]:
    historic = sorted((r for r in c1 if r['c1_outcome'] == 'SOURCE_CELL_REVALIDATED'),
                      key=lambda r: r['question_id'])
    if len(historic) != 52:
        raise ValueError('Historical 52-cell group changed')
    findings = []
    for item in historic[::SAMPLE_STEP]:
        document = html.fromstring(store.bytes(item['accession']))
        for cell in item['source_cells']:
            nodes = document.xpath(cell['primary_xpath'])
            if len(nodes) != 1:
                raise ValueError(f'Missing primary cell: {item["question_id"]}')
            node = nodes[0]
            row = node.xpath('ancestor::tr[1]')
            table = node.xpath('ancestor::table[1]')
            row_text = norm(' '.join(row[0].itertext())) if row else ''
            table_text = norm(' '.join(table[0].itertext())) if table else ''
            value = re.sub(r'\D', '', cell['value_decimal'])
            compact_row = re.sub(r'\D', '', row_text)
            scale = str(cell.get('scale', '')).casefold()
            scale_in_table = (scale in table_text or scale.rstrip('s') in table_text) if scale else False
            dollar_in_row = '$' in ' '.join(row[0].itertext()) if row else False
            findings.append({'question_id': item['question_id'], 'accession': item['accession'],
                             'source_sha256': item['source_sha256'],
                             'cell_xpath': cell['primary_xpath'],
                             'row_text_contains_metric': norm(cell['row']) in row_text,
                             'row_text_contains_value_digits': value in compact_row,
                             'period_year_in_table': cell['period'][:4] in table_text or
                                 bool(re.search(r'20\d\d', cell['period']) and
                                      re.search(r'20\d\d', cell['period']).group() in table_text),
                             'claimed_currency': cell.get('currency'), 'claimed_scale': scale,
                             'scale_explicit_in_same_table': scale_in_table,
                             'dollar_symbol_in_same_row': dollar_in_row,
                             'unit_scale_status': 'SOURCE_TABLE_EXPLICIT' if scale_in_table else
                                 'INHERITED_OR_OUTSIDE_TABLE_HUMAN_CHECK'})
    return findings


def run(args: argparse.Namespace) -> dict:
    if args.out.exists():
        raise FileExistsError(args.out)
    integrity = verify_handoff(args.handoff, args.manifest, args.review_sha)
    c1, c2 = records(args.c1), records(args.c2)
    if len(c1) != 94 or len({r['question_id'] for r in c1}) != 94:
        raise ValueError('C1 94-ID integrity failed')
    verify_ai_chain(c2, sha(args.policy.read_bytes()), sha(args.c1.read_bytes()))
    if {r['question_id'] for r in c1} != {r['question_id'] for r in c2}:
        raise ValueError('C1/C2 question IDs changed')
    by_c1 = {r['question_id']: r for r in c1}
    exact = [r for r in c2 if r['technical_label'] == 'AI_SUPPORTED_EXACT']
    if len(exact) != 71:
        raise ValueError('Expected G3T exact-label contradiction changed')
    store = SourceStore(args.registry, args.nine, args.eight, args.thirty)
    try:
        sample = audit_sample(c1, store)
        strict = strict_exact_candidates(by_c1, c2)
        bounded = by_c1['V7A_G2_12_01']
        if not any('bounded_negative' in x and x.get('verification') == 'COMPLETE_STATEMENT_ROWS_INSPECTED'
                   for x in bounded['source_cells']):
            raise ValueError('Amazon negative statement boundary missing')
    finally:
        store.close()
    overlay = {'schema': 'g3u_ai_exact_label_risk_overlay/v1',
               'original_c1_sha256': sha(args.c1.read_bytes()),
               'original_c2_sha256': sha(args.c2.read_bytes()),
               'original_policy_sha256': sha(args.policy.read_bytes()),
               'score_exposure': 'NO_NEW_G2_RANKINGS_OR_SCORES',
               'original_exact_proposals': len(exact),
               'strict_exact_hold_ids': sorted(HOLD),
               'strict_exact_candidate_count': len(strict),
               'hold_reason': 'C1 frozen wording comparative scope pending; C2 applied prospective minimum-answer rule only. Human adjudication required for strict release.',
               'sample_method': 'Every seventh sorted historical SOURCE_CELL_REVALIDATED record, all cells in record',
               'historic_sample_questions': len({x['question_id'] for x in sample}),
               'historic_sample_cells': len(sample),
               'sample_scale_explicit_in_table': sum(x['scale_explicit_in_same_table'] for x in sample),
               'sample_scale_inherited_or_outside_table': sum(not x['scale_explicit_in_same_table'] for x in sample),
               'sample_private_findings': sample,
               'negative_12_01': 'BOUNDED_CONSOLIDATED_STATEMENT_ONLY',
               'human_approval_count': 0, 'integrity': integrity,
               'original_label_counts': dict(Counter(r['technical_label'] for r in c2))}
    args.out.write_text(json.dumps(overlay, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return {'overlay_sha256': sha(args.out.read_bytes()),
            'strict_exact_candidate_count': overlay['strict_exact_candidate_count'],
            'sample_questions': overlay['historic_sample_questions'],
            'sample_cells': overlay['historic_sample_cells'],
            'sample_scale_explicit_in_table': overlay['sample_scale_explicit_in_table'],
            'sample_scale_inherited_or_outside_table': overlay['sample_scale_inherited_or_outside_table'],
            'integrity': integrity}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('handoff', 'manifest', 'c1', 'c2', 'policy', 'registry', 'nine', 'eight', 'thirty', 'out'):
        p.add_argument('--' + name.replace('_', '-'), type=Path, required=True)
    p.add_argument('--review-sha', required=True)
    print(json.dumps(run(p.parse_args()), indent=2))

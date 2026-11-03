"""Diagnose three AMD source/chunk discrepancies on immutable original text."""

from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re
import zipfile


CORPUS_SHA = '7c6852a8c68ed1c64194c2da9339fbb4719482949e5705596499db53114abb1f'
TARGETS = ('V7A_G2_09_01', 'V7A_G2_10_01', 'V7A_G2_10_02')


def value_hit(text: str, value: str) -> bool:
    """Accept 3,240 / 3 240 / 3240, but never a substring of a larger number."""
    digits = re.sub(r'\D', '', value)
    if not digits:
        return False
    pattern = r'(?<!\d)' + r'[\s,]*'.join(map(re.escape, digits)) + r'(?!\d)'
    return re.search(pattern, text) is not None


def row_hit(text: str, row: str) -> bool:
    return re.search(r'\b' + r'\s+'.join(map(re.escape, row.casefold().split())) + r'\b',
                     text.casefold()) is not None


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def classify_chunk_evidence(filing: list[dict], row_matches: list[int],
                            value_matches: list[int], joint: list[int]) -> str:
    if joint:
        return 'EVIDENCE_PRESENT_NEEDS_MANUAL_QREL'
    if any(abs(r - v) == 1 for r in row_matches for v in value_matches):
        return 'CHUNK_SPLIT_EVIDENCE'
    if not value_matches and all(str(chunk.get('section', '')).startswith('Part II - ')
                                 for chunk in filing):
        return 'SOURCE_PRESENT_CORPUS_CHUNK_MISSING'
    if row_matches or value_matches:
        return 'CORPUS_PRESENT_WRONG_SCOPE'
    return 'SOURCE_PRESENT_CORPUS_CHUNK_MISSING'


def run(corpus_zip: Path, c1_ledger: Path, out: Path) -> dict:
    if out.exists():
        raise FileExistsError(out)
    with zipfile.ZipFile(corpus_zip) as archive:
        raw = archive.read('corpus/chunks_frozen.jsonl')
        if sha(raw) != CORPUS_SHA:
            raise ValueError('Frozen original corpus changed')
    chunks = [json.loads(line) for line in raw.splitlines()]
    if len(chunks) != 8670 or len({c['chunk_id'] for c in chunks}) != 8670:
        raise ValueError('Original corpus cardinality changed')
    c1 = {r['question_id']: r for r in
          (json.loads(line) for line in c1_ledger.read_text(encoding='utf-8').splitlines())}
    if len(c1) != 94:
        raise ValueError('C1 ledger missing questions')
    by_acc = defaultdict(list)
    for chunk in chunks:
        by_acc[chunk['document_id'].split('_')[-1]].append(chunk)
    cases = []
    for qid in TARGETS:
        item = c1[qid]
        if len(item['source_cells']) != 1:
            raise ValueError(f'Unexpected AMD source-cell count: {qid}')
        cell = item['source_cells'][0]
        filing = sorted(by_acc[item['accession']], key=lambda c: c['chunk_index'])
        row_matches, value_matches, joint = [], [], []
        for index, chunk in enumerate(filing):
            row = row_hit(chunk['text'], cell['row'])
            value = value_hit(chunk['text'], cell['value_decimal'])
            if row: row_matches.append(index)
            if value: value_matches.append(index)
            if row and value: joint.append(index)
        nearby = set(row_matches + value_matches)
        nearby.update(j for i in list(nearby) for j in (i - 1, i + 1) if 0 <= j < len(filing))
        evidence = []
        for index in sorted(nearby):
            chunk = filing[index]
            body = chunk['text']
            evidence.append({'chunk_id': chunk['chunk_id'], 'chunk_index': chunk['chunk_index'],
                             'section': chunk.get('section'), 'text_hash': chunk['text_hash'],
                             'original_text_sha256': sha(body.encode('utf-8')),
                             'row_hit': index in row_matches, 'value_hit': index in value_matches,
                             'excerpt': re.sub(r'\s+', ' ', body)[:650]})
        disposition = classify_chunk_evidence(filing, row_matches, value_matches, joint)
        cases.append({'question_id': qid, 'accession': item['accession'],
                      'source_sha256': item['source_sha256'], 'source_url': item['source_url'],
                      'source_locator': cell['primary_xpath'], 'metric_row': cell['row'],
                      'value_decimal': cell['value_decimal'], 'currency': cell['currency'],
                      'scale': cell['scale'], 'period': cell['period'], 'scope': cell['scope'],
                      'source_header_context': cell.get('header_context'),
                      'source_row_text': cell.get('source_row_text'),
                      'target_filing_chunks': len(filing), 'row_hit_count': len(row_matches),
                      'value_hit_count': len(value_matches), 'joint_hit_count': len(joint),
                      'disposition': disposition, 'review_status': 'AI_DIAGNOSIS_NOT_HUMAN_QREL',
                      'neighbor_evidence': evidence})
    out.write_text(json.dumps({'schema': 'g3u_amd_original_chunk_diagnosis/v1',
                               'corpus_sha256': CORPUS_SHA, 'cases': cases},
                              ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return {'case_count': len(cases), 'private_sha256': sha(out.read_bytes()),
            'summary': [{k: c[k] for k in ('question_id', 'target_filing_chunks',
                'row_hit_count', 'value_hit_count', 'joint_hit_count', 'disposition')}
                        for c in cases]}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('corpus_zip', 'c1_ledger', 'out'):
        p.add_argument('--' + name.replace('_', '-'), type=Path, required=True)
    print(json.dumps(run(**vars(p.parse_args())), indent=2))

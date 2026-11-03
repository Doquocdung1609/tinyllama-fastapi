"""Verify frozen chunk/index provenance and prepare conservative source-only qrels."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import io
import json
from pathlib import Path
import pickletools
import sqlite3
import zipfile

from scripts.topic3_v7a_g3s_evidence import norm


CORPUS_SHA = '7c6852a8c68ed1c64194c2da9339fbb4719482949e5705596499db53114abb1f'
INDEX_SHA = {'A': '1e8e3c6393e7e59786575ed0228254079639016c7b986d1e9702fa5a3ce32540',
             'B': 'fef99bfa5cde1ec358f460efacd3db4ca540673213491c569d64e313070df663'}


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def index_payload_identity(blob: bytes) -> tuple[str, str]:
    """Inspect pickle opcodes as data; never execute the pickle payload."""
    values = [arg for opcode, arg, _ in pickletools.genops(blob)
              if opcode.name in ('SHORT_BINUNICODE', 'BINUNICODE', 'BINUNICODE8')]
    if 'chunk_id' not in values or 'text_hash' not in values:
        raise ValueError('Index payload lacks original chunk identity')
    return values[values.index('chunk_id') + 1], values[values.index('text_hash') + 1]


def run(corpus_zip: Path, c1_ledger: Path, c2_ledger: Path, policy: Path, out: Path) -> dict:
    if out.exists():
        raise FileExistsError(out)
    with zipfile.ZipFile(corpus_zip) as outer:
        if outer.testzip() is not None:
            raise ValueError('Restored baseline handoff CRC failed')
        raw = outer.read('corpus/chunks_frozen.jsonl')
        if sha(raw) != CORPUS_SHA:
            raise ValueError('Frozen corpus SHA mismatch')
        chunks = [json.loads(line) for line in raw.splitlines()]
        by_id = {x['chunk_id']: x for x in chunks}
        if len(chunks) != 8670 or len(by_id) != 8670:
            raise ValueError('Frozen corpus count or unique IDs failed')
        index_membership = {}
        for name, member in [('A','snapshots/FAITH_R_P3D_RECOVERED_8670.zip'),
                             ('B','snapshots/FAITH_R_P7K_CORRECTED_8670.zip')]:
            archive_bytes = outer.read(member)
            if sha(archive_bytes) != INDEX_SHA[name]:
                raise ValueError(f'Index {name} SHA mismatch')
            with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
                if archive.testzip() is not None:
                    raise ValueError(f'Index {name} ZIP CRC failed')
                connection = sqlite3.connect(':memory:')
                connection.deserialize(archive.read('collection/financial_docs/storage.sqlite'))
                found = {}
                for _, blob in connection.execute('SELECT id, point FROM points'):
                    chunk_id, text_hash = index_payload_identity(blob)
                    if chunk_id in found or chunk_id not in by_id or by_id[chunk_id]['text_hash'] != text_hash:
                        raise ValueError(f'Index {name} original chunk/hash mismatch')
                    found[chunk_id] = text_hash
                connection.close()
                if len(found) != 8670 or set(found) != set(by_id):
                    raise ValueError(f'Index {name} membership incomplete')
                index_membership[name] = len(found)
    c1 = {x['question_id']: x for x in (json.loads(line) for line in c1_ledger.read_text(encoding='utf-8').splitlines())}
    c2 = {x['question_id']: x for x in (json.loads(line) for line in c2_ledger.read_text(encoding='utf-8').splitlines())}
    if len(c1) != 94 or set(c1) != set(c2):
        raise ValueError('G3T C1/C2 question ID mismatch')
    by_acc = defaultdict(list)
    for chunk in chunks:
        accession = chunk['document_id'].split('_')[-1]
        by_acc[accession].append(chunk)
    if len(by_acc) != 47 or set(by_acc) != {x['accession'] for x in c1.values()}:
        raise ValueError('Frozen corpus filing identity mismatch')
    out.mkdir(parents=True)
    provenance_path = out / 'G3T_C3_ORIGINAL_CHUNK_PROVENANCE.jsonl'
    with provenance_path.open('w', encoding='utf-8') as stream:
        for chunk in chunks:
            item = {k: chunk.get(k) for k in ('chunk_id','document_id','ticker','cik','document_type',
                'filing_date','fiscal_period','section','text_hash','chunk_index','source_url')}
            item.update(index_A_member=True,index_B_member=True,
                        original_text_sha256=sha(chunk['text'].encode('utf-8')))
            stream.write(json.dumps(item, ensure_ascii=False)+'\n')
    qrels_path = out / 'G3T_C3_QRELS_PROVISIONAL.jsonl'
    coverage = []
    grades = Counter()
    with qrels_path.open('w', encoding='utf-8') as stream:
        for qid in sorted(c1):
            evidence = c1[qid]
            judged = []
            for chunk in by_acc[evidence['accession']]:
                grade = 'UNJUDGED'
                matched = []
                for cell in evidence['source_cells']:
                    row, value = cell.get('row',''), cell.get('value_decimal','')
                    if not row or not value:
                        continue
                    value_printed = f'{int(value):,}' if value.lstrip('-').isdigit() else value
                    if norm(row) in norm(chunk['text']) and (value in chunk['text'].replace(',','') or value_printed in chunk['text']):
                        matched.append(cell.get('primary_xpath',''))
                if matched:
                    # Row/value co-occurrence does not prove that period or units bind to that cell.
                    grade = 'PARTIAL'
                    judged.append(chunk['chunk_id'])
                item = {'schema': 'g3t_original_chunk_qrel/v1', 'question_id': qid,
                        'chunk_id': chunk['chunk_id'], 'document_accession': evidence['accession'],
                        'original_text_sha256': sha(chunk['text'].encode('utf-8')),
                        'source_sha256': evidence['source_sha256'],
                        'grade': grade, 'graded_value': 1 if grade == 'PARTIAL' else None,
                        'assessment_method': 'STATIC_SOURCE_CELL_CO_OCCURRENCE_NOT_RETRIEVAL_RUN',
                        'source_locators': matched,
                        'human_certified': False}
                stream.write(json.dumps(item, ensure_ascii=False)+'\n')
                grades[grade] += 1
            coverage.append({'question_id': qid, 'accession': evidence['accession'],
                             'target_filing_chunk_count': len(by_acc[evidence['accession']]),
                             'static_partial_chunk_count': len(judged),
                             'exact_original_chunk_judgments': 0,
                             'pool_status': 'STATIC_TARGET_FILING_ONLY_NO_SEALED_RANKINGS',
                             'source_present': True,
                             'retrieval_miss': 'NOT_ASSESSED'})
    coverage_path = out / 'G3T_C3_SOURCE_CORPUS_COVERAGE.csv'
    import csv
    with coverage_path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(coverage[0])); writer.writeheader(); writer.writerows(coverage)
    manifest = {'schema': 'g3t_c3_provenance_manifest/v1', 'chunks': 8670,
                'filings': 47, 'questions': 94, 'index_A_members': index_membership['A'],
                'index_B_members': index_membership['B'], 'corpus_sha256': CORPUS_SHA,
                'index_A_sha256': INDEX_SHA['A'], 'index_B_sha256': INDEX_SHA['B'],
                'provenance_sha256': sha(provenance_path.read_bytes()),
                'qrels_sha256': sha(qrels_path.read_bytes()),
                'coverage_sha256': sha(coverage_path.read_bytes()),
                'qrel_grades': dict(grades),
                'exact_judgments': 0, 'method': 'STATIC_CORPUS_AUDIT_NOT_SEALED_RETRIEVAL',
                'source_only_html_not_retrieval_credit': True,
                'policy_sha256': sha(policy.read_bytes())}
    (out / 'G3T_C3_PROVENANCE_MANIFEST.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')
    return manifest


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('corpus_zip','c1_ledger','c2_ledger','policy','out'):
        p.add_argument('--'+name.replace('_','-'), type=Path, required=True)
    print(json.dumps(run(**vars(p.parse_args())), indent=2))

"""Mutate only an explicit P7 clone and prove the automatic path refuses evidence."""
import argparse
from contextlib import contextmanager
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
from app.research_qa.backend import ResearchBackend

QUESTION = "What were P&G's net sales for the three months ended September 30, 2026?"


@contextmanager
def changed_file(path, data):
    original = path.read_bytes()
    try:
        path.write_bytes(data)
        yield
    finally:
        path.write_bytes(original)


@contextmanager
def changed_db(db_path, table, key, field, value):
    if (table, field) not in {('documents', 'payload'), ('documents', 'payload_hash'),
                              ('members', 'source')}:
        raise ValueError('P7_DB_MUTATION_NOT_ALLOWED')
    column = 'cid'
    with sqlite3.connect(db_path) as db:
        original = db.execute(f'SELECT {field} FROM {table} WHERE {column}=?', (key,)).fetchone()[0]
        db.execute(f'UPDATE {table} SET {field}=? WHERE {column}=?', (value, key))
    try:
        yield
    finally:
        with sqlite3.connect(db_path) as db:
            db.execute(f'UPDATE {table} SET {field}=? WHERE {column}=?', (original, key))


def ask(backend):
    try:
        response = backend.query(QUESTION, {}, 'B', 'EXTRACT', 5, False, 'automatic_real')
        return {'result': response['answer']['status'],
                'values': response['answer'].get('result_values', []),
                'code': response.get('failure_code')}
    except (ValueError, RuntimeError, OSError, KeyError) as exc:
        return {'result': 'REJECTED_EXCEPTION', 'values': [], 'code': str(exc)[:120]}


def run(root):
    root = root.resolve(strict=True)
    if 'p7-isolated-review' not in root.name or not (root / 'ownership.json').is_file():
        raise ValueError('P7_EXPLICIT_ISOLATED_CLONE_REQUIRED')
    backend = ResearchBackend(root)
    baseline = ask(backend)
    if baseline['result'] != 'SUPPORTED' or baseline['values'] != ['23276000000']:
        raise AssertionError('P7_UNTAMPERED_CONTROL_FAILED')
    parent = 'fin_d411518414b61a2eb637d96721c5aaed'
    db_path = root / 'lexical_v1.sqlite3'
    with sqlite3.connect(db_path) as db:
        raw_source = db.execute('SELECT source FROM members WHERE cid=?', (parent,)).fetchone()[0]
        payload_text, payload_hash = db.execute('SELECT payload,payload_hash FROM documents WHERE cid=?', (parent,)).fetchone()
    source = json.loads(raw_source)
    raw_path = Path(source['raw_path'])
    raw = raw_path.read_bytes()
    if sha256(raw).hexdigest() != source['raw_hash']:
        raise AssertionError('P7_CLONE_SOURCE_HASH_MISMATCH')
    cases = []

    def check(case_id, context):
        with context:
            observed = ask(backend)
        restored = ask(backend)
        if observed['result'] == 'SUPPORTED' or observed['values'] or restored != baseline:
            raise AssertionError(f'P7_TAMPER_NOT_FAIL_CLOSED:{case_id}:{observed}:{restored}')
        cases.append({'case_id': case_id, 'control': baseline, 'tampered': observed,
                      'restored_control': restored})

    check('raw_byte', changed_file(raw_path, raw + b' '))
    modified_source = dict(source)
    modified_source['manifest_hash'] = 'f' * 64
    check('source_manifest_hash', changed_db(db_path, 'members', parent, 'source', json.dumps(modified_source)))
    check('parent_payload_hash', changed_db(db_path, 'documents', parent, 'payload_hash', 'e' * 64))
    payload = json.loads(payload_text)
    moved = json.loads(payload_text)
    moved['source_location']['structural_path'] = 'forged/row/cell'
    check('source_locator', changed_db(db_path, 'documents', parent, 'payload', json.dumps(moved)))
    other = json.loads(payload_text)
    other['metadata']['cik'] = '0000354950'
    check('issuer_membership', changed_db(db_path, 'documents', parent, 'payload', json.dumps(other)))
    other_source = dict(source)
    other_source['filing_id'] = 'sec:0000354950:0001628280-26-058715'
    check('filing_membership', changed_db(db_path, 'members', parent, 'source', json.dumps(other_source)))
    changed = raw.replace(b'23,276', b'23,277', 1)
    if changed == raw:
        raise AssertionError('P7_NUMERIC_CELL_NOT_FOUND')
    check('raw_numeric_cell', changed_file(raw_path, changed))
    changed = raw.replace(b'iso4217:USD', b'iso4217:EUR', 1)
    if changed == raw:
        raise AssertionError('P7_UNIT_NOT_FOUND')
    check('raw_xbrl_unit', changed_file(raw_path, changed))
    changed = raw.replace(b'2026-09-30', b'2026-09-29', 1)
    if changed == raw:
        raise AssertionError('P7_PERIOD_NOT_FOUND')
    check('raw_xbrl_period', changed_file(raw_path, changed))
    cost_path = next((root / 'raw').rglob('cost-20260510.htm'))
    check('different_filing_bytes', changed_file(raw_path, cost_path.read_bytes()))
    changed_source = dict(source)
    changed_source['raw_hash'] = sha256(raw + b' ').hexdigest()
    with changed_file(raw_path, raw + b' '):
        with changed_db(db_path, 'members', parent, 'source', json.dumps(changed_source)):
            observed = ask(backend)
    restored = ask(backend)
    if observed['result'] == 'SUPPORTED' or observed['values'] or restored != baseline:
        raise AssertionError('P7_SELF_DECLARED_HASH_ACCEPTED')
    cases.append({'case_id': 'self_declared_hash_replaced', 'control': baseline,
                  'tampered': observed, 'restored_control': restored})
    old_generation = backend.adapter.freeze['generation']
    try:
        backend.adapter.freeze['generation'] = 'd' * 64
        observed = ask(backend)
    finally:
        backend.adapter.freeze['generation'] = old_generation
    restored = ask(backend)
    if observed['result'] == 'SUPPORTED' or observed['values'] or restored != baseline:
        raise AssertionError('P7_STALE_GENERATION_NOT_FAIL_CLOSED')
    cases.append({'case_id': 'stale_generation', 'control': baseline, 'tampered': observed,
                  'restored_control': restored})
    return {'schema_version': 'topic3-p7-tamper/v1', 'source_sha256': sha256(raw).hexdigest(),
            'clone_only': True, 'cases': cases}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = run(args.root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'tamper_cases': len(result['cases']), 'all_refused': True}))

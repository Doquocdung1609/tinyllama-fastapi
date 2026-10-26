"""Temporarily invalidate clone generation and query a live local P7 API."""
import argparse
import json
from pathlib import Path
import sqlite3
import requests


def run(root, url, token):
    root = root.resolve(strict=True)
    if 'p7-isolated-review' not in root.name or not url.startswith('http://127.0.0.1:'):
        raise ValueError('P7_ISOLATED_CLONE_AND_LOCAL_API_REQUIRED')
    generation = json.loads((root / 'frozen_v1' / 'freeze.json').read_text())['generation']
    db_path = root / 'lexical_v1.sqlite3'
    payload = {'workflow': 'automatic_real', 'arm': 'B',
               'question': "What were P&G's net sales for the three months ended September 30, 2026?"}
    headers = {'Authorization': 'Bearer ' + token}
    with sqlite3.connect(db_path) as db:
        original = db.execute('SELECT state FROM generations WHERE generation=?', (generation,)).fetchone()[0]
        db.execute('UPDATE generations SET state=? WHERE generation=?', ('FAILED', generation))
    try:
        response = requests.post(url + '/research/v1/query', json=payload, headers=headers, timeout=30)
        body = response.json()
        invalid = {'http_status': response.status_code,
                   'answer_status': body.get('answer', {}).get('status'),
                   'values': body.get('answer', {}).get('result_values', []),
                   'detail': body.get('detail')}
    finally:
        with sqlite3.connect(db_path) as db:
            db.execute('UPDATE generations SET state=? WHERE generation=?', (original, generation))
    result = {'schema_version': 'topic3-p7-invalid-generation/v1', 'clone_only': True,
              'original_state': original, 'invalid_state': 'FAILED', 'observed': invalid}
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--url', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    import os
    result = run(args.root, args.url, os.environ['TOPIC3_RESEARCH_API_TOKEN'])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result['observed']))

"""Real local HTTP verification of P7 semantic guards on the isolated clone."""
import argparse
import json
import os
from pathlib import Path
import requests


CASES = [
    ('exact', "What were P&G's net sales for the three months ended September 30, 2026?", 'B', False, 'SUPPORTED'),
    ('fair_value', "What were P&G's net sales fair value for the three months ended September 30, 2026?", 'B', False, 'NEEDS_CLARIFICATION'),
    ('percentage_points', 'What was the percentage-point change in P&G net sales from the quarter ended September 30, 2025 to the quarter ended September 30, 2026?', 'B', False, 'UNSUPPORTED_OPERATION'),
    ('dense_unavailable', "What were P&G's net sales for the three months ended September 30, 2026?", 'D', False, 'INSUFFICIENT_EVIDENCE'),
    ('ollama_not_enabled', "What were P&G's net sales for the three months ended September 30, 2026?", 'B', True, 'INSUFFICIENT_EVIDENCE'),
]


def run(url, token):
    if not url.startswith('http://127.0.0.1:'):
        raise ValueError('LOCAL_API_REQUIRED')
    results = []
    for name, question, arm, use_llm, expected in CASES:
        response = requests.post(url + '/research/v1/query',
            headers={'Authorization': 'Bearer ' + token},
            json={'workflow': 'automatic_real', 'question': question, 'arm': arm, 'use_llm': use_llm}, timeout=30)
        body = response.json()
        observed = body.get('answer', {}).get('status')
        values = body.get('answer', {}).get('result_values', [])
        if response.status_code != 200 or observed != expected or (name != 'exact' and values):
            raise AssertionError(f'P7_HTTP_SEMANTIC_CASE_FAILED:{name}:{response.status_code}:{observed}:{values}')
        results.append({'case_id': name, 'http_status': response.status_code,
                        'answer_status': observed, 'values': values,
                        'failure_code': body.get('failure_code')})
    return {'schema_version': 'topic3-p7-http-semantics/v1', 'cases': results, 'token_recorded': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = run(args.url, os.environ['TOPIC3_RESEARCH_API_TOKEN'])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps([(x['case_id'], x['answer_status']) for x in result['cases']]))

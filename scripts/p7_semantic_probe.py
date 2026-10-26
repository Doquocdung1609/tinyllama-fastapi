"""Adversarial development questions against the pinned real SEC clone."""
import argparse
import json
from pathlib import Path
from app.research_qa.backend import ResearchBackend


BASE = "What were P&G's net sales for the three months ended September 30, 2026?"
CASES = [
    ('wrong_issuer', 'What were HD net sales for the three months ended September 30, 2026?', {}),
    ('cik_conflict', BASE, {'cik': '0000354950'}),
    ('wrong_year', "What were P&G's net sales for the three months ended September 30, 2024?", {}),
    ('wrong_quarter', "What were P&G's net sales for the three months ended June 30, 2026?", {}),
    ('instant_not_duration', "What were P&G's net sales as of September 30, 2026?", {}),
    ('prior_comparative', "What were P&G's net sales for the three months ended September 30, 2025?", {}),
    ('wrong_multiplier', "What were P&G's net sales in thousands for the three months ended September 30, 2026?", {}),
    ('negative_requested', "Were P&G's net sales negative (125.50) for the three months ended September 30, 2026?", {}),
    ('basic_eps', "What were P&G's basic earnings per share for the three months ended September 30, 2026?", {}),
    ('diluted_eps', "What were P&G's diluted earnings per share for the three months ended September 30, 2026?", {}),
    ('beauty_segment', "What were P&G's Beauty segment net sales for the three months ended September 30, 2026?", {}),
    ('fair_value', "What were P&G's net sales fair value for the three months ended September 30, 2026?", {}),
    ('amended', "What were P&G's net sales in amended 10-Q/A for the three months ended September 30, 2026?", {}),
    ('percentage_points', "What was the percentage-point change in P&G net sales from the quarter ended September 30, 2025 to the quarter ended September 30, 2026?", {}),
]


def run(root):
    backend = ResearchBackend(root)
    rows = []
    for name, question, filters in CASES:
        try:
            response = backend.query(question, filters, 'B', 'EXTRACT', 5, False, 'automatic_real')
            rows.append({'case_id': name, 'question': question, 'filters': filters,
                         'answer_status': response['answer']['status'],
                         'values': response['answer'].get('result_values', []),
                         'failure_code': response.get('failure_code')})
        except (ValueError, RuntimeError) as exc:
            rows.append({'case_id': name, 'question': question, 'filters': filters,
                         'answer_status': 'REJECTED_EXCEPTION', 'values': [],
                         'failure_code': str(exc)[:120]})
    return {'schema_version': 'topic3-p7-semantic-development/v1', 'heldout_used': False, 'cases': rows}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = run(args.root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps([(row['case_id'], row['answer_status'], row['values']) for row in result['cases']]))

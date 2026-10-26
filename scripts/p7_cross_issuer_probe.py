"""Development-only source coverage probe; never accesses D5 heldout queries."""
import argparse
from contextlib import closing
import json
from pathlib import Path
from app.research_qa.backend import ResearchBackend
from app.table_evidence.real_source import verified_real_cells


QUESTIONS = [
    ('PG', "What were P&G's net sales for the three months ended September 30, 2026?"),
    ('HD', 'What were HD net sales for the quarter ended August 2, 2026?'),
    ('COST', 'What were COST net sales for the 12 weeks ended May 10, 2026?'),
]


def run(root):
    backend = ResearchBackend(root)
    answers = []
    for issuer, question in QUESTIONS:
        try:
            result = backend.query(question, {}, 'B', 'EXTRACT', 5, False, 'automatic_real')
            refinement = result.get('column_refinement') or {}
            answers.append({'issuer': issuer, 'question': question,
                            'status': result['answer']['status'], 'values': result['answer'].get('result_values', []),
                            'failure_code': result.get('failure_code'),
                            'rank': refinement.get('original_bm25_rank'),
                            'parent_id': refinement.get('selected_parent_id'),
                            'source_cells': result['answer'].get('source_cells', [])})
        except (ValueError, RuntimeError) as exc:
            answers.append({'issuer': issuer, 'question': question, 'status': 'REJECTED_EXCEPTION',
                            'values': [], 'failure_code': str(exc)[:120]})
    families = []
    with closing(backend.adapter.lexical.connect()) as db:
        rows = db.execute('SELECT cid,cik,payload FROM documents ORDER BY cik,cid').fetchall()
    for cik, issuer in [('0000080424', 'PG'), ('0000354950', 'HD'), ('0000909832', 'COST')]:
        for label in ('net sales', 'total assets', 'net income', 'earnings per share'):
            matches = [(cid, json.loads(payload)) for cid, c, payload in rows
                       if c == cik and json.loads(payload)['metadata'].get('row_label', '').casefold() == label]
            if not matches:
                families.append({'issuer': issuer, 'row_label': label, 'status': 'NO_EXACT_ROW_IN_INDEX'})
                continue
            cid, payload = matches[0]
            try:
                cells = verified_real_cells(backend.adapter, cid)
                families.append({'issuer': issuer, 'row_label': label, 'parent_id': cid,
                                 'status': 'VERIFIED_CELLS' if cells else 'NO_SUPPORTED_CELL',
                                 'cells': [c.model_dump(mode='json') for c in cells]})
            except (ValueError, RuntimeError) as exc:
                families.append({'issuer': issuer, 'row_label': label, 'parent_id': cid,
                                 'status': 'REJECTED', 'reason': str(exc)[:120]})
    return {'schema_version': 'topic3-p7-cross-issuer-development/v1', 'heldout_used': False,
            'answers': answers, 'table_family_attempts': families}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = run(args.root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'answers': [(x['issuer'], x['status']) for x in result['answers']],
                      'family_attempts': len(result['table_family_attempts'])}))

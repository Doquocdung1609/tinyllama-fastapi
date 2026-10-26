"""Publish a new lexical generation only in a disposable P7 research clone."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
from app.research_qa.backend import ResearchBackend


QUESTION = "What were P&G's net sales for the three months ended September 30, 2026?"


def run(root):
    root = root.resolve(strict=True)
    if 'p7-isolated-review' not in root.name:
        raise ValueError('P7_CLONE_REQUIRED')
    backend = ResearchBackend(root)
    lexical = backend.adapter.lexical
    dataset = backend.catalog.dataset_id
    old = backend.adapter.freeze['generation']
    new = '7' * 64
    if lexical.generation(dataset)['generation'] != old:
        raise ValueError('P7_OLD_GENERATION_NOT_ACTIVE')
    records = list(lexical.records(old))
    def reader(index):
        results = []
        for _ in range(3):
            response = backend.query(QUESTION, {}, 'B', 'EXTRACT', 5, False, 'automatic_real')
            result = {'status': response['answer']['status'],
                      'values': response['answer'].get('result_values', []),
                      'generation': response.get('generation'),
                      'cell_generations': [c['generation'] for c in response['answer'].get('source_cells', [])]}
            if result['status'] != 'SUPPORTED' or result['values'] != ['23276000000'] or result['generation'] != old or set(result['cell_generations']) != {old}:
                raise AssertionError(f'P7_MIXED_GENERATION:{result}')
            results.append(result)
        return results
    def publisher():
        lexical.start(dataset, new, {'p7_isolated_concurrency': True})
        lexical.add(new, records)
        lexical.seal(new)
        lexical.publish(dataset, new)
        return lexical.generation(dataset)['generation']
    with ThreadPoolExecutor(max_workers=4) as pool:
        reads = [pool.submit(reader, i) for i in range(3)]
        publication = pool.submit(publisher)
        outcomes = [future.result(timeout=90) for future in reads]
        active = publication.result(timeout=90)
    if active != new or lexical.generation(dataset, old)['state'] != 'READY':
        raise AssertionError('P7_PUBLICATION_OR_OLD_RETENTION_FAILED')
    after = reader(3)
    return {'schema_version': 'topic3-p7-concurrency/v1', 'clone_only': True,
            'old_generation': old, 'new_active_generation': active,
            'old_generation_state': lexical.generation(dataset, old)['state'],
            'parallel_readers': 3, 'queries_during_publication': sum(map(len, outcomes)),
            'queries_after_publication': len(after), 'mixed_generation_claims': 0}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = run(args.root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'read_queries': result['queries_during_publication'] + result['queries_after_publication'],
                      'mixed_claims': result['mixed_generation_claims']}))

"""Observational P6 development-budget costs; no policy or heldout change."""
import argparse
from contextlib import closing
import json
from pathlib import Path
import statistics
from time import perf_counter
import psutil
from app.financial_query import resolve_financial_query
from app.financial_ingestion.schemas import FinancialChunk
from app.research_qa.backend import ResearchBackend
from app.research_qa.source_alias import verified_alias_catalog
from app.table_evidence.real_source import verified_real_cells


QUESTION = "What were P&G's net sales for the three months ended September 30, 2026?"
BUDGETS = (5, 10, 20, 32, 64)


def percentile(values, fraction):
    values = sorted(values)
    return round(values[max(0, int(len(values) * fraction + .999999) - 1)], 3)


def run(root):
    backend = ResearchBackend(root)
    catalog = verified_alias_catalog(backend.adapter)
    scope = resolve_financial_query(QUESTION, {}, catalog).resolved_scope
    if scope is None or scope.cik != '0000080424':
        raise AssertionError('P7_DEVELOPMENT_SCOPE_INVALID')
    rows = []
    for budget in BUDGETS:
        for repeat in range(3):
            start = perf_counter()
            with backend.adapter.pin(scope):
                hits = backend.adapter.search(QUESTION, scope, 'B', budget, 30)
            search_ms = round((perf_counter() - start) * 1000, 3)
            selected = []
            for rank, hit in enumerate(hits, 1):
                parent = FinancialChunk.model_validate_json(hit.parent_json)
                if parent.metadata.get('row_label', '').strip().casefold() != 'net sales':
                    continue
                started = perf_counter()
                cells = verified_real_cells(backend.adapter, parent.chunk_id)
                verify_ms = round((perf_counter() - started) * 1000, 3)
                if any(c.period_end == '2026-09-30' and c.period_months == 3 for c in cells):
                    selected.append({'rank': rank, 'parent_id': parent.chunk_id,
                                     'verify_ms': verify_ms, 'cell_count': len(cells)})
            rows.append({'budget': budget, 'repeat': repeat, 'search_ms': search_ms,
                         'selected': selected, 'rss_bytes': psutil.Process().memory_info().rss})
    full = []
    for i in range(5):
        start = perf_counter()
        response = backend.query(QUESTION, {}, 'B', 'EXTRACT', 5, False, 'automatic_real')
        if response['answer']['result_values'] != ['23276000000']:
            raise AssertionError('P7_FULL_PIPELINE_CONTROL_FAILED')
        full.append({'repeat': i, 'wall_ms': round((perf_counter() - start) * 1000, 3),
                     'stages_ms': response['timings_ms'],
                     'rss_bytes': psutil.Process().memory_info().rss})
    return {'schema_version': 'topic3-p7-observational-budget/v1', 'dataset': catalog.dataset_id,
            'generation': scope.generation_id, 'policy_unchanged': True, 'heldout_used': False,
            'original_selected_rank': 47, 'budgets': rows, 'full_pipeline': full,
            'full_p50_ms': percentile([x['wall_ms'] for x in full], .5),
            'full_p95_ms_nearest_rank': percentile([x['wall_ms'] for x in full], .95),
            'peak_observed_rss_bytes': max(x['rss_bytes'] for x in rows + full)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = run(args.root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'budget_measurements': len(result['budgets']),
                      'full_p50_ms': result['full_p50_ms'],
                      'full_p95_ms': result['full_p95_ms_nearest_rank']}))

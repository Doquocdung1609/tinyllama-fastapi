"""Read-only, explicitly scoped real-source probe for the opt-in recovery adapter.

Usage: python scripts/recovery_real_sec_probe.py --root <owned-research-root> --output <json>
Never downloads or mutates source/index data.
"""
import argparse
import json
from pathlib import Path
from time import perf_counter
from app.research_retrieval.snapshot import FrozenResearchSnapshot
from app.research_qa.real_cells import RealCellRequestV1, answer_from_verified_real_cells


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    snapshot = FrozenResearchSnapshot(args.root)
    base = dict(parent_id='fin_d411518414b61a2eb637d96721c5aaed', cik='0000080424',
                accession='0000080424-26-000256', table_id='table_24f0cc566ca5c5871edfcdb7')
    cases = [('EXTRACT', ('2026-09-30',)), ('COMPARE', ('2025-09-30', '2026-09-30')),
             ('ABS_CHANGE', ('2025-09-30', '2026-09-30')),
             ('PERCENT_CHANGE', ('2025-09-30', '2026-09-30')),
             ('COMPARE', ('2024-09-30', '2026-09-30'))]
    rows = []
    for operation, ends in cases:
        start = perf_counter()
        result = answer_from_verified_real_cells(snapshot, RealCellRequestV1(**base, operation=operation, period_ends=ends))
        rows.append({'operation': operation, 'requested_period_ends': ends,
                     'elapsed_ms': round((perf_counter()-start)*1000, 3),
                     'result': result.model_dump(mode='json')})
    output = {'schema_version': 'topic3-real-sec-recovery-probe/v1',
              'generation': snapshot.freeze['generation'], 'manifest_hash': snapshot.freeze['manifest_hash'],
              'cases': rows}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'cases': len(rows), 'statuses': [r['result']['status'] for r in rows],
                      'output': str(args.output)}, ensure_ascii=False))


if __name__ == '__main__':
    main()

"""Publish small, non-gold G3S audit indexes from immutable private evidence."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs/topic3_v7a_g3'
DOWNLOADS = Path('C:/Users/Admin/Downloads')
ARCHIVE = DOWNLOADS / 'V7A_G3S_SEC47_SOURCE_RECOVERY_20261102/V7A_G3S_SEC47_RAW_SOURCE_MANIFEST.json'
EVIDENCE = DOWNLOADS / 'V7A_G3S_PRIVATE_EVIDENCE_AUDIT_20261102_V6'
G3R = DOWNLOADS / 'V7A_G3R_PRIVATE_AUDIT_20261102_V5'


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def save_json(name: str, value: object) -> None:
    (DOCS / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def save_csv(name: str, rows: list[dict]) -> None:
    with (DOCS / name).open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    registry = json.loads(ARCHIVE.read_text(encoding='utf-8'))
    audit_path = EVIDENCE / 'V7A_G3S_94_SOURCE_EVIDENCE_AUDIT.csv'
    cells_path = EVIDENCE / 'V7A_G3S_FINANCIAL_CELL_EVIDENCE.jsonl'
    narrative_path = EVIDENCE / 'V7A_G3S_NARRATIVE_SUPPORT_AUDIT.csv'
    audit = read_csv(audit_path)
    narratives = read_csv(narrative_path)
    cells = [json.loads(line) for line in cells_path.read_text(encoding='utf-8').splitlines() if line]
    queue = read_csv(G3R / 'V7A_G3R_HUMAN_ADJUDICATION_QUEUE.csv')
    if len(registry['sources']) != 47 or len(audit) != 94 or len(queue) != 94:
        raise ValueError('Frozen source/question counts changed')
    if {x['question_id'] for x in audit} != {x['question_id'] for x in queue}:
        raise ValueError('G3S and G3R question IDs differ')
    if any(x['state'] != 'VERIFIED_RAW_PRIMARY' for x in registry['sources']):
        raise ValueError('One or more primary sources unverified')

    source_packages = {**registry['packages'], 'G3S_THIRTY': {
        'path': str(DOWNLOADS / 'V7A_G3S_SEC47_SOURCE_RECOVERY_20261102_SOURCE_HANDOFF.zip'),
        'sha256': digest(DOWNLOADS / 'V7A_G3S_SEC47_SOURCE_RECOVERY_20261102_SOURCE_HANDOFF.zip')}}
    public_sources = [{k: x.get(k, '') for k in (
        'accession', 'ticker', 'cik', 'form', 'report_date', 'source_url',
        'primary_filename', 'origin_package', 'source_zip_member', 'sha256',
        'byte_size', 'state')} for x in registry['sources']]
    save_json('V7A_G3S_SEC47_RAW_SOURCE_MANIFEST.json', {
        'schema': 'g3s_sec47_public_source_index/v1',
        'frozen_g2_manifest_sha256': registry['frozen_g2_manifest_sha256'],
        'private_registry_sha256': digest(ARCHIVE),
        'verified': 47, 'newly_acquired': 30, 'failed': 0,
        'source_packages': source_packages, 'sources': public_sources})

    # Public audit deliberately omits proposed answer values. Full evidence stays outside Git.
    fields = ('question_id', 'accession', 'ticker', 'source_sha256',
              'historical_classification', 'post_source_decision_relation',
              'proposed_cell_count', 'source_cell_levels', 'source_evidence_level',
              'human_review_state')
    save_csv('V7A_G3S_94_SOURCE_EVIDENCE_AUDIT.csv',
             [{k: r[k] for k in fields} for r in audit])
    public_cells = [{k: c.get(k, '') for k in (
        'question_id', 'cell_index', 'accession', 'source_sha256', 'source_evidence_level',
        'source_locator', 'candidate_count', 'all_candidate_locators')} for c in cells]
    with (DOCS / 'V7A_G3S_FINANCIAL_CELL_EVIDENCE.jsonl').open('w', encoding='utf-8') as stream:
        for c in public_cells:
            stream.write(json.dumps(c, ensure_ascii=False, separators=(',', ':')) + '\n')
    save_csv('V7A_G3S_NARRATIVE_SUPPORT_AUDIT.csv',
             [{k: r[k] for k in ('question_id', 'accession', 'source_sha256',
                                  'source_evidence_level', 'whole_proposition_human_verified',
                                  'curated_source_locator')} for r in narratives])

    priorities = {'V7A_G2_05_01', 'V7A_G2_09_02', 'V7A_G2_12_01',
                  'V7A_G2_12_02', 'V7A_G2_14_02', 'V7A_G2_15_01',
                  'V7A_G2_21_01', 'V7A_G2_24_01', 'V7A_G2_25_02',
                  'V7A_G2_30_01', 'V7A_G2_32_01', 'V7A_G2_38_01'}
    rows_by_id = {r['question_id']: r for r in audit}
    public_queue = []
    for q in queue:
        a = rows_by_id[q['question_id']]
        priority = ('P0_DISPUTE_OR_UNRESOLVED' if q['question_id'] in priorities else
                    'P1_SOURCE_SCOPE' if a['source_evidence_level'] == 'SOURCE_EVIDENCE_PARTIAL_REVIEW_REQUIRED' else
                    'P2_NARRATIVE' if a['source_evidence_level'] == 'SOURCE_PASSAGE_CANDIDATE' else
                    'P3_REMAINING')
        public_queue.append({'priority': priority, 'question_id': q['question_id'],
                             'ticker': a['ticker'], 'accession': q['accession'],
                             'agent1_decision': q['agent1_decision'],
                             'agent2_decision': q['agent2_decision'],
                             'source_evidence_level': a['source_evidence_level'],
                             'human_decision': ''})
    public_queue.sort(key=lambda r: (r['priority'], r['ticker'], r['accession'], r['question_id']))
    save_csv('V7A_G3S_HUMAN_ADJUDICATION_QUEUE.csv', public_queue)
    print(json.dumps({'sources': len(public_sources), 'questions': len(audit),
                      'cells': len(cells), 'narratives': len(narratives),
                      'priority_cases': sum(q['question_id'] in priorities for q in queue),
                      'private_cell_evidence_sha256': digest(cells_path)}, indent=2))


if __name__ == '__main__':
    main()

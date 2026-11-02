"""Validate the committed, unscored V7A G2 blind-review release."""

import csv
import hashlib
import io
import json
import re
import zipfile
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/topic3_v7a_g2'


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def rows(name: str):
    return list(csv.DictReader(io.StringIO((OUT / name).read_text(encoding='utf-8'))))


def test_coverage_and_public_query_leakage():
    design = rows('V7A_SEC47_QUESTION_DESIGN_V1.csv')
    public = rows('V7A_SEC47_QUESTION_ONLY.csv')
    private = rows('V7A_SEC47_PRIVATE_SOURCE_MANIFEST.csv')
    assert len(design) == len(public) == len(private) == 94
    assert len({r['question_id'] for r in public}) == 94
    assert len({r['question'] for r in public}) == 94
    assert Counter(r['accession_number'] for r in private) == {a: 2 for a in set(r['accession_number'] for r in private)}
    assert len({r['accession_number'] for r in private}) == 47
    assert len({r['ticker'] for r in private}) == 10
    assert set(r['form_type'] for r in private) == {'10-K', '10-Q', '20-F', '6-K'}
    for r in public:
        q = r['question']
        assert not re.search(r'\b\d{10}-\d{2}-\d{6}\b', q)
        assert 'http://' not in q and 'https://' not in q
        assert '_chunk_' not in q.lower()


def test_blind_packages_share_identical_inputs_and_blank_templates():
    shared = {'QUESTION_ONLY.csv', 'SOURCE_FILINGS.csv', 'SOURCE_LOOKUP.md', 'REVIEW_RUBRIC.md', 'READ_FIRST.md'}
    packages = []
    for agent in ('AGENT1', 'AGENT2'):
        with zipfile.ZipFile(OUT / f'V7A_{agent}_BLIND_REVIEW_PACKAGE.zip') as z:
            names = set(z.namelist())
            assert shared.issubset(names)
            template = f'{agent}_EMPTY_REVIEW_TEMPLATE.csv'
            assert names == shared | {template}
            assert 'agent1' not in z.read('SOURCE_FILINGS.csv').decode('utf-8').lower()
            assert 'exact_value' not in z.read('SOURCE_FILINGS.csv').decode('utf-8').lower()
            blank = list(csv.DictReader(io.StringIO(z.read(template).decode('utf-8'))))
            assert len(blank) == 94
            assert all(all(not value for key, value in row.items() if key != 'question_id') for row in blank)
            packages.append({name: z.read(name) for name in shared})
    assert packages[0] == packages[1]


def test_freeze_hashes_and_v6_integrity():
    manifest = json.loads((OUT / 'V7A_G2_FREEZE_MANIFEST.json').read_text(encoding='utf-8'))
    for name, expected in manifest['output_sha256'].items():
        assert sha((OUT / name).read_bytes()) == expected
    assert sha((ROOT / 'docs/topic3_v6/V6_FRESH_HOLDOUT_30_UNJUDGED.csv').read_bytes()) == manifest['v6_sealed_csv_sha256_unchanged']
    with zipfile.ZipFile(OUT / 'V7A_AGENT1_BLIND_REVIEW_PACKAGE.zip') as z:
        for name, expected in manifest['shared_blind_input_sha256'].items():
            assert sha(z.read(name)) == expected


def test_overlap_audit_has_all_reference_sets_for_each_question():
    overlap = rows('V7A_QUESTION_OVERLAP_AUDIT.csv')
    assert len(overlap) == 94 * 6
    assert Counter(r['question_id'] for r in overlap) == {q: 6 for q in set(r['question_id'] for r in overlap)}
    assert {r['reference_set'] for r in overlap} == {'P5', 'P7L15', 'F10_60', 'F10_192', 'V6_PILOT30', 'V6_SEALED30'}

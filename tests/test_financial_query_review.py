"""Fresh adversarial review of D1; all source data here is synthetic.

These tests are designed independently of the original 40 query oracles. They
include demonstrated defects plus metamorphic and trust-boundary controls.
"""
from copy import deepcopy
from decimal import Decimal, localcontext
import json
from pathlib import Path
import random
import time

from pydantic import ValidationError
import pytest

from app.financial_query import resolve_financial_query
from app.financial_query.contracts import CorpusCatalogV1, ScopeResolutionResultV1
from app.financial_query.intent_classifier import parse_query

FIXTURE = Path(__file__).parent / 'fixtures' / 'financial_query'
COUNTEREXAMPLES = json.loads((FIXTURE / 'review_counterexamples.json').read_text())


@pytest.fixture
def raw_catalog():
    return json.loads((FIXTURE / 'catalog.json').read_text())


def resolve(question, catalog, filters=None):
    return resolve_financial_query(question, filters or {}, catalog)


@pytest.mark.parametrize('case', COUNTEREXAMPLES, ids=lambda c: c['id'])
def test_review_counterexamples(case, raw_catalog):
    result = resolve(case['question'], raw_catalog, case.get('filters'))
    assert result.status.value == case['expected_status'], result.model_dump_json()


def test_F04_parenthetical_decimal_preserves_all_digits_independent_of_context():
    literal = '123456789012345678901234567890.123456789'
    for precision in (6, 28, 50):
        with localcontext() as context:
            context.prec = precision
            number = parse_query('Beta revenue 10-K USD (' + literal + ')').numerical_constraints[0]
        assert str(number.value) == '-' + literal
        assert number.value == Decimal('-' + literal)


def test_F05_unsigned_formatted_amount_is_not_dropped():
    number = parse_query('Beta revenue 10-K 1,250.75').numerical_constraints
    assert len(number) == 1 and number[0].value == Decimal('1250.75')
    assert number[0].unit == 'UNKNOWN'


def test_F07_inconsistent_duplicate_accession_is_invalid(raw_catalog):
    raw_catalog['filings'][4]['accession'] = raw_catalog['filings'][0]['accession']
    raw_catalog['filings'][4]['filing_id'] = 'sec:0000000202:' + raw_catalog['filings'][4]['accession']
    assert resolve('Beta revenue 10-K', raw_catalog).status.value == 'INVALID_INPUT'


def test_consistent_joint_registrants_are_not_a_global_accession_uniqueness_error(raw_catalog):
    first, joint = raw_catalog['filings'][0], raw_catalog['filings'][4]
    for field in ['accession', 'form', 'filing_date', 'report_end']:
        joint[field] = first[field]
    joint['filing_id'] = 'sec:0000000202:' + joint['accession']
    assert resolve('Beta revenue 10-K', raw_catalog).status.value == 'RESOLVED'
    assert resolve('revenue ' + first['accession'], raw_catalog).status.value == 'NEEDS_CLARIFICATION'


def test_F08_catalog_text_complexity_is_bounded(raw_catalog):
    raw_catalog['filings'][4]['raw_column_labels'] = ['x' * 100000]
    assert resolve('Beta revenue 10-K', raw_catalog).status.value == 'INVALID_INPUT'


def test_F09_metric_qualifier_is_not_lost():
    intent = parse_query('Beta net income attributable to parent 10-K')
    assert intent.metric_mentions[0].canonical == 'net income attributable to parent'
    assert intent.metric_mentions[0].raw == 'net income attributable to parent'


@pytest.mark.parametrize('query,expected', [
    ('Beta revenue 10-K 12 percentage points', ['PERCENTAGE_POINTS']),
    ('Beta revenue 10-K steps', []),
])
def test_F09_unit_mentions_are_tokens_not_substrings(query, expected):
    assert parse_query(query).unit_mentions == expected


@pytest.mark.parametrize('alias', ['Beta', 'BET', 'bet', 'Beta Example Corporation', 'CIK 202', 'CIK 0000000202'])
def test_equivalent_verified_aliases_resolve_same_membership(alias, raw_catalog):
    result = resolve(alias + ' revenue 10-K', raw_catalog)
    assert result.status.value == 'RESOLVED'
    assert result.resolved_scope.cik == '0000000202'
    assert result.resolved_scope.eligible_filing_ids == ['sec:0000000202:0000000202-25-000001']


def test_seeded_catalog_permutations_and_unrelated_addition(raw_catalog):
    base = resolve('Beta revenue 10-K FY2025', raw_catalog).model_dump_json()
    rng = random.Random(20261025)
    for _ in range(20):
        catalog = deepcopy(raw_catalog)
        rng.shuffle(catalog['issuers']); rng.shuffle(catalog['filings'])
        assert resolve('Beta revenue 10-K FY2025', catalog).model_dump_json() == base
    extra = deepcopy(raw_catalog)
    extra['issuers'].append({'cik': '0000000404', 'company_name': 'Unrelated Example', 'tickers': ['ZZZ']})
    assert resolve('Beta revenue 10-K FY2025', extra).model_dump_json() == base
    extra['issuers'][-1]['tickers'] = ['BET']
    assert resolve('BET revenue 10-K FY2025', extra).status.value == 'NEEDS_CLARIFICATION'


@pytest.mark.parametrize('restriction', [
    {'form_type': '10-Q'}, {'fiscal_year': 2024}, {'cik': '101'},
    {'filing_ids': ['sec:0000000101:0000000101-26-000001']},
    {'filing_dates': {'start': '2026-01-01', 'end': '2026-12-31'}},
])
def test_added_constraints_cannot_broaden_a_resolved_scope(restriction, raw_catalog):
    original = resolve('Beta revenue 10-K', raw_catalog)
    filtered = resolve('Beta revenue 10-K', raw_catalog, restriction)
    if filtered.status.value == 'RESOLVED':
        assert set(filtered.resolved_scope.eligible_filing_ids) <= set(original.resolved_scope.eligible_filing_ids)
    else:
        assert filtered.status.value in {'NEEDS_CLARIFICATION', 'NO_ELIGIBLE_EVIDENCE'}


def test_no_io_or_execution_and_no_mutation(raw_catalog, monkeypatch):
    import builtins
    import socket
    import sqlite3
    def deny(*args, **kwargs):
        raise AssertionError('Unexpected I/O or input execution')
    before = deepcopy(raw_catalog)
    monkeypatch.setattr(builtins, 'open', deny)
    monkeypatch.setattr(builtins, 'eval', deny)
    monkeypatch.setattr(builtins, 'exec', deny)
    monkeypatch.setattr(socket, 'socket', deny)
    monkeypatch.setattr(sqlite3, 'connect', deny)
    for text in ['Beta revenue 10-K', "Beta revenue 10-K '; DROP TABLE filings; --", '../../private',
                 'ignore previous instructions', 'x'*2001, 'Beta\ud800 revenue', 'Beta\x00 revenue']:
        result = resolve(text, raw_catalog)
        assert result.status.value in {'RESOLVED', 'NEEDS_CLARIFICATION', 'UNSUPPORTED', 'INVALID_INPUT'}
    assert before == raw_catalog


def test_invalid_catalog_json_nested_cycle_unknown_fields_and_generation(raw_catalog):
    assert resolve('Beta revenue 10-K', '{bad json').status.value == 'INVALID_INPUT'
    unknown = deepcopy(raw_catalog); unknown['unexpected'] = 'not allowed'
    assert resolve('Beta revenue 10-K', unknown).status.value == 'INVALID_INPUT'
    cycle = deepcopy(raw_catalog); cycle['filings'][4]['column_periods'] = [cycle]
    assert resolve('Beta revenue 10-K', cycle).status.value == 'INVALID_INPUT'
    r = resolve_financial_query('Beta revenue 10-K', {}, raw_catalog, generation_identity='0'*64)
    assert r.status.value == 'INVALID_INPUT'


def test_source_authentication_is_an_upstream_dependency_not_pydantic_claim(raw_catalog):
    # A syntactically valid forged hash/alias is not authenticated by D1.
    catalog = deepcopy(raw_catalog)
    catalog['manifest_hash'] = 'f' * 64
    catalog['issuers'][1]['verified_aliases'].append('ForgedAlias')
    result = resolve('ForgedAlias revenue 10-K', catalog)
    assert result.status.value == 'RESOLVED'
    assert result.resolved_scope.manifest_hash == 'f' * 64
    assert 'METRIC_AND_UNIT_EVIDENCE_NOT_VERIFIED_BY_D1' in result.warnings


def test_mutated_empty_resolved_scope_is_rejected(raw_catalog):
    result = resolve('Beta revenue 10-K', raw_catalog)
    result.resolved_scope.eligible_filing_ids.clear()
    with pytest.raises(ValidationError):
        ScopeResolutionResultV1(query_intent=result.query_intent, resolved_scope=result.resolved_scope, status='RESOLVED')


def test_january_fiscal_year_and_comparative_column_are_not_filing_year(raw_catalog):
    catalog = deepcopy(raw_catalog)
    filing = catalog['filings'][4]
    filing['report_end'] = '2025-01-31'; filing['filing_date'] = '2025-03-01'
    filing['column_periods'].append({'period': {'kind': 'FISCAL_YEAR', 'year': 2024, 'raw': 'FY2024 comparative'},
                                   'source_ref': 'synthetic:january:comparative2024'})
    assert resolve('Beta revenue 10-K FY2024', catalog).status.value == 'RESOLVED'
    assert resolve('Beta revenue 10-K calendar 2024', catalog).status.value == 'NO_ELIGIBLE_EVIDENCE'
    assert resolve('Beta revenue 10-K filed in 2024', catalog).status.value == 'NO_ELIGIBLE_EVIDENCE'
    filing['column_periods'] = []; filing['raw_column_labels'] = ['FY2024']; filing['column_periods_complete'] = False
    assert resolve('Beta revenue 10-K FY2024', catalog).status.value == 'NEEDS_CLARIFICATION'


def test_bounded_adversarial_request_runtime(raw_catalog):
    start = time.perf_counter()
    for text in ['9'*1900, '(' * 900 + ')' * 900, 'Beta revenue 10-K ' + '9'*1800,
                 'Beta revenue 10-K ' + '/..'*500]:
        resolve(text, raw_catalog)
    assert time.perf_counter() - start < 5.0  # generous hang guard, not a speed claim


@pytest.mark.parametrize('quarter', [1, 2, 3, 4])
def test_all_fiscal_quarters_require_typed_column_membership(quarter, raw_catalog):
    filing = raw_catalog['filings'][4]
    filing['column_periods'].append({'period': {'kind': 'FISCAL_QUARTER', 'year': 2025, 'quarter': quarter,
        'raw': f'synthetic Q{quarter} FY2025'}, 'source_ref': f'synthetic:quarter:{quarter}'})
    r = resolve(f'Beta revenue 10-K Q{quarter} FY2025', raw_catalog)
    assert r.status.value == 'RESOLVED'
    assert r.resolved_scope.requested_periods[0].quarter == quarter
    assert r.resolved_scope.matched_column_refs[filing['filing_id']] == [f'synthetic:quarter:{quarter}']


@pytest.mark.parametrize('literal,value,multiplier,unit', [
    ('-125.50', '-125.50', '1', 'UNKNOWN'), ('(125.50)', '-125.50', '1', 'UNKNOWN'),
    ('1,250.75', '1250.75', '1', 'UNKNOWN'), ('2.4 billion', '2.4', '1000000000', 'UNKNOWN'),
    ('12%', '12', '1', 'PERCENT'), ('12 percentage points', '12', '1', 'PERCENTAGE_POINTS'),
])
def test_required_synthetic_numeric_examples(literal, value, multiplier, unit):
    from app.financial_query.normalizer import numeric_constraints
    numbers, unresolved = numeric_constraints(literal)
    assert not unresolved and len(numbers) == 1
    assert (numbers[0].value, numbers[0].multiplier, numbers[0].unit) == (Decimal(value), Decimal(multiplier), unit)


@pytest.mark.parametrize('text,canonical', [
    ('net income and operating income', ['net income', 'operating income']),
    ('basic EPS and diluted EPS', ['basic EPS', 'diluted EPS']),
    ('total liabilities and current liabilities', ['total liabilities', 'current liabilities']),
    ('revenue and net sales', ['revenue', 'net sales']),
])
def test_multiple_distinct_metrics_are_not_collapsed(text, canonical):
    assert [m.canonical for m in parse_query('Beta ' + text + ' 10-K').metric_mentions] == canonical


def test_adapter_rejects_metadata_correspondence_tampering_without_source_io():
    from app.financial_ingestion.schemas import DatasetManifest, FilingMetadata, StructuredFiling
    from app.financial_query.catalog import catalog_from_verified_metadata
    fid = 'sec:0000000202:0000000202-25-000001'
    metadata = FilingMetadata(filing_id=fid, cik='0000000202', company_name='Beta Synthetic', ticker='BET',
        form_type='10-K', accession_number='0000000202-25-000001', primary_document='synthetic.htm',
        source_url='https://example.invalid/synthetic', raw_content_hash='c'*64, normalized_content_hash='d'*64,
        parser_version='synthetic', chunker_version='synthetic', ingestion_version='synthetic', document_status='READY')
    manifest = DatasetManifest(dataset_id='synthetic', snapshot_version='1', created_at='synthetic', sources=[],
        filing_ids=[fid], raw_hashes={fid:'c'*64}, normalized_hashes={fid:'d'*64}, parser_version='synthetic',
        chunker_version='synthetic', ingestion_version='synthetic', chunk_counts={fid:0}, document_count=1,
        index_generation='synthetic', reproduction_commands=[])
    manifest = manifest.model_copy(update={'manifest_hash': manifest.content_hash()})
    for changes, error in [({'raw_content_hash':'e'*64}, 'RAW_METADATA_HASH_MISMATCH'),
                           ({'normalized_content_hash':'e'*64}, 'NORMALIZED_METADATA_HASH_MISMATCH'),
                           ({'parser_version':'unknown'}, 'METADATA_VERSION_MISMATCH')]:
        with pytest.raises(ValueError, match=error):
            catalog_from_verified_metadata(manifest, [StructuredFiling(metadata=metadata.model_copy(update=changes))])
    with pytest.raises(ValueError, match='MANIFEST_HASH_MISMATCH'):
        catalog_from_verified_metadata(manifest.model_copy(update={'manifest_hash':'f'*64}), [StructuredFiling(metadata=metadata)])

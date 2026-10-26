"""D4 test-first source-bound numeric/claim oracles; every value is synthetic."""
from decimal import Decimal
import pytest
from test_table_evidence import source,CASES
from app.table_evidence import build_evidence_bundle
from app.research_qa import answer_from_bundle,verify_claim
from app.research_qa.contracts import NumericRequestV1


def bound(case=0):
    p,ctx,*_=source(CASES[case]);bundle=build_evidence_bundle([p],ctx)
    return ctx,bundle,bundle.results[0].evidence.cells[1:]


def test_exact_source_extraction_preserves_raw_and_citation():
    ctx,bundle,cells=bound()
    request=NumericRequestV1(operation='EXTRACT',metric='Net sales',cell_ids=(cells[0].evidence_id,))
    result=answer_from_bundle(request,bundle,ctx)
    assert result.status=='SUPPORTED' and result.claims[0].result_values==(Decimal(100000000),)
    operand=result.claims[0].operands[0]
    assert operand.raw_value=='100' and operand.multiplier==Decimal(1000000)
    assert operand.row==1 and operand.column==1 and operand.source_url=='https://example.invalid/synthetic'
    assert operand.structural_path.endswith('/tr[2]/td[2]')
    assert verify_claim(request,result.claims[0],bundle,ctx)


@pytest.mark.parametrize('operation,expected,unit',[
    ('COMPARE',('90000000','100000000'),'USD'),
    ('ABS_CHANGE',('10000000',),'USD'),
    ('PERCENT_CHANGE',('11.11111111111111111111111111',),'PERCENT'),
])
def test_comparison_arithmetic_uses_old_then_new_source_periods(operation,expected,unit):
    ctx,bundle,cells=bound()
    request=NumericRequestV1(operation=operation,metric='Net sales',cell_ids=(cells[1].evidence_id,cells[0].evidence_id))
    result=answer_from_bundle(request,bundle,ctx)
    assert result.status=='SUPPORTED',result.model_dump_json()
    assert tuple(str(v) for v in result.claims[0].result_values)==expected
    assert result.claims[0].unit==unit and result.claims[0].formula


def test_negative_source_is_not_negated_twice_and_eps_not_scaled():
    for case,value,unit in [(1,'-125500.00','USD'),(3,'2.74','USD_PER_SHARE')]:
        ctx,bundle,cells=bound(case)
        result=answer_from_bundle(NumericRequestV1(operation='EXTRACT',metric=CASES[case]['row'],cell_ids=(cells[0].evidence_id,)),bundle,ctx)
        assert result.status=='SUPPORTED'
        assert result.claims[0].result_values[0]==Decimal(value) and result.claims[0].unit==unit


def test_mutated_numeric_claim_or_citation_does_not_verify():
    ctx,bundle,cells=bound();request=NumericRequestV1(operation='EXTRACT',metric='Net sales',cell_ids=(cells[0].evidence_id,))
    claim=answer_from_bundle(request,bundle,ctx).claims[0]
    for altered in [claim.model_copy(update={'result_values':(Decimal(999),)}),
                    claim.model_copy(update={'operands':(claim.operands[0].model_copy(update={'column':99}),)})]:
        assert not verify_claim(request,altered,bundle,ctx)


@pytest.mark.parametrize('case',[4])
def test_partial_bundle_abstains(case):
    ctx,bundle,cells=bound(case)
    r=answer_from_bundle(NumericRequestV1(operation='EXTRACT',metric=CASES[case]['row'],cell_ids=(cells[0].evidence_id,)),bundle,ctx)
    assert r.status=='INSUFFICIENT_EVIDENCE' and not r.claims


def test_wrong_metric_missing_cell_or_generation_cannot_answer():
    ctx,bundle,cells=bound()
    for metric,ids in [('Operating income',(cells[0].evidence_id,)),('Net sales',('cell_'+'0'*64,))]:
        r=answer_from_bundle(NumericRequestV1(operation='EXTRACT',metric=metric,cell_ids=ids),bundle,ctx)
        assert r.status!='SUPPORTED' and not r.claims
    tampered=bundle.model_copy(update={'source_generation':'f'*64})
    r=answer_from_bundle(NumericRequestV1(operation='EXTRACT',metric='Net sales',cell_ids=(cells[0].evidence_id,)),tampered,ctx)
    assert r.status=='CONFLICTED_EVIDENCE' and not r.claims


def test_unknown_operation_expression_extra_fields_are_rejected():
    for payload in [{'operation':'eval','metric':'Net sales','cell_ids':()},
                    {'operation':'EXTRACT','metric':'Net sales','cell_ids':('cell_'+'0'*64,),'expression':'__import__("os")'},
                    {'operation':'EXTRACT','metric':'Net sales','cell_ids':('cell_'+'0'*64,)*9}]:
        with pytest.raises(ValueError):NumericRequestV1.model_validate(payload)


def test_reverse_change_and_mixed_measurement_basis_abstain():
    ctx,bundle,cells=bound()
    r=answer_from_bundle(NumericRequestV1(operation='ABS_CHANGE',metric='Net sales',cell_ids=(cells[0].evidence_id,cells[1].evidence_id)),bundle,ctx)
    assert r.status=='UNSUPPORTED_OPERATION'
    ctx,bundle,cells=bound(5)
    r=answer_from_bundle(NumericRequestV1(operation='COMPARE',metric='Long-term debt',cell_ids=(cells[0].evidence_id,cells[1].evidence_id)),bundle,ctx)
    assert r.status!='SUPPORTED'


def custom(headers,values,row='Net sales'):
    from test_table_evidence import html_row
    html=html_row(headers,values,row=row).replace('Synthetic statement','Consolidated statement')
    p,ctx,*_=source({**CASES[0],'row':row},html=html);b=build_evidence_bundle([p],ctx)
    return ctx,b,b.results[0].evidence.cells[1:]


@pytest.mark.parametrize('operation,expected,unit',[
    ('PERCENTAGE_POINTS','-2','PERCENTAGE_POINTS'),
    ('PERCENT_CHANGE','-16.66666666666666666666666667','PERCENT'),
])
def test_percent_vs_percentage_points_are_distinct(operation,expected,unit):
    ctx,b,cells=custom(['FY2024','FY2025'],['12%','10%'],'Operating margin')
    r=answer_from_bundle(NumericRequestV1(operation=operation,metric='Operating margin',cell_ids=tuple(c.evidence_id for c in cells)),b,ctx)
    assert r.status=='SUPPORTED' and r.claims[0].result_values==(Decimal(expected),) and r.claims[0].unit==unit


@pytest.mark.parametrize('base',['0','(10)'])
def test_nonpositive_percent_denominator_is_unsupported(base):
    ctx,b,cells=custom(['FY2024','FY2025'],[base,'20'])
    r=answer_from_bundle(NumericRequestV1(operation='PERCENT_CHANGE',metric='Net sales',cell_ids=tuple(c.evidence_id for c in cells)),b,ctx)
    assert r.status=='UNSUPPORTED_OPERATION' and not r.claims


@pytest.mark.parametrize('headers',[
    ['FY2024 / GAAP','FY2025 / Non-GAAP'],
    ['FY2024 / Segment A','FY2025 / Consolidated'],
])
def test_hidden_accounting_or_entity_header_mismatch_cannot_compare(headers):
    ctx,b,cells=custom(headers,['90','100'])
    r=answer_from_bundle(NumericRequestV1(operation='COMPARE',metric='Net sales',cell_ids=tuple(c.evidence_id for c in cells)),b,ctx)
    assert r.status!='SUPPORTED' and not r.claims


@pytest.mark.parametrize('headers',[
    ['Quarter ended January 31, 2024','Year ended January 31, 2025'],
    ['As of January 31, 2024','Year ended January 31, 2025'],
])
def test_quarter_annual_and_instant_duration_never_mix(headers):
    ctx,b,cells=custom(headers,['90','100'])
    r=answer_from_bundle(NumericRequestV1(operation='COMPARE',metric='Net sales',cell_ids=tuple(c.evidence_id for c in cells)),b,ctx)
    assert r.status=='UNSUPPORTED_OPERATION'


def test_large_or_overprecise_operands_are_rejected_not_rounded():
    ctx,b,cells=custom(['FY2025'],['123456789012345678901234567890.123456789'])
    r=answer_from_bundle(NumericRequestV1(operation='EXTRACT',metric='Net sales',cell_ids=(cells[0].evidence_id,)),b,ctx)
    assert r.status=='UNSUPPORTED_OPERATION' and not r.claims


def test_measurement_basis_filter_cannot_silently_select_other_basis():
    ctx,b,cells=bound(5)
    r=answer_from_bundle(NumericRequestV1(operation='EXTRACT',metric='Long-term debt',measurement_basis='CARRYING_VALUE',cell_ids=(cells[1].evidence_id,)),b,ctx)
    assert r.status=='CONFLICTED_EVIDENCE' and not r.claims


def test_claim_schema_stable_serialization_and_no_parent_mutation():
    ctx,b,cells=bound();before=b.model_dump_json()
    req=NumericRequestV1(operation='EXTRACT',metric='Net sales',cell_ids=(cells[0].evidence_id,))
    a=answer_from_bundle(req,b,ctx);z=answer_from_bundle(req,b,ctx)
    assert a.model_dump_json()==z.model_dump_json() and before==b.model_dump_json()

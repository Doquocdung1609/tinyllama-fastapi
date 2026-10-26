"""D2 source-bound development oracles. Every filing/value is synthetic."""
import json
from copy import deepcopy
from decimal import Decimal, localcontext
from hashlib import sha256
from pathlib import Path

import pytest

from app.financial_ingestion import PARSER_VERSION, CHUNKER_VERSION, INGESTION_VERSION
from app.financial_ingestion.chunker import chunk_filing
from app.financial_ingestion.html_parser import parse_sec_html, normalized_filing_text
from app.financial_ingestion.schemas import FilingMetadata
from app.table_evidence import build_table_evidence, build_evidence_bundle, context_from_snapshot
from app.table_evidence.contracts import SourceBindingV1, EvidenceValidationResultV1
from app.table_evidence.identity import digest

CASES = json.loads((Path(__file__).parent / 'fixtures/table_evidence/cases.json').read_text())


def source(case=None, *, html=None):
    case = case or CASES[0]
    if html is None:
        html = ('<html><body><h1>' + case['title'] + '</h1><p>' + case['unit'] + '</p><table>'
                '<tr><th>Metric</th>' + ''.join('<th>'+h+'</th>' for h in case['headers']) + '</tr>'
                '<tr><td>'+case['row']+'</td>' + ''.join('<td>'+v+'</td>' for v in case['values']) + '</tr>'
                '</table></body></html>')
    raw = html.encode()
    meta = FilingMetadata(filing_id='sec:0000000202:0000000202-25-000001', cik='0000000202',
        accession_number='0000000202-25-000001', company_name='Synthetic D2', form_type='10-K',
        filing_date='2026-03-01', report_date='2025-01-31', primary_document='synthetic.htm',
        source_url='https://example.invalid/synthetic', raw_content_hash=sha256(raw).hexdigest(),
        parser_version=PARSER_VERSION, chunker_version=CHUNKER_VERSION, ingestion_version=INGESTION_VERSION,
        document_status='READY')
    filing = parse_sec_html(raw, meta.model_copy(deep=True))
    chunks = chunk_filing(filing)
    parent = next(c for c in chunks if c.kind == 'table' and c.metadata['row_label'] == case['row']) if html and case['row'] in html else next(c for c in chunks if c.kind=='table')
    binding = SourceBindingV1(dataset_id='synthetic-d2', manifest_hash='a'*64, generation_id='b'*64,
        filing_id=meta.filing_id, raw_hash=sha256(raw).hexdigest(),
        normalized_hash=sha256(normalized_filing_text(filing).encode()).hexdigest(),
        metadata_hash=digest(meta.model_dump(mode='json')),
        parent_hashes=tuple(sorted((c.chunk_id,digest(c.model_dump(mode='json'))) for c in chunks)))
    context = context_from_snapshot(raw, meta, binding)
    return parent, context, raw, meta, binding


@pytest.mark.parametrize('case', CASES, ids=lambda c:c['id'])
def test_six_families_exact_source_binding(case):
    parent,ctx,*_ = source(case)
    before = deepcopy(parent.model_dump())
    result = build_table_evidence(parent,ctx)
    assert result.status == ('PARTIAL_CONTEXT' if case['id']=='segment' else 'VERIFIED_CONTEXT')
    assert parent.model_dump() == before
    evidence = result.evidence
    assert evidence.original_parent_text == parent.text
    assert evidence.parent_payload_hash == digest(parent.model_dump(mode='json'))
    assert evidence.parent_chunk_id == parent.chunk_id and evidence.filing_date == '2026-03-01'
    cells = evidence.cells[1:]
    assert [c.original_text for c in cells] == case['values']
    assert [c.column for c in cells] == list(range(1,len(cells)+1))
    assert all(c.row == 1 and c.locator.structural_path.endswith(f'/tr[2]/td[{c.column+1}]') for c in cells)
    assert cells[0].unit == case['expected_unit'] and cells[0].multiplier == Decimal(case['scale'])
    assert cells[0].measurement_basis == case['role']
    assert cells[0].period.kind == case['kind']
    if 'ends' in case:
        assert [c.period.end for c in cells] == case['ends']
    else:
        assert [c.period.year if c.period else None for c in cells] == case['years']
        assert cells[-1].unit == 'PERCENT' and cells[-1].multiplier == Decimal(1)
        assert cells[1].measurement_basis == 'AMOUNT_CHANGE' and cells[-1].measurement_basis == 'PERCENT_CHANGE'
    if case['id']=='fair':
        assert cells[1].measurement_basis == 'FAIR_VALUE'
    if case['id']=='eps':
        assert cells[0].effective_value == Decimal('2.74')
    assert EvidenceValidationResultV1.model_validate_json(result.model_dump_json()) == result


def test_wrong_column_sorted_period_hazard():
    parent,ctx,*_=source()
    cells=build_table_evidence(parent,ctx).evidence.cells[1:]
    assert [(c.period.end,c.value) for c in cells] == [('2025-01-31',Decimal(100)),('2024-01-31',Decimal(90))]
    assert [(c.period.end,c.value) for c in cells] != [('2024-01-31',Decimal(100)),('2025-01-31',Decimal(90))]


def test_forged_parent_and_missing_context_fail_closed():
    parent,ctx,*_=source()
    for field,value in [('text',parent.text+' fake'),('chunk_id','fin_fake'),('filing_id','wrong')]:
        forged=parent.model_copy(update={field:value})
        assert build_table_evidence(forged,ctx).status=='INVALID_SOURCE'
    unverified=build_table_evidence(parent,None)
    assert unverified.status=='PARTIAL_CONTEXT'
    assert unverified.evidence.parent_provenance=='UNAUTHENTICATED'
    assert all(c.status!='VERIFIED_CONTEXT' for c in unverified.evidence.cells)


def test_context_checks_bytes_metadata_and_binding():
    parent,ctx,raw,meta,binding=source()
    for changed_raw,changed_meta,changed_binding in [
        (raw+b' ',meta,binding),(raw,meta.model_copy(update={'filing_date':'2020-01-01'}),binding),
        (raw,meta,binding.model_copy(update={'normalized_hash':'0'*64})),
        (raw,meta,binding.model_copy(update={'parent_hashes':((parent.chunk_id,'0'*64),)})),
    ]:
        with pytest.raises(ValueError):
            context_from_snapshot(changed_raw,changed_meta,changed_binding)


def test_contract_version_unknown_fields_immutable_and_deterministic():
    parent,ctx,*_=source()
    a=build_table_evidence(parent,ctx); b=build_table_evidence(parent,ctx)
    assert a.model_dump_json()==b.model_dump_json()
    with pytest.raises(ValueError):
        a.evidence.cells[1].column=77
    for update in [{'unknown':1},{'contract_version':'bad'}]:
        with pytest.raises(ValueError):
            EvidenceValidationResultV1.model_validate({**a.model_dump(),**update})
    assert a.evidence.cells[1].evidence_id!=a.evidence.cells[2].evidence_id


def html_row(headers,values,row='Net sales',unit='USD amounts in millions',extra='',tail=''):
    return ('<html><body><h1>Synthetic statement</h1><p>'+unit+'</p><table>'+extra+
            '<tr><th>Metric</th>'+''.join('<th>'+h+'</th>' for h in headers)+'</tr>'+
            '<tr><td>Control data row</td>'+''.join('<td>1</td>' for _ in values)+'</tr>'+
            '<tr><td>'+row+'</td>'+''.join('<td>'+v+'</td>' for v in values)+'</tr>'+tail+'</table></body></html>')


@pytest.mark.parametrize('headers,expected', [
    (['FY2025','FY2024'],[2025,2024]),(['FY2024','FY2025'],[2024,2025]),
    (['FY2026','FY2025','FY2024'],[2026,2025,2024]),(['FY2025','FY2025'],[2025,2025]),
])
def test_period_columns_never_sorted_or_deduplicated(headers,expected):
    p,ctx,*_=source(html=html_row(headers,[str(i+10) for i in range(len(headers))]))
    e=build_table_evidence(p,ctx).evidence
    assert [c.period.year for c in e.cells[1:]]==expected
    assert [c.value for c in e.cells[1:]]==[Decimal(i+10) for i in range(len(headers))]
    assert len({c.evidence_id for c in e.cells})==len(e.cells)


def test_multilevel_merged_headers_preserve_origin_and_hierarchy():
    html=('<html><body><p>USD amounts in millions</p><table>'
          '<tr><th rowspan="2">Metric</th><th colspan="2">As of January 31, 2025</th></tr>'
          '<tr><th>Carrying amount</th><th>Fair value</th></tr>'
          '<tr><td>Net sales</td><td>100</td><td>90</td></tr></table></body></html>')
    p,ctx,*_=source(html=html)
    e=build_table_evidence(p,ctx).evidence
    assert e.status=='VERIFIED_CONTEXT'
    a,b=e.cells[1:]
    assert (a.row,a.column,b.row,b.column)==(2,1,2,2)
    assert [(h.row,h.column,h.colspan) for h in a.header_path]==[(0,1,2),(1,1,1)]
    assert [(h.row,h.column,h.colspan) for h in b.header_path]==[(0,1,2),(1,2,1)]
    assert a.period.end==b.period.end=='2025-01-31'
    assert a.measurement_basis=='CARRYING_VALUE' and b.measurement_basis=='FAIR_VALUE'


@pytest.mark.parametrize('raw,expected,missing', [
    ('-125.50','-125.50','NUMBER'),('(125.50)','-125.50','NUMBER'),('1,250.75','1250.75','NUMBER'),
    ('−12.50','-12.50','NUMBER'),('+2.00','2.00','NUMBER'),('12%','12','NUMBER'),
    ('',None,'BLANK'),('-',None,'DASH'),('—',None,'DASH'),('N/A',None,'NOT_AVAILABLE'),
    ('1,23',None,'TEXT'),('10(1)',None,'TEXT'),('1e20',None,'TEXT'),('NaN',None,'TEXT'),
])
def test_raw_numeric_missing_sign_and_precision(raw,expected,missing):
    p,ctx,*_=source(html=html_row(['FY2025'],[raw]))
    c=build_table_evidence(p,ctx).evidence.cells[1]
    assert c.original_text==raw
    assert c.value==(Decimal(expected) if expected else None)
    assert c.missing_kind==missing
    if expected is None:
        assert c.effective_value is None and c.status=='PARTIAL_CONTEXT'


@pytest.mark.parametrize('precision',[6,28,50])
def test_decimal_cell_and_effective_values_do_not_round(precision):
    number='123456789012345678901234567890.123456789'
    p,ctx,*_=source(html=html_row(['FY2025'],['('+number+')']))
    with localcontext() as decimal_context:
        decimal_context.prec=precision
        c=build_table_evidence(p,ctx).evidence.cells[1]
    assert str(c.value)=='-'+number
    assert c.effective_value==Decimal('-123456789012345678901234567890123456.789')


@pytest.mark.parametrize('display,attrs,expected,status,code',[
    ('(125)','sign="-" scale="6"','-125','VERIFIED_CONTEXT',None),
    ('125','sign="-" scale="6"','-125','VERIFIED_CONTEXT',None),
    ('(125)','sign="+" scale="6"','-125','CONFLICTED_CONTEXT','INLINE_DISPLAY_SIGN_CONFLICT'),
    ('+125','sign="-" scale="6"','125','CONFLICTED_CONTEXT','INLINE_DISPLAY_SIGN_CONFLICT'),
    ('125','scale="0"','125','CONFLICTED_CONTEXT','INLINE_HEADER_SCALE_CONFLICT'),
    ('125','scale="99999"','125','PARTIAL_CONTEXT','UNSUPPORTED_INLINE_SCALE'),
    ('125','unitref="usd" contextref="c2024" scale="6"','125','PARTIAL_CONTEXT','XBRL_CONTEXT_RESOURCE_NOT_RETAINED'),
    ('125','format="ixt:unknown" scale="6"','125','PARTIAL_CONTEXT','UNSUPPORTED_XBRL_FORMAT'),
])
def test_inline_display_sign_scale_and_opaque_resources(display,attrs,expected,status,code):
    value='<ix:nonfraction '+attrs+'>'+display+'</ix:nonfraction>'
    p,ctx,*_=source(html=html_row(['FY2025'],[value]))
    c=build_table_evidence(p,ctx).evidence.cells[1]
    assert c.value==Decimal(expected) and c.status==status
    assert json.loads(c.inline_attributes[0])['source_text']==display
    if code:
        assert code in c.unresolved_fields or code in [v.code for v in c.conflicts]
        assert c.effective_value is None


@pytest.mark.parametrize('row,header,name,code',[
    ('Basic EPS','FY2025 / Diluted EPS','us-gaap:EarningsPerShareBasic','ROW_HEADER_MEASUREMENT_CONFLICT'),
    ('Basic EPS','FY2025','us-gaap:EarningsPerShareDiluted','INLINE_HEADER_EPS_CONFLICT'),
    ('Diluted EPS','FY2025','us-gaap:EarningsPerShareBasic','INLINE_HEADER_EPS_CONFLICT'),
    ('Net sales','As of January 31, 2025 / Carrying amount','us-gaap:LongTermDebtFairValue','INLINE_HEADER_MEASUREMENT_CONFLICT'),
])
def test_metric_context_conflicts_do_not_choose_plausible_values(row,header,name,code):
    case={**CASES[0],'row':row}
    p,ctx,*_=source(case,html=html_row([header],['<ix:nonfraction name="'+name+'">2.74</ix:nonfraction>'],row,
        'USD amounts in millions, except per share data' if 'EPS' in row else 'USD amounts in millions'))
    result=build_table_evidence(p,ctx); c=result.evidence.cells[1]
    assert result.status=='CONFLICTED_CONTEXT' and c.effective_value is None
    assert code in [x.code for x in c.conflicts]


def test_conflicting_header_periods_do_not_use_filing_date():
    html=('<html><body><p>USD amounts in millions</p><table>'
          '<tr><th>Metric</th><th>FY2025</th></tr><tr><th></th><th>FY2024</th></tr>'
          '<tr><td>Net sales</td><td>100</td></tr></table></body></html>')
    p,ctx,*_=source(html=html)
    c=build_table_evidence(p,ctx).evidence.cells[1]
    assert c.period is None and c.status=='CONFLICTED_CONTEXT'
    assert 'CONFLICTING_HEADER_PERIODS' in [v.code for v in c.conflicts]


@pytest.mark.parametrize('header,unit,expected,scale',[
    ('FY2025 / Percentage points','USD amounts in millions','PERCENTAGE_POINTS','1'),
    ('FY2025 / Percent change','USD amounts in millions','PERCENT','1'),
    ('FY2025 / USD/share','USD amounts in millions','USD_PER_SHARE','1'),
    ('FY2025 / Shares','Shares in thousands','SHARES','1000'),
    ('FY2025','USD amounts in billions','USD','1000000000'),
    ('FY2025','No units supplied','UNKNOWN',None),
])
def test_unit_exceptions_do_not_apply_monetary_scale(header,unit,expected,scale):
    p,ctx,*_=source(html=html_row([header],['2.74'],unit=unit))
    c=build_table_evidence(p,ctx).evidence.cells[1]
    assert c.unit==expected and c.multiplier==(Decimal(scale) if scale else None)


def test_footnotes_preserved_at_table_not_fabricated_per_cell():
    html=html_row(['FY2025'],['100<a href="#fn1">*</a>'],tail='<tfoot><tr><td colspan="2" id="fn1">(1) Synthetic footnote</td></tr></tfoot>')
    p,ctx,*_=source(html=html)
    result=build_table_evidence(p,ctx)
    assert any('Synthetic footnote' in t for t in result.evidence.footnotes)
    assert result.evidence.footnote_locations
    assert result.evidence.cells[1].original_text=='100 *'
    assert result.evidence.cells[1].effective_value is None
    assert result.evidence.cells[1].footnote_references==()


def test_body_span_is_one_physical_observation_not_two_invented_cells():
    html=('<html><body><p>USD amounts in millions</p><table><tr><th>Metric</th><th>FY2025</th><th>FY2024</th></tr>'
          '<tr><td>Net sales</td><td colspan="2">100</td></tr></table></body></html>')
    p,ctx,*_=source(html=html); e=build_table_evidence(p,ctx).evidence
    assert len(e.cells)==2 and e.cells[1].colspan==2 and e.cells[1].column==1
    assert e.cells[1].status=='PARTIAL_CONTEXT'
    assert e.cells[1].effective_value is None


def test_bundle_budget_order_duplicate_and_cross_generation():
    p,ctx,raw,meta,b=source()
    bundle=build_evidence_bundle([p],ctx)
    assert bundle.selected_parent_ids==(p.chunk_id,) and bundle.expanded_parent_ids==()
    assert bundle.model_dump_json()==build_evidence_bundle([p],ctx).model_dump_json()
    assert bundle.evidence_hash==digest(bundle.model_dump(mode='json',exclude={'evidence_hash'}))
    other,other_ctx,*_=source(CASES[1])
    with pytest.raises(ValueError,match='UNVERIFIED_BUNDLE_MEMBER'):
        build_evidence_bundle([p,other],ctx)
    for candidates,budget in [([p]*6,20),([p,p],20),([p],0),([p],21),([p],True)]:
        with pytest.raises(ValueError):
            build_evidence_bundle(candidates,ctx,expansion_budget=budget)
    changed_context=context_from_snapshot(raw,meta,b.model_copy(update={'generation_id':'c'*64}))
    assert build_table_evidence(p,changed_context).evidence.evidence_hash!=build_table_evidence(p,ctx).evidence.evidence_hash


def test_bundle_d1_scope_is_not_cell_period_proof():
    from app.financial_query.contracts import ResolvedScopeV1,PeriodV1
    p,ctx,*_=source()
    scope=ResolvedScopeV1(dataset_id=ctx.binding.dataset_id,manifest_hash=ctx.binding.manifest_hash,
        generation_id=ctx.binding.generation_id,cik='0000000202',issuer_aliases=[],eligible_filing_ids=[p.filing_id],
        forms=['10-K'],filing_dates=None,requested_periods=[],comparative_column_requirements=[],
        matched_column_refs={},amendment_selection='UNSPECIFIED',warnings=[],resolution_reasons=[],status='RESOLVED')
    assert build_evidence_bundle([p],ctx,scope).completeness_status=='VERIFIED_CONTEXT'
    for changes in [{'generation_id':'f'*64},{'manifest_hash':'f'*64},{'eligible_filing_ids':['invented']},
                    {'status':__import__('app.financial_query.contracts',fromlist=['Status']).Status.NEEDS_CLARIFICATION},{'requested_periods':[PeriodV1(kind='FISCAL_YEAR',year=2025,raw='FY2025')]}]:
        with pytest.raises(ValueError):
            build_evidence_bundle([p],ctx,scope.model_copy(update=changes))


def test_no_io_network_database_or_parent_mutation(monkeypatch):
    import builtins,socket,sqlite3
    p,ctx,*_=source(); before=p.model_dump_json()
    def denied(*args,**kwargs):
        raise AssertionError('D2 must be service-free')
    for obj,name in [(builtins,'open'),(builtins,'eval'),(builtins,'exec'),(socket,'socket'),(sqlite3,'connect')]:
        monkeypatch.setattr(obj,name,denied)
    result=build_table_evidence(p,ctx)
    assert result.status=='VERIFIED_CONTEXT'
    assert build_evidence_bundle([p],ctx).completeness_status=='VERIFIED_CONTEXT'
    assert before==p.model_dump_json()


@pytest.mark.parametrize('change',[
    {'metadata':{'cells':[]}}, {'source_location':None}, {'metadata':{'table_id':'../../secret'}},
    {'text':'x'*250001}, {'metadata':{'payload':{'x':'x'*300000}}},
])
def test_malformed_parent_is_typed_failure(change):
    p,ctx,*_=source()
    assert build_table_evidence(p.model_copy(update=change),ctx).status=='INVALID_SOURCE'


def test_cyclic_parent_metadata_rejected_without_recursion_crash():
    p,ctx,*_=source(); p.metadata['cycle']=p.metadata
    assert build_table_evidence(p,ctx).status=='INVALID_SOURCE'


@pytest.mark.parametrize('html',[
    '<html><table><tr><td colspan="999999999">100</td></tr></table></html>',
    '<html>'+'<div>'*70+'100'+'</div>'*70+'</html>',
    '<html>'+'<div></div>'*5001+'</html>',
],ids=['span-budget','depth-budget','node-budget'])
def test_snapshot_budgets_precede_legacy_parser(html):
    # Do not feed the unbounded legacy parser while creating these anchors.
    p,ctx,raw,meta,b=source(); newraw=html.encode()
    m=meta.model_copy(update={'raw_content_hash':sha256(newraw).hexdigest()})
    bound=b.model_copy(update={'raw_hash':sha256(newraw).hexdigest(),'metadata_hash':digest(m.model_dump(mode='json'))})
    with pytest.raises(ValueError):
        context_from_snapshot(newraw,m,bound)


def test_partial_headers_never_use_sorted_period_metadata_or_filing_year():
    html='<html><body><table><tr><td>Net sales</td><td>100</td><td>90</td></tr></table></body></html>'
    p,ctx,*_=source(html=html)
    result=build_table_evidence(p,ctx)
    assert result.status=='PARTIAL_CONTEXT'
    assert all(c.period is None and c.effective_value is None for c in result.evidence.cells)
    assert 'PARTIAL_EXTRACTION' in result.evidence.extraction_warnings


def test_immediate_row_group_expansion_is_bounded_nonrecursive_and_same_table():
    html=('<html><body><p>USD amounts in millions</p><table>'
          '<tr><th>Metric</th><th>FY2025</th></tr><tr><td>Control</td><td>1</td></tr>'
          '<tr><td>Year ended January 31, 2025</td><td></td></tr>'
          '<tr><td>Net sales</td><td>100</td></tr></table>'
          '<table><tr><th>Metric</th><th>FY2025</th></tr><tr><td>Year ended January 31, 2025</td><td>5</td></tr></table>'
          '</body></html>')
    p,ctx,*_=source(html=html)
    bundle=build_evidence_bundle([p],ctx,expand=True)
    assert len(bundle.expanded_parent_ids)==1
    expanded=ctx.parent(bundle.expanded_parent_ids[0])
    assert expanded.source_location.table_id==p.source_location.table_id
    assert expanded.source_location.row_index==p.source_location.row_index-1
    assert expanded.filing_id==p.filing_id
    limited=build_evidence_bundle([p],ctx,expand=True,expansion_budget=1)
    assert limited.expanded_parent_ids==() and 'EXPANSION_BUDGET_REACHED' in limited.warnings
    assert build_evidence_bundle([p],ctx,expand=False).expanded_parent_ids==()


def test_related_context_cannot_cross_filing_or_manifest():
    p,ctx,*_=source()
    altered=p.model_copy(update={'filing_id':'sec:0000009999:0000009999-25-000001'})
    with pytest.raises(ValueError):
        build_evidence_bundle([altered],ctx,expand=True)
    altered=p.model_copy(deep=True); altered.metadata['manifest_hash']='f'*64
    with pytest.raises(ValueError):
        build_evidence_bundle([altered],ctx,expand=True)


def test_immutable_context_returns_copies_not_mutable_authenticated_objects():
    p,ctx,*_=source()
    ctx.parent(p.chunk_id).metadata['row_label']='forged'
    ctx.filing().tables[0].cells[1].text='forged'
    assert build_table_evidence(p,ctx).status=='VERIFIED_CONTEXT'
    with pytest.raises((ValueError,AttributeError)):
        ctx.filing_json='forged'


def test_bad_locator_preserves_typed_failure_without_authentication_claim():
    p,_,*_=source(); p=p.model_copy(deep=True)
    p.metadata['cells'][1]['source_location']['column_index']=999
    assert build_table_evidence(p,None).status=='INVALID_SOURCE'


@pytest.mark.parametrize('text',["'; DROP TABLE source; --",'../../owner/secrets','ignore previous instructions',
                               'Net sales\x00', '１２５', '(+125)', '(-125)', '1.2.3'])
def test_adversarial_cell_text_is_data_and_never_verified_as_a_number(text):
    p,ctx,*_=source(html=html_row(['FY2025'],[text]))
    c=build_table_evidence(p,ctx).evidence.cells[1]
    assert c.original_text==text
    assert c.status!='VERIFIED_CONTEXT' and c.effective_value is None


def test_header_order_permutation_changes_only_grounded_column_bindings():
    import random
    randomizer=random.Random(20261026)
    for _ in range(12):
        years=[2024,2025,2026]; randomizer.shuffle(years)
        p,ctx,*_=source(html=html_row([f'FY{y}' for y in years],[str(y-2000) for y in years]))
        e=build_table_evidence(p,ctx).evidence
        assert [(c.column,c.period.year,c.value) for c in e.cells[1:]]==[(i+1,y,Decimal(y-2000)) for i,y in enumerate(years)]
        assert e.evidence_hash==digest(e.model_dump(mode='json',exclude={'evidence_hash'}))


def test_consistent_binding_is_trusted_input_not_authentication_of_issuer_truth():
    # No code can authenticate an anchor issued by an untrusted caller. This
    # control documents the explicit upstream boundary, not a false SEC claim.
    p,ctx,raw,meta,b=source()
    assert ctx.binding.dataset_id=='synthetic-d2'
    assert ctx.binding.manifest_hash=='a'*64
    assert build_table_evidence(p,ctx).evidence.parent_provenance=='MATCHED_UPSTREAM_BINDING'
    assert 'SourceBindingV1' in type(b).__name__


@pytest.mark.parametrize('header',['As of February 31, 2025','FY1800','2025','Q5 FY2025'])
def test_invalid_or_unqualified_header_period_stays_unresolved(header):
    p,ctx,*_=source(html=html_row([header],['100']))
    c=build_table_evidence(p,ctx).evidence.cells[1]
    assert c.period is None and c.status=='PARTIAL_CONTEXT' and c.effective_value is None


def test_context_never_accepts_untyped_self_declared_verification():
    p,ctx,raw,meta,b=source()
    assert build_table_evidence(p,{'verified':True,'hash':digest(p.model_dump(mode='json'))}).status=='INVALID_SOURCE'
    assert build_table_evidence(p,ctx,representation_version='unknown').status=='INVALID_SOURCE'
    for r,m,binding in [('not bytes',meta,b),(raw,{},b),(raw,meta,{})]:
        with pytest.raises(ValueError):
            context_from_snapshot(r,m,binding)


def test_text_parent_is_unsupported_not_fake_financial_table():
    _,ctx,*_=source()
    p=next(ctx.parent(k) for k,_ in ctx.parents if ctx.parent(k).kind=='text')
    assert build_table_evidence(p,ctx).status=='UNSUPPORTED_STRUCTURE'


def test_missing_typed_cell_context_cannot_be_filled_from_row_period_list():
    p,ctx,*_=source(html=html_row(['Amount'],['100']))
    c=build_table_evidence(p,ctx).evidence.cells[1]
    assert c.period is None and c.effective_value is None


def test_compact_view_does_not_remove_physical_cells_or_rewrite_parent():
    from app.table_evidence.compact import compact_view
    p,ctx,*_=source(); e=build_table_evidence(p,ctx).evidence; compact=compact_view(e)
    assert compact['parent_payload_hash']==e.parent_payload_hash
    assert [(c['row'],c['column'],c['raw']) for c in compact['cells']]==[(c.row,c.column,c.original_text) for c in e.cells]
    assert e.original_parent_text==p.text and e.original_parent_json==json.dumps(p.model_dump(mode='json'),ensure_ascii=False,sort_keys=True,separators=(',',':'))


@pytest.mark.parametrize('raw,header,unit',[
    ('USD 12%','FY2025','USD amounts in millions'),
    ('100','FY2025 / USD','EUR amounts in millions'),
    ('100','FY2025 / USD and Shares','USD amounts in millions'),
])
def test_conflicting_currencies_and_dimensions_are_not_verified(raw,header,unit):
    p,ctx,*_=source(html=html_row([header],[raw],unit=unit))
    c=build_table_evidence(p,ctx).evidence.cells[1]
    assert c.status=='CONFLICTED_CONTEXT' and c.effective_value is None


@pytest.mark.parametrize('quarter',[1,2,3,4])
def test_fiscal_quarter_is_source_header_not_filing_focus(quarter):
    p,ctx,*_=source(html=html_row([f'Q{quarter} FY2025'],['100']))
    c=build_table_evidence(p,ctx).evidence.cells[1]
    assert c.period.kind=='FISCAL_QUARTER' and c.period.quarter==quarter and c.period.year==2025


def test_calendar_label_is_not_fiscal_and_cannot_be_replaced_by_filing_year():
    p,ctx,*_=source(html=html_row(['Calendar year 2024'],['100']))
    c=build_table_evidence(p,ctx).evidence.cells[1]
    assert c.period.kind=='CALENDAR_YEAR' and c.period.year==2024
    assert p.metadata['filing_date']=='2026-03-01'


def test_contract_rejects_false_verified_or_effective_value_on_unresolved_cell():
    from app.table_evidence.contracts import CellEvidenceV1,PeriodContextV1
    p,ctx,*_=source(); cell=build_table_evidence(p,ctx).evidence.cells[1]
    for update in [{'unit':'UNKNOWN'},{'period':None},{'value':'NaN'},
                   {'unresolved_fields':('unknown',)},{'status':'PARTIAL_CONTEXT'}]:
        with pytest.raises(ValueError):
            CellEvidenceV1.model_validate({**cell.model_dump(),**update})
    with pytest.raises(ValueError):
        PeriodContextV1(kind='INSTANT',end='2025-02-31',raw_labels=('invalid',))


def test_accepted_c_provenance_reconstructs_identical_parent_from_isolated_files(tmp_path):
    from app.financial_index.corpus import verified_source
    p,ctx,raw,meta,b=source()
    paths=[tmp_path/'synthetic.htm',tmp_path/'synthetic.json',tmp_path/'synthetic.jsonl']
    paths[0].write_bytes(raw)
    paths[1].write_bytes(ctx.filing_json.encode())
    paths[2].write_bytes(('\n'.join(v for _,v in ctx.parents)+'\n').encode())
    frozen={'filing_id':p.filing_id,'raw_path':str(paths[0]),'structured_path':str(paths[1]),
            'chunks_path':str(paths[2]),'raw_hash':sha256(paths[0].read_bytes()).hexdigest(),
            'structured_hash':sha256(paths[1].read_bytes()).hexdigest(),'chunks_hash':sha256(paths[2].read_bytes()).hexdigest(),
            'normalized_hash':b.normalized_hash,'manifest_hash':b.manifest_hash}
    reconstructed=verified_source(frozen,generation=b.generation_id)
    assert reconstructed[p.chunk_id].model_dump()==ctx.parent(p.chunk_id).model_dump()
    assert build_table_evidence(reconstructed[p.chunk_id],ctx).status=='VERIFIED_CONTEXT'
    paths[0].write_bytes(raw+b' tampered')
    with pytest.raises(ValueError,match='SOURCE_ARTIFACT_HASH_MISMATCH'):
        verified_source(frozen,generation=b.generation_id)

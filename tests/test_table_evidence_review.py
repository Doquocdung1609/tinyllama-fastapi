"""Fresh same-system adversarial review of D2; synthetic counterexamples only."""
from decimal import Decimal
import pytest
from test_table_evidence import source, html_row
from app.table_evidence import build_table_evidence


@pytest.mark.parametrize('tag',['th','td'])
def test_repeated_body_header_cannot_reuse_original_period(tag):
    html=('<html><body><p>USD amounts in millions</p><table>'
          '<tr><th>Metric</th><th>FY2025</th></tr><tr><td>Control</td><td>1</td></tr>'
          f'<tr><{tag}>Metric</{tag}><{tag}>FY2024</{tag}></tr>'
          '<tr><td>Net sales</td><td>90</td></tr></table></body></html>')
    p,ctx,*_=source(html=html)
    c=build_table_evidence(p,ctx).evidence.cells[1]
    assert c.status!='VERIFIED_CONTEXT',c.model_dump_json()
    assert c.effective_value is None
    assert 'REPEATED_BODY_HEADER_UNRESOLVED' in c.unresolved_fields


@pytest.mark.parametrize('raw',['USD 100','$100'])
def test_displayed_currency_cannot_become_share_count(raw):
    p,ctx,*_=source(html=html_row(['FY2025 / Shares'],[raw],unit='Shares in thousands'))
    c=build_table_evidence(p,ctx).evidence.cells[1]
    assert c.status=='CONFLICTED_CONTEXT' and c.effective_value is None


def test_numeric_first_physical_cell_is_not_financial_metric():
    p,ctx,*_=source(html=html_row(['FY2025'],['100'],row='2024'))
    p=next(ctx.parent(k) for k,_ in ctx.parents if ctx.parent(k).metadata.get('row_label')=='2024')
    e=build_table_evidence(p,ctx).evidence
    assert e.status!='VERIFIED_CONTEXT'


def test_unknown_xbrl_concept_must_not_claim_metric_correspondence():
    p,ctx,*_=source(html=html_row(['FY2025'],['<ix:nonfraction name="us-gaap:OperatingIncomeLoss" scale="6">100</ix:nonfraction>']))
    c=build_table_evidence(p,ctx).evidence.cells[1]
    assert c.status!='VERIFIED_CONTEXT' and c.effective_value is None


@pytest.mark.parametrize('header',['FY2025 / Percent change','FY2025 / USD change'])
def test_change_column_keeps_change_basis_not_amount_basis(header):
    p,ctx,*_=source(html=html_row([header],['100']))
    c=build_table_evidence(p,ctx).evidence.cells[1]
    assert c.measurement_basis in {'PERCENT_CHANGE','AMOUNT_CHANGE'}
    assert c.measurement_basis!='AMOUNT'


def test_text_label_does_not_hide_inline_conflict_in_adjacent_column():
    p,ctx,*_=source(html=html_row(['FY2025'],['<ix:nonfraction scale="0">100</ix:nonfraction>']))
    assert build_table_evidence(p,ctx).status=='CONFLICTED_CONTEXT'


def test_missing_header_does_not_read_filing_date():
    p,ctx,*_=source(html=html_row(['Amount'],['100']))
    c=build_table_evidence(p,ctx).evidence.cells[1]
    assert c.period is None and c.effective_value is None


def test_noncontiguous_source_cells_do_not_create_observation_from_inherited_body_span():
    html=('<html><body><p>USD amounts in millions</p><table><tr><th>Metric</th><th>FY2025</th><th>FY2024</th></tr>'
          '<tr><td rowspan="2">Net sales</td><td>100</td><td>90</td></tr>'
          '<tr><td>70</td><td>60</td></tr></table></body></html>')
    p,ctx,*_=source(html=html)
    e=build_table_evidence(p,ctx).evidence
    assert e.cells[0].rowspan==2 and e.cells[0].status=='PARTIAL_CONTEXT'
    assert len(e.cells)==3


def test_nested_table_remains_unsupported():
    html=('<html><body><p>USD amounts in millions</p><table><tr><th>Metric</th><th>FY2025</th></tr>'
          '<tr><td>Net sales</td><td><table><tr><td>100</td><td>90</td></tr></table></td></tr>'
          '</table></body></html>')
    p,ctx,*_=source(html=html)
    assert build_table_evidence(p,ctx).status=='UNSUPPORTED_STRUCTURE'


def test_source_size_limit_is_not_bypassed_by_a_trusted_binding():
    from app.table_evidence import context_from_snapshot
    p,ctx,raw,meta,b=source()
    with pytest.raises(ValueError,match='INVALID_SOURCE_CONTEXT'):
        context_from_snapshot(b'x'*250001,meta,b)


def test_original_source_context_is_not_mutated_after_many_reads():
    p,ctx,*_=source(); before=ctx.filing_json
    results=[build_table_evidence(p,ctx).model_dump_json() for _ in range(5)]
    assert len(set(results))==1 and ctx.filing_json==before

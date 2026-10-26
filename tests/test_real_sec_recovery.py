"""Synthetic fail-first checks for the real-source iXBRL adapter, never SEC ground truth."""
from hashlib import sha256
from decimal import Decimal
import pytest
from app.financial_ingestion import PARSER_VERSION,CHUNKER_VERSION,INGESTION_VERSION
from app.financial_ingestion.schemas import FilingMetadata
from app.financial_ingestion.html_parser import parse_sec_html
from app.financial_ingestion.chunker import chunk_filing
from app.table_evidence.real_source import MAX_SOURCE_BYTES,parse_resources,derive_cell
from app.research_qa.real_cells import RealCellRequestV1, answer_from_verified_real_cells


def synthetic():
    raw=b'''<html><body><ix:resources>
    <xbrli:unit id="usd"><xbrli:measure>iso4217:USD</xbrli:measure></xbrli:unit>
    <xbrli:context id="c1"><xbrli:entity><xbrli:identifier scheme="http://www.sec.gov/CIK">0000000202</xbrli:identifier></xbrli:entity>
    <xbrli:period><xbrli:startDate>2026-07-01</xbrli:startDate><xbrli:endDate>2026-09-30</xbrli:endDate></xbrli:period></xbrli:context></ix:resources>
    <h2>Consolidated Statements of Earnings</h2><table><tr><th>Metric</th><th>Three Months Ended September 30</th></tr>
    <tr><th>Amounts in millions except per share amounts</th><th>2026</th></tr>
    <tr><td>NET SALES</td><td><ix:nonFraction name="us-gaap:Revenues" contextRef="c1" unitRef="usd" scale="6" format="ixt:num-dot-decimal">23,276</ix:nonFraction></td></tr></table></body></html>'''
    m=FilingMetadata(filing_id='sec:0000000202:0000000202-26-000001',cik='0000000202',accession_number='0000000202-26-000001',
        company_name='Synthetic Recovery Issuer',form_type='10-Q',filing_date='2026-11-01',report_date='2026-09-30',
        primary_document='synthetic.htm',source_url='https://example.invalid/synthetic.htm',raw_content_hash=sha256(raw).hexdigest(),
        parser_version=PARSER_VERSION,chunker_version=CHUNKER_VERSION,ingestion_version=INGESTION_VERSION,document_status='READY')
    filing=parse_sec_html(raw,m);parent=next(c for c in chunk_filing(filing) if c.kind=='table' and c.metadata.get('row_label')=='NET SALES')
    table=next(t for t in filing.tables if t.table_id==parent.source_location.table_id)
    cell=next(c for c in table.cells if c.row==parent.source_location.row_index and c.text=='23,276')
    return raw,filing,parent,table,cell


def test_source_derived_xbrl_unit_period_and_exact_cell():
    raw,filing,parent,table,cell=synthetic()
    resources=parse_resources(raw)
    observed=derive_cell(parent,table,cell,resources,raw_hash=sha256(raw).hexdigest(),generation='a'*64,manifest_hash='b'*64)
    assert observed.raw_value=='23,276' and observed.effective_value==Decimal('23276000000')
    assert observed.unit=='USD' and observed.multiplier==Decimal(1000000)
    assert observed.display_unit_header=='Amounts in millions except per share amounts'
    assert observed.period_start=='2026-07-01' and observed.period_end=='2026-09-30'
    assert observed.row==cell.row and observed.column==cell.column and observed.structural_path==cell.source_location.structural_path
    assert observed.parent_id==parent.chunk_id and observed.fact_name=='us-gaap:Revenues'


def test_untrusted_or_inconsistent_fact_fails_closed():
    raw,filing,parent,table,cell=synthetic();resources=parse_resources(raw)
    for facts in [[],[{**cell.numeric_facts[0],'contextref':'unknown'}],
                  [{**cell.numeric_facts[0],'name':'us-gaap:Assets'}],
                  [{**cell.numeric_facts[0],'source_text':'99,999'}]]:
        altered=cell.model_copy(update={'numeric_facts':facts})
        with pytest.raises(ValueError):derive_cell(parent,table,altered,resources,raw_hash=sha256(raw).hexdigest(),generation='a'*64,manifest_hash='b'*64)


def test_entity_and_period_header_mismatch_fail_closed():
    raw,filing,parent,table,cell=synthetic()
    resources=parse_resources(raw)
    bad=raw.replace(b'0000000202</xbrli:identifier>',b'0000000999</xbrli:identifier>')
    with pytest.raises(ValueError):derive_cell(parent,table,cell,parse_resources(bad),raw_hash=sha256(raw).hexdigest(),generation='a'*64,manifest_hash='b'*64)
    altered=table.model_copy(update={'cells':[c.model_copy(update={'text':'2025'}) if c.text=='2026' else c for c in table.cells]})
    with pytest.raises(ValueError):derive_cell(parent,altered,cell,resources,raw_hash=sha256(raw).hexdigest(),generation='a'*64,manifest_hash='b'*64)


def test_resource_budget_duplicate_identity_and_missing_unit_fail_closed():
    raw,filing,parent,table,cell=synthetic()
    with pytest.raises(ValueError,match='SOURCE_SIZE_BUDGET'):
        parse_resources(b'x'*(MAX_SOURCE_BYTES+1))
    duplicated=raw.replace(b'</ix:resources>',b'<xbrli:unit id="usd"></xbrli:unit></ix:resources>')
    with pytest.raises(ValueError,match='DUPLICATE_OR_EXCESSIVE_XBRL_RESOURCE'):
        parse_resources(duplicated)
    no_unit=raw.replace(b'iso4217:USD',b'iso4217:EUR')
    with pytest.raises(ValueError,match='XBRL_UNIT_UNSUPPORTED'):
        derive_cell(parent,table,cell,parse_resources(no_unit),raw_hash=sha256(raw).hexdigest(),generation='a'*64,manifest_hash='b'*64)


def test_visible_unit_header_must_match_xbrl_scale():
    raw,filing,parent,table,cell=synthetic();resources=parse_resources(raw)
    contradictory=table.model_copy(update={'header_rows':[[text.replace('millions','thousands') for text in row]
                                                     for row in table.header_rows]})
    with pytest.raises(ValueError):derive_cell(parent,contradictory,cell,resources,raw_hash=sha256(raw).hexdigest(),generation='a'*64,manifest_hash='b'*64)
    changed=cell.model_copy(update={'numeric_facts':[{**cell.numeric_facts[0],'scale':'3'}]})
    with pytest.raises(ValueError):derive_cell(parent,table,changed,resources,raw_hash=sha256(raw).hexdigest(),generation='a'*64,manifest_hash='b'*64)


def test_verified_cell_arithmetic_requires_exact_source_period(monkeypatch):
    raw,filing,parent,table,cell=synthetic();resources=parse_resources(raw)
    current=derive_cell(parent,table,cell,resources,raw_hash=sha256(raw).hexdigest(),generation='a'*64,manifest_hash='b'*64)
    prior=current.model_copy(update={'period_start':'2025-07-01','period_end':'2025-09-30',
                                     'value':Decimal('22386'),'effective_value':Decimal('22386000000'),
                                     'raw_value':'22,386','column':current.column+1})
    monkeypatch.setattr('app.research_qa.real_cells.verified_real_cells',lambda snapshot,parent_id:(prior,current))
    base={'parent_id':parent.chunk_id,'cik':current.cik,'accession':current.accession,
          'table_id':current.table_id,'period_ends':('2025-09-30','2026-09-30')}
    result=answer_from_verified_real_cells(None,RealCellRequestV1(**base,operation='ABS_CHANGE'))
    assert result.status=='SUPPORTED' and result.result_values==(Decimal('890000000'),)
    pct=answer_from_verified_real_cells(None,RealCellRequestV1(**base,operation='PERCENT_CHANGE'))
    assert pct.status=='SUPPORTED' and pct.result_values[0]==(Decimal('890')/Decimal('22386')*Decimal(100))
    missing=answer_from_verified_real_cells(None,RealCellRequestV1(**{**base,'period_ends':('2024-09-30','2026-09-30')},operation='COMPARE'))
    assert missing.status=='INSUFFICIENT_EVIDENCE' and not missing.operands
    with pytest.raises(ValueError):RealCellRequestV1(**{**base,'period_ends':('2026-09-30','2025-09-30')},operation='COMPARE')


def test_negative_prior_value_never_produces_percent_growth(monkeypatch):
    raw,filing,parent,table,cell=synthetic()
    current=derive_cell(parent,table,cell,parse_resources(raw),raw_hash=sha256(raw).hexdigest(),generation='a'*64,manifest_hash='b'*64)
    prior=current.model_copy(update={'period_start':'2025-07-01','period_end':'2025-09-30',
        'value':Decimal('-125.50'),'effective_value':Decimal('-125500000'),'raw_value':'(125.50)','column':current.column+1})
    monkeypatch.setattr('app.research_qa.real_cells.verified_real_cells',lambda snapshot,parent_id:(prior,current))
    request=RealCellRequestV1(parent_id=parent.chunk_id,cik=current.cik,accession=current.accession,
        table_id=current.table_id,period_ends=('2025-09-30','2026-09-30'),operation='PERCENT_CHANGE')
    result=answer_from_verified_real_cells(None,request)
    assert result.status=='INSUFFICIENT_EVIDENCE' and result.reason=='NONPOSITIVE_PERCENT_CHANGE_BASE'
    assert not result.operands and not result.result_values

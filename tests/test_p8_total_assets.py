"""Synthetic instant total-assets source cell; not a real SEC value."""
from hashlib import sha256
from decimal import Decimal
from app.financial_ingestion import PARSER_VERSION,CHUNKER_VERSION,INGESTION_VERSION
from app.financial_ingestion.schemas import FilingMetadata
from app.financial_ingestion.html_parser import parse_sec_html
from app.financial_ingestion.chunker import chunk_filing
from app.table_evidence.real_source import derive_cell,parse_resources
from app.financial_query.contracts import CorpusCatalogV1
from app.research_qa.automatic_real import automatic_real_query
from test_p6_automatic import FakeSnapshot
from app.research_qa.real_cells import RealCellRequestV1
import pytest


def assets_fixture():
    raw=b'''<html><body><ix:resources><xbrli:unit id="usd"><xbrli:measure>iso4217:USD</xbrli:measure></xbrli:unit>
    <xbrli:context id="c1"><xbrli:entity><xbrli:identifier>0000000202</xbrli:identifier></xbrli:entity>
    <xbrli:period><xbrli:instant>2026-09-30</xbrli:instant></xbrli:period></xbrli:context></ix:resources>
    <h1>CONSOLIDATED BALANCE SHEETS</h1><table><tr><th>Metric</th><th>September 30</th></tr>
    <tr><th>Amounts in millions</th><th>2026</th></tr>
    <tr><td>TOTAL ASSETS</td><td><ix:nonFraction name="us-gaap:Assets" contextRef="c1" unitRef="usd" scale="6" format="ixt:num-dot-decimal">133,132</ix:nonFraction></td></tr></table></body></html>'''
    metadata=FilingMetadata(filing_id='sec:0000000202:0000000202-26-000001',cik='0000000202',
        accession_number='0000000202-26-000001',company_name='Synthetic Fixture',form_type='10-Q',
        filing_date='2026-10-20',report_date='2026-09-30',primary_document='fixture.htm',
        source_url='https://example.invalid/fixture.htm',raw_content_hash=sha256(raw).hexdigest(),
        parser_version=PARSER_VERSION,chunker_version=CHUNKER_VERSION,ingestion_version=INGESTION_VERSION,
        document_status='READY')
    filing=parse_sec_html(raw,metadata)
    parent=next(p for p in chunk_filing(filing) if p.kind=='table' and p.metadata.get('row_label')=='TOTAL ASSETS')
    table=next(t for t in filing.tables if t.table_id==parent.source_location.table_id)
    cell=next(c for c in table.cells if c.row==parent.source_location.row_index and c.numeric_facts)
    observed=derive_cell(parent,table,cell,parse_resources(raw),raw_hash=sha256(raw).hexdigest(),
                         generation='a'*64,manifest_hash='b'*64,dataset_id='SYNTHETIC_P8')
    catalog=CorpusCatalogV1(dataset_id='SYNTHETIC_P8',manifest_hash='b'*64,generation_id='a'*64,
        provenance='SYNTHETIC_TEST_ONLY',issuers=[{'cik':'0000000202','company_name':'Synthetic Fixture','tickers':['FX']}],
        filings=[{'filing_id':parent.filing_id,'cik':'0000000202','accession':'0000000202-26-000001',
                  'form':'10-Q','extraction_status':'READY','column_periods_complete':False}])
    return parent,cell,observed,catalog


def test_exact_total_assets_fact_is_instant_usd_with_source_coordinates():
    parent,cell,observed,catalog=assets_fixture()
    assert observed.row_label=='TOTAL ASSETS' and observed.fact_name=='us-gaap:Assets'
    assert observed.period_kind=='INSTANT' and observed.period_end=='2026-09-30'
    assert observed.effective_value==Decimal('133132000000') and observed.unit=='USD'
    assert observed.row==cell.row and observed.column==cell.column


def test_automatic_total_assets_uses_verified_instant_cell(monkeypatch):
    parent,cell,observed,catalog=assets_fixture();snapshot=FakeSnapshot(parent,catalog,rank=1)
    monkeypatch.setattr('app.research_qa.automatic_real.verified_real_cells',lambda snap,cid:(observed,))
    monkeypatch.setattr('app.research_qa.real_cells.verified_real_cells',lambda snap,cid:(observed,))
    result=automatic_real_query(snapshot,'What were FX total assets as of September 30, 2026?',{},catalog=catalog)
    assert result['answer']['status']=='SUPPORTED'
    assert result['answer']['result_values']==['133132000000']
    assert result['answer']['source_cells'][0]['period_kind']=='INSTANT'
    assert result['evidence'][0]['accession']=='0000000202-26-000001'
    assert result['evidence'][0]['row_label']=='TOTAL ASSETS'
    assert result['evidence'][0]['raw_value']=='133,132'
    assert result['evidence'][0]['locator']['row_index']==cell.row
    wrong_duration=automatic_real_query(snapshot,
        'What were FX total assets for the three months ended September 30, 2026?',{},catalog=catalog)
    assert wrong_duration['answer']['status']!='SUPPORTED' and not wrong_duration['answer']['result_values']


def test_total_assets_request_cannot_relabel_duration_as_instant():
    common={'parent_id':'fin_'+'a'*32,'cik':'0000000202',
            'accession':'0000000202-26-000001','table_id':'table_'+'b'*16,
            'row_label':'total assets','period_ends':('2026-09-30',)}
    with pytest.raises(ValueError,match='METRIC_PERIOD_KIND_CONFLICT'):
        RealCellRequestV1(**common)
    with pytest.raises(ValueError,match='METRIC_PERIOD_KIND_CONFLICT'):
        RealCellRequestV1(**common,period_kind='DURATION',period_months=3)
    valid=RealCellRequestV1(**common,period_kind='INSTANT',period_months=None)
    assert valid.period_kind=='INSTANT' and valid.period_months is None

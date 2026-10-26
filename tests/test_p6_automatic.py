"""Isolated P6 routing checks; synthetic values are never labeled SEC ground truth."""
from contextlib import contextmanager
from decimal import Decimal
from hashlib import sha256
from app.financial_ingestion import PARSER_VERSION,CHUNKER_VERSION,INGESTION_VERSION
from app.financial_ingestion.schemas import FilingMetadata
from app.financial_ingestion.html_parser import parse_sec_html
from app.financial_ingestion.chunker import chunk_filing
from app.financial_query.contracts import CorpusCatalogV1
from app.research_retrieval.adapters import candidate
from app.research_qa.automatic_real import automatic_real_query,CANDIDATE_BUDGET
from app.table_evidence.real_source import derive_cell,parse_resources


def fixture():
    raw=b'''<html><body><ix:resources><xbrli:unit id="usd"><xbrli:measure>iso4217:USD</xbrli:measure></xbrli:unit>
    <xbrli:context id="c1"><xbrli:entity><xbrli:identifier>0000000202</xbrli:identifier></xbrli:entity>
    <xbrli:period><xbrli:startDate>2026-07-01</xbrli:startDate><xbrli:endDate>2026-09-30</xbrli:endDate></xbrli:period></xbrli:context></ix:resources>
    <h1>CONSOLIDATED STATEMENTS OF EARNINGS</h1><table><tr><th>Metric</th><th>Three Months Ended September 30</th></tr>
    <tr><th>Amounts in millions except per share amounts</th><th>2026</th></tr>
    <tr><td>NET SALES</td><td><ix:nonFraction name="us-gaap:Revenues" contextRef="c1" unitRef="usd" scale="6" format="ixt:num-dot-decimal">23,276</ix:nonFraction></td></tr></table></body></html>'''
    metadata=FilingMetadata(filing_id='sec:0000000202:0000000202-26-000001',cik='0000000202',
        accession_number='0000000202-26-000001',company_name='Fixture Example',form_type='10-Q',
        filing_date='2026-11-01',report_date='2026-09-30',primary_document='fixture.htm',
        source_url='https://example.invalid/fixture.htm',raw_content_hash=sha256(raw).hexdigest(),
        parser_version=PARSER_VERSION,chunker_version=CHUNKER_VERSION,ingestion_version=INGESTION_VERSION,
        document_status='READY')
    filing=parse_sec_html(raw,metadata)
    parent=next(p for p in chunk_filing(filing) if p.kind=='table' and p.metadata.get('row_label')=='NET SALES')
    table=next(t for t in filing.tables if t.table_id==parent.source_location.table_id)
    cell=next(c for c in table.cells if c.row==parent.source_location.row_index and c.numeric_facts)
    observation=derive_cell(parent,table,cell,parse_resources(raw),raw_hash=sha256(raw).hexdigest(),
        generation='a'*64,manifest_hash='b'*64,dataset_id='p6-fixture')
    catalog=CorpusCatalogV1(dataset_id='p6-fixture',manifest_hash='b'*64,generation_id='a'*64,
        provenance='SYNTHETIC_TEST_ONLY',issuers=[{'cik':'0000000202','company_name':'Fixture Example','tickers':['FX']}],
        filings=[{'filing_id':parent.filing_id,'cik':'0000000202','accession':'0000000202-26-000001',
            'form':'10-Q','extraction_status':'READY','column_periods_complete':False}])
    return parent,observation,catalog


class FakeSnapshot:
    def __init__(self,parent,catalog,rank=6):
        self.parent=parent;self.catalog=catalog;self.freeze={'generation':'a'*64,'manifest_hash':'b'*64}
        self.rank=rank;self.calls=0

    @contextmanager
    def pin(self,scope):yield

    def search(self,question,scope,channel,limit,deadline):
        self.calls+=1
        assert channel=='B' and limit==CANDIDATE_BUDGET and scope.cik=='0000000202'
        filler=[self.parent.model_copy(update={'chunk_id':f'fin_{i:032x}',
             'metadata':{**self.parent.metadata,'row_label':'other metric'}}) for i in range(min(limit,self.rank-1))]
        parents=filler+([self.parent] if self.rank<=limit else [])
        return [candidate(p,scope,'B',1/(i+1)) for i,p in enumerate(parents)]


def test_p6_expands_candidates_only_inside_d1_scope(monkeypatch):
    parent,cell,catalog=fixture();snapshot=FakeSnapshot(parent,catalog)
    monkeypatch.setattr('app.research_qa.automatic_real.verified_real_cells',lambda snap,cid:(cell,) if cid==parent.chunk_id else ())
    monkeypatch.setattr('app.research_qa.real_cells.verified_real_cells',lambda snap,cid:(cell,))
    q='What were FX net sales for the quarter ended September 30, 2026?'
    result=automatic_real_query(snapshot,q,{})
    assert result['retrieval_status']=='OK' and result['answer']['status']=='SUPPORTED'
    assert result['answer']['result_values']==['23276000000']
    assert result['column_refinement']['metadata_scope_status']=='NEEDS_CLARIFICATION'
    assert result['column_refinement']['original_bm25_rank']==6
    assert snapshot.calls==1 and result['evidence'][0]['parent_id']==parent.chunk_id
    conflict=automatic_real_query(snapshot,q,{'cik':'0000000999'})
    assert conflict['answer']['status']!='SUPPORTED' and snapshot.calls==1


def test_p6_absent_or_out_of_budget_cell_abstains(monkeypatch):
    parent,cell,catalog=fixture();snapshot=FakeSnapshot(parent,catalog)
    monkeypatch.setattr('app.research_qa.automatic_real.verified_real_cells',lambda snap,cid:(cell,) if cid==parent.chunk_id else ())
    missing=automatic_real_query(snapshot,'What were FX net sales for the quarter ended September 30, 2024?',{})
    assert missing['answer']['status']=='INSUFFICIENT_EVIDENCE'
    assert missing['column_refinement']['refinement_status']=='NO_VERIFIED_CELL'
    far=FakeSnapshot(parent,catalog,rank=65)
    out=automatic_real_query(far,'What were FX net sales for the quarter ended September 30, 2026?',{})
    assert out['answer']['status']=='INSUFFICIENT_EVIDENCE' and out['failure_code']=='NO_VERIFIED_CELL_WITHIN_CANDIDATE_BUDGET'


def test_p6_unknown_issuer_invalid_generation_and_unsupported_metric_never_search():
    parent,cell,catalog=fixture();snapshot=FakeSnapshot(parent,catalog)
    for question,filters in [
        ('What were ACME net sales for the quarter ended September 30, 2026?',{}),
        ('What were FX net sales for the quarter ended September 30, 2026?',{'cik':'0000000999'}),
        ('What were FX operating income for the quarter ended September 30, 2026?',{}),
        ('What were FX net sales for the quarter ended September 30, 2026 in the amended 10-Q/A?',{}),
    ]:
        result=automatic_real_query(snapshot,question,filters)
        assert result['answer']['status']!='SUPPORTED'
    assert snapshot.calls==0
    snapshot.freeze['generation']='c'*64
    result=automatic_real_query(snapshot,'What were FX net sales for the quarter ended September 30, 2026?',{})
    assert result['failure_code']=='PINNED_GENERATION_OR_MANIFEST_MISMATCH' and snapshot.calls==0


def test_p6_instant_or_segmented_evidence_does_not_fill_duration(monkeypatch):
    parent,cell,catalog=fixture();snapshot=FakeSnapshot(parent,catalog)
    wrong=cell.model_copy(update={'period_kind':'INSTANT','period_start':None,'period_months':None})
    monkeypatch.setattr('app.research_qa.automatic_real.verified_real_cells',lambda snap,cid:(wrong,) if cid==parent.chunk_id else ())
    result=automatic_real_query(snapshot,'What were FX net sales for the quarter ended September 30, 2026?',{})
    assert result['answer']['status']=='INSUFFICIENT_EVIDENCE'


def test_p6_ambiguous_verified_parent_rows_refuse_selection(monkeypatch):
    parent,cell,catalog=fixture();snapshot=FakeSnapshot(parent,catalog,rank=1)
    second=parent.model_copy(update={'chunk_id':'fin_'+'f'*32})
    def search(question,scope,channel,limit,deadline):
        return [candidate(p,scope,'B',score) for p,score in [(parent,1.),(second,.5)]]
    snapshot.search=search
    monkeypatch.setattr('app.research_qa.automatic_real.verified_real_cells',
                        lambda snap,cid:(cell.model_copy(update={'parent_id':cid}),))
    result=automatic_real_query(snapshot,'What were FX net sales for the quarter ended September 30, 2026?',{})
    assert result['answer']['status']=='NEEDS_CLARIFICATION'
    assert result['failure_code']=='MULTIPLE_VERIFIED_PARENT_ROWS' and not result['evidence']
    assert result['column_refinement']['refinement_status']=='AMBIGUOUS_VERIFIED_CELLS'


def test_p6_reversed_change_periods_refuse_wrong_sign():
    parent,cell,catalog=fixture();snapshot=FakeSnapshot(parent,catalog)
    query='What was the difference in FX net sales from the quarter ended September 30, 2026 to the quarter ended September 30, 2025?'
    result=automatic_real_query(snapshot,query,{})
    assert result['answer']['status']=='NEEDS_CLARIFICATION'
    assert result['failure_code']=='CHANGE_DIRECTION_REQUIRES_OLD_THEN_NEW'
    assert snapshot.calls==0

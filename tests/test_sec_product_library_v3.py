from types import SimpleNamespace
import pytest
from app.product.sec_import_identity import validate
from app.product.sec_library import ScopedIndex

def dei(cik='80424',form='10-Q',period='2026-03-31'):
    return f'<html><body><ix:nonNumeric name="dei:EntityCentralIndexKey">{cik}</ix:nonNumeric><ix:nonNumeric name="dei:DocumentType">{form}</ix:nonNumeric><ix:nonNumeric name="dei:DocumentPeriodEndDate">{period}</ix:nonNumeric></body></html>'.encode()

def test_source_identity_rejects_sec_error_page_even_with_http_200():
    m=SimpleNamespace(cik='0000080424',form_type='10-Q',report_date='2026-03-31')
    assert validate(dei(),m)['identity']=='VERIFIED_FROM_ORIGINAL_DEI'
    for raw in [b'<html>Request rate threshold exceeded</html>',dei(cik='320193'),dei(form='10-K'),dei(period='2026-06-30')]:
        with pytest.raises(ValueError,match='SEC_SOURCE_IDENTITY_REQUIRES_REVIEW'):validate(raw,m)

def test_selected_filing_limits_every_expansion_surface():
    a={'chunk':SimpleNamespace(filing_id='A')};b={'chunk':SimpleNamespace(filing_id='B')}
    base=SimpleNamespace(catalog_rows=[{'filing_id':'A'},{'filing_id':'B'}],parents=[a,b],by_id={'a':a,'b':b})
    selected=ScopedIndex(base,['A'])
    assert selected.catalog_rows==[{'filing_id':'A'}]
    assert selected.parents==[a]
    assert set(selected.by_id)=={'a'}

def test_product_source_accepts_authentic_external_caption_and_modern_revenue_concept():
    from hashlib import sha256
    from test_real_sec_recovery import synthetic
    from app.financial_ingestion.html_parser import parse_sec_html
    from app.financial_ingestion.chunker import chunk_filing
    from app.table_evidence.real_source import derive_cell,parse_resources
    raw,filing,_,_,_=synthetic()
    raw=raw.replace(b'us-gaap:Revenues',b'us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax')
    raw=raw.replace(b'<table>',b'<p>Amounts in millions except per share amounts</p><table>')
    raw=raw.replace(b'<th>Amounts in millions except per share amounts</th>',b'<th></th>')
    parsed=parse_sec_html(raw,filing.metadata.model_copy(update={'raw_content_hash':sha256(raw).hexdigest()}))
    parent=next(p for p in chunk_filing(parsed) if p.kind=='table' and p.metadata.get('row_label')=='NET SALES')
    table=next(t for t in parsed.tables if t.table_id==parent.source_location.table_id)
    cell=next(c for c in table.cells if c.row==parent.source_location.row_index and c.numeric_facts)
    args={'raw_hash':sha256(raw).hexdigest(),'generation':'a'*64,'manifest_hash':'b'*64}
    with pytest.raises(ValueError):derive_cell(parent,table,cell,parse_resources(raw),**args)
    observed=derive_cell(parent,table,cell,parse_resources(raw),product_mode=True,**args)
    assert str(observed.effective_value)=='23276000000'
    assert observed.display_unit_header=='Amounts in millions except per share amounts'
    # Legacy research behavior remains unchanged; target rows/headers still bind.
    bad=parent.model_copy(deep=True);bad.metadata['unit_context']='Amounts in billions'
    with pytest.raises(ValueError):derive_cell(bad,table,cell,parse_resources(raw),product_mode=True,**args)

def test_only_identical_source_verified_financial_facts_are_deduplicated():
    from app.product.sec_verified_rows import collapse_identical
    c=SimpleNamespace(cik='202',filing_id='source',raw_sha256='hash',row_label='NET SALES',period_kind='DURATION',
        period_start='2026-07-01',period_end='2026-09-30',period_months=3,unit='USD',multiplier=1000000,effective_value=123000000)
    a=(1,SimpleNamespace(chunk_id='a',metadata={'statement_title':'Results of operations'}),[c])
    b=(2,SimpleNamespace(chunk_id='b',metadata={'statement_title':'Consolidated Statements of Earnings'}),[c])
    assert collapse_identical([a,b])==[b]
    other=SimpleNamespace(**{**vars(c),'effective_value':124000000})
    conflict=(2,b[1],[other])
    assert collapse_identical([a,conflict])==[a,conflict]

def test_sec_raw_question_gate_rejects_wrong_metric_and_independently_checks_scale():
    from app.product.sec_answer_contract import annotate
    cell={'source_status':'VERIFIED_SOURCE_CELL','cik':'202','filing_id':'filing','raw_sha256':'hash','unit':'USD',
        'multiplier':'1000000','row_label':'NET SALES','raw_value':'123','value':'123','effective_value':'123000000',
        'period_end':'2026-09-30','period_kind':'DURATION','period_months':3,'parent_id':'source'}
    result={'status':'SUPPORTED','operation':'EXTRACT','values':['123000000'],'unit':'USD','source_cells':[cell],'citations':[{'chunk_id':'source'}]}
    good=annotate('Net sales for the quarter ended 2026-09-30',result)
    assert good['semantic_question_coverage']['status']=='COMPLETE' and good['values']==['123000000']
    wrong=annotate('Services net sales for the quarter ended 2026-09-30',result)
    assert wrong['answer_status']=='PARTIAL_VERIFIED' and wrong['values']==[] and wrong['citations']==result['citations']
    inflated=annotate('Net sales for the quarter ended 2026-09-30',{**result,'values':['123000000000']})
    assert inflated['independent_verification']['reason']=='SEC_INDEPENDENT_ARITHMETIC_MISMATCH' and inflated['values']==[]

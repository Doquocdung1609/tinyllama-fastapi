from pathlib import Path
from unittest.mock import Mock
from threading import Event
import pytest
from app.product.search_v3r import FinancialSearchV3R,_kind,_scope,_label_metric
from app.product.search_preparation import SearchPreparation


def test_source_labels_do_not_conflate_continuing_or_attributable_profit():
    assert _label_metric('Profit for the year','INCOME_STATEMENT',[])==['net_income']
    assert not _label_metric('Profit attributable to owners','INCOME_STATEMENT',[])
    assert not _label_metric('Profit from continuing operations','INCOME_STATEMENT',[])
    assert not _label_metric('Profit for the year','BALANCE_SHEET',[])
    assert _kind('Consolidated statements of financial position')=='BALANCE_SHEET'
    assert _scope('Unconsolidated report') is None


def test_evaluation_digit_locator_preserves_sign_and_source_page():
    from scripts.benchmark_search_v3r import locator
    ref={'document_id':'same','page':7,'source_values':['(123,456,789)']}
    hit={'document_id':'same','page':7,'text':'raw','source_cells':[{'text':'123.456.789'}]}
    assert not locator(hit,ref)
    hit['source_cells'][0]['text']='-123.456.789';assert locator(hit,ref)
    hit['page']=8;assert not locator(hit,ref)


def test_short_financial_fragment_requires_adjacent_table_and_real_source_label():
    from app.product.region_layout import rows_with_fragments
    from app.product.pdf_extract import _lines
    def word(text,x,y,region):return {'text':text,'rx':x,'ry':y,'rh':8,'rw':30,'box':[x,y,x+30,y+8],'confidence':90,'region_id':region,'line':[int(y),0]}
    words=[word('Cash and cash equivalents',10,20,'short'),word('123,456,789',180,20,'short'),word('234,567,890',280,20,'short')]
    saved={'tables':[],'engine':{},'lines':_lines(words),'regions':[{'id':'short','kind':'TEXT_IMAGE','box':[0,0,400,40]},{'id':'long','kind':'TABLE_IMAGE_CANDIDATE','box':[0,40,400,400]}]}
    rows=rows_with_fragments(saved,2);assert len(rows)==1
    assert rows[0]['cells'][0]['text']=='123,456,789'
    assert all(c['financial_evidence_status']=='FINANCIAL_EVIDENCE_REVIEW_PENDING' for c in rows[0]['cells'])
    saved['regions'][1]['box']=[0,100,400,400];assert rows_with_fragments(saved,2)==[]
    saved['regions'][1]['box']=[0,40,400,400];words[0]['text']='Signed by director';saved['lines']=_lines(words)
    assert rows_with_fragments(saved,2)==[]


def test_prewarm_does_not_issue_search_and_query_reverifies(tmp_path):
    w=Mock();engine=FinancialSearchV3R(w,tmp_path,False)
    engine.base.prepare=Mock(return_value={'generation':'a','documents':[],'entries':[]})
    engine.prewarm();engine.prewarm()
    assert engine.base.prepare.call_count==2
    w.search.assert_not_called()


def test_background_preparation_is_explicit_and_does_not_duplicate_work(tmp_path):
    p=SearchPreparation(Mock(),tmp_path);entered=Event();release=Event()
    def warm():entered.set();release.wait(3);return {'status':'READY','generation':'verified'}
    p.engine.prewarm=Mock(side_effect=warm)
    p.schedule();assert entered.wait(2)
    with pytest.raises(ValueError,match='SEARCH_INDEX_PREPARING'):p.ready_engine()
    p.schedule();release.set();p.close()
    assert p.engine.prewarm.call_count==2,'A source change during preparation must cause one coalesced refresh'
    assert p.ready_engine() is p.engine


def test_background_failure_remains_visible(tmp_path):
    p=SearchPreparation(Mock(),tmp_path);p.engine.prewarm=Mock(side_effect=ValueError('corrupt'))
    p.schedule();p.close()
    assert p.status()=={'status':'FAILED','reason':'SEARCH_PREPARATION_FAILED_CHECK_SOURCE'}


def test_warmed_index_rejects_rehashed_checkpoint_outside_sealed_generation(tmp_path):
    import pymupdf,json,hashlib
    from contextlib import closing
    from app.product.derived_workspace import DerivedPdfWorkspace
    class Vectors:
        def identity(self):return {'model':'SYNTHETIC_TEST_ONLY'}
        def embed(self,texts,query=False):return [[1.]+[0.]*767 for _ in texts]
    pdf=pymupdf.open();p=pdf.new_page();p.insert_text((40,60),'Total assets 123,450 at year end 2025. Native financial statement source.')
    raw=pdf.tobytes();pdf.close();w=DerivedPdfWorkspace(tmp_path/'derived',embedder=Vectors())
    try:
        doc=w.add_pdf('example.pdf',raw,'Example','TEST','2025');w.process(doc['id'])
        engine=FinancialSearchV3R(w,tmp_path/'index');engine.prewarm()
        with closing(w._connect()) as db,db:
            value=json.loads(db.execute('SELECT payload FROM page_evidence').fetchone()[0]);value['text']+=' tampered'
            encoded=json.dumps(value);db.execute('UPDATE page_evidence SET payload=?,payload_hash=?',(encoded,hashlib.sha256(encoded.encode()).hexdigest()))
        with pytest.raises(ValueError,match='DERIVED_GENERATION_MEMBERSHIP_CHANGED'):engine.prewarm()
    finally:w.close()

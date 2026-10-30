from contextlib import closing
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from threading import Event,Thread
import hashlib,json
import pymupdf
import pytest
from app.product.financial_labels import normalize_label,label_metrics,statement_candidate,source_row_candidate

def test_damaged_vas_after_tax_is_only_a_candidate_on_income_statement():
    raw='60 Lợi nhuận thuế TNDN'
    assert source_row_candidate(raw,'INCOME_STATEMENT')=='60 Lợi nhuận sau thuế TNDN'
    assert source_row_candidate(raw,'BALANCE_SHEET')==raw
    assert source_row_candidate('50 Lợi nhuận thuế TNDN','INCOME_STATEMENT')=='50 Lợi nhuận thuế TNDN'
    assert raw=='60 Lợi nhuận thuế TNDN'

def test_damaged_vas_revenue_and_property_rows_require_code_and_statement():
    revenue='cấp địch (10=01-02) vụ'
    property_row="230 III. Bi't ding san (nu tu' 11"
    assert label_metrics(source_row_candidate(revenue,'INCOME_STATEMENT'))==['net_revenue']
    assert label_metrics(source_row_candidate(property_row,'BALANCE_SHEET'))==['investment_property']
    assert source_row_candidate(revenue,'BALANCE_SHEET')==revenue
    assert source_row_candidate(property_row,'INCOME_STATEMENT')==normalize_label(property_row)
    assert source_row_candidate('cấp địch (10=01-02)','INCOME_STATEMENT')=='cấp địch (10=01-02)'

def test_precision_adjustment_demotes_known_other_metric_without_certifying_it():
    engine=FinancialSearchV3R2.__new__(FinancialSearchV3R2)
    intent=SimpleNamespace(metrics=('net_income',))
    wrong={'kind':'row','metrics':['pretax_income'],'row_label':'Profit before tax'}
    matching={'kind':'row','metrics':['net_income'],'row_label':'Profit after tax'}
    unknown={'kind':'row','metrics':[],'row_label':'Uncertain OCR'}
    assert engine._metric_ranking_adjustment(wrong,intent,'Profit after tax')==-12
    assert engine._metric_ranking_adjustment(matching,intent,'Profit after tax')==0
    assert engine._metric_ranking_adjustment(unknown,intent,'Profit after tax')==0
    assert engine._metric_ranking_adjustment({'kind':'row','metrics':[],'row_label':'Profit before tax from continuing operations'},SimpleNamespace(metrics=()),'Profit before tax from continuing operations Samsung 2025')==4
from app.product.source_units import units_in,header_unit,word_units,cell_unit,numeric_syntax
from app.product.resource_control import ResourceControl
from app.product.derived_workspace import DerivedPdfWorkspace
from app.product.search_v3r2 import FinancialSearchV3R2
from app.product.analysis import parse_number

@pytest.mark.parametrize('raw,metric',[("TOTAL OWNERS’ EQUITY",'equity'),("Owners' equity",'equity'),('Stockholders equity','equity'),('XI Pro t before tax','pretax_income'),('XIII Pro\x06t after tax','net_income'),('Proﬁt after tax','net_income'),('TOTAL LIABILITIES AND OWNERS’ EQUITY','total_funding')])
def test_controlled_label_candidates_preserve_original(raw,metric):
    before=raw;assert label_metrics(raw)==[metric];assert raw==before

@pytest.mark.parametrize('raw',['Gross profit','Operating profit','Profit margin','Profit after tax attributable to owners','Net income from discontinued operations','Profit from continuing operations'])
def test_profit_components_do_not_become_total_net_income(raw):
    assert not label_metrics(raw)

def test_font_gap_only_changes_constrained_financial_candidate():
    assert normalize_label('The consolidated statement of pro t or loss').endswith('profit or loss')
    assert normalize_label('Pro t margin')=='Pro t margin'
    assert statement_candidate('The consolidated statement of pro t or loss')=='INCOME_STATEMENT'
    assert statement_candidate('The consolidated statements of financial position')=='BALANCE_SHEET'

def test_multimetric_query_preserves_accounting_operands(tmp_path):
    engine=FinancialSearchV3R2(None,tmp_path)
    intent,_=engine._query_intent('Phương trình kế toán tổng tài sản bằng nợ phải trả và vốn chủ sở hữu năm2025')
    assert set(intent.metrics)=={'assets','liabilities','equity'}
    intent,_=engine._query_intent('Total assets liabilities and equity consolidated2025')
    assert 'assets' in intent.metrics

@pytest.mark.parametrize('text,unit',[('Unit: VND','VND'),('VND million','TRIEU_VND'),('Millions of VND','TRIEU_VND'),('Triệu đồng','TRIEU_VND'),('Nghìn đồng','NGHIN_VND'),('KRW','KRW'),('Korean won','KRW'),('USD','USD'),('U.S. dollars','USD')])
def test_explicit_source_units(text,unit):assert header_unit(text)==unit

def test_ambiguous_and_unsupported_scales_do_not_default_to_unscaled():
    assert header_unit('KRW and USD') is None
    assert header_unit('KRW million') is None
    assert header_unit('VND / VND million') is None

def test_source_unit_words_bind_separate_currency_columns():
    words=[{'text':'KRW','box':[95,10,115,20]},{'text':'USD','box':[295,10,315,20]}]
    for x,unit in [(100,'KRW'),(300,'USD')]:
        cell={'box':[x-10,80,x+10,90]};result=cell_unit(cell,words,'KRW USD')
        assert result['unit']==unit and result['source_text']==unit
    words=[{'text':'VND','box':[300,10,320,20]},{'text':'million','box':[322,10,350,20]}]
    assert cell_unit({'box':[315,80,350,90]},words,'VND million')['unit']=='TRIEU_VND'

@pytest.mark.parametrize('raw',['14,595895.255468','2,412,996843,057'])
def test_equal_digits_do_not_make_malformed_ocr_valid(raw):assert numeric_syntax(raw)['status']=='INVALID_NUMERIC_FORMAT'

def test_signed_decimal_blank_and_locale_ambiguity():
    assert parse_number('(1,234)','en_US')==Decimal(-1234)
    assert parse_number('−1.234,50','vi_VN')==Decimal('-1234.50')
    assert numeric_syntax('1,234')['status']=='AMBIGUOUS_NUMERIC_FORMAT'
    assert numeric_syntax('')['status']=='BLANK_NOT_ZERO'
    for raw in ['(-1,234)','((1,234))','1,234)']:
        with pytest.raises(ValueError):parse_number(raw,'en_US')

def test_low_memory_defers_before_heavy_work_and_does_not_change_processes(monkeypatch):
    monkeypatch.setattr('app.product.resource_control.psutil.virtual_memory',lambda:SimpleNamespace(available=100*1024**2))
    resources=ResourceControl()
    with pytest.raises(ValueError,match='LOW_MEMORY_DEFERRED'):
        with resources.claim('OCR'):pytest.fail('Heavy task entered under low memory')
    assert resources.status()['warning'] and resources.status()['active'] is None

def test_resource_tasks_are_single_flight_and_reentrant(monkeypatch):
    monkeypatch.setattr('app.product.resource_control.psutil.virtual_memory',lambda:SimpleNamespace(available=4096*1024**2))
    resources=ResourceControl(max_waiters=1);entered=Event();release=Event()
    def task():
        with resources.claim('OCR'):
            with resources.claim('EMBEDDING'):entered.set();release.wait(3)
    thread=Thread(target=task);thread.start();assert entered.wait(2)
    with pytest.raises(ValueError,match='RESOURCE_BUSY_RETRY'):
        with resources.claim('QUERY',timeout=.01):pytest.fail('Concurrent task entered')
    release.set();thread.join();assert resources.status()['max_active_observed']==1 and resources.status()['waiting']==0

class Vectors:
    def identity(self):return {'model':'SYNTHETIC_TEST_ONLY'}
    def embed(self,texts,query=False):return [[1.]+[0.]*767 for _ in texts]

def test_compact_index_reuses_verified_cache_and_blocks_rehashed_source(tmp_path):
    pdf=pymupdf.open();p=pdf.new_page();p.insert_text((30,50),'Consolidated statement of profit or loss. VND million. 2022 and 2021.')
    for i,label in enumerate(['Profit before tax','Profit after tax','Total equity']):
        p.insert_text((30,110+i*25),label);p.insert_text((340,110+i*25),'123,456');p.insert_text((440,110+i*25),'234,567')
    raw=pdf.tobytes();pdf.close();w=DerivedPdfWorkspace(tmp_path/'source',Vectors())
    try:
        doc=w.add_pdf('fixture.pdf',raw,'Fixture','TEST','2022');w.process(doc['id']);engine=FinancialSearchV3R2(w,tmp_path/'index');first=engine.prewarm();second=engine.prewarm()
        assert first['generation']==second['generation'] and engine.base.builds==1
        assert not engine.base.source._cache['entries'] and engine.base.cache_stats()['retained_page_views']==0
        found=engine.search('Profit before tax consolidated 2022','bm25',5,[doc['id']]);assert any(h.get('metric_ids')==['pretax_income'] for h in found['results'])
        with closing(w._connect()) as db,db:
            row=db.execute('SELECT payload FROM page_evidence').fetchone();data=json.loads(row[0]);data['text']+=' altered';encoded=json.dumps(data)
            db.execute('UPDATE page_evidence SET payload=?,payload_hash=?',(encoded,hashlib.sha256(encoded.encode()).hexdigest()))
        with pytest.raises(ValueError,match='DERIVED_GENERATION_MEMBERSHIP_CHANGED'):engine.prewarm()
    finally:w.close()

def test_explicit_english_million_cannot_be_reviewed_as_unscaled_currency(tmp_path):
    from app.product.workspace import PdfWorkspace
    from app.product.analysis import FactReview,review_fact
    pdf=pymupdf.open();p=pdf.new_page();p.insert_text((30,45),'SYNTHETIC Bao cao rieng cong ty me Example. Unit: VND million')
    p.insert_text((340,80),'31/12/2025');p.insert_text((440,80),'01/01/2025')
    p.insert_text((30,110),'Tong cong tai san');p.insert_text((340,110),'123,456');p.insert_text((440,110),'234,567')
    raw=pdf.tobytes();pdf.close();w=PdfWorkspace(tmp_path/'legacy',Vectors())
    try:
        doc=w.add_pdf('fixture.pdf',raw,'Synthetic Example','TEST','2025');w.process(doc['id']);row=w.page_evidence(doc['id'],1)['tables'][0]
        request=FactReview(page=1,row_id=row['id'],column_index=0,metric='assets',period='2025-12-31',column_label='31/12/2025',statement_scope='SEPARATE',unit='VND',convention='en_US',source_image_reviewed=True)
        with pytest.raises(ValueError,match='SOURCE_UNIT_SCALE_MISMATCH'):review_fact(w,doc['id'],request)
        fact=review_fact(w,doc['id'],request.model_copy(update={'unit':'TRIEU_VND'}))
        assert Decimal(fact['base_value'])==Decimal('123456000000')
    finally:w.close()

def test_owner_clone_preserves_parent_bytes_and_refuses_existing_target(tmp_path,monkeypatch):
    import scripts.clone_search_v3r2_workspace as cloning
    repo=tmp_path/'repo';(repo/'scripts').mkdir(parents=True);(repo/'studio_workspace').mkdir()
    monkeypatch.setattr(cloning,'__file__',str(repo/'scripts/clone_search_v3r2_workspace.py'))
    parents=[]
    for i in range(2):
        pdf=pymupdf.open();p=pdf.new_page();p.insert_text((30,50),f'Synthetic source number {i} Native report Total assets 123,456 in 2025.')
        w=DerivedPdfWorkspace(tmp_path/f'parent{i}',Vectors());raw=pdf.tobytes();pdf.close()
        doc=w.add_pdf(f'fixture{i}.pdf',raw,f'Fixture{i}','TEST','2025');w.process(doc['id']);w.close();parents.append(tmp_path/f'parent{i}')
    before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for parent in parents for p in parent.rglob('*') if p.is_file()}
    destination=repo/'studio_workspace/search-v3r2-test';out=tmp_path/'clone.json';cloning.clone(parents,destination,out)
    assert json.loads(out.read_text())['status']=='PASS_SOURCE_AND_BOUNDED_VECTOR_COPY'
    assert before=={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for parent in parents for p in parent.rglob('*') if p.is_file()}
    with pytest.raises(ValueError,match='NEW_V3R2_OWNER_ROOT_REQUIRED'):cloning.clone(parents,destination,tmp_path/'other.json')

def test_changed_document_preparation_discards_old_corpus_without_deleting_snapshots(tmp_path):
    from unittest.mock import Mock
    from threading import RLock
    from app.product.search_preparation import SearchPreparation
    w=Mock(search_candidate_version='V3R2');w.resources=ResourceControl();preparation=SearchPreparation(w,tmp_path)
    engine=preparation.engine;engine.base._cache={'old':'corpus'};engine.base.source._cache={'entries':['old']};engine._last_entries={'old':{}}
    def warm():
        assert engine.base._cache is None and engine.base.source._cache is None and not engine._last_entries
        return {'status':'READY','generation':'new'}
    engine.prewarm=warm;old=tmp_path/'old-generation.sqlite3';old.write_bytes(b'kept source index')
    preparation.schedule(invalidate=True);preparation.close()
    assert preparation.status()['generation']=='new' and old.read_bytes()==b'kept source index'

"""Deterministic product integrity tests; live owner PDFs are tested separately."""
from contextlib import closing
from decimal import Decimal
import json
import pymupdf
import pytest
from fastapi.testclient import TestClient

from app.product.workspace import PdfWorkspace,DIMENSION
from app.product.pdf_extract import inverse_box,folded
from app.product.analysis import FactReview,review_fact,eligible_facts,AnalysisRequest,numeric_answer,parse_number


class Vectors:
    def identity(self):return {'model':'fixture-only','dimension':DIMENSION}
    def embed(self,texts,query=False):return [[1.]+[0.]*(DIMENSION-1) for _ in texts]


@pytest.fixture
def evidence_workspace(tmp_path):
    pdf=pymupdf.open();page=pdf.new_page()
    page.insert_text((40,60),'SYNTHETIC TEST SOURCE - Bao cao rieng cong ty me Example')
    page.insert_text((40,90),'Unit: VND')
    page.insert_text((330,120),'31/12/2025');page.insert_text((430,120),'01/01/2025')
    page.insert_text((40,150),'Tong cong tai san');page.insert_text((350,150),'1,250');page.insert_text((450,150),'1,000')
    page.insert_text((40,180),'Narrative text for deterministic page classification and native extraction only.')
    workspace=PdfWorkspace(tmp_path/'owned',embedder=Vectors())
    doc=workspace.add_pdf('synthetic.pdf',pdf.tobytes(),'Synthetic Example','TEST','2025');pdf.close()
    assert workspace.process(doc['id'])['status']=='READY'
    page=workspace.page_evidence(doc['id'],1)
    row=next(r for r in page['tables'] if 'tong cong tai san' in folded(r['row_label']))
    yield workspace,doc,row
    workspace.close()


def reviewed(workspace,doc,row,col=0):
    return review_fact(workspace,doc['id'],FactReview(page=1,row_id=row['id'],column_index=col,
        metric='assets',period='2025-12-31' if col==0 else '2025-01-01',
        column_label='31/12/2025' if col==0 else '01/01/2025',statement_scope='SEPARATE',unit='VND',
        convention='en_US',source_image_reviewed=True))


def test_v3_retrieval_retains_context_without_promoting_wrong_period(evidence_workspace,tmp_path):
    from app.product.search_v3 import FinancialSearchV3
    w,d,row=evidence_workspace;reviewed(w,d,row)
    v=FinancialSearchV3(w,tmp_path/'v3')
    result=v.search('Tìm tổng tài sản công ty mẹ năm 2031','bm25',5,[d['id']])
    assert result['results'], 'Related source must remain discoverable'
    assert not any(h['numeric_answer_eligible'] for h in result['results'])
    assert any('PERIOD_NOT_PROVEN' in h['conflicts'] for h in result['results'])
    assert v.search('Tong tai san rieng ngay 31/12/2025','bm25',5,[d['id']])['results'][0]['numeric_answer_eligible']


def test_v3_entity_and_duration_guards(evidence_workspace,tmp_path):
    from app.product.search_v3 import FinancialSearchV3,intent_for
    w,d,row=evidence_workspace;reviewed(w,d,row)
    v=FinancialSearchV3(w,tmp_path/'v3')
    for query in ['Total assets of AnotherCompany separate as of 31/12/2025',
                  'AnotherCompany total assets separate as of 31/12/2025',
                  'anothercompany total assets separate as of 31/12/2025',
                  'Tong tai san rieng quy IV nam 2025', 'Tong tai san khong phai hop nhat 31/12/2025']:
        result=v.search(query,'bm25',5,[d['id']])
        assert result['results'] and not any(h['numeric_answer_eligible'] for h in result['results'])
    assert intent_for('net sales September 30, 2026')[0].dates==('2026-09-30',)
    assert intent_for('Phuong trinh ke toan nam 2025')[0].metrics==('assets','liabilities','equity')


def test_v3_natural_capitalization_does_not_guess_company(evidence_workspace,tmp_path):
    from app.product.search_v3 import FinancialSearchV3
    w,d,row=evidence_workspace
    result=FinancialSearchV3(w,tmp_path/'v3').search('Tìm tổng tài sản trong bảng cân đối kế toán','bm25',5,[d['id']])
    assert result['results'] and not result['intent']['entity_scope']['unrecognized_name']
    assert not any(h['numeric_answer_eligible'] for h in result['results'])
    from app.product.search_v3 import entity_conflict
    assert not entity_conflict('Tong tai san quy IV nam 2025',[d])[1]


@pytest.mark.parametrize('label,metric',[
    ('Finance income','financial_revenue'),('Net operating revenues','net_revenue'),
    ('Total equity','equity'),('Income before income taxes','pretax_income')])
def test_v3_additive_concepts(label,metric):
    from app.product.search_v3 import metrics_in
    assert metrics_in(label)==[metric]


def test_v3_fuzzy_ocr_is_candidate_only_and_does_not_merge_concepts():
    from app.product.search_v3 import row_metrics
    assert row_metrics('Tong loi nhuan ke toan truoc thue')==['pretax_income']
    assert row_metrics('Tai san co dinh vo hinh')==['intangible_assets']
    assert row_metrics('financial expenses')==[]


@pytest.mark.parametrize('raw,locale,expected',[
 ('1.234.567','vi_VN','1234567'),('1.234,56','vi_VN','1234.56'),('1,234.56','en_US','1234.56'),
 ('(1.234.567)','vi_VN','-1234567'),('-1.234.567','vi_VN','-1234567'),('2,5','vi_VN','2.5'),
 ('0','vi_VN','0')])
def test_explicit_numeric_conventions(raw,locale,expected):
    assert parse_number(raw,locale)==Decimal(expected)


@pytest.mark.parametrize('raw,locale',[('-', 'vi_VN'),('', 'en_US'),('1,234.56','vi_VN'),('12.34.567','vi_VN')])
def test_ambiguous_or_blank_never_becomes_zero(raw,locale):
    with pytest.raises(ValueError):parse_number(raw,locale)


def test_real_geometry_inverse_quarter_turn():
    assert inverse_box([20,30,60,80],90,200,300)==[30,240,80,280]
    assert inverse_box([20,30,60,80],180,200,300)==[140,220,180,270]
    assert inverse_box([20,30,60,80],270,200,300)==[120,20,170,60]
    assert folded('TỔNG   TÀI SẢN ĐẦU NĂM')=='tong tai san dau nam'


def test_ocr_numbers_require_explicit_image_review_and_period_scope_unit(evidence_workspace):
    w,d,row=evidence_workspace
    base=dict(page=1,row_id=row['id'],column_index=0,metric='assets',period='2025-12-31',column_label='31/12/2025',
              statement_scope='SEPARATE',unit='VND',convention='en_US',source_image_reviewed=True)
    for updates,reason in [({'source_image_reviewed':False},'SOURCE_IMAGE_REVIEW'),
                           ({'statement_scope':'CONSOLIDATED'},'SOURCE_SCOPE'),
                           ({'unit':'TRIEU_VND'},'SOURCE_UNIT'),
                           ({'period':'2025-02-01'},'EXACT_SOURCE_PERIOD'),
                           ({'column_index':1},'SOURCE_COLUMN_GEOMETRY')]:
        with pytest.raises(ValueError,match=reason):review_fact(w,d['id'],FactReview(**(base|updates)))


def test_decimal_comparison_and_question_conflicts(evidence_workspace):
    w,d,row=evidence_workspace
    request=AnalysisRequest(question='Tong tai san tang bao nhieu so voi dau nam 2025?',document_ids=[d['id']],
                            mode='numeric',operation='ABS_CHANGE',current_period='2025-12-31',previous_period='2025-01-01')
    assert numeric_answer(w,request)['values']==[]
    reviewed(w,d,row);reviewed(w,d,row,1)
    answer=numeric_answer(w,request)
    assert answer['status']=='SUPPORTED' and answer['values']==['250'] and answer['unit']=='VND'
    assert len(answer['citations'])==2
    for question in ['Tong tai san nam 2031?','Doanh thu thuan nam 2025?','Tong tai san hop nhat?']:
        assert numeric_answer(w,request.model_copy(update={'question':question}))['values']==[]


def test_reviewed_evidence_tampering_fails_closed(evidence_workspace):
    w,d,row=evidence_workspace;reviewed(w,d,row)
    assert eligible_facts(w,[d['id']])
    with closing(w._connect()) as db,db:
        record=db.execute('SELECT payload FROM page_evidence WHERE document_id=?',(d['id'],)).fetchone()
        data=json.loads(record['payload']);data['text']='tampered'
        db.execute('UPDATE page_evidence SET payload=? WHERE document_id=?',(json.dumps(data),d['id']))
    with pytest.raises(ValueError,match='HASH_MISMATCH'):eligible_facts(w,[d['id']])


def test_new_api_auth_scope_comparison_and_no_local_paths(evidence_workspace,monkeypatch):
    from main import app
    from app.product import frontend_api as api
    w,d,row=evidence_workspace
    monkeypatch.setattr(api,'workspace',lambda:w)
    monkeypatch.setenv('STUDIO_API_TOKEN','fixture-only-not-a-production-secret')
    with TestClient(app) as client:
        assert client.post('/studio/query',json={'query':'tai san'}).status_code==401
        headers={'Authorization':'Bearer fixture-only-not-a-production-secret'}
        result=client.post('/studio/compare',headers=headers,json={'query':'tong tai san','source':'USER_UPLOADS','document_ids':[d['id']]})
        assert result.status_code==200,result.text
        data=result.json();assert data['quality_metrics'] is None
        assert len({arm['generation'] for arm in data['arms'].values()})==1
        comparison=client.post('/studio/compare',headers=headers,json={
            'query':'tong tai san','source':'USER_UPLOADS','document_ids':[d['id']],
            'include_faith_r':True,'top_k':5,
        })
        assert comparison.status_code==200,comparison.text
        compared=comparison.json()
        assert set(compared['arms'])=={'bm25','dense','hybrid'}
        assert not compared['arm_errors']
        assert compared['faith_r']['search_profile']=='faith_r_product_v1'
        assert compared['faith_r']['results']
        assert all(hit['document_id']==d['id'] for hit in compared['faith_r']['results'])
        assert 'raw_path' not in result.text and str(w.root) not in result.text
        assert client.get('/studio/documents/../../secrets/file',headers=headers).status_code in {404,409}
        pdf=client.get(f'/studio/documents/{d["id"]}/file',headers=headers)
        assert pdf.content.startswith(b'%PDF')


def test_optional_model_failure_does_not_become_verified_fact(monkeypatch):
    from app.product.analysis import bounded_summary
    from app.services import ollama_service
    monkeypatch.setattr(ollama_service,'generate',lambda *a,**k:'Tổng tài sản là 999 tỷ [S1].')
    result=bounded_summary('test',[{'chunk_id':'fixture','text':'No verified number'}])
    assert result['status']=='MODEL_PROSE_REJECTED'


def test_corrupted_review_record_is_not_a_verified_value(evidence_workspace):
    w,d,row=evidence_workspace;reviewed(w,d,row)
    with closing(w._connect()) as db,db:
        record=db.execute('SELECT payload FROM reviewed_facts').fetchone()
        payload=json.loads(record['payload']);payload['base_value']='999999'
        db.execute('UPDATE reviewed_facts SET payload=?',(json.dumps(payload),))
    with pytest.raises(ValueError,match='INTEGRITY_FAILED'):eligible_facts(w,[d['id']])


def test_product_registry_requires_exact_manifest_and_generation():
    from app.table_evidence.product_registry import product_registry
    assert product_registry({'manifest_hash':'unregistered','generation':'unregistered'}) is None


def test_failed_page_retries_without_reextracting_completed_checkpoint(tmp_path,monkeypatch):
    from app.product import pdf_extract as extraction
    import pymupdf
    path=tmp_path/'resume.pdf'
    with pymupdf.open() as pdf:
        for _ in range(2):pdf.new_page().insert_text((50,50),'Financial source evidence with enough native text to retain a complete checkpoint for subsequent recovery.')
        pdf.save(path)
    original=extraction.extract_page;calls=[];saved={}
    def page_once(page,number):
        calls.append(number)
        if number==2 and calls.count(2)==1:raise ValueError('OCR_PAGE_FAILED')
        return original(page,number)
    monkeypatch.setattr(extraction,'extract_page',page_once)
    def checkpoint(number):
        result=saved.get(number)
        return result if result and result['status']!='FAILED' else None
    def progress(number,value,total):saved[number]=value
    with pytest.raises(ValueError,match='OCR_PAGE_FAILED'):
        extraction.extract_document(path,'resume',checkpoint,progress)
    assert saved[1]['status']=='EXTRACTED' and saved[2]['status']=='FAILED'
    pages,chunks=extraction.extract_document(path,'resume',checkpoint,progress)
    assert pages==2 and {chunk['page'] for chunk in chunks}=={1,2}
    assert calls==[1,2,2] and saved[2]['status']=='EXTRACTED'


@pytest.mark.parametrize('text,expected',[
 ('Tổng tài sản','assets'),('Quy mo tai san','assets'),('Tài sản cố định','fixed_assets'),
 ('Tài sản cố định vô hình','intangible_assets'),('Doanh thu thuần','net_revenue'),
 ('Doanh thu hoạt động tài chính','financial_revenue'),('Lãi sau thuế','net_income'),
 ('Lợi nhuận kế toán trước thuế','pretax_income'),('Nợ phải trả khác','other_liabilities'),
 ('Tổng nguồn vốn','total_funding'),('Tiền và tương đương tiền','cash_equivalents'),
 ('Số dư tiền','cash_balance'),('Dòng tiền thuần trong kỳ','net_cashflow')])
def test_financial_ontology_concepts_remain_distinct(text,expected):
    from app.product.query_intent import metric_matches
    assert metric_matches(text)==[expected]


def test_query_intent_period_basis_operation():
    from app.product.query_intent import understand
    intent=understand('So sánh tổng tài sản hợp nhất số trình bày lại ngày 31/12/2024 với ngày 31/12/2023, triệu đồng')
    assert intent.scope=='CONSOLIDATED' and intent.basis=='RESTATED'
    assert intent.dates==('2023-12-31','2024-12-31') and intent.operation=='CHANGE' and intent.unit=='TRIEU_VND'


def test_scope_basis_prefixes_and_negations_are_not_positive_matches():
    from app.product.query_intent import understand
    assert understand('unconsolidated total assets').scope=='SEPARATE'
    assert understand('unrestated total assets').basis=='ORIGINAL'
    assert understand('tổng tài sản không phải hợp nhất').scope=='AMBIGUOUS'
    assert understand('total assets not restated').basis=='AMBIGUOUS'


def test_source_statement_classification_and_conflicting_request(evidence_workspace,tmp_path):
    from app.product.search_v2 import FinancialSearchV2,statement_kind,unit_header
    assert statement_kind('BẢNG CÂN ĐỐI KẾ TOÁN HỢP NHẤT')=='BALANCE_SHEET'
    assert statement_kind('BÁO CÁO KẾT QUẢ HOẠT ĐỘNG KINH DOANH')=='INCOME_STATEMENT'
    assert statement_kind('Thuyết minh báo cáo tài chính')=='NOTES'
    assert statement_kind('unreadable')=='UNKNOWN'
    assert unit_header('Đơn vị: triệu đồng')=='TRIEU_VND'
    w,d,row=evidence_workspace;reviewed(w,d,row)
    result=FinancialSearchV2(w,tmp_path/'sidecar').search('tổng tài sản riêng trong báo cáo kết quả kinh doanh ngày 31/12/2025','bm25',5,[d['id']])
    assert result['results']==[]


def test_v2_row_provenance_and_review_are_separate(evidence_workspace,tmp_path):
    from app.product.search_v2 import FinancialSearchV2
    w,d,row=evidence_workspace;v=FinancialSearchV2(w,tmp_path/'sidecar')
    result=v.search('Tổng tài sản báo cáo riêng ngày 31/12/2025','bm25',5,[d['id']])
    assert result['results'][0]['row_id']==row['id']
    assert not result['results'][0]['numeric_answer_eligible']
    reviewed(w,d,row)
    result=v.search('Quy mô tài sản báo cáo riêng ngày 31/12/2025','bm25',5,[d['id']])
    hit=result['results'][0]
    assert hit['numeric_answer_eligible'] and hit['reviewed_facts'][0]['period']=='2025-12-31'
    assert hit['source_sha256']==d['sha256'] and hit['box']==row['cells'][0]['box']
    # The sidecar holds no open Windows SQLite handle after search.
    file=next((tmp_path/'sidecar').glob('*.sqlite3'));renamed=file.with_suffix('.roundtrip')
    file.rename(renamed);renamed.rename(file)


@pytest.mark.parametrize('question',[
 'Tổng tài sản riêng năm 2031','Tổng tài sản hợp nhất năm 2025',
 'Tổng tài sản của ACME năm 2025','Tổng tài sản của Missing Company năm 2025',
 'Total assets of Apple separate as of 31/12/2025','total assets of missing company separate as of 31/12/2025',
 'Tổng tài sản riêng ngày 31/02/2025','Tổng tài sản riêng số trình bày lại năm 2025'])
def test_v2_missing_context_never_claims_answer(evidence_workspace,tmp_path,question):
    from app.product.search_v2 import FinancialSearchV2
    w,d,row=evidence_workspace;reviewed(w,d,row)
    result=FinancialSearchV2(w,tmp_path/'sidecar').search(question,'bm25',5,[d['id']])
    assert result['evidence_status']=='NO_SUFFICIENT_EVIDENCE' and result['results']==[]


def test_v2_index_tamper_rejected_without_changing_parent(evidence_workspace,tmp_path):
    import sqlite3
    from app.product.search_v2 import FinancialSearchV2
    w,d,row=evidence_workspace;v=FinancialSearchV2(w,tmp_path/'sidecar')
    result=v.search('tổng tài sản','bm25',5,[d['id']]);parent=result['results'][0]['chunk_id']
    with closing(sqlite3.connect(next((tmp_path/'sidecar').glob('*.sqlite3')))) as db,db:db.execute("UPDATE fts SET body='forged'")
    with pytest.raises(ValueError,match='INDEX_BYTES_CHANGED'):v.search('tổng tài sản','bm25',5,[d['id']])
    assert w.search('tổng tài sản','bm25',5,[d['id']])['results'][0]['chunk_id']==parent


def test_narrative_request_cannot_inherit_unrelated_reviewed_numbers(evidence_workspace,tmp_path):
    from app.product.search_v2 import FinancialSearchV2
    w,d,row=evidence_workspace;reviewed(w,d,row)
    v=FinancialSearchV2(w,tmp_path/'sidecar')
    for experiment in ['C2','C3','C4']:
        result=v.search('rủi ro và dự phòng tài chính','bm25',5,[d['id']],experiment)
        assert not any(h['numeric_answer_eligible'] for h in result['results'])


def test_v2_multiple_source_periods_need_explicit_column(evidence_workspace,tmp_path):
    from app.product.search_v2 import FinancialSearchV2
    w,d,row=evidence_workspace;reviewed(w,d,row,0);reviewed(w,d,row,1)
    v=FinancialSearchV2(w,tmp_path/'sidecar')
    ambiguous=v.search('tổng tài sản báo cáo riêng năm 2025','bm25',5,[d['id']])
    assert not any(r['numeric_answer_eligible'] for r in ambiguous['results'])
    specific=v.search('tổng tài sản báo cáo riêng cuối năm 2025','bm25',5,[d['id']])
    assert specific['results'][0]['numeric_answer_eligible']
    assert {f['period'] for f in specific['results'][0]['reviewed_facts']}=={'2025-12-31'}


def test_pdfjs_worker_mime_ignores_windows_registry_association(tmp_path,monkeypatch):
    import mimetypes
    from app.product.static_files import StudioStaticFiles
    from fastapi import FastAPI
    monkeypatch.setitem(mimetypes.types_map,'.mjs','text/plain')
    worker=tmp_path/'pdf.worker.mjs';worker.write_text('export const test=1')
    app=FastAPI();app.mount('/app',StudioStaticFiles(directory=tmp_path))
    with TestClient(app) as client:
        response=client.get('/app/pdf.worker.mjs')
        assert response.status_code==200 and response.headers['content-type'].split(';')[0] in {'text/javascript','application/javascript'}
        cached=client.get('/app/pdf.worker.mjs',headers={'If-None-Match':response.headers['etag']})
        assert cached.status_code==304 and cached.headers['content-type'].startswith('text/javascript')


def test_benchmark_duplicate_source_hits_cannot_inflate_ndcg():
    from scripts.benchmark_search_v2 import score_query
    import math
    q={'relevant':[{'document_id':'d','page':3,'row_id':'r','span':'gold'}],'expected_abstention':False}
    hits=[{'document_id':'d','page':1,'text':'wrong'},
          {'document_id':'d','page':3,'text':'gold','row_id':'r'},
          {'document_id':'d','page':3,'text':'gold duplicate','row_id':'r'}]
    metrics=score_query(q,{'results':hits})
    assert metrics['ndcg_at_5']==pytest.approx(1/math.log2(3))
    assert metrics['recall_at_5']==1 and metrics['mrr_at_5']==.5
    assert metrics['precision_at_5'] is None


def test_api_v2_opt_in_and_baseline_comparison_contract(evidence_workspace,tmp_path,monkeypatch):
    from app.product import frontend_api
    from fastapi import FastAPI
    w,d,row=evidence_workspace;reviewed(w,d,row)
    monkeypatch.setattr(frontend_api,'workspace',lambda:w)
    monkeypatch.setenv('STUDIO_API_TOKEN','fixture-private-test-access')
    monkeypatch.setenv('STUDIO_SEARCH_V2_ROOT',str(tmp_path/'sidecar'))
    app=FastAPI();app.include_router(frontend_api.router)
    headers={'Authorization':'Bearer fixture-private-test-access'}
    body={'query':'Tổng tài sản riêng ngày 31/12/2025','source':'USER_UPLOADS','mode':'bm25','document_ids':[d['id']],'search_profile':'production_v2'}
    with TestClient(app) as client:
        result=client.post('/studio/query',headers=headers,json=body)
        assert result.status_code==200,result.text
        assert result.json()['results'][0]['numeric_answer_eligible']
        comparison=client.post('/studio/compare',headers=headers,json=body).json()
        assert {arm['search_profile'] for arm in comparison['arms'].values()}=={'baseline'}
        assert len({arm['generation'] for arm in comparison['arms'].values()})==1
        v3=client.post('/studio/compare',headers=headers,json={**body,'search_profile':'production_v3'}).json()
        assert {arm['search_profile'] for arm in v3['arms'].values()}=={'baseline'}
        assert v3['candidate']['search_profile']=='production_v3'
        assert v3['candidate']['results'][0]['numeric_answer_eligible']


def test_experiment_copy_preserves_source_and_refuses_existing_destination(tmp_path,monkeypatch):
    from scripts import prepare_search_v2_workspace as copying
    from app.product.workspace import OWNER
    fake=tmp_path/'repo';(fake/'scripts').mkdir(parents=True);(fake/'studio_workspace').mkdir()
    monkeypatch.setattr(copying,'__file__',str(fake/'scripts/copy.py'))
    source=tmp_path/'source';source.mkdir();(source/'ownership.json').write_text(json.dumps({'owner':OWNER}));(source/'raw.pdf').write_bytes(b'copy-test-only')
    before=copying.inventory(source);destination=fake/'studio_workspace/search-v2-test'
    copying.prepare(source,destination)
    assert copying.inventory(source)==before and (destination/'raw.pdf').read_bytes()==b'copy-test-only'
    with pytest.raises(ValueError,match='NEW_DISTINCT_DESTINATION_REQUIRED'):copying.prepare(source,destination)


def test_experiment_copy_rejects_unowned_source(tmp_path,monkeypatch):
    from scripts import prepare_search_v2_workspace as copying
    fake=tmp_path/'repo';(fake/'scripts').mkdir(parents=True);(fake/'studio_workspace').mkdir()
    monkeypatch.setattr(copying,'__file__',str(fake/'scripts/copy.py'))
    source=tmp_path/'source';source.mkdir();(source/'ownership.json').write_text('{"owner":"not-owned"}')
    with pytest.raises(ValueError,match='OWNERSHIP_INVALID'):copying.prepare(source,fake/'studio_workspace/search-v2-test')

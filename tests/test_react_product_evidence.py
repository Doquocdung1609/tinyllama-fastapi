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

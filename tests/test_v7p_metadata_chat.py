from hashlib import sha256
import pytest
from app.product.document_metadata import extract_metadata,read_metadata,correct_metadata
from app.product.workspace import PdfWorkspace,DIMENSION
from app.product import frontend_api
from test_v7p_verified_operands import setup_source


class SyntheticEmbedder:
    def identity(self):return {'model':'synthetic-test-only','dimension':DIMENSION}
    def embed(self,texts,query=False):return [[1.0]+[0.0]*(DIMENSION-1) for _ in texts]


def test_malformed_pdf_has_no_record_or_locked_source(tmp_path):
    w=PdfWorkspace(tmp_path/'workspace',embedder=SyntheticEmbedder())
    try:
        for _ in range(2):
            with pytest.raises(ValueError,match='PDF_CONTENT_INVALID_OR_ENCRYPTED'):
                w.add_pdf('broken.pdf',b'%PDF-not-a-document')
        assert w.list_documents()==[]
        assert not list(w.files.iterdir())
    finally:w.close()


def test_zero_metadata_upload_and_auditable_correction(tmp_path):
    _,_,path=setup_source(tmp_path)
    raw=path.read_bytes();w=PdfWorkspace(tmp_path/'workspace',embedder=SyntheticEmbedder())
    try:
        doc=w.add_pdf('report.pdf',raw)
        assert doc['issuer'].strip()=='Example Inc.'
        assert doc['document_type']=='10-K' and doc['report_period']=='2025-09-27'
        source=read_metadata(w,doc['id'])
        assert source['fields']['issuer']['status']=='AUTO_CONFIRMED'
        assert source['fields']['currency']['status']=='UNKNOWN'
        assert w.add_pdf('different-name.pdf',raw)['duplicate'] is True
        corrected=correct_metadata(w,doc['id'],{'issuer':'Confirmed display name'})
        assert corrected['fields']['issuer']==source['fields']['issuer']
        assert corrected['corrections'][-1]['status']=='USER_CORRECTED'
        assert sha256(w.source_file(doc['id']).read_bytes()).hexdigest()==doc['sha256']
        assert w.document(doc['id'])['issuer']=='Confirmed display name'
    finally:w.close()
    w=PdfWorkspace(tmp_path/'workspace',embedder=SyntheticEmbedder())
    try:assert read_metadata(w,doc['id'])['corrections']==corrected['corrections']
    finally:w.close()


def test_chat_followup_scope_reset_and_real_source_operands(tmp_path,monkeypatch):
    _,_,path=setup_source(tmp_path)
    w=PdfWorkspace(tmp_path/'workspace',embedder=SyntheticEmbedder())
    monkeypatch.setenv('STUDIO_SEARCH_V2_ROOT',str(tmp_path/'search'))
    monkeypatch.setattr(frontend_api,'workspace',lambda:w)
    try:
        doc=w.add_pdf('report.pdf',path.read_bytes());assert w.process(doc['id'])['status']=='READY'
        first=frontend_api.financial_chat(frontend_api.ChatRequest(question='Total net sales fiscal 2025?',document_ids=[doc['id']]))
        assert first['status']=='SUPPORTED' and first['values']==['125']
        next_=frontend_api.financial_chat(frontend_api.ChatRequest(question='So với năm 2024 tăng bao nhiêu phần trăm?',document_ids=[doc['id']],session_id=first['session_id']))
        assert next_['status']=='SUPPORTED' and next_['values']==['25.00']
        other=frontend_api.financial_chat(frontend_api.ChatRequest(question='Còn năm 2024?',document_ids=[doc['id']],session_id=first['session_id']))
        assert other['status']=='SUPPORTED' and other['values']==['100'],other
        correct_metadata(w,doc['id'],{'report_period':'2025'})
        reset=frontend_api.financial_chat(frontend_api.ChatRequest(question='Growth compared with 2024?',document_ids=[doc['id']],session_id=first['session_id']))
        assert reset['conversation_reset'] is True and reset['values']==[]
    finally:w.close()


def test_fabricated_source_chunk_is_rejected(tmp_path):
    from app.product.native_financial_tables import recover_retrieved_tables
    _,_,path=setup_source(tmp_path);w=PdfWorkspace(tmp_path/'workspace',embedder=SyntheticEmbedder())
    try:
        doc=w.add_pdf('report.pdf',path.read_bytes());w.process(doc['id'])
        hit={'document_id':doc['id'],'page':2,'source_sha256':doc['sha256'],'chunk_id':'fabricated'}
        with pytest.raises(ValueError,match='CHUNK_MEMBERSHIP'):recover_retrieved_tables(w,[doc['id']],[hit])
    finally:w.close()


def test_chat_and_metadata_tamper_return_typed_conflict(tmp_path,monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    _,_,path=setup_source(tmp_path);w=PdfWorkspace(tmp_path/'workspace',embedder=SyntheticEmbedder())
    monkeypatch.setattr(frontend_api,'workspace',lambda:w)
    monkeypatch.setenv('STUDIO_API_TOKEN','synthetic-test-token-only')
    try:
        doc=w.add_pdf('report.pdf',path.read_bytes());w.process(doc['id'])
        w.source_file(doc['id']).write_bytes(path.read_bytes()+b'tampered')
        app=FastAPI();app.include_router(frontend_api.router)
        with TestClient(app) as client:
            headers={'Authorization':'Bearer synthetic-test-token-only'}
            responses=[client.post('/studio/chat',headers=headers,json={'question':'Net income 2025?','document_ids':[doc['id']]}),
                       client.get('/studio/documents/'+doc['id']+'/metadata',headers=headers)]
        assert all(r.status_code==409 and r.json()['detail']['code']=='PDF_SOURCE_HASH_MISMATCH' for r in responses)
    finally:w.close()

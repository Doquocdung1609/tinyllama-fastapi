import json
from contextlib import closing
import pytest
from app.product.financial_understanding import understand,requested_unit
from app.product.query_source_context import source_company_conflict,company_mentions
from app.product.assistant_answer import needs_number
from app.product import frontend_api
from app.product.workspace import PdfWorkspace
from test_v7p_metadata_chat import SyntheticEmbedder
from test_v7p_verified_operands import setup_source

Q2='Tìm dòng lợi nhuận sau thuế chưa phân phối trong bảng điều chỉnh báo cáo tài chính BIDV năm 2024'
Q2B='Tìm dòng "Lợi nhuận sau thuế chưa phân phối" trong tài liệu đang chọn. Cho biết các đoạn nguồn liên quan và trang PDF.'

@pytest.mark.parametrize('q',[Q2,Q2B])
def test_evidence_intent_precedes_financial_metric(q):
    assert understand(q).intent=='FIND_EVIDENCE'
    assert understand(q).metric=='retained_earnings'
    assert not needs_number(q)
    assert company_mentions(Q2)==['BIDV']

@pytest.mark.parametrize('word',['dòng','đóng','động','dong'])
def test_bare_folded_dong_is_not_currency(word):
    assert requested_unit('Tìm '+word+' trong tài liệu') is None

@pytest.mark.parametrize('text,unit',[('triệu đồng','TRIEU_VND'),('tỷ đồng','TY_VND'),('VND','VND'),('đồng','VND'),('%','%'),('million USD','USD')])
def test_actual_units(text,unit):assert requested_unit(text)==unit

def test_document_aware_alias_and_unknown_are_not_contradiction():
    class W:
        def document(self,_):return {'filename':'BID_BCTC_2024.pdf','issuer':'Bảng cân đối kế toán'}
    assert source_company_conflict(W(),['a'],Q2) is None
    assert source_company_conflict(W(),['a'],'Hòa Phát doanh thu năm 2024?')['status']=='QUERY_CONTEXT_CONFLICT'
    class Unknown:
        def document(self,_):return {'filename':'unknown.pdf','issuer':''}
    assert source_company_conflict(Unknown(),['a'],'BIDV doanh thu năm 2024?') is None

def test_session_migration_preserves_legacy_payload_and_restart(tmp_path,monkeypatch):
    from app.product.chat_store import connect,save
    root=tmp_path/'workspace';w=PdfWorkspace(root,embedder=SyntheticEmbedder())
    legacy=[{'question':'Legacy source question','response':{'status':'SOURCE_EXCERPTS','citations':[]}}]
    sid='c'*32
    with closing(w._connect()) as db,db:
        db.execute('CREATE TABLE financial_chat_sessions(id TEXT PRIMARY KEY,scope TEXT NOT NULL,payload TEXT NOT NULL)')
        db.execute('INSERT INTO financial_chat_sessions VALUES(?,?,?)',(sid,'old',json.dumps(legacy)))
    monkeypatch.setattr(frontend_api,'workspace',lambda:w)
    assert frontend_api.chat_session(sid)['turns']==legacy
    frontend_api.rename_chat(sid,frontend_api.ChatRename(title='Renamed'))
    assert frontend_api.chat_sessions(q='Renamed')['sessions'][0]['id']==sid
    w.close();w=PdfWorkspace(root,embedder=SyntheticEmbedder())
    try:
        assert frontend_api.chat_session(sid)['turns']==legacy
        assert frontend_api.chat_session(sid)['title']=='Renamed'
        with pytest.raises(Exception):frontend_api.chat_sessions(q='',limit=101)
    finally:w.close()

def test_abstention_keeps_search_chat_evidence_and_trace(tmp_path,monkeypatch):
    _,_,path=setup_source(tmp_path);w=PdfWorkspace(tmp_path/'w',embedder=SyntheticEmbedder())
    monkeypatch.setattr(frontend_api,'workspace',lambda:w)
    try:
        d=w.add_pdf('Example.pdf',path.read_bytes());w.process(d['id'])
        query='How much net income fiscal 2025 in EUR?'
        search=frontend_api.unified_search(frontend_api.UnifiedSearch(query=query,document_ids=[d['id']],source='USER_UPLOADS',search_profile='auto'))
        answer=frontend_api.analysis(frontend_api.AnalysisRequest(question=query,document_ids=[d['id']],search_profile='auto'))
        assert answer['values']==[] and answer['citations']
        assert answer['reason']=='FX_CONVERSION_NOT_AUTHORIZED'
        assert answer['composer_version']=='VERIFIED_ANSWER_COMPOSER_V2'
        assert {h['citation_id'] for h in answer['citations']} <= {h['citation_id'] for h in search['results']}
        assert search['engine_version']=='FAITH_R_PRODUCT_V1'
    finally:w.close()

def test_sec_unavailable_is_persisted_without_breaking_pdf(tmp_path,monkeypatch):
    w=PdfWorkspace(tmp_path/'w',embedder=SyntheticEmbedder())
    monkeypatch.setattr(frontend_api,'workspace',lambda:w)
    def unavailable():raise ValueError('SEC_SHARED_SOURCE_ROOTS_NOT_CONFIGURED')
    monkeypatch.setattr(frontend_api,'sec_index',unavailable)
    try:
        r=frontend_api.financial_chat(frontend_api.ChatRequest(question='Explain Apple revenue FY2025',source='US_SEC',ticker='AAPL'))
        assert r['status']=='SOURCE_UNAVAILABLE' and r['citations']==[]
        assert frontend_api.chat_session(r['session_id'])['document_ids']==['SEC:AAPL']
    finally:w.close()

def test_optional_generator_rejects_changed_numbers(tmp_path,monkeypatch):
    from app.product.grounded_narrative import compose
    monkeypatch.setenv('FIS_NARRATIVE_MODEL','test-only')
    class Response:
        def raise_for_status(self):pass
        def json(self):return {'response':json.dumps({'sections':[{'citation_id':'1','quote':'Revenue is 999999 dollars.'}]})}
    monkeypatch.setattr('app.product.grounded_narrative.requests.post',lambda *a,**k:Response())
    answer={'status':'SOURCE_EXCERPTS','answer':'Original extractive answer','citations':[{'text':'Revenue is 125 dollars.'}]}
    assert compose('Summarize revenue',answer)['answer']=='Original extractive answer'
    assert answer['generation_trace']['model_status']=='FAILED_OR_UNGROUNDED_EXTRACTIVE_FALLBACK'

def test_workspace_owner_blocks_read_overwrite_delete(tmp_path,monkeypatch):
    from app.product.chat_store import save,connect
    w=PdfWorkspace(tmp_path/'w',embedder=SyntheticEmbedder());monkeypatch.setattr(frontend_api,'workspace',lambda:w)
    sid='b'*32;save(w,sid,'scope',[],[])
    try:
        with connect(w) as db:db.execute('UPDATE financial_chat_sessions SET owner=? WHERE id=?',('another-workspace',sid))
        with pytest.raises(Exception):frontend_api.chat_session(sid)
        frontend_api.reset_financial_chat(sid)
        with connect(w) as db:assert db.execute('SELECT id FROM financial_chat_sessions WHERE id=?',(sid,)).fetchone()
    finally:w.close()

def test_known_alias_cannot_override_source_verified_unmapped_issuer(tmp_path):
    w,_,_=setup_source(tmp_path)
    assert source_company_conflict(w,['d'],'What was Apple net income in fiscal 2025?')['status']=='QUERY_CONTEXT_CONFLICT'

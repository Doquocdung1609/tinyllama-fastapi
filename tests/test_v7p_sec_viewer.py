"""Small synthetic registered-source tests; not claimed as real SEC evidence."""
from contextlib import closing
from hashlib import sha256
import json,sqlite3
from types import SimpleNamespace
from threading import RLock
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.product import frontend_api
from app.product.sec_viewer import reference,resolve,SourceViewError,server_key
from app.financial_index.corpus import ProvenanceCache
from app.financial_ingestion.html_parser import parse_sec_html,normalized_filing_text
from app.financial_ingestion.chunker import chunk_filing
from app.table_evidence.real_source import derive_cell,parse_resources
from app.table_evidence.identity import digest
from test_real_sec_recovery import synthetic

SECRET='synthetic-server-only-signing-key'


def source_fixture(tmp_path,hostile=False):
    raw,filing,_,_,_=synthetic()
    if hostile:
        raw=raw.replace(b'<body>',b'<body><script>window.SEC_PWNED=1</script><img src="https://example.invalid/track" onerror="window.SEC_PWNED=2"><a href="javascript:alert(1)">unsafe link</a><p>&lt;script&gt;encoded&lt;/script&gt;</p>')
        raw=raw.replace(b'</table>',b'<tr><td onclick="window.SEC_PWNED=3">Encoded &lt;script&gt;window.SEC_PWNED=4&lt;/script&gt;</td><td><a href="javascript:alert(1)">unsafe link</a><img src="https://example.invalid/track2" onerror="window.SEC_PWNED=5"></td></tr></table><table><tr><td>Malformed adjacent table',1)
    m=filing.metadata.model_copy(update={'source_url':'https://www.sec.gov/Archives/edgar/data/202/000000020226000001/synthetic.htm','raw_content_hash':sha256(raw).hexdigest()})
    parsed=parse_sec_html(raw,m);m.normalized_content_hash=sha256(normalized_filing_text(parsed).encode()).hexdigest()
    parsed=parse_sec_html(raw,m);parents=chunk_filing(parsed)
    parent=next(p for p in parents if p.kind=='table' and p.metadata.get('row_label')=='NET SALES')
    table=next(t for t in parsed.tables if t.table_id==parent.source_location.table_id)
    cell=next(c for c in table.cells if c.row==parent.source_location.row_index and c.numeric_facts)
    raw_path=tmp_path/'raw.htm';raw_path.write_bytes(raw)
    structured=tmp_path/'structured.json';structured.write_text(parsed.model_dump_json(),encoding='utf-8')
    chunks=tmp_path/'chunks.jsonl';chunks.write_text('\n'.join(p.model_dump_json() for p in parents),encoding='utf-8')
    frozen={'filing_id':parent.filing_id,'raw_path':str(raw_path),'raw_hash':sha256(raw).hexdigest(),'structured_path':str(structured),'structured_hash':sha256(structured.read_bytes()).hexdigest(),'chunks_path':str(chunks),'chunks_hash':sha256(chunks.read_bytes()).hexdigest(),'normalized_hash':m.normalized_content_hash,'manifest_hash':'b'*64}
    identity={'dataset_id':'synthetic-viewer','generation':'a'*64,'manifest_hash':'b'*64,'state':'READY'}
    (tmp_path/'frozen_v1').mkdir();(tmp_path/'frozen_v1/freeze.json').write_text(json.dumps(identity))
    vectors=tmp_path/'vectors';vectors.mkdir();(vectors/'generation_manifest.json').write_text(json.dumps(identity))
    dbpath=tmp_path/'lexical.sqlite3'
    def connect():
        c=sqlite3.connect(dbpath);c.row_factory=sqlite3.Row;return c
    with closing(connect()) as c,c:
        c.execute('CREATE TABLE documents(cid TEXT,payload TEXT,payload_hash TEXT)');c.execute('CREATE TABLE members(cid TEXT,generation TEXT,source TEXT)')
        payload=parent.model_dump(mode='json');c.execute('INSERT INTO documents VALUES(?,?,?)',(parent.chunk_id,json.dumps(payload),digest(payload)))
        c.execute('INSERT INTO members VALUES(?,?,?)',(parent.chunk_id,'a'*64,json.dumps(frozen)))
    index=SimpleNamespace(root=tmp_path,vector_root=vectors,identity=identity,_cache=ProvenanceCache(),_lock=RLock(),lexical=SimpleNamespace(connect=connect,generation=lambda *_:{'state':'READY','n':1}),by_id={parent.chunk_id:{'chunk':parent,'frozen':frozen}})
    observed=derive_cell(parent,table,cell,parse_resources(raw),raw_hash=frozen['raw_hash'],generation='a'*64,manifest_hash='b'*64,dataset_id='synthetic-viewer').model_dump(mode='json')
    return index,observed,raw_path


def test_verified_source_context_is_from_original_bytes(tmp_path):
    i,c,_=source_fixture(tmp_path);r=reference(i,c['parent_id'],SECRET,c);d=resolve(i,r,SECRET)
    assert d['status']=='VERIFIED_LOCAL_SEC_SNAPSHOT' and d['selected_cell']['raw_value']=='23,276'
    assert d['selected_cell']['period_end']=='2026-09-30' and d['selected_cell']['multiplier']=='1000000'
    assert d['report_period']=='2026-09-30' and d['filing_date']=='2026-11-01'
    assert d['fiscal_year'] is None  # Never derive FY from a calendar/filing year.
    assert any('Three Months' in cell['text'] for row in d['table']['rows'] for cell in row['cells'])
    assert not any(key.endswith('_path') for key in d)


@pytest.mark.parametrize('mutation',['byte','missing','locator','period','value','identity','generation','token','self_hash'])
def test_source_or_navigation_tampering_fails_closed(tmp_path,mutation):
    i,c,path=source_fixture(tmp_path);r=reference(i,c['parent_id'],SECRET,c)
    if mutation=='byte':path.write_bytes(path.read_bytes()+b'changed')
    elif mutation=='missing':path.unlink()
    elif mutation in {'locator','period','value'}:
        c.update({'column':999} if mutation=='locator' else {'period_end':'2025-09-30'} if mutation=='period' else {'raw_value':'99,999'})
        r=reference(i,c['parent_id'],SECRET,c)
    elif mutation=='identity':
        with closing(i.lexical.connect()) as db,db:db.execute('UPDATE documents SET payload=?',(json.dumps({'filing_id':'wrong'}),))
    elif mutation=='generation':(i.vector_root/'generation_manifest.json').write_text('{}')
    elif mutation=='token':r=reference(i,c['parent_id'],'client-bearer-token-is-not-signing-secret',c)
    elif mutation=='self_hash':
        path.write_bytes(path.read_bytes()+b'changed');r=reference(i,c['parent_id'],SECRET,c)
        i.by_id[c['parent_id']]['frozen']['raw_hash']=sha256(path.read_bytes()).hexdigest()
    with pytest.raises((SourceViewError,ValueError)):resolve(i,r,SECRET)


def test_search_parent_navigation_and_hostile_source_text_only(tmp_path,monkeypatch):
    import requests
    monkeypatch.setattr(requests.sessions.Session,'request',lambda *a,**k:(_ for _ in ()).throw(AssertionError('No network allowed')))
    i,c,_=source_fixture(tmp_path,hostile=True)
    d=resolve(i,reference(i,c['parent_id'],SECRET),SECRET)
    assert d['selected_cell'] is None and d['table']['selected_row']==c['row']
    serialized=json.dumps(d['table'])
    assert 'window.SEC_PWNED=1' not in serialized and 'window.SEC_PWNED=2' not in serialized
    assert 'https://example.invalid/track' not in serialized and 'javascript:' not in serialized
    assert all(set(c)=={'column','text','colspan','rowspan'} for r in d['table']['rows'] for c in r['cells'])
    assert any('Encoded <script>window.SEC_PWNED=4</script>'==c['text'] for r in d['table']['rows'] for c in r['cells'])


def test_signing_key_is_separate_persistent_and_not_client_bearer(tmp_path):
    a=server_key(tmp_path);assert len(a)==64 and a==server_key(tmp_path)


def test_cross_workspace_reference_cannot_be_reused(tmp_path):
    a=tmp_path/'a';a.mkdir();b=tmp_path/'b';b.mkdir()
    index,cell,_=source_fixture(a)
    ref=reference(index,cell['parent_id'],server_key(a),cell)
    with pytest.raises(SourceViewError,match='UNREGISTERED_SOURCE_REFERENCE'):
        resolve(index,ref,server_key(b))


@pytest.mark.parametrize('body',[{'reference':'../../secret'},{'reference':'https://example.invalid'},{'reference':'x'*5000},{'reference':'a.'+'0'*64,'path':'C:/secret'}])
def test_api_rejects_arbitrary_paths_urls_and_oversize(tmp_path,monkeypatch,body):
    app=FastAPI();app.include_router(frontend_api.router);monkeypatch.setenv('STUDIO_API_TOKEN','synthetic-local-test-token')
    with TestClient(app) as client:
        assert client.post('/studio/sec/evidence',json=body).status_code==401
        assert client.post('/studio/sec/evidence',json=body,headers={'Authorization':'Bearer synthetic-local-test-token'}).status_code==422


def test_http_tamper_refuses_with_no_stale_evidence(tmp_path,monkeypatch):
    i,c,path=source_fixture(tmp_path);key=server_key(tmp_path)
    monkeypatch.setattr(frontend_api,'sec_index',lambda:i);monkeypatch.setattr(frontend_api,'workspace',lambda:SimpleNamespace(root=tmp_path))
    monkeypatch.setenv('STUDIO_API_TOKEN','synthetic-local-test-token');app=FastAPI();app.include_router(frontend_api.router)
    with TestClient(app) as client:
        headers={'Authorization':'Bearer synthetic-local-test-token'};body={'reference':reference(i,c['parent_id'],key,c)}
        good=client.post('/studio/sec/evidence',json=body,headers=headers);assert good.status_code==200
        assert good.headers['cache-control']=='no-store' and 'none' in good.headers['content-security-policy']
        path.write_bytes(path.read_bytes()+b'tampered')
        bad=client.post('/studio/sec/evidence',json=body,headers=headers)
        assert bad.status_code==409 and bad.json()=={'detail':{'code':'SOURCE_HASH_MISMATCH'}}


def test_supported_automatic_answer_has_no_stale_numeric_warning(tmp_path,monkeypatch):
    from test_v7p_verified_operands import setup_source
    from test_v7p_metadata_chat import SyntheticEmbedder
    from app.product.workspace import PdfWorkspace
    from app.product.analysis import AnalysisRequest
    _,_,path=setup_source(tmp_path);w=PdfWorkspace(tmp_path/'pdf',embedder=SyntheticEmbedder())
    monkeypatch.setattr(frontend_api,'workspace',lambda:w);monkeypatch.setenv('STUDIO_SEARCH_V2_ROOT',str(tmp_path/'search'))
    try:
        d=w.add_pdf('synthetic.pdf',path.read_bytes());w.process(d['id'])
        answer=frontend_api.analysis(AnalysisRequest(question='Net income fiscal 2025?',document_ids=[d['id']],search_profile='auto'))
        assert answer['status']=='SUPPORTED' and answer['warnings']==[]
        assert answer['retrieved_excerpt_verification']=='SOURCE_TEXT_UNREVIEWED'
        prior=frontend_api.analysis(AnalysisRequest(question='Net income fiscal 2024?',document_ids=[d['id']],search_profile='auto'))
        assert prior['status']=='SUPPORTED' and prior['period']=='2024-09-28'
        assert prior['source_periods']==['2024-09-28'] and prior['answer_source_chunk_id'] is None
        assert prior['answer_evidence_ids']==[c['evidence_id'] for c in prior['citations']]
    finally:w.close()


def test_sec_citation_keeps_html_locator_without_exposing_filesystem(tmp_path,monkeypatch):
    i,c,_=source_fixture(tmp_path);m=i.by_id[c['parent_id']]['chunk'].metadata
    i.catalog=lambda:{'filings':[{'filing_id':c['filing_id'],'cik':c['cik'],'issuer':'Synthetic','form':'10-Q','ticker':'FX'}]}
    backend=SimpleNamespace(query=lambda *a:{'generation':'a'*64,'answer':{'status':'SUPPORTED','source_cells':[{**c,'raw_path':'C:/private/source.htm'}],'result_values':['23276000000'],'result_unit':'USD'}})
    monkeypatch.setattr(frontend_api,'sec_index',lambda:i);monkeypatch.setattr(frontend_api,'sec_backend',lambda:backend)
    monkeypatch.setattr(frontend_api,'workspace',lambda:SimpleNamespace(root=tmp_path))
    result=frontend_api.sec_analysis(frontend_api.SecQA(question='fixture query'))
    assert result['citations'][0]['source_location']['structural_path']==c['structural_path']
    assert result['source_cells'][0]['structural_path']==c['structural_path']
    assert 'raw_path' not in result['source_cells'][0] and 'C:/private' not in json.dumps(result)


def test_duplicate_retrieval_links_do_not_inflate_cell_evidence(tmp_path):
    from test_v7p_verified_operands import setup_source
    from app.product.verified_financial import automatic_answer
    from app.product.analysis import AnalysisRequest
    w,result,_=setup_source(tmp_path);result['results']*=3
    answer=automatic_answer(w,AnalysisRequest(question='Total net sales growth fiscal 2024 to 2025?',document_ids=['d']),result)
    assert answer['status']=='SUPPORTED'
    assert len(answer['retrieval_trace']['original_hit_ids'])==1
    assert len({c['evidence_id'] for c in answer['citations']})==2
    assert all(len(c['retrieved_chunk_ids'])==1 for c in answer['citations'])


def test_final_sec_search_profile_retains_source_resolver_reference(tmp_path,monkeypatch):
    from app.product.sec_viewer import decode_reference
    i,c,_=source_fixture(tmp_path)
    monkeypatch.setattr(frontend_api,'workspace',lambda:SimpleNamespace(root=tmp_path))
    monkeypatch.setattr(frontend_api,'sec_index',lambda:i)
    monkeypatch.setattr('app.product.search_v3.search_sec_v3',lambda *a:{'intent':{},'evidence_status':'RELATED_UNVERIFIED_EVIDENCE','results':[{'rank':1,'chunk_id':c['parent_id'],'text':'synthetic source'}],'generation':'a'*64,'latency_ms':0})
    r=frontend_api.unified_search(frontend_api.UnifiedSearch(query='net sales',source='US_SEC',mode='bm25',search_profile='production_v3'))
    ref=r['results'][0]['source_reference']
    assert decode_reference(ref,server_key(tmp_path))['parent_id']==c['parent_id']
    assert resolve(i,ref,server_key(tmp_path))['table']['selected_row']==c['row']

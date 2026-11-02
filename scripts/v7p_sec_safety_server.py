"""Ephemeral synthetic security harness only; NEVER imported by main/app routes."""
import os,sys
from pathlib import Path
from fastapi import FastAPI,Depends
from fastapi.staticfiles import StaticFiles
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tests'))
from test_v7p_sec_viewer import source_fixture
from test_v7p_metadata_chat import SyntheticEmbedder
from app.product import api,frontend_api
from app.product.workspace import PdfWorkspace
from app.product.sec_viewer import reference,server_key

root=Path(os.environ['V7P_SYNTHETIC_SAFETY_ROOT']).resolve()
assert root.is_relative_to(Path.cwd().resolve()/'tmp/topic3')
root.mkdir(parents=True)
index,cell,raw_path=source_fixture(root,hostile=True)
w=PdfWorkspace(root/'workspace',embedder=SyntheticEmbedder())
index.catalog=lambda:{'status':'READY','filings':[],'generation':index.identity['generation']}
api.workspace=frontend_api.workspace=lambda:w
api.sec_index=frontend_api.sec_index=lambda:index
app=FastAPI();app.include_router(api.router);app.include_router(frontend_api.router)
app.mount('/app',StaticFiles(directory='frontend/dist',html=True))

@app.get('/studio/security-fixture',dependencies=[Depends(api.require_studio_token)])
def fixture():
    return {'label':'SYNTHETIC_HTML_SECURITY_FIXTURE_NOT_REAL_SEC_EVIDENCE','reference':reference(index,cell['parent_id'],server_key(w.root),cell)}

@app.post('/studio/security-fixture/tamper',dependencies=[Depends(api.require_studio_token)])
def tamper():
    raw_path.write_bytes(raw_path.read_bytes()+b'controlled fixture tamper');return {'synthetic_fixture_tampered':True}

"""Separate opt-in research ASGI app. Accepted app.main/routes remain unchanged."""
import hmac
import os
from threading import BoundedSemaphore
from typing import Literal
from fastapi import FastAPI,HTTPException,Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel,ConfigDict,Field
from app.financial_query.contracts import ExplicitFiltersV1
from app.research_retrieval.contracts import Arm
from app.research_qa.contracts import Operation


class ResearchRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    question:str=Field(min_length=2,max_length=2000)
    filters:ExplicitFiltersV1=Field(default_factory=ExplicitFiltersV1)
    arm:Arm='B'
    operation:Operation='EXTRACT'
    top_k:Literal[5,10]=5
    use_llm:bool=False
    workflow:Literal['research','automatic_real']='research'


def create_research_app(backend=None,token=''):
    app=FastAPI(title='Financial Intelligence Research v1',version='1');slots=BoundedSemaphore(1)

    @app.middleware('http')
    async def bounded_body(request,call_next):
        chunks=[];size=0
        async for chunk in request.stream():
            size+=len(chunk)
            if size>16384:return JSONResponse({'detail':'RESEARCH_REQUEST_TOO_LARGE'},status_code=413)
            chunks.append(chunk)
        request._body=b''.join(chunks)
        return await call_next(request)

    @app.get('/research/v1/health')
    def health():return {'status':'ready' if backend is not None and token else 'not_configured','interface_version':'financial-research-api/v1','source_type':getattr(backend,'source_type','NONE')}

    @app.post('/research/v1/query')
    def query(payload:ResearchRequest,request:Request):
        if not token or backend is None:raise HTTPException(503,'RESEARCH_NOT_CONFIGURED')
        supplied=request.headers.get('authorization','')
        if not hmac.compare_digest(supplied.encode('utf-8'),'Bearer '.encode()+token.encode('utf-8')):raise HTTPException(401,'RESEARCH_AUTHORIZATION_REQUIRED')
        if not slots.acquire(blocking=False):raise HTTPException(429,'RESEARCH_RESOURCE_BUSY')
        try:return backend.query(payload.question,payload.filters.model_dump(mode='json'),payload.arm,payload.operation,payload.top_k,payload.use_llm,payload.workflow)
        except (ValueError,RuntimeError):raise HTTPException(409,'RESEARCH_SOURCE_OR_SCOPE_VALIDATION_FAILED') from None
        finally:slots.release()
    return app


def from_environment():
    token=os.getenv('TOPIC3_RESEARCH_API_TOKEN','');root=os.getenv('TOPIC3_RESEARCH_ROOT','')
    if not token or not root:return create_research_app()
    if len(token)<16:raise ValueError('RESEARCH_TOKEN_TOO_SHORT')
    from app.research_qa.backend import ResearchBackend,DemoResearchBackend
    mode=os.getenv('TOPIC3_RESEARCH_MODE','real_frozen')
    if mode not in {'real_frozen','synthetic_demo'}:raise ValueError('UNKNOWN_RESEARCH_MODE')
    return create_research_app(DemoResearchBackend(root) if mode=='synthetic_demo' else ResearchBackend(root),token)


app=from_environment()

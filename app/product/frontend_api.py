"""Typed product orchestration; algorithms remain in the existing Python engine."""
from contextlib import closing
from functools import lru_cache
from hashlib import sha256
import json
import os
from threading import BoundedSemaphore, Thread
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field
import psutil
import requests

from app.product.api import workspace,sec_index,require_studio_token,_error,_factory_lock
from app.product.analysis import AnalysisRequest,FactReview,review_fact,eligible_facts,numeric_answer,research_steps
from app.product.pdf_extract import ocr_capability,folded

router=APIRouter(prefix='/studio',tags=['react-product'],dependencies=[Depends(require_studio_token)])
slots=BoundedSemaphore(1)


class UnifiedSearch(BaseModel):
    model_config=ConfigDict(extra='forbid')
    query:str=Field(min_length=2,max_length=2000)
    mode:Literal['bm25','dense','hybrid']='hybrid'
    top_k:int=Field(default=5,ge=1,le=20)
    source:Literal['VIETNAM','US_SEC','ALL','USER_UPLOADS']='VIETNAM'
    document_ids:list[str]=Field(default_factory=list,max_length=100)
    issuer:str=Field(default='',max_length=160)
    period:str=Field(default='',max_length=80)
    search_profile:Literal['baseline','production_v2']='baseline'


class EvidenceResponse(BaseModel):
    model_config=ConfigDict(extra='allow')
    text:str
    rank:int=Field(ge=1)
    source_kind:Literal['PDF','SEC']
    source_sha256:str
    page:int|None=Field(default=None,ge=1)


class SearchResponse(BaseModel):
    status:Literal['READY','PARTIAL']
    generation:str
    source_generations:list[tuple[str,str|None]]
    results:list[EvidenceResponse]
    mode:Literal['bm25','dense','hybrid']
    source_errors:list[dict[str,str]]
    latency_ms:float=Field(ge=0)
    timings_ms:dict[str,float]
    cross_source_order:str|None
    intent:dict|None=None
    evidence_status:str|None=None
    evidence_reason:str|None=None
    search_profile:str='baseline'


class ComparisonResponse(BaseModel):
    arms:dict[str,SearchResponse]
    generation:str
    overlap:dict[str,int]
    quality_metrics:None=None
    quality_reason:str


def unified_search(payload:UnifiedSearch):
    results=[];scopes=[];errors=[];timings={};intent=None;evidence_status=None;evidence_reason=None
    if payload.source!='US_SEC':
        docs=workspace()._eligible(payload.document_ids)
        if payload.issuer:docs=[d for d in docs if folded(payload.issuer) in folded(d['issuer'])]
        if payload.period:docs=[d for d in docs if payload.period in d['report_period']]
        if payload.source=='VIETNAM':
            def vietnamese(doc):
                try:text=workspace().page_evidence(doc['id'],min(3,doc['pages']))['text']
                except ValueError:text=doc['issuer']
                return any(word in folded(text) for word in ('tai san','bao cao','ngan hang','hoa phat'))
            docs=[d for d in docs if vietnamese(d)]
        if docs:
            if payload.search_profile=='production_v2':
                from app.product.search_v2 import FinancialSearchV2
                from pathlib import Path
                w=workspace();root=Path(os.getenv('STUDIO_SEARCH_V2_ROOT','tmp/studio-runtime/search-v2'))
                with _factory_lock:
                    if not hasattr(w,'_search_v2') or w._search_v2.root!=root:w._search_v2=FinancialSearchV2(w,root)
                    engine=w._search_v2
                found=engine.search(payload.query,payload.mode,payload.top_k,[d['id'] for d in docs])
                intent=found['intent'];evidence_status=found['evidence_status'];evidence_reason=found.get('reason')
            else:found=workspace().search(payload.query,payload.mode,payload.top_k,[d['id'] for d in docs])
            results.extend({**r,'source_kind':'PDF'} for r in found['results'])
            scopes.append(('PDF',found.get('generation')));timings['PDF']=found['latency_ms']
    if payload.source in {'US_SEC','ALL'}:
        try:
            found=sec_index().search(payload.query,payload.mode,payload.top_k,payload.issuer,payload.period)
            results.extend({**r,'source_kind':'SEC'} for r in found['results'])
            scopes.append(('SEC',found.get('generation')));timings['SEC']=found.get('latency_ms',0)
        except Exception as exc:
            if payload.source=='US_SEC':raise ValueError(_error(exc)) from None
            errors.append({'source':'US_SEC','reason':_error(exc)})
    # Across stores use ranks, never raw BM25/cosine magnitudes. Per-store retrieval stays unchanged.
    if len(scopes)>1:results.sort(key=lambda r:(r['rank'],r.get('chunk_id',r.get('parent_id',''))))
    generation=sha256(json.dumps(scopes,sort_keys=True).encode()).hexdigest()
    for rank,result in enumerate(results[:payload.top_k],1):result['rank']=rank
    return {'status':'PARTIAL' if errors else 'READY','generation':generation,'source_generations':scopes,
            'results':results[:payload.top_k],'mode':payload.mode,'source_errors':errors,
            'latency_ms':sum(timings.values()),'timings_ms':timings,
            'intent':intent,'evidence_status':evidence_status,'evidence_reason':evidence_reason,'search_profile':payload.search_profile,
            'cross_source_order':'PER_STORE_RANK_THEN_SOURCE_ID' if len(scopes)>1 else None}


@router.post('/query',response_model=SearchResponse)
def query(payload:UnifiedSearch):
    try:return unified_search(payload)
    except Exception as exc:raise HTTPException(409,detail={'code':_error(exc)}) from None


@router.post('/compare',response_model=ComparisonResponse)
def compare(payload:UnifiedSearch):
    try:
        # Scientific comparison remains B0/B1/B2 independently of the product profile.
        arms={mode:unified_search(payload.model_copy(update={'mode':mode,'search_profile':'baseline'})) for mode in ('bm25','dense','hybrid')}
        if len({r['generation'] for r in arms.values()})!=1:
            raise ValueError('COMPARISON_SNAPSHOT_CHANGED')
        ids={mode:{r.get('chunk_id',r.get('parent_id')) for r in result['results']} for mode,result in arms.items()}
        return {'arms':arms,'generation':arms['bm25']['generation'],
                'overlap':{'bm25_dense':len(ids['bm25']&ids['dense']),'all_three':len(set.intersection(*ids.values()))},
                'quality_metrics':None,'quality_reason':'NO_QRELS_FOR_THIS_QUERY'}
    except Exception as exc:raise HTTPException(409,detail={'code':_error(exc)}) from None


@router.get('/evaluation')
def recorded_evaluation():
    from pathlib import Path
    path=Path(__file__).resolve().parents[2]/'docs/topic3/MILESTONE_C_MEASUREMENTS.json'
    if not path.is_file():return {'status':'NOT_AVAILABLE'}
    saved=json.loads(path.read_text(encoding='utf-8'))
    return {'status':'RECORDED_DEVELOPMENT_ONLY','dataset':saved['dataset'],'generation':saved['generation'],
            'chunks':saved['chunks'],'queries':saved['queries'],'quality_at_5':saved['quality_at_5'],
            'scope_note':'Bộ câu hỏi development đã ghi nhận trước đây, không phải holdout độc lập và không áp dụng cho các PDF/câu hỏi mới.'}


@router.get('/evaluation/search-v2')
def search_v2_evaluation():
    from pathlib import Path
    root=Path(__file__).resolve().parents[2]/'docs/search_v2'
    path=root/'BENCHMARK_SUMMARY.json'
    if not path.is_file():return {'status':'NOT_RUN'}
    saved=json.loads(path.read_text(encoding='utf-8'))
    if sha256((root/'SEARCH_BENCHMARK_QRELS.jsonl').read_bytes()).hexdigest()!=saved['qrels_sha256']:
        return {'status':'STALE_LABELS'}
    from scripts.benchmark_search_v2 import policy_hash
    if policy_hash()!=saved['policy_sha256']:return {'status':'STALE_POLICY'}
    return saved


@router.get('/readiness')
def readiness():
    try:
        models=requests.get(os.getenv('OLLAMA_BASE_URL','http://127.0.0.1:11434')+'/api/tags',timeout=4)
        models.raise_for_status();ollama={'status':'ONLINE','models':[m['name'] for m in models.json().get('models',[])]}
    except Exception:ollama={'status':'UNAVAILABLE','models':[]}
    try:sec=sec_index().catalog()
    except Exception as exc:sec={'status':'UNAVAILABLE','reason':_error(exc),'filings':[]}
    return {'api':'ONLINE','workspace':workspace().health(),'ocr':ocr_capability(),'ollama':ollama,'sec':sec,
            'resources':{'available_ram_bytes':psutil.virtual_memory().available},
            'limits':{'pdf_mb':20,'ocr_concurrency':1,'embedding_dimension':768}}


@router.get('/documents/{document_id}/file')
def pdf_file(document_id:str):
    try:
        path=workspace().source_file(document_id)
        return FileResponse(path,media_type='application/pdf',headers={'Cache-Control':'no-store','Content-Disposition':'inline'})
    except ValueError as exc:raise HTTPException(404,detail={'code':_error(exc)}) from None


@router.get('/documents/{document_id}/extraction')
def extraction(document_id:str):
    try:return workspace().extraction_status(document_id)
    except ValueError as exc:raise HTTPException(404,detail={'code':_error(exc)}) from None


@router.get('/documents/{document_id}/pages/{page}/evidence')
def page_evidence(document_id:str,page:int):
    try:return workspace().page_evidence(document_id,page)
    except ValueError as exc:raise HTTPException(409,detail={'code':_error(exc)}) from None


@router.get('/documents/{document_id}/chunks')
def document_chunks(document_id:str,page:int=1):
    if not 1<=page<=250:raise HTTPException(422,detail='INVALID_PAGE')
    workspace().source_file(document_id)
    with closing(workspace()._connect()) as db:
        return {'chunks':[dict(r) for r in db.execute('SELECT id AS chunk_id,document_id,page,text FROM chunks WHERE document_id=? AND page=? LIMIT 30',(document_id,page))]}


@router.get('/documents/{document_id}/facts')
def facts(document_id:str):
    try:return {'facts':eligible_facts(workspace(),[document_id])}
    except ValueError as exc:raise HTTPException(409,detail={'code':_error(exc)}) from None


@router.post('/documents/{document_id}/facts/review')
def review(document_id:str,payload:FactReview):
    try:return review_fact(workspace(),document_id,payload)
    except ValueError as exc:raise HTTPException(409,detail={'code':_error(exc)}) from None


@router.post('/analysis')
def analysis(payload:AnalysisRequest):
    try:
        if payload.mode=='numeric':return numeric_answer(workspace(),payload)
        if payload.mode=='document_qa':
            result=workspace().search(payload.question,'hybrid',5,payload.document_ids)
            # Ordinary RAG explanations never certify unchecked numbers.
            return {'status':'SOURCE_EXCERPTS' if result['results'] else 'INSUFFICIENT_EVIDENCE',
                    'answer':'Các đoạn nguồn liên quan; số liệu trong trích đoạn chưa được xác minh ô nguồn.',
                    'citations':result['results'],'values':[]}
        raise ValueError('USE_RESEARCH_JOB_ENDPOINT')
    except Exception as exc:raise HTTPException(409,detail={'code':_error(exc)}) from None


def job_store(job_id,payload):
    with closing(workspace()._connect()) as db,db:
        db.execute('CREATE TABLE IF NOT EXISTS analysis_jobs(id TEXT PRIMARY KEY,payload TEXT NOT NULL)')
        db.execute('INSERT OR REPLACE INTO analysis_jobs VALUES(?,?)',(job_id,json.dumps(payload,ensure_ascii=False)))


def execute_research(job_id,payload):
    record={'id':job_id,'status':'RUNNING','events':[]}
    try:
        for event in research_steps(workspace(),payload):
            record['events'].append(event);job_store(job_id,record)
        record['status']='COMPLETED'
    except Exception as exc:record.update(status='FAILED',error=_error(exc))
    finally:job_store(job_id,record);slots.release()


@router.post('/research',status_code=202)
def research(payload:AnalysisRequest):
    if not slots.acquire(blocking=False):raise HTTPException(429,detail={'code':'RESEARCH_RESOURCE_BUSY'})
    job_id=uuid4().hex
    try:
        job_store(job_id,{'id':job_id,'status':'QUEUED','events':[]})
        Thread(target=execute_research,args=(job_id,payload),daemon=True).start()
    except Exception:
        slots.release();raise
    return {'id':job_id,'status':'QUEUED'}


@router.get('/research/{job_id}')
def research_status(job_id:str):
    with closing(workspace()._connect()) as db:
        db.execute('CREATE TABLE IF NOT EXISTS analysis_jobs(id TEXT PRIMARY KEY,payload TEXT NOT NULL)')
        row=db.execute('SELECT payload FROM analysis_jobs WHERE id=?',(job_id,)).fetchone()
    if row is None:raise HTTPException(404,detail={'code':'RESEARCH_JOB_NOT_FOUND'})
    return json.loads(row['payload'])


@lru_cache(maxsize=1)
def sec_backend():
    from app.research_qa.backend import ResearchBackend
    root=os.getenv('TOPIC3_RESEARCH_ROOT','')
    if not root:raise ValueError('SEC_QA_NOT_CONFIGURED')
    return ResearchBackend(root)


class SecQA(BaseModel):
    model_config=ConfigDict(extra='forbid')
    question:str=Field(min_length=2,max_length=2000)
    operation:Literal['EXTRACT','ABS_CHANGE','PERCENT_CHANGE']='EXTRACT'
    ticker:str=Field(default='',max_length=20)


@router.post('/sec/analysis')
def sec_analysis(payload:SecQA):
    def public(value):
        if isinstance(value,dict):return {key:public(item) for key,item in value.items() if not key.endswith('_path') and key not in {'root','token'}}
        if isinstance(value,list):return [public(item) for item in value]
        if isinstance(value,str) and (len(value)>2 and value[1:3] in {':\\',':/'}):return '[local path omitted]'
        return value
    try:
        filings=sec_index().catalog()['filings']
        filters={}
        if payload.ticker:
            selected=[f for f in filings if f['ticker']==payload.ticker.upper()]
            if len(selected)!=1:raise ValueError('SEC_COMPANY_SCOPE_AMBIGUOUS')
            filters={'cik':selected[0]['cik'],'filing_ids':[selected[0]['filing_id']]}
        raw=sec_backend().query(payload.question,filters,'B',payload.operation,5,False,'automatic_real')
        answer=raw.get('answer',{});citations=[]
        for cell in answer.get('source_cells',[]):
            source=next((f for f in filings if f['cik']==cell['cik']),{})
            citations.append({'source_kind':'SEC','chunk_id':cell['parent_id'],'issuer':source.get('issuer',cell['cik']),
                'report_period':cell['period_end'],'source_url':cell['source_url'],'source_sha256':cell['raw_sha256'],
                'text':f"{cell['row_label']}: {cell['raw_value']} ({cell['display_unit_header']}) · {cell['period_end']}",
                'row_label':cell['row_label'],'column_label':' / '.join(cell['header_path']),
                'verification':'VERIFIED_SOURCE_CELL','unit':cell['unit'],
                'source_location':{'structural_path':cell['structural_path'],'table_id':cell['table_id'],'row_index':cell['row'],'column_index':cell['column']}})
        return public({'status':answer.get('status','INSUFFICIENT_EVIDENCE'),
            'answer':'Kết quả từ ô nguồn SEC được xác thực.' if answer.get('status')=='SUPPORTED' else 'KHÔNG ĐỦ BẰNG CHỨNG',
            'values':[str(v) for v in answer.get('result_values',[])],'unit':answer.get('result_unit'),
            'formula':answer.get('formula'),'reason':', '.join(answer.get('reasons',[])),
            'citations':citations,'source_cells':answer.get('source_cells',[]),'generation':raw.get('generation')})
    except Exception as exc:raise HTTPException(409,detail={'code':_error(exc)}) from None

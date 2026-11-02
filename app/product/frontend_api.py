"""Typed product orchestration; algorithms remain in the existing Python engine."""
from contextlib import closing
from functools import lru_cache
from hashlib import sha256
import json
import os
import subprocess
from pathlib import Path
from threading import BoundedSemaphore, Thread
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field
import psutil
import requests

from app.product.api import workspace,sec_index,require_studio_token,_error,_factory_lock
from app.product.analysis import AnalysisRequest,FactReview,review_fact,eligible_facts,numeric_answer,research_steps,METRICS
from app.product.pdf_extract import ocr_capability,folded

router=APIRouter(prefix='/studio',tags=['react-product'],dependencies=[Depends(require_studio_token)])
slots=BoundedSemaphore(1)
research_slots=BoundedSemaphore(1)


class UnifiedSearch(BaseModel):
    model_config=ConfigDict(extra='forbid')
    query:str=Field(min_length=2,max_length=2000)
    mode:Literal['bm25','dense','hybrid']='hybrid'
    top_k:int=Field(default=5,ge=1,le=20)
    source:Literal['VIETNAM','US_SEC','ALL','USER_UPLOADS']='VIETNAM'
    document_ids:list[str]=Field(default_factory=list,max_length=100)
    issuer:str=Field(default='',max_length=160)
    period:str=Field(default='',max_length=80)
    search_profile:Literal['baseline','production_v2','production_v3','production_v3r','production_v3r2','production_v3r3']='baseline'


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
    candidate:SearchResponse|None=None


def unified_search(payload:UnifiedSearch):
    w=workspace()
    if hasattr(w,'resources'):
        with w.resources.claim('QUERY_OR_COMPARISON',minimum_mb=256,timeout=10):return _unified_search(payload)
    return _unified_search(payload)


def _unified_search(payload:UnifiedSearch):
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
            if payload.search_profile in {'production_v2','production_v3','production_v3r','production_v3r2','production_v3r3'}:
                from app.product.search_v2 import FinancialSearchV2
                from pathlib import Path
                w=workspace();root=Path(os.getenv('STUDIO_SEARCH_V2_ROOT','tmp/studio-runtime/search-v2'))
                with _factory_lock:
                    if not hasattr(w,'_search_v2') or w._search_v2.root!=root:w._search_v2=FinancialSearchV2(w,root)
                    engine=w._search_v2
                if payload.search_profile=='production_v3':
                    from app.product.search_v3 import FinancialSearchV3
                    engine=FinancialSearchV3(w,root)
                    engine.base=w._search_v2
                if payload.search_profile in {'production_v3r','production_v3r2','production_v3r3'}:
                    if not (w.root/'derived-generation.json').exists():raise ValueError('V3R_DERIVED_WORKSPACE_REQUIRED')
                    from app.product.search_preparation import preparation
                    if payload.search_profile in {'production_v3r2','production_v3r3'}:
                        expected='V3R3' if payload.search_profile=='production_v3r3' else 'V3R2'
                        if getattr(w,'search_candidate_version',None)!=expected:raise ValueError(expected+'_OWNER_WORKSPACE_REQUIRED')
                        engine=preparation(w).ready_engine()
                    elif getattr(w,'search_candidate_version',None) in {'V3R2','V3R3'}:
                        from app.product.search_v3r import FinancialSearchV3R
                        if not hasattr(w,'_legacy_v3r'):w._legacy_v3r=FinancialSearchV3R(w,w.root/'legacy-v3r-index')
                        engine=w._legacy_v3r
                    else:engine=preparation(w).ready_engine()
                found=engine.search(payload.query,payload.mode,payload.top_k,[d['id'] for d in docs])
                intent=found['intent'];evidence_status=found['evidence_status'];evidence_reason=found.get('reason')
            else:found=workspace().search(payload.query,payload.mode,payload.top_k,[d['id'] for d in docs])
            results.extend({**r,'source_kind':'PDF'} for r in found['results'])
            scopes.append(('PDF',found.get('generation')));timings['PDF']=found['latency_ms']
    if payload.source in {'US_SEC','ALL'}:
        try:
            if payload.search_profile in {'production_v3','production_v3r','production_v3r2','production_v3r3'}:
                from app.product.search_v3 import search_sec_v3
                found=search_sec_v3(sec_index(),payload.query,payload.mode,payload.top_k,payload.issuer,payload.period)
                intent=found['intent'];evidence_status=found['evidence_status'];evidence_reason=found.get('reason')
            else:found=sec_index().search(payload.query,payload.mode,payload.top_k,payload.issuer,payload.period)
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
                  'quality_metrics':None,'quality_reason':'NO_QRELS_FOR_THIS_QUERY',
                  'candidate':unified_search(payload) if payload.search_profile in {'production_v3','production_v3r','production_v3r2','production_v3r3'} else None}
    except Exception as exc:raise HTTPException(409,detail={'code':_error(exc)}) from None


@router.get('/search-preparation')
def search_preparation():
    w=workspace()
    if not (w.root/'derived-generation.json').exists():return {'status':'LEGACY_WORKSPACE','profile':'production_v3'}
    from app.product.search_preparation import preparation
    state=preparation(w)
    if state.status()['status']=='NOT_PREPARED':state.schedule()
    if state.status()['status']=='DEFERRED' and hasattr(w,'resources') and w.resources.status()['available_ram_bytes']>=768*1024**2:state.schedule()
    version=getattr(w,'search_candidate_version',None)
    return {**state.status(),'profile':'production_v3r3' if version=='V3R3' else 'production_v3r2' if version=='V3R2' else 'production_v3r'}


@router.get('/resource-status')
def resource_status():
    w=workspace()
    if not hasattr(w,'resources'):return {'profile':'LEGACY','available_ram_bytes':psutil.virtual_memory().available}
    return {**w.resources.status(),'profile':getattr(w,'search_candidate_version','V3R2')}


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


@router.get('/research-lab/topic3')
def topic3_historical_lab():
    from app.product.topic3_lab import historical_experiment
    try:return historical_experiment()
    except (OSError,ValueError,KeyError) as exc:raise HTTPException(409,detail={'code':_error(exc)}) from None


@router.get('/research-lab/faith-r')
def faith_r_historical_lab():
    from app.product.topic3_lab import faith_r_recorded_experiment
    try:return faith_r_recorded_experiment()
    except (OSError,ValueError,KeyError) as exc:raise HTTPException(409,detail={'code':_error(exc)}) from None


class FaithRLiveRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    query:str=Field(min_length=3,max_length=300)
    arm:Literal['A0','A1','A2','A3','A4','A4R','A5']='A4R'


@router.get('/research-lab/faith-r/live/status')
def faith_r_live_status():
    root=Path(__file__).resolve().parents[2]
    ready=(root/'tmp/topic3_v5r/research-venv/Scripts/python.exe').is_file() and all(
        (root/f'tmp/topic3_v5r/restored/{arm}/meta.json').is_file() for arm in ('A','B'))
    return {'status':'AVAILABLE' if os.getenv('FAITH_R_LIVE_ENABLED')=='1' and ready else 'NOT_AVAILABLE',
            'index_a':'P3D_RECOVERED_NOT_EXACT_P3C','index_b':'P7K_FISCAL_CORRECTED',
            'mode':'LIVE_ON_DEMAND' if os.getenv('FAITH_R_LIVE_ENABLED')=='1' and ready else 'DISABLED'}


@router.get('/research-lab/faith-r/live/summary')
def faith_r_live_summary():
    root=Path(__file__).resolve().parents[2]
    path=root/'docs/topic3_v5/recovery_live/ablation_summary.json'
    repair=root/'docs/topic3_v5/recovery_live/posthoc_repair.json'
    if not path.is_file():
        raise HTTPException(404,detail={'code':'LIVE_EXPERIMENT_NOT_RECORDED'})
    measured=json.loads(path.read_text(encoding='utf-8'))
    arms={key:{'known_positive_hit':value['known_positive_hit'],
               'target_filing_hit':value['target_filing_hit'],
               'top1_labels':value['top1_labels'],'p50_ms':value['p50_ms']}
          for key,value in measured['arms'].items()}
    if repair.is_file():
        posthoc=json.loads(repair.read_text(encoding='utf-8'))
        arms['A4R']={'known_positive_hit':{'1':posthoc['a4r_top1_labels'].get('YES',0),
                                          '3':posthoc['a4r_known_positive_h3'],
                                          '10':posthoc['a4r_known_positive_h10']},
                     'target_filing_hit':None,
                     'top1_labels':posthoc['a4r_top1_labels'],
                     'p50_ms':posthoc['a4r_p50_ms']}
    return {'status':'RECORDED_LIVE_RUN_EXPOSED_DEVELOPMENT','case_count':measured['case_count'],
            'arms':arms,'human_gold':False,'numeric_cells_verified':0}


@router.get('/research-lab/faith-r/v6/development')
def faith_r_v6_development():
    root=Path(__file__).resolve().parents[2]
    base=root/'docs/topic3_v5/recovery_live'
    study=json.loads((base/'ablation_summary.json').read_text(encoding='utf-8'))
    repair=json.loads((base/'posthoc_repair.json').read_text(encoding='utf-8'))
    repair_cases={case['case']:case for case in repair['cases']}
    cases=[]
    for item in study['cases']:
        arms={}
        for name,data in item['arms'].items():
            arms[name]={'top1_id':data['ids'][0] if data['ids'] else None,
                        'top1_label':data['labels'][0] if data['labels'] else 'NO_RESULT',
                        'known_positive_rank':next((i for i,label in enumerate(data['labels'],1) if label=='YES'),None),
                        'elapsed_ms':data['elapsed_ms']}
        posthoc=repair_cases[item['id']]
        arms['A4R']={'top1_id':posthoc['a4r_top1']['id'],'top1_label':posthoc['a4r_top1']['label'],
                     'known_positive_rank':1 if posthoc['a4r_top1']['label']=='YES' else None,
                     'elapsed_ms':posthoc['a4r_ms']}
        cases.append({'id':item['id'],'question':item['question'],'source_url':item['source_url'],
                      'target_accession':item['target_accession'],'arms':arms,
                      'a3_added_ids':sorted(set(item['arms']['A3']['ids'])-set(item['arms']['A2']['ids'])),
                      'a4_changed_top1':arms['A4']['top1_id']!=arms['A3']['top1_id']})
    freeze=root/'docs/topic3_v6/V6_ALGORITHM_FREEZE_MANIFEST.json'
    return {'status':'RECORDED_EXPOSED_DEVELOPMENT','case_count':len(cases),'human_gold':False,
            'numeric_cells_verified':0,'freeze_sha256':sha256(freeze.read_bytes()).hexdigest() if freeze.is_file() else None,
            'cases':cases}


@router.post('/research-lab/faith-r/live')
def faith_r_live_lab(payload:FaithRLiveRequest):
    if os.getenv('FAITH_R_LIVE_ENABLED')!='1':
        raise HTTPException(503,detail={'code':'RESEARCH_INDEX_NOT_ENABLED'})
    root=Path(__file__).resolve().parents[2]
    python=root/'tmp/topic3_v5r/research-venv/Scripts/python.exe'
    script=root/'scripts/topic3_v5r_query_once.py'
    if not python.is_file() or not all((root/f'tmp/topic3_v5r/restored/{arm}/meta.json').is_file() for arm in ('A','B')):
        raise HTTPException(503,detail={'code':'RESTORED_RESEARCH_INDEX_NOT_AVAILABLE'})
    if not research_slots.acquire(blocking=False):
        raise HTTPException(429,detail={'code':'RESEARCH_INDEX_BUSY'})
    try:
        try:
            result=subprocess.run([str(python),str(script),'--query',payload.query,'--arm',payload.arm],
                                  cwd=root,capture_output=True,text=True,encoding='utf-8',timeout=60,check=False)
        except subprocess.TimeoutExpired:
            raise HTTPException(504,detail={'code':'RESEARCH_QUERY_TIMEOUT'}) from None
        if result.returncode!=0:
            raise HTTPException(503,detail={'code':'RESEARCH_QUERY_FAILED'})
        return json.loads(result.stdout)
    except (ValueError,json.JSONDecodeError):
        raise HTTPException(503,detail={'code':'RESEARCH_QUERY_INVALID_RESULT'}) from None
    finally:
        research_slots.release()


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
            from app.product.assistant_answer import contract,needs_number,reviewed_plan
            profile=payload.search_profile
            if profile=='auto':
                profile='production_v3r3' if getattr(workspace(),'search_candidate_version',None)=='V3R3' else 'production_v3'
            if profile in {'production_v3','production_v3r3'}:
                result=unified_search(UnifiedSearch(query=payload.question,mode='hybrid',top_k=5,
                    source='USER_UPLOADS',document_ids=payload.document_ids,search_profile=profile))
            else:
                result=workspace().search(payload.question,'hybrid',5,payload.document_ids)
            answer=contract(payload.question,result,profile)
            if needs_number(payload.question):
                plan=reviewed_plan(payload.question,eligible_facts(workspace(),payload.document_ids),METRICS)
                if plan:
                    verified=numeric_answer(workspace(),payload.model_copy(update={'mode':'numeric',**plan}))
                    if verified['status']=='SUPPORTED':
                        return {**answer,**verified,'verification_status':verified['verification'],
                                'warnings':[],'retrieval_trace':answer['retrieval_trace'],
                                'search_profile':profile,'generation':result.get('generation')}
            return answer
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

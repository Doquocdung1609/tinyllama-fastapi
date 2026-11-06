"""Typed product orchestration; algorithms remain in the existing Python engine."""
from contextlib import closing
from functools import lru_cache
from hashlib import sha256
import json
import os
import re
import subprocess
from pathlib import Path
from threading import BoundedSemaphore, Thread
from typing import Literal, Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Response, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError
import psutil
import requests

from app.product.api import workspace,sec_index,require_studio_token,_error,_factory_lock
from app.product.analysis import AnalysisRequest,FactReview,review_fact,eligible_facts,numeric_answer,research_steps,METRICS
from app.product.pdf_extract import ocr_capability,folded

router=APIRouter(prefix='/studio',tags=['react-product'],dependencies=[Depends(require_studio_token)])
from app.product.sec_library import scoped as sec_scoped
slots=BoundedSemaphore(1)
research_slots=BoundedSemaphore(1)
sec_view_slots=BoundedSemaphore(1)


class SecSourceRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    reference:str=Field(min_length=10,max_length=4096,pattern=r'^[A-Za-z0-9_-]+\.[a-f0-9]{64}$')


@router.post('/sec/evidence')
def sec_source_evidence(payload:SecSourceRequest,response:Response):
    from app.product.sec_viewer import resolve,SourceViewError,server_key
    if not sec_view_slots.acquire(blocking=False):raise HTTPException(429,detail={'code':'SOURCE_VIEW_BUSY'})
    try:
        from app.product.sec_library import for_reference
        from app.product.sec_viewer import decode_reference
        data=decode_reference(payload.reference,server_key(workspace().root))
        try:index=sec_index()
        except Exception:index=None
        if index is None or index.identity['generation']!=data['generation']:
            index=for_reference(payload.reference,server_key(workspace().root))
        with index._lock:result=resolve(index,payload.reference,server_key(workspace().root))
        response.headers['Cache-Control']='no-store'
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Content-Security-Policy']="default-src 'none'; frame-ancestors 'none'"
        return result
    except SourceViewError as exc:raise HTTPException(409,detail={'code':str(exc)}) from None
    except (FileNotFoundError,OSError):raise HTTPException(409,detail={'code':'SOURCE_BYTES_NOT_AVAILABLE'}) from None
    except (ValueError,RecursionError,KeyError,TypeError):raise HTTPException(409,detail={'code':'SOURCE_IDENTITY_MISMATCH'}) from None
    finally:sec_view_slots.release()


class MetadataUpdate(BaseModel):
    model_config=ConfigDict(extra='forbid')
    changes:dict[str,str]


@router.get('/documents/{document_id}/metadata')
def metadata(document_id:str):
    from app.product.document_metadata import read_metadata,extract_metadata,save_metadata
    w=workspace()
    try:path=w.source_file(document_id)
    except ValueError as exc:raise HTTPException(409,detail={'code':_error(exc)}) from None
    saved=read_metadata(w,document_id)
    if not saved['fields']:
        saved=extract_metadata(path);save_metadata(w,document_id,saved)
    return saved


@router.patch('/documents/{document_id}/metadata')
def metadata_update(document_id:str,payload:MetadataUpdate):
    from app.product.document_metadata import correct_metadata
    try:return correct_metadata(workspace(),document_id,payload.changes)
    except ValueError as exc:raise HTTPException(409,detail={'code':_error(exc)}) from None


class ChatRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    question:str=Field(min_length=2,max_length=2000)
    document_ids:list[Annotated[str,Field(pattern=r'^[a-f0-9]{32}$')]]=Field(default_factory=list,max_length=20)
    source:Literal['USER_UPLOADS','US_SEC']='USER_UPLOADS'
    ticker:str=Field(default='',max_length=20,pattern=r'^[A-Za-z0-9.-]*$')
    filing_ids:list[str]=Field(default_factory=list,max_length=20)
    session_id:str|None=Field(default=None,pattern=r'^[a-f0-9]{32}$')
    constraints:dict[str,str]=Field(default_factory=dict,max_length=6)
    evidence_context:dict=Field(default_factory=dict,max_length=20)
    progress_id:str|None=Field(default=None,pattern=r'^[a-f0-9]{32}$')


@router.get('/chat/progress/{request_id}')
def chat_progress(request_id:str):
    from app.product.chat_store import owner
    from app.product.document_progress import get
    return get(owner(workspace()),request_id)


@router.get('/chat/sessions')
def chat_sessions(q:str=Query(default='',max_length=200),limit:int=20,offset:int=0):
    from app.product.chat_store import connect,owner,public
    # Explicit checks also cover direct Python callers.
    if not isinstance(q,str):q=''
    if not 1<=limit<=100 or offset<0:raise HTTPException(422,detail={'code':'INVALID_PAGINATION'})
    w=workspace()
    with connect(w) as db:
        rows=db.execute('SELECT * FROM financial_chat_sessions WHERE owner=? AND (title LIKE ? OR payload LIKE ?) ORDER BY updated_at DESC,id LIMIT ? OFFSET ?',
            (owner(w),'%'+q+'%','%'+q+'%',limit+1,offset)).fetchall()
    return {'sessions':[public(r) for r in rows[:limit]],'has_more':len(rows)>limit,'offset':offset}


@router.get('/chat/{session_id}')
def chat_session(session_id:str):
    from app.product.chat_store import connect,owner,public
    w=workspace()
    with connect(w) as db:row=db.execute('SELECT * FROM financial_chat_sessions WHERE id=? AND owner=?',(session_id,owner(w))).fetchone()
    if row is None:raise HTTPException(404,detail={'code':'CHAT_NOT_FOUND'})
    return public(row,True)


class ChatRename(BaseModel):
    model_config=ConfigDict(extra='forbid')
    title:str=Field(min_length=1,max_length=120)


@router.patch('/chat/{session_id}')
def rename_chat(session_id:str,payload:ChatRename):
    from app.product.chat_store import connect,owner,now
    w=workspace()
    with connect(w) as db:
        cursor=db.execute('UPDATE financial_chat_sessions SET title=?,updated_at=? WHERE id=? AND owner=?',
            (payload.title.strip() or 'Hội thoại mới',now(),session_id,owner(w)))
        if cursor.rowcount!=1:raise HTTPException(404,detail={'code':'CHAT_NOT_FOUND'})
    return chat_session(session_id)


@router.delete('/chat/{session_id}')
def reset_financial_chat(session_id:str):
    if not re.fullmatch(r'[a-f0-9]{32}',session_id):raise HTTPException(422,detail={'code':'INVALID_CHAT_SESSION'})
    from app.product.chat_store import connect,owner
    w=workspace()
    with connect(w) as db:
        db.execute('DELETE FROM financial_chat_sessions WHERE id=? AND owner=?',(session_id,owner(w)))
    return {'reset':True}


@router.post('/chat')
@sec_scoped
def financial_chat(payload:ChatRequest):
    from app.product.natural_pdf_dialogue import respond as natural_pdf_answer
    from app.product.document_reasoning import answer as document_reasoning
    from app.product.statement_question_answer import answer as statement_answer
    w=workspace();session=payload.session_id or uuid4().hex
    if payload.source=='USER_UPLOADS' and not payload.document_ids:raise HTTPException(422,detail={'code':'SELECT_PDF_SOURCE'})
    if payload.source=='US_SEC' and payload.document_ids:raise HTTPException(422,detail={'code':'SEC_PDF_SOURCE_SCOPE_CONFLICT'})
    for doc_id in payload.document_ids:
        doc=w.document(doc_id)
        if not doc or doc['status']!='READY':raise HTTPException(409,detail={'code':'PDF_DOCUMENT_NOT_READY'})
        try:w.source_file(doc_id)
        except ValueError as exc:raise HTTPException(409,detail={'code':_error(exc)}) from None
    from app.product.query_source_context import source_company_conflict
    conflict=source_company_conflict(w,payload.document_ids,payload.question)
    claim = re.search(r'\b(?:chi (?:dang )?(?:su dung|chon|dung)|only (?:using|selected|use))'
                      r'\s+(?P<one>(?:mot|one)\s+)?(?:pdf|file)\b(?P<name>[^.!?\n]*)', folded(payload.question))
    if len(set(payload.document_ids))>1 and claim:
        from app.product.financial_understanding import issuers
        single_claim = bool(claim['one']) or len(issuers(claim['name'])) == 1
    else:
        single_claim = False
    if single_claim:
        filenames=', '.join(w.document(doc_id)['filename'] for doc_id in dict.fromkeys(payload.document_ids))
        conflict={'status':'QUERY_CONTEXT_CONFLICT','reason':'SELECTED_PDF_COUNT_MISMATCH',
                  'answer':f"Câu hỏi nói chỉ dùng một PDF. Bộ chọn hiện có {len(set(payload.document_ids))} PDF: {filenames}. "
                           "Hãy bỏ chọn file thừa hoặc hỏi lại với cả hai nguồn.",
                  'citations':[],'values':[]}
    from app.product.document_metadata import read_metadata
    source_set=sorted((d,w.document(d)['sha256'],len(read_metadata(w,d)['corrections'])) for d in payload.document_ids)
    sec_identities=[]; selected_index=None
    if payload.source=='US_SEC':
        try:
            selected_index=sec_index()
            sec_identities=sorted((f['filing_id'],f.get('raw_sha256',''),f.get('generation') or selected_index.identity['generation'])
                for f in selected_index.catalog()['filings'] if (not payload.filing_ids or f['filing_id'] in payload.filing_ids)
                and (not payload.ticker or f['ticker']==payload.ticker.upper()))
        except Exception:pass
    fingerprint=sha256(json.dumps(source_set if payload.source=='USER_UPLOADS' else ['SEC_SOURCE_SCOPE_V2',payload.ticker,sorted(payload.filing_ids),sec_identities]).encode()).hexdigest()
    with closing(w._connect()) as db,db:
        from app.product.chat_store import connect as chat_connect
        with chat_connect(w):pass
        from app.product.chat_store import owner
        owned=db.execute('SELECT owner FROM financial_chat_sessions WHERE id=?',(session,)).fetchone()
        if owned and owned['owner']!=owner(w):raise HTTPException(404,detail={'code':'CHAT_NOT_FOUND'})
        prior=db.execute('SELECT scope,payload FROM financial_chat_sessions WHERE id=? AND owner=?',(session,owner(w))).fetchone()
    history=json.loads(prior['payload']) if prior and prior['scope']==fingerprint else []
    if prior and prior['scope']!=fingerprint:session=uuid4().hex
    question=payload.question
    from app.product.answer_planner_v2 import resolve_followup
    from app.product.chat_source_focus import explain_focus,reference_followup,selected_source
    selection=selected_source(w,payload)
    focused_reply=explain_focus(selection or reference_followup(w,payload,history),question)
    context_history=history
    if selection and selection[1] and not focused_reply:
        from app.product.answer_planner_v2 import plan_question
        source,row,cell=selection
        label=source.get('row_label','')
        column=cell.get('column_label','') if cell else ''
        bound=plan_question(f'{label} {column}').public()
        context_history=[{'question':label,'response':{'conversation_slots':bound}}]
    question,conversation_plan=resolve_followup(question,context_history)
    allowed={'metric','operation','current_period','previous_period','statement_scope','basis'}
    if set(payload.constraints)-allowed:raise HTTPException(422,detail={'code':'UNKNOWN_ADVANCED_CONSTRAINT'})
    if any(not isinstance(v,str) or len(v)>80 for v in payload.constraints.values()):raise HTTPException(422,detail={'code':'INVALID_ADVANCED_CONSTRAINT'})
    if payload.source=='US_SEC' and payload.constraints:raise HTTPException(422,detail={'code':'SEC_ADVANCED_CONSTRAINTS_NOT_SUPPORTED'})
    try:request=None if payload.source=='US_SEC' else AnalysisRequest(question=question,document_ids=payload.document_ids,search_profile='auto',**payload.constraints)
    except ValidationError:raise HTTPException(422,detail={'code':'INVALID_ADVANCED_CONSTRAINT'}) from None
    if not slots.acquire(blocking=False):raise HTTPException(429,detail={'code':'FINANCIAL_ASSISTANT_BUSY'})
    try:
        if payload.source=='US_SEC':
            from app.product.faith_r_product import evidence_answer
            from app.product.assistant_answer import contract
            from app.product.sec_multi_qa import resolve_followup as resolve_sec_followup
            from app.product.sec_question import answer as sec_answer
            from app.product.sec_viewer import server_key
            if history:
                question=resolve_sec_followup(payload.question,history[-1]['response'])
            pending=history[-1]['response'].get('pending_clarification') if history else None
            still_missing=bool(pending and question==payload.question and re.fullmatch(
                r'(?:dung roi|chinh xac|yes|correct|ok|okay)[?!. ]*',folded(question)))
            if still_missing:
                answer={'status':'NEEDS_CLARIFICATION','answer_status':'REQUIRES_SOURCE_REVIEW',
                        'answer':'Tôi vẫn cần '+('tên doanh nghiệp cần phân tích.' if pending['missing_slot']=='issuer'
                                           else 'kỳ báo cáo hoặc độ dài kỳ cần so sánh.'),
                        'reason':'SEC_CLARIFICATION_STILL_MISSING','values':[],'citations':[],
                        'pending_clarification':pending}
            else:
                try:
                    answer = sec_answer(selected_index, question, payload.ticker, server_key(w.root)) if selected_index is not None else None
                except (ValueError,OSError,RuntimeError):
                    answer={'status':'SOURCE_EXCERPTS','answer_status':'REQUIRES_SOURCE_REVIEW',
                            'answer':'Chưa đối chiếu được ô tài chính trong nguồn SEC đã chọn. Các đoạn liên quan chỉ dùng để kiểm tra thêm.',
                            'reason':'SEC_SOURCE_CELL_VERIFICATION_FAILED','values':[],'citations':[]}
            if selected_index is None:
                answer={'status':'SOURCE_UNAVAILABLE','answer_status':'SOURCE_UNAVAILABLE',
                        'answer':'Không truy cập được chỉ mục hoặc nguồn SEC đang chọn.',
                        'reason':'SEC_SELECTED_INDEX_UNAVAILABLE','values':[],'citations':[]}
            if selected_index is not None and answer is None:
                # Numeric QA goes directly to authenticated rows, avoiding an
                # unrelated dense query on the successful verification path.
                profile='baseline' if answer else 'faith_r_product_v1'
                try:
                    result=unified_search(UnifiedSearch(query=question,source='US_SEC',issuer=payload.ticker,
                        mode='bm25',top_k=2 if answer else 5,search_profile=profile,auto_fallback=True))
                except ValueError:
                    result={'results':[],'source_errors':[{'source':'US_SEC','reason':'SEC_RELATED_EVIDENCE_UNAVAILABLE'}]}
                evidence=evidence_answer(question,result) or contract(question,result,profile)
                if answer:
                    answer={**evidence,**answer,'citations':answer.get('citations') or evidence.get('citations',[])}
                else:
                    answer=evidence
                if result['source_errors'] and not answer.get('reason'):
                    answer.update(status='SOURCE_UNAVAILABLE',answer='Không truy cập được chỉ mục hoặc nguồn SEC đang chọn.',
                                  source_errors=result['source_errors'])
        elif conflict:answer=conflict
        elif focused_reply is not None:answer=focused_reply
        elif not payload.constraints and selection is None and (statement:=statement_answer(w,question,payload.document_ids)) is not None:
            answer=statement
        elif not payload.constraints and (reasoned:=_reason_with_progress(w,request,payload.progress_id,document_reasoning)) is not None:
            answer=reasoned
        elif len(set(payload.document_ids))>1:
            from app.product.pdf_multi_qa import answer as pdf_multi
            def per_document(doc_id, scoped_question):
                try:
                    if payload.constraints:
                        return analysis(request.model_copy(update={'document_ids':[doc_id],'question':scoped_question}))
                    local=statement_answer(w,scoped_question,[doc_id])
                    if local is not None:
                        return local
                    results=unified_search(UnifiedSearch(query=scoped_question,mode='bm25',source='USER_UPLOADS',
                        document_ids=[doc_id],top_k=5,search_profile='faith_r_product_v1'))
                    return results['financial_evidence']
                except HTTPException as exc:
                    return {'answer':'Chưa xác minh được yêu cầu trong PDF này.','reason':exc.detail}
            answer=pdf_multi(w,question,payload.document_ids,per_document,payload.constraints)
        elif not payload.constraints and (natural := natural_pdf_answer(w, payload.question, payload.document_ids, history)) is not None:
            answer=natural
        elif re.search(r'nghien cuu|tong quan doanh nghiep|company research|company overview',folded(question)):
            sections=[];citations=[]
            for label,query in [('Hoạt động','business operations strategy'),('Tài chính','financial condition net sales'),('Rủi ro','risk factors')]:
                found=unified_search(UnifiedSearch(query=query,document_ids=payload.document_ids,source='USER_UPLOADS',search_profile='auto',top_k=2))
                quotes=found['results'];citations.extend(quotes);sections.append(label+': '+(' '.join(quotes[0]['text'].split())[:400] if quotes else 'Chưa có nguồn phù hợp.'))
            answer={'status':'SOURCE_EXCERPTS','answer':'\n\n'.join(sections),'citations':citations,'values':[],
                    'verification_status':'SOURCE_TEXT_UNREVIEWED','warnings':['Tổng hợp trích đoạn tài liệu, chưa chứng nhận số liệu hay tin tức hiện tại.']}
        else:answer=analysis(request)
        if payload.source=='US_SEC':
            answer['question_contract']={'original_question':payload.question,'resolved_question':question,'source_filing_ids':payload.filing_ids,
                'source_identities':sec_identities,'raw_obligation_audit':answer.get('semantic_question_coverage',{}).get('original_question_audit')}
        if answer.get('query_plan') and 'supporting_claims' in answer:
            from app.product.semantic_answer_gate import verify_coverage
            raw_plan={**answer['query_plan'],'raw_text':payload.question}
            coverage=verify_coverage(raw_plan,answer['supporting_claims'],answer.get('answer',''))
            answer['semantic_question_coverage']=coverage
            answer['question_contract']={'original_question':payload.question,'resolved_question':question,
                'source_document_ids':payload.document_ids,'source_filing_ids':payload.filing_ids,
                'inherited_slots':conversation_plan.inherited_slots,'raw_obligation_audit':coverage['original_question_audit']}
            if coverage['status']!='COMPLETE' and answer.get('answer_status')=='VERIFIED_ANSWER':
                answer.update(answer_status='PARTIAL_VERIFIED',status='SOURCE_EXCERPTS',unanswered_subquestions=coverage['unanswered_subquestions'])
        if conversation_plan.inherited_slots:
            for key in ('query_plan','conversation_slots'):
                if isinstance(answer.get(key),dict):answer[key]['inherited_slots']=conversation_plan.inherited_slots
        from app.product.chat_store import save,now
        stamp=now()
        messages=[{'id':uuid4().hex,'role':'user','text':payload.question,'created_at':stamp},
            {'id':uuid4().hex,'role':'assistant','text':answer.get('answer',''),'created_at':stamp,
             'evidence_ids':[c.get('citation_id',c.get('evidence_id',c.get('chunk_id'))) for c in answer.get('citations',[])],
             'status':answer.get('status'),'trace':answer.get('retrieval_trace',{})}]
        history=history+[{'question':payload.question,'resolved_question':question,'response':answer,'created_at':stamp,'messages':messages}]
        save(w,session,fingerprint,history,payload.document_ids if payload.source=='USER_UPLOADS' else ['SEC:'+f for f in payload.filing_ids] if payload.filing_ids else ['SEC:'+payload.ticker])
        return {**answer,'session_id':session,'resolved_question':question,'source_scope':payload.document_ids,
                'conversation_reset':bool(prior and prior['scope']!=fingerprint)}
    finally:slots.release()


class UnifiedSearch(BaseModel):
    model_config=ConfigDict(extra='forbid')
    query:str=Field(min_length=2,max_length=2000)
    mode:Literal['bm25','dense','hybrid']='hybrid'
    top_k:int=Field(default=5,ge=1,le=20)
    source:Literal['VIETNAM','US_SEC','ALL','USER_UPLOADS']='VIETNAM'
    document_ids:list[str]=Field(default_factory=list,max_length=100)
    filing_ids:list[str]=Field(default_factory=list,max_length=20)
    issuer:str=Field(default='',max_length=160)
    period:str=Field(default='',max_length=80)
    auto_fallback:bool=False
    statement_scope:Literal['SEPARATE','CONSOLIDATED']|None=None
    search_profile:Literal['faith_r_product_v1','auto','baseline','production_v2','production_v3','production_v3r','production_v3r2','production_v3r3']='baseline'


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
    engine_version:str|None=None
    algorithm_executed:str|None=None
    candidate_count:int|None=None
    scope_availability:list[str]|None=None
    scope_missing:bool|None=None
    routing_reason:str|None=None
    financial_evidence:dict|None=None
    query_plan:dict|None=None
    requested_top_k:int|None=None
    returned_count:int|None=None
    mode_requested:str|None=None
    mode_executed:str|None=None
    search_profile_requested:str|None=None
    search_profile_executed:str|None=None
    filter_reason:str|None=None
    dedup_count:int|None=None
    truncation_reason:str|None=None
    retrieval_status:str|None=None
    matching_evidence_count:int|None=None
    verified_value_count:int=0


class ComparisonResponse(BaseModel):
    arms:dict[str,SearchResponse]
    generation:str
    overlap:dict[str,int]
    quality_metrics:None=None
    quality_reason:str
    candidate:SearchResponse|None=None


@sec_scoped
def unified_search(payload:UnifiedSearch):
    w=workspace()
    reason=None
    requested=payload
    is_auto=payload.search_profile=='auto' or payload.auto_fallback
    if payload.search_profile=='auto':
        profile,reason=('faith_r_product_v1','SHARED_FINANCIAL_PRODUCT_ENGINE') if hasattr(w,'source_file') else automatic_profile(w)
        payload=payload.model_copy(update={'search_profile':profile})
    if payload.search_profile=='faith_r_product_v1' and payload.source=='USER_UPLOADS':
        from app.product.query_source_context import source_company_conflict
        conflict=source_company_conflict(w,payload.document_ids,payload.query)
        if conflict:
            return {'status':'READY','generation':sha256(json.dumps(payload.document_ids).encode()).hexdigest(),
                'source_generations':[],'results':[],'mode':payload.mode,'source_errors':[],
                'latency_ms':0,'timings_ms':{},'cross_source_order':None,'search_profile':payload.search_profile,
                'evidence_status':'QUERY_CONTEXT_CONFLICT','financial_evidence':conflict,
                'requested_top_k':requested.top_k,'returned_count':0,'mode_requested':requested.mode,'mode_executed':None,
                'search_profile_requested':requested.search_profile,'search_profile_executed':None,'filter_reason':'ISSUER_CONFLICT','dedup_count':0,'retrieval_status':'CLARIFY_SCOPE'}
    try:
        if hasattr(w,'resources'):
            with w.resources.claim('QUERY_OR_COMPARISON',minimum_mb=256,timeout=10):result=_unified_search(payload)
        else:result=_unified_search(payload)
    except requests.RequestException:
        if not is_auto or payload.mode!='hybrid':raise
        result=_unified_search(payload.model_copy(update={'mode':'bm25'}))
        reason='DENSE_UNAVAILABLE_BM25_FALLBACK'
    except ValueError as exc:
        if not is_auto or payload.mode!='hybrid' or str(exc)!='EMBEDDING_MODEL_DIGEST_MISMATCH':raise
        result=_unified_search(payload.model_copy(update={'mode':'bm25'}))
        reason='COMPATIBLE_DENSE_MODEL_UNAVAILABLE_BM25_FALLBACK'
    result['routing_reason']=reason or result.get('routing_reason')
    if payload.search_profile=='faith_r_product_v1':
        from app.product.financial_understanding import understand
        result['intent']=understand(payload.query).public()
    if payload.source=='USER_UPLOADS' and hasattr(w,'source_file') and payload.search_profile=='faith_r_product_v1':
        from app.product.answer_composer_v2 import compose_answer
        from app.product.statement_question_answer import answer as statement_answer
        scoped_ids=sorted({h['document_id'] for h in result['results'] if h.get('document_id')})
        structured=None if payload.issuer or payload.period or not payload.document_ids else statement_answer(w,payload.query,payload.document_ids)
        result['financial_evidence']=structured or compose_answer(w,payload.query,result,scoped_ids)
    evidence=result.get('financial_evidence') or {}
    result.update(requested_top_k=requested.top_k,returned_count=len(result['results']),mode_requested=requested.mode,
        mode_executed=result['mode'] if result.get('source_generations') else None,search_profile_requested=requested.search_profile,search_profile_executed=result['search_profile'] if result.get('source_generations') else None,
        verified_value_count=len({a['citation_id'] for a in evidence.get('independent_verification',{}).get('stage_a',[])} |
                                 {a['citation_id'] for a in evidence.get('operands',[]) if
                                  a.get('verification_status')=='NATIVE_CELL_VERIFIED' and a.get('value') is not None}),
        matching_evidence_count=len(result['results']) if result['search_profile']=='faith_r_product_v1' else None,
        retrieval_status='SOURCE_UNAVAILABLE' if result['source_errors'] and not result['results'] else 'RESULTS_FOUND' if result['results'] else 'NO_RESULTS')
    result.setdefault('filter_reason','SOURCE_ISSUER_PERIOD_FILTER' if requested.issuer or requested.period else None)
    result.setdefault('truncation_reason','TOP_K_LIMIT' if len(result['results'])==requested.top_k else 'FEWER_SOURCE_CANDIDATES')
    return result


def automatic_profile(w):
    root=getattr(w,'root',None)
    if root is None and getattr(w,'search_candidate_version',None)=='V3R3':
        return 'production_v3r3','ADAPTER_DECLARED_V3R3_CAPABILITY'
    if root is not None and (root/'derived-generation.json').exists():
        from app.product.search_preparation import preparation
        if preparation(w).status().get('status')=='READY' and getattr(w,'search_candidate_version',None)=='V3R3':
            return 'production_v3r3','MATCHING_READY_DERIVED_V3R3'
    return 'production_v3','GENERIC_PDF_V3_NO_COMPATIBLE_READY_DERIVED_INDEX'


def _unified_search(payload:UnifiedSearch):
    results=[];scopes=[];errors=[];timings={};intent=None;evidence_status=None;evidence_reason=None;engine_trace={}
    if payload.source!='US_SEC':
        docs=workspace()._eligible(payload.document_ids)
        if payload.issuer or payload.period:
            from app.product.financial_understanding import document_profile,issuers
            profiles={d['id']:document_profile(workspace(),d) for d in docs}
            if payload.issuer:
                aliases=set(issuers(payload.issuer))
                docs=[d for d in docs if aliases.intersection(profiles[d['id']]['identities'])] if aliases else [d for d in docs if folded(payload.issuer) in folded(d['issuer'])]
            if payload.period:docs=[d for d in docs if payload.period in (d.get('report_period') or profiles[d['id']].get('report_year') or '')]
        if payload.source=='VIETNAM':
            def vietnamese(doc):
                try:text=workspace().page_evidence(doc['id'],min(3,doc['pages']))['text']
                except ValueError:text=doc['issuer']
                return any(word in folded(text) for word in ('tai san','bao cao','ngan hang','hoa phat'))
            docs=[d for d in docs if vietnamese(d)]
        if docs:
            if payload.search_profile=='faith_r_product_v1':
                from app.product.faith_r_product import pdf_search
                found=pdf_search(workspace(),payload.query,payload.mode,payload.top_k,[d['id'] for d in docs])
                intent=found.get('intent');evidence_status=found.get('evidence_status')
                engine_trace={k:found.get(k) for k in ('engine_version','algorithm_executed','candidate_count','scope_availability','scope_missing','dedup_count','filter_reason','truncation_reason','query_plan')}
            elif payload.search_profile in {'production_v2','production_v3','production_v3r','production_v3r2','production_v3r3'}:
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
                intent=found.get('intent');evidence_status=found.get('evidence_status');evidence_reason=found.get('reason')
            else:found=workspace().search(payload.query,payload.mode,payload.top_k,[d['id'] for d in docs],**({'_candidate_limit':80} if payload.statement_scope else {}))
            engine_trace.setdefault('candidate_count',found.get('candidate_count'))
            engine_trace.setdefault('dedup_count',found.get('dedup_count'))
            executed_mode=found.get('mode',payload.mode)
            if payload.statement_scope:
                from app.product.faith_r_product import _scope
                scoped=[]
                for hit in found['results']:
                    actual=None
                    for page_no in (hit['page'],hit['page']-1):
                        if page_no<1:continue
                        text=workspace().page_evidence(hit['document_id'],page_no)['text'][:1600]
                        normalized=folded(text)
                        if ('hop nhat' in normalized or 'consolidated' in normalized) and ('rieng' in normalized or 'parent company' in normalized):actual='MIXED';break
                        explicit=_scope(text)
                        if explicit:actual=explicit;break
                    if actual==payload.statement_scope:scoped.append({**hit,'statement_scope':actual})
                found['results']=scoped[:payload.top_k]
                for rank,h in enumerate(found['results'],1):h['rank']=rank
                engine_trace['filter_reason']='STATEMENT_SCOPE_FILTER'
                engine_trace['truncation_reason']='TOP_K_LIMIT' if len(found['results'])==payload.top_k else 'FEWER_MATCHING_SCOPE_CANDIDATES'
            results.extend({**r,'source_kind':'PDF'} for r in found['results'])
            scopes.append(('PDF',found.get('generation')));timings['PDF']=found['latency_ms']
    if payload.source in {'US_SEC','ALL'}:
        try:
            from app.product.sec_library import FederatedIndex, federated_search, for_hit
            index = sec_index()
            if payload.search_profile=='faith_r_product_v1':
                from app.product.faith_r_product import sec_search
                def retrieve(part):
                    return sec_search(part,payload.query,payload.mode,payload.top_k,payload.issuer,payload.period)
                found = federated_search(index, retrieve, payload.top_k) if isinstance(index,FederatedIndex) else retrieve(index)
                intent=found.get('intent');evidence_status=found.get('evidence_status')
                engine_trace={k:found.get(k) for k in ('engine_version','algorithm_executed','candidate_count','scope_availability','scope_missing','dedup_count','filter_reason','truncation_reason','query_plan')}
            elif payload.search_profile in {'production_v3','production_v3r','production_v3r2','production_v3r3'}:
                from app.product.search_v3 import search_sec_v3
                def retrieve(part):
                    return search_sec_v3(part,payload.query,payload.mode,payload.top_k,payload.issuer,payload.period)
                found = federated_search(index,retrieve,payload.top_k) if isinstance(index,FederatedIndex) else retrieve(index)
                intent=found.get('intent');evidence_status=found.get('evidence_status');evidence_reason=found.get('reason')
            else:found=sec_index().search(payload.query,payload.mode,payload.top_k,payload.issuer,payload.period)
            # V3 constructs new result dictionaries; sign final canonical
            # parents here as well, without changing ranks or evidence grades.
            from app.product.sec_viewer import reference,server_key
            key=server_key(workspace().root)
            for hit in found['results']:
                hit['source_reference']=reference(for_hit(index,hit),hit['chunk_id'],key)
            results.extend({**r,'source_kind':'SEC'} for r in found['results'])
            scopes.extend(('SEC',g) for g in found.get('generations',[found.get('generation')]));timings['SEC']=found.get('latency_ms',0)
            errors.extend({'source':'US_SEC',**unavailable} for unavailable in found.get('unavailable_partitions',[]))
        except Exception as exc:
            if payload.source=='US_SEC' and payload.search_profile!='faith_r_product_v1':raise ValueError(_error(exc)) from None
            errors.append({'source':'US_SEC','reason':_error(exc)})
    # Across stores use ranks, never raw BM25/cosine magnitudes. Per-store retrieval stays unchanged.
    if len(scopes)>1:results.sort(key=lambda r:(r['rank'],r.get('chunk_id',r.get('parent_id',''))))
    generation=sha256(json.dumps(scopes,sort_keys=True).encode()).hexdigest()
    for rank,result in enumerate(results[:payload.top_k],1):result['rank']=rank
    return {**engine_trace,'status':'PARTIAL' if errors else 'READY','generation':generation,'source_generations':scopes,
            'results':results[:payload.top_k],'mode':locals().get('executed_mode',payload.mode),'source_errors':errors,
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
                  'candidate':unified_search(payload) if payload.search_profile in {'auto','faith_r_product_v1','production_v3','production_v3r','production_v3r2','production_v3r3'} else None}
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
    try:
        from app.product.sec_library import catalog
        sec=catalog()
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


def _reason_with_progress(w,request,request_id,reason):
    if not request_id:
        return reason(w,request)
    from app.product.chat_store import owner
    from app.product.document_progress import update
    scope=owner(w)
    return reason(w,request,lambda **event:update(scope,request_id,**event))


@router.get('/documents/{document_id}/page-map')
def pdf_page_map(document_id:str):
    from app.product.document_page_map import document_map
    w=workspace()
    doc=w.document(document_id)
    if not doc:
        raise HTTPException(404,detail={'code':'DOCUMENT_NOT_FOUND'})
    try:
        return document_map(w,doc)
    except ValueError as exc:
        raise HTTPException(409,detail={'code':_error(exc)}) from None


@router.get('/documents/{document_id}/pages/{page}/evidence')
def page_evidence(document_id:str,page:int):
    try:return workspace().page_evidence(document_id,page)
    except ValueError as exc:raise HTTPException(409,detail={'code':_error(exc)}) from None


@router.get('/documents/{document_id}/pages/{page}/ocr-comparison')
def ocr_comparison(document_id:str,page:int):
    if not re.fullmatch(r'[a-f0-9]{32}',document_id) or not 1<=page<=250:
        raise HTTPException(422,detail={'code':'INVALID_OCR_COMPARISON_SOURCE'})
    w=workspace()
    try:
        evidence=w.page_evidence(document_id,page)
        root=w.root.resolve()
        target=(root/'ocr-comparison'/document_id/f'{page}.json').resolve()
        if not target.is_relative_to(root) or not target.is_file() or target.stat().st_size>512_000:
            return {'available':False}
        data=json.loads(target.read_bytes())
        if (data['source_sha256']!=evidence['source_sha256'] or data['page']!=page
                or data['checkpoint_sha256']!=evidence['checkpoint_sha256']):
            return {'available':False}
        return {'available':True,'engine':data['engine'],'words':data['words'][:600]}
    except (OSError,ValueError,KeyError,TypeError):
        return {'available':False}


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
        if hasattr(workspace(),'document'):
            from app.product.query_source_context import source_company_conflict
            conflict=source_company_conflict(workspace(),payload.document_ids,payload.question)
            if conflict:return conflict
        if payload.mode=='numeric':
            reviewed=numeric_answer(workspace(),payload)
            if reviewed['status']=='SUPPORTED':
                from app.product.verified_financial import validate_supported_response
                return validate_supported_response(workspace(),reviewed,payload.operation)
            return analysis(payload.model_copy(update={'mode':'document_qa'}))
        if payload.mode=='document_qa':
            from app.product.assistant_answer import contract,needs_number,reviewed_plan
            profile=payload.search_profile
            if profile=='auto':
                profile='faith_r_product_v1' if hasattr(workspace(),'source_file') else automatic_profile(workspace())[0]
            if profile in {'faith_r_product_v1','production_v3','production_v3r3'}:
                result=unified_search(UnifiedSearch(query=payload.question,mode='hybrid',top_k=5,
                    source='USER_UPLOADS',document_ids=payload.document_ids,search_profile=profile,auto_fallback=payload.search_profile=='auto'))
            else:
                result=workspace().search(payload.question,'hybrid',5,payload.document_ids)
            answer=contract(payload.question,result,profile)
            if profile=='faith_r_product_v1':
                answer=result['financial_evidence']
                from app.product.answer_planner_v2 import constraint_conflicts
                conflicts=constraint_conflicts(payload,answer)
                if conflicts:
                    return {**answer,'status':'QUERY_CONTEXT_CONFLICT','answer_status':'CONFLICTING_EVIDENCE',
                        'answer':'Tùy chọn nâng cao mâu thuẫn hoặc chưa được chứng minh bởi câu hỏi và ô nguồn. Hãy bỏ tùy chọn hoặc nêu rõ yêu cầu trong câu hỏi.',
                        'reason':'EXPLICIT_QUERY_CONTEXT_CONFLICT','conflicting_fields':conflicts,'values':[],'calculation_steps':[],
                        'verification_status':'QUERY_CONTEXT_CONFLICT'}
                from app.product.ocr_financial_workspace import AdaptiveFinancialOcrWorkspace, FinancialOcrWorkspace
                w=workspace()
                if (isinstance(w,AdaptiveFinancialOcrWorkspace) and not answer.get('values')
                        and not payload.model_fields_set.intersection({'metric','operation','current_period','previous_period','basis','statement_scope'})):
                    from app.product.ocr_reviewed_answer import answer as reviewed_ocr, calculation as reviewed_ocr_calculation
                    from app.product.ocr_candidate_answer import answer as candidate_ocr
                    return reviewed_ocr(w,payload) or reviewed_ocr_calculation(w,payload) or candidate_ocr(w,payload,result.get('results',[])) or answer
                if (isinstance(w,FinancialOcrWorkspace) and len(payload.document_ids)==1 and not answer.get('values')
                        and not payload.model_fields_set.intersection({'metric','operation','current_period','previous_period','basis','statement_scope'})
                        and re.search(r'\b\d{1,2}/\d{1,2}/20\d{2}\b',payload.question)
                        and (needs_number(payload.question) or 'trích giá trị' in payload.question.casefold())):
                    plan=reviewed_plan(payload.question,eligible_facts(w,payload.document_ids),METRICS)
                    if plan and plan['operation']=='EXTRACT' and plan['metric'] in {'assets','liabilities','equity'}:
                        from app.product.verified_financial import validate_supported_response
                        reviewed=numeric_answer(w,payload.model_copy(update={'mode':'numeric',**plan}))
                        verified=validate_supported_response(w,reviewed,'EXTRACT')
                        if verified['status']=='SUPPORTED':
                            from app.product.answer_composer_v2 import display
                            return {**verified,'answer':f"{verified['citations'][0]['row_label']}: {display(verified['values'][0])} {verified['unit']}. [1]",
                                    'verification_status':'VERIFIED_BY_LOCAL_SOURCE_IMAGE_REVIEW',
                                    'answer_status':'VERIFIED_ANSWER'}
                return answer
            if needs_number(payload.question):
                plan=reviewed_plan(payload.question,eligible_facts(workspace(),payload.document_ids),METRICS)
                if plan:
                    conflicts=[key for key,value in plan.items()
                               if key in payload.model_fields_set and getattr(payload,key)!=value]
                    if conflicts:
                        return {**answer,'status':'QUERY_CONTEXT_CONFLICT',
                                'answer':'Câu hỏi mâu thuẫn với tùy chọn đã chọn. Hãy sửa hoặc bỏ tùy chọn trước khi tính.',
                                'reason':'EXPLICIT_QUERY_CONTEXT_CONFLICT','conflicting_fields':conflicts,
                                'values':[],'citations':[], 'verification_status':'QUERY_CONTEXT_CONFLICT'}
                    verified=numeric_answer(workspace(),payload.model_copy(update={'mode':'numeric',**plan}))
                    if verified['status']=='SUPPORTED':
                        from app.product.verified_financial import validate_supported_response
                        verified=validate_supported_response(workspace(),verified,plan['operation'])
                        return {**answer,**verified,'verification_status':verified.get('verification',verified.get('verification_status')),
                                'warnings':[],'retrieval_trace':answer['retrieval_trace'],
                                'search_profile':profile,'generation':result.get('generation')}
                # Filing-level report_period does not exclude prior-year table
                # columns. Only the source-bound column verifier may resolve
                # such comparative periods; empty retrieval still abstains.
                if answer['status'] in {'SOURCE_EXCERPTS','INSUFFICIENT_EVIDENCE'} and result.get('results') and hasattr(workspace(),'source_file'):
                    from app.product.verified_financial import automatic_answer
                    verified=automatic_answer(workspace(),payload,result)
                    from app.product.verified_financial import validate_supported_response
                    verified=validate_supported_response(workspace(),verified)
                    if verified['status'] in {'SUPPORTED','QUERY_CONTEXT_CONFLICT'}:
                        return {**answer,**verified,'citations':verified.get('citations') or answer.get('citations',[]),
                                'numeric_verification':verified,'warnings':verified.get('warnings',[]),
                                'retrieved_excerpt_verification':'SOURCE_TEXT_UNREVIEWED',
                                'search_profile':profile,'generation':result.get('generation')}
                    return {**answer,'numeric_verification':verified,'reason':verified.get('reason'),
                            'verification_status':verified.get('verification_status'),'related_evidence':answer.get('citations',[]),
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


def sec_backend():
    from app.research_qa.backend import ResearchBackend
    from app.product.local_config import sec_roots
    from app.product.sec_library import active
    root=str(active.get().root) if active.get() is not None else sec_roots()['TOPIC3_RESEARCH_ROOT']
    if not root:raise ValueError('SEC_QA_NOT_CONFIGURED')
    from app.product.sec_product_snapshot import snapshot
    return ResearchBackend(root,snapshot_factory=snapshot)


class SecQA(BaseModel):
    model_config=ConfigDict(extra='forbid')
    question:str=Field(min_length=2,max_length=2000)
    operation:Literal['EXTRACT','ABS_CHANGE','PERCENT_CHANGE']='EXTRACT'
    ticker:str=Field(default='',max_length=20)
    filing_ids:list[str]=Field(default_factory=list,max_length=20)


@router.post('/sec/analysis')
@sec_scoped
def sec_analysis(payload:SecQA):
    def public(value):
        if isinstance(value,dict):return {key:public(item) for key,item in value.items() if (not key.endswith('_path') or key=='structural_path') and key not in {'root','token'}}
        if isinstance(value,list):return [public(item) for item in value]
        if isinstance(value,str) and (len(value)>2 and value[1:3] in {':\\',':/'}):return '[local path omitted]'
        return value
    try:
        from app.product.sec_multi_qa import answer as verified_answer
        from app.product.sec_viewer import server_key
        verified = verified_answer(sec_index(),payload.question,payload.ticker,server_key(workspace().root),payload.operation)
        if verified is not None and (payload.filing_ids or verified['status']=='SUPPORTED'):
            return public(verified)
        filings=sec_index().catalog()['filings']
        filters={'filing_ids':[f['filing_id'] for f in filings]}
        if payload.ticker:
            selected=[f for f in filings if f['ticker']==payload.ticker.upper()]
            if len(selected)!=1:raise ValueError('SEC_COMPANY_SCOPE_AMBIGUOUS')
            filters={'cik':selected[0]['cik'],'filing_ids':[selected[0]['filing_id']]}
        raw=sec_backend().query(payload.question,filters,'B',payload.operation,5,False,'automatic_real')
        answer=raw.get('answer',{});citations=[]
        for cell in answer.get('source_cells',[]):
            source=next((f for f in filings if f['filing_id']==cell['filing_id']),{})
            if not source:raise ValueError('SEC_CITATION_FILING_NOT_REGISTERED')
            from app.product.sec_viewer import reference,server_key
            citations.append({'source_kind':'SEC','chunk_id':cell['parent_id'],'issuer':source.get('issuer',cell['cik']),
                'source_reference':reference(sec_index(),cell['parent_id'],server_key(workspace().root),cell),
                'filing_id':cell['filing_id'],'accession':cell['accession'],'form':source['form'],
                'report_period':cell['period_end'],'source_url':cell['source_url'],'source_sha256':cell['raw_sha256'],
                'text':f"{cell['row_label']}: {cell['raw_value']} ({cell['display_unit_header']}) · {cell['period_end']}",
                'row_label':cell['row_label'],'column_label':' / '.join(cell['header_path']),
                'verification':'VERIFIED_SOURCE_CELL','unit':cell['unit'],
                'source_location':{'structural_path':cell['structural_path'],'table_id':cell['table_id'],'row_index':cell['row'],'column_index':cell['column']}})
        from app.product.answer_composer_v2 import display
        values=[str(v) for v in answer.get('result_values',[])]
        direct='Chưa đủ bằng chứng để trả lời chỉ tiêu/kỳ đang hỏi.'
        if answer.get('status')=='SUPPORTED' and values:
            labels='; '.join(dict.fromkeys(c['row_label']+' · '+c['period_end'] for c in answer.get('source_cells',[])))
            direct=labels+': '+', '.join(display(v)+' '+str(answer.get('result_unit') or '') for v in values)+'. '+''.join('['+str(i)+']' for i in range(1,len(citations)+1))
        from app.product.sec_answer_contract import annotate
        return public(annotate(payload.question,{'status':answer.get('status','INSUFFICIENT_EVIDENCE'),
            'answer':direct,
            'values':[str(v) for v in answer.get('result_values',[])],'unit':answer.get('result_unit'),
            'formula':answer.get('formula'),'operation':answer.get('operation'),'reason':', '.join(answer.get('reasons',[])),
            'citations':citations,'source_cells':answer.get('source_cells',[]),'generation':raw.get('generation')}))
    except Exception as exc:raise HTTPException(409,detail={'code':_error(exc)}) from None

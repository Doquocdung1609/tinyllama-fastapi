"""P6 opt-in automatic discovery of authenticated real SEC table cells.

This policy is exploratory and distinct from every frozen D3/D5 ranking arm.
It refines only missing typed column evidence after D1 has fixed issuer/filing
scope; it never changes D1's status or accepts a client-provided source ID.
"""
from time import perf_counter
from typing import Literal
import re
from pydantic import BaseModel,ConfigDict,Field
from app.financial_ingestion.schemas import FinancialChunk
from app.financial_query import resolve_financial_query
from app.financial_query.contracts import Status
from app.research_qa.real_cells import RealCellRequestV1,answer_from_verified_real_cells
from app.table_evidence.real_source import RealCellObservationV1,verified_real_cells

POLICY='p6-bm25-verified-cell-expansion/v1'
INITIAL_BUDGET=5
CANDIDATE_BUDGET=64
MAX_EXACT_ROWS=12


class ColumnRefinementV1(BaseModel):
    model_config=ConfigDict(extra='forbid',frozen=True)
    contract_version:Literal['p6-authenticated-column-refinement/v1']='p6-authenticated-column-refinement/v1'
    metadata_scope_status:Literal['RESOLVED','NEEDS_CLARIFICATION']
    refinement_status:Literal['VERIFIED','NO_VERIFIED_CELL','AMBIGUOUS_VERIFIED_CELLS']
    generation:str
    manifest_hash:str
    cik:str
    eligible_filing_ids:tuple[str,...]
    requested_period_ends:tuple[str,...]
    candidate_budget:Literal[64]=64
    selected_parent_id:str|None=None
    original_bm25_rank:int|None=None
    cells:tuple[RealCellObservationV1,...]=()
    reasons:tuple[str,...]=()


def _response(status,reason,*,resolution=None,timings=None,trace=()):
    scope=resolution.resolved_scope if resolution else None
    return {'interface_version':'financial-research-api/v1','automatic_workflow_version':POLICY,
        'source_type':'OFFICIAL_SEC_RESEARCH_DIAGNOSTIC','retrieval_status':status,
        'effective_mode':'NONE','generation':scope.generation_id if scope else None,
        'manifest_hash':scope.manifest_hash if scope else None,'failure_code':reason,
        'trace':tuple(trace),'timings_ms':timings or {},'evidence':[],
        'answer':{'status':{'NEEDS_CLARIFICATION':'NEEDS_CLARIFICATION','INVALID_INPUT':'INVALID_INPUT',
                            'UNSUPPORTED':'UNSUPPORTED_OPERATION'}.get(status,'INSUFFICIENT_EVIDENCE'),
                  'reasons':[reason],'result_values':[],'result_unit':None},
        'column_refinement':None,
        'limitations':['P6 opt-in source-authenticated cell policy; no general answer certification.']}


def _with_refinement(response,scope,ends,status,reason):
    response['column_refinement']=ColumnRefinementV1(metadata_scope_status=scope.status.value,
        refinement_status=status,generation=scope.generation_id,manifest_hash=scope.manifest_hash,
        cik=scope.cik,eligible_filing_ids=tuple(scope.eligible_filing_ids),
        requested_period_ends=ends,reasons=(reason,)).model_dump(mode='json')
    return response


def automatic_real_query(snapshot,question,filters,operation='EXTRACT',use_llm=False,arm='B',catalog=None):
    """Return a complete research response without guessing issuer, filing or period."""
    t0=perf_counter();trace=[];timings={}
    catalog=catalog or snapshot.catalog
    resolution=resolve_financial_query(question,filters,catalog)
    timings['question_scope']=(perf_counter()-t0)*1000
    scope=resolution.resolved_scope;intent=resolution.query_intent
    if use_llm:return _response('BLOCKED','LLM_NOT_AUTHORIZED_FOR_SOURCE_SELECTION',resolution=resolution,timings=timings)
    if arm!='B':return _response('BLOCKED','P6_REQUIRES_VALID_BM25_CHANNEL',resolution=resolution,timings=timings)
    if scope is None:
        return _response(resolution.status.value,'D1_'+resolution.status.value,resolution=resolution,timings=timings)
    if resolution.status==Status.NEEDS_CLARIFICATION:
        allowed={'COLUMN_PERIOD_METADATA_INCOMPLETE','EXPLICIT_FILING_CONSTRAINTS_APPLIED'}
        if 'COLUMN_PERIOD_METADATA_INCOMPLETE' not in scope.resolution_reasons or not set(scope.resolution_reasons)<=allowed:
            return _response('NEEDS_CLARIFICATION','D1_UNRESOLVED_NONCOLUMN_SCOPE',resolution=resolution,timings=timings)
        trace.append('D1_COLUMN_METADATA_UNCERTAIN_REQUIRES_SOURCE_PROOF')
    elif resolution.status!=Status.RESOLVED:
        return _response(resolution.status.value,'D1_'+resolution.status.value,resolution=resolution,timings=timings)
    lowered=question.casefold()
    if re.search(r'\b(?:percentage|percent)[\s\-\u2010-\u2015]*points?\b',lowered):
        return _response('UNSUPPORTED','PERCENTAGE_POINTS_NOT_SUPPORTED',resolution=resolution,timings=timings)
    if re.search(r'\b(?:fair\s+value|carrying\s+(?:amount|value))\b',lowered):
        return _response('NEEDS_CLARIFICATION','NET_SALES_VALUATION_CONTEXT_UNSUPPORTED',resolution=resolution,timings=timings)
    if scope.generation_id!=snapshot.freeze['generation'] or scope.manifest_hash!=snapshot.freeze['manifest_hash']:
        return _response('BLOCKED','PINNED_GENERATION_OR_MANIFEST_MISMATCH',resolution=resolution,timings=timings)
    if len(scope.eligible_filing_ids)!=1 or any(f.form.endswith('/A') for f in catalog.filings if f.filing_id in scope.eligible_filing_ids):
        return _response('NEEDS_CLARIFICATION','SINGLE_UNAMENDED_FILING_REQUIRED',resolution=resolution,timings=timings)
    exact_metrics={m.canonical.casefold() for m in intent.metric_mentions if m.relationship=='EXACT'}
    allowed_units={'USD','MILLIONS'}|({'PERCENT'} if operation=='PERCENT_CHANGE' or intent.comparison_operation=='RELATIVE_CHANGE' else set())
    if exact_metrics!={'net sales'} or intent.numerical_constraints or any(u not in allowed_units for u in intent.unit_mentions):
        return _response('NEEDS_CLARIFICATION','EXACT_SUPPORTED_METRIC_AND_UNIT_REQUIRED',resolution=resolution,timings=timings)
    periods=scope.requested_periods
    if len(periods) not in {1,2} or any(p.kind!='DURATION' or p.months!=3 or p.end is None for p in periods):
        return _response('NEEDS_CLARIFICATION','EXPLICIT_QUARTER_ENDS_REQUIRED',resolution=resolution,timings=timings)
    ends=tuple(sorted(str(p.end) for p in periods))
    if len(set(ends))!=len(ends):
        return _response('NEEDS_CLARIFICATION','DISTINCT_PERIODS_REQUIRED',resolution=resolution,timings=timings)
    if operation=='EXTRACT' and len(ends)==2:
        operation={'COMPARE':'COMPARE','DIFFERENCE':'ABS_CHANGE','RELATIVE_CHANGE':'PERCENT_CHANGE'}.get(intent.comparison_operation,'EXTRACT')
    if operation not in {'EXTRACT','COMPARE','ABS_CHANGE','PERCENT_CHANGE'} or len(ends)!=(1 if operation=='EXTRACT' else 2):
        return _response('NEEDS_CLARIFICATION','QUESTION_OPERATION_PERIOD_CONFLICT',resolution=resolution,timings=timings)
    expected_operation={'DIFFERENCE':'ABS_CHANGE','RELATIVE_CHANGE':'PERCENT_CHANGE'}.get(intent.comparison_operation)
    if expected_operation and operation!=expected_operation:
        return _response('NEEDS_CLARIFICATION','QUESTION_OPERATION_FILTER_CONFLICT',resolution=resolution,timings=timings)
    if operation in {'ABS_CHANGE','PERCENT_CHANGE'} and str(periods[0].end)>=str(periods[1].end):
        return _response('NEEDS_CLARIFICATION','CHANGE_DIRECTION_REQUIRES_OLD_THEN_NEW',resolution=resolution,timings=timings)
    if len(ends)==1 and intent.comparison_operation:
        return _response('NEEDS_CLARIFICATION','QUESTION_COMPARISON_PERIOD_MISSING',resolution=resolution,timings=timings)
    t=perf_counter()
    with snapshot.pin(scope):
        candidates=snapshot.search(question,scope,'B',CANDIDATE_BUDGET,30)
    timings['candidate_retrieval']=(perf_counter()-t)*1000
    trace.extend((POLICY,f'INITIAL_BM25_BUDGET_{INITIAL_BUDGET}',f'EXPANDED_BM25_BUDGET_{CANDIDATE_BUDGET}'))
    exact=[]
    for rank,candidate in enumerate(candidates,1):
        parent=FinancialChunk.model_validate_json(candidate.parent_json)
        if parent.metadata.get('row_label','').strip().casefold()=='net sales':
            if parent.metadata.get('cik')!=scope.cik or parent.filing_id not in scope.eligible_filing_ids:
                raise ValueError('P6_CANDIDATE_ESCAPED_D1_SCOPE')
            exact.append((rank,parent))
    if len(exact)>MAX_EXACT_ROWS:
        return _response('BLOCKED','EXACT_ROW_DERIVATION_BUDGET',resolution=resolution,timings=timings,trace=trace)
    t=perf_counter();eligible=[]
    for rank,parent in exact:
        cells=verified_real_cells(snapshot,parent.chunk_id)
        selected=tuple(c for c in cells if c.cik==scope.cik and c.filing_id in scope.eligible_filing_ids
            and c.period_kind=='DURATION' and c.period_months==3 and c.period_end in ends
            and c.row_label.strip().casefold()=='net sales')
        if len(selected)==len(ends) and {c.period_end for c in selected}==set(ends):
            eligible.append((rank,parent,selected))
    timings['source_authentication_and_cell_derivation']=(perf_counter()-t)*1000
    if not eligible:
        reason='NO_VERIFIED_CELL_WITHIN_CANDIDATE_BUDGET'
        return _with_refinement(_response('NO_ELIGIBLE_EVIDENCE',reason,resolution=resolution,timings=timings,trace=trace),
                                scope,ends,'NO_VERIFIED_CELL',reason)
    if len(eligible)!=1:
        reason='MULTIPLE_VERIFIED_PARENT_ROWS'
        return _with_refinement(_response('NEEDS_CLARIFICATION',reason,resolution=resolution,timings=timings,trace=trace),
                                scope,ends,'AMBIGUOUS_VERIFIED_CELLS',reason)
    rank,parent,cells=eligible[0]
    filing=next(f for f in catalog.filings if f.filing_id==parent.filing_id)
    request=RealCellRequestV1(parent_id=parent.chunk_id,cik=scope.cik,accession=filing.accession,
        table_id=cells[0].table_id,period_ends=ends,period_months=3,operation=operation)
    t=perf_counter();answer=answer_from_verified_real_cells(snapshot,request)
    timings['d4_typed_numeric_verification']=(perf_counter()-t)*1000
    timings['total']=(perf_counter()-t0)*1000
    if answer.status!='SUPPORTED':
        return _response('BLOCKED',answer.reason or 'NUMERIC_VERIFICATION_FAILED',resolution=resolution,timings=timings,trace=trace)
    refinement=ColumnRefinementV1(metadata_scope_status=resolution.status.value,refinement_status='VERIFIED',
        generation=scope.generation_id,manifest_hash=scope.manifest_hash,cik=scope.cik,
        eligible_filing_ids=tuple(scope.eligible_filing_ids),requested_period_ends=ends,
        selected_parent_id=parent.chunk_id,original_bm25_rank=rank,cells=tuple(answer.operands),
        reasons=tuple(scope.resolution_reasons))
    issuer=next(i.company_name for i in catalog.issuers if i.cik==scope.cik)
    citations=[{'parent_id':c.parent_id,'payload_hash':c.parent_payload_hash,'filing_id':c.filing_id,
        'issuer':issuer,'form':filing.form,'report_date':str(filing.report_end) if filing.report_end else None,
        'financial_period':{'kind':c.period_kind,'start':c.period_start,'end':c.period_end,'months':c.period_months},
        'source_url':c.source_url,'locator':{'structural_path':c.structural_path,'table_id':c.table_id,
                                          'row_index':c.row,'column_index':c.column},
        'row_label':c.row_label,'extraction_status':'PARTIAL_EXTRACTION' if c.warnings else 'OK',
        'verification_status':c.source_status,'content':f'{c.row_label}: {c.raw_value} ({c.display_unit_header})',
        'warnings':list(c.warnings)} for c in answer.operands]
    trace.extend((f'SELECTED_ORIGINAL_BM25_RANK_{rank}',f'SELECTED_PARENT_{parent.chunk_id}',
                  'D1_METADATA_STATUS_RETAINED_'+resolution.status.value,'D4_TYPED_DECIMAL_CALCULATE'))
    return {'interface_version':'financial-research-api/v1','automatic_workflow_version':POLICY,
        'source_type':'OFFICIAL_SEC_RESEARCH_DIAGNOSTIC','retrieval_status':'OK',
        'effective_mode':'B_P6_VERIFIED_CELL_EXPANSION','generation':scope.generation_id,
        'manifest_hash':scope.manifest_hash,'failure_code':None,'trace':tuple(trace),'timings_ms':timings,
        'evidence':citations,'answer':{'status':'SUPPORTED','reasons':[],
            'result_values':[str(v) for v in answer.result_values],'result_unit':answer.result_unit,
            'operation':answer.operation,'formula':answer.formula,'source_cells':[c.model_dump(mode='json') for c in answer.operands]},
        'column_refinement':refinement.model_dump(mode='json'),
        'limitations':['Authenticated source-cell result; not general financial answer certification.',
                       'D1 metadata scope remains '+resolution.status.value+'.']}

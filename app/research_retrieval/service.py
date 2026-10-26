"""Opt-in D1-scoped seven-arm D3 research orchestrator. No production wiring."""
from time import perf_counter
from app.financial_query import resolve_financial_query
from app.financial_query.contracts import IntentCategory as I
from app.research_retrieval.contracts import PolicyV1,RetrievalResultV1,CandidateV1,ChannelUnavailable
from app.research_retrieval.ranking import deduplicate,fuse,single,table_rerank


def retrieve_financial_query(question,explicit_filters,corpus_catalog,adapter,arm='B',policy=None,
                             evidence_lookup=None,allow_operational_degraded=False):
    policy=policy or PolicyV1();trace=[];timings=[];start=perf_counter()
    if arm not in {'B','D','F','R','T','A','AT'}:
        raise ValueError('UNKNOWN_RESEARCH_ARM')
    resolution=resolve_financial_query(question,explicit_filters,corpus_catalog)
    timings.append(('scope',(perf_counter()-start)*1000))
    if resolution.status.value!='RESOLVED':
        return RetrievalResultV1(requested_arm=arm,effective_mode='NONE',status=resolution.status.value,
            scope_json=resolution.model_dump_json(),trace=('D1_SCOPE_NOT_RESOLVED',),timings_ms=tuple(timings))
    scope=resolution.resolved_scope;intent=resolution.query_intent
    if not scope.generation_id:
        return RetrievalResultV1(requested_arm=arm,effective_mode='NONE',status='BLOCKED',failure_code='GENERATION_IDENTITY_REQUIRED')
    base=dict(requested_arm=arm,generation=scope.generation_id,manifest_hash=scope.manifest_hash,scope_json=resolution.model_dump_json())
    b=[];d=[];effective=arm
    def channel(name):
        before=perf_counter();items=adapter.search(question,scope,name,policy.candidate_limit,policy.channel_deadline_seconds)
        elapsed=(perf_counter()-before)*1000;timings.append((name,elapsed))
        if elapsed>policy.channel_deadline_seconds*1000:raise TimeoutError('CHANNEL_DEADLINE_EXCEEDED')
        if len(items)>policy.candidate_limit:raise ValueError('CHANNEL_CANDIDATE_BUDGET')
        candidates=[CandidateV1.model_validate(c.model_dump()) for c in items]
        for c in candidates:
            if c.channel!=name or c.generation!=scope.generation_id or c.manifest_hash!=scope.manifest_hash or c.cik!=scope.cik or c.filing_id not in scope.eligible_filing_ids:
                raise ValueError('CHANNEL_SCOPE_OR_GENERATION_MISMATCH')
        return deduplicate(candidates)
    try:
        # The adapter pins cleanup/publication across all channel calls.
        with adapter.pin(scope):
            category=intent.category
            exact=category in {I.EXACT_FINANCIAL_VALUE,I.FINANCIAL_TABLE}
            route=arm
            if arm=='R':
                route='F' if category in {I.PERIOD_COMPARISON,I.CROSS_SECTION} else 'D' if category in {I.SEMANTIC_PARAPHRASE,I.FINANCIAL_TERMINOLOGY} else 'B'
                trace.append('R_ROUTE_'+route)
            if route in {'B','F','T','A','AT'}:b=channel('B')
            if route in {'A','AT'} and exact and sum(c.score>0 for c in b)>=5:
                ranks=single(b);effective='B_SUFFICIENT_COUNT_HEURISTIC';trace.append('FIVE_POSITIVE_HITS_IS_NOT_RELEVANCE_PROOF')
            elif route=='B':ranks=single(b);effective='B'
            else:
                try:d=channel('D')
                except (ChannelUnavailable,TimeoutError,ConnectionError):
                    if not allow_operational_degraded or route=='D':raise
                    if not b:b=channel('B')
                    ranks=single(b);effective='BM25_DEGRADED';trace.append('DENSE_FAILED_OPERATIONAL_FALLBACK_NOT_SCIENTIFIC_SUCCESS')
                else:
                    if route=='D':ranks=single(d);effective='D'
                    else:
                        weights=(2,1) if route in {'A','AT'} and category in {I.EXACT_FINANCIAL_VALUE,I.FINANCIAL_TABLE,I.PERIOD_COMPARISON} else (1,1)
                        ranks=fuse(b,d,weights=weights,k=policy.rrf_k);effective='F' if weights==(1,1) else 'WEIGHTED_RRF_2_1'
                        trace.append('RRF_WEIGHTS_'+str(weights))
            if arm in {'T','AT'}:
                if evidence_lookup is None:raise RuntimeError('D2_EVIDENCE_LOOKUP_UNAVAILABLE')
                ranks=table_rerank(ranks,intent,evidence_lookup);trace.append('FIXED_TABLE_BONUSES_TOP20')
            if scope.requested_periods:
                if evidence_lookup is None:raise RuntimeError('D2_CELL_PERIOD_SCOPE_UNVERIFIABLE')
                wanted={(p.kind,p.year,p.quarter,str(p.end) if p.end else None,p.months) for p in scope.requested_periods}
                eligible=[]
                for hit in ranks[:20]:
                    e=evidence_lookup(hit.candidate)
                    if e is None:continue
                    if (e.parent_payload_hash,e.source_generation,e.manifest_hash)!=(hit.candidate.payload_hash,scope.generation_id,scope.manifest_hash):
                        raise ValueError('D2_EVIDENCE_IDENTITY_MISMATCH')
                    if e.parent_provenance!='MATCHED_UPSTREAM_BINDING':raise ValueError('D2_SOURCE_UNAUTHENTICATED')
                    actual={(c.period.kind,c.period.year,c.period.quarter,c.period.end,c.period.months) for c in e.cells if c.period and c.status=='VERIFIED_CONTEXT'}
                    if actual&wanted:eligible.append(hit)
                ranks=eligible;trace.append('CELL_PERIOD_SCOPE_FILTER_TOP20')
                if not ranks:raise RuntimeError('NO_VERIFIED_CELL_PERIOD_CANDIDATES')
        timings.append(('total',(perf_counter()-start)*1000))
        return RetrievalResultV1(**base,status='OK',effective_mode=effective,results=tuple(ranks[:policy.top_k]),
            b_candidates=tuple(c.chunk_id for c in b),d_candidates=tuple(c.chunk_id for c in d),trace=tuple(trace),timings_ms=tuple(timings))
    except (ValueError,RuntimeError,TimeoutError,ConnectionError) as exc:
        code=str(exc) if str(exc).isupper() and str(exc).replace('_','').isalnum() else 'RESEARCH_RETRIEVAL_FAILED'
        return RetrievalResultV1(**base,status='BLOCKED',effective_mode='NONE',failure_code=code,
            b_candidates=tuple(c.chunk_id for c in b),d_candidates=tuple(c.chunk_id for c in d),trace=tuple(trace),timings_ms=tuple(timings))

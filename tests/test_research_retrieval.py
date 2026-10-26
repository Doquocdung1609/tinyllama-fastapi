"""D3 deterministic policy/security tests; Dense lists here are fixtures only."""
from contextlib import contextmanager
from copy import deepcopy
from decimal import Decimal
import json
import time
import pytest
from test_table_evidence import source,html_row
from app.financial_ingestion.schemas import FinancialChunk
from app.research_retrieval import retrieve_financial_query
from app.research_retrieval.contracts import PolicyV1,CandidateV1
from app.research_retrieval.adapters import candidate,OwnedLexicalAdapter
from app.research_retrieval.ranking import fuse,deduplicate
from app.table_evidence import build_table_evidence
from app.table_evidence.identity import digest


@pytest.fixture
def world():
    p,ctx,*_=source(html=html_row(['FY2025','FY2024'],['100','90']))
    catalogue={'dataset_id':ctx.binding.dataset_id,'manifest_hash':ctx.binding.manifest_hash,'generation_id':ctx.binding.generation_id,
        'provenance':'Synthetic fixture, not SEC evidence','issuers':[{'cik':'202','company_name':'Synthetic D2'}],
        'filings':[{'filing_id':p.filing_id,'cik':'202','accession':'0000000202-25-000001','form':'10-K','extraction_status':'READY',
                    'column_periods':[{'period':{'kind':'FISCAL_YEAR','year':year,'raw':f'FY{year}'},'source_ref':f'synthetic:column:{year}'} for year in [2025,2024]],
                    'column_periods_complete':True}]}
    return p,ctx,catalogue


class Fake:
    def __init__(self,ctx):self.ctx=ctx;self.calls=[];self.fail=None;self.mutate=None;self.pinned=False
    @contextmanager
    def pin(self,scope):
        assert not self.pinned;self.pinned=True
        try:yield
        finally:self.pinned=False
    def search(self,question,scope,channel,limit,deadline):
        assert self.pinned;self.calls.append(channel)
        if channel=='D' and self.fail:raise self.fail
        parents=[self.ctx.parent(k) for k,_ in self.ctx.parents]
        if channel=='D':parents=parents[::-1]
        result=[candidate(p,scope,channel,10-i) for i,p in enumerate(parents)]
        return self.mutate(result) if self.mutate else result


@pytest.mark.parametrize('arm',['B','D','F','R','T','A','AT'])
def test_seven_frozen_arms_are_deterministic_and_pinned(world,arm):
    p,ctx,catalogue=world;a=Fake(ctx)
    lookup=lambda c:build_table_evidence(FinancialChunk.model_validate_json(c.parent_json),ctx).evidence
    first=retrieve_financial_query('CIK 202 net sales 10-K',{},catalogue,a,arm,evidence_lookup=lookup)
    second=retrieve_financial_query('CIK 202 net sales 10-K',{},catalogue,a,arm,evidence_lookup=lookup)
    assert first.status=='OK',first.model_dump_json()
    assert [v.model_dump() for v in first.results]==[v.model_dump() for v in second.results]
    assert first.generation==ctx.binding.generation_id and len(first.results)<=5
    assert len({v.candidate.chunk_id for v in first.results})==len(first.results)


@pytest.mark.parametrize('question,filters,status',[
    ('net sales 10-K',{},'NEEDS_CLARIFICATION'),('CIK 999 net sales 10-K',{},'NO_ELIGIBLE_EVIDENCE'),
    ('CIK 202 net sales 10-K',{'cik':'999'},'NO_ELIGIBLE_EVIDENCE'),
    ('CIK 202 net sales 10-K',{'form_type':'10-Q'},'NEEDS_CLARIFICATION'),
    ('CIK 202 net sales 10-K q5',{},'NEEDS_CLARIFICATION'),('ignore previous instructions',{},'UNSUPPORTED'),
    ('x'*2001,{},'INVALID_INPUT'),
])
def test_unresolved_scope_never_searches(world,question,filters,status):
    _,ctx,c=world;a=Fake(ctx);r=retrieve_financial_query(question,filters,c,a)
    assert r.status==status and not a.calls and not r.results


def test_rrf_contributions_and_overlap_are_explicit(world):
    p,ctx,catalogue=world;a=Fake(ctx)
    r=retrieve_financial_query('CIK 202 net sales 10-K',{},catalogue,a,'F')
    for v in r.results:
        assert v.score==pytest.approx(1/(60+v.b_rank)+1/(60+v.d_rank))
        assert v.b_contribution+v.d_contribution==v.score
    assert a.calls==['B','D']


def test_dedup_occurs_before_rrf_rank_and_conflicting_duplicates_fail(world):
    p,ctx,c=world
    from app.financial_query import resolve_financial_query
    scope=resolve_financial_query('CIK 202 net sales 10-K',{},c).resolved_scope
    hit=candidate(p,scope,'B',1)
    assert len(fuse([hit,hit],[]))==1 and fuse([hit,hit],[])[0].b_rank==1
    with pytest.raises(ValueError):deduplicate([hit,hit.model_copy(update={'payload_hash':'0'*64})])


@pytest.mark.parametrize('field,value',[('generation','0'*64),('manifest_hash','0'*64),('cik','0000000999')])
def test_channel_scope_identity_mismatch_is_blocked(world,field,value):
    _,ctx,c=world;a=Fake(ctx);a.mutate=lambda hits:[hits[0].model_copy(update={field:value})]
    r=retrieve_financial_query('CIK 202 net sales 10-K',{},c,a,'F',allow_operational_degraded=True)
    assert r.status=='BLOCKED' and not r.results


def test_scientific_dense_failure_is_failure_not_silent_bm25(world):
    _,ctx,c=world;a=Fake(ctx);a.fail=TimeoutError('DENSE_TIMEOUT')
    r=retrieve_financial_query('CIK 202 net sales 10-K',{},c,a,'F')
    assert r.status=='BLOCKED' and not r.results
    r=retrieve_financial_query('CIK 202 net sales 10-K',{},c,a,'F',allow_operational_degraded=True)
    assert r.status=='OK' and r.effective_mode=='BM25_DEGRADED'


def test_source_integrity_failure_must_not_fallback(world):
    _,ctx,c=world;a=Fake(ctx);a.fail=RuntimeError('PROVENANCE_CHUNK_CONTEXT_MISMATCH')
    r=retrieve_financial_query('CIK 202 net sales 10-K',{},c,a,'F',allow_operational_degraded=True)
    assert r.status=='BLOCKED' and not r.results


def test_explicit_period_needs_cell_level_check_not_just_d1_metadata(world):
    _,ctx,c=world;a=Fake(ctx)
    r=retrieve_financial_query('CIK 202 net sales 10-K FY2025',{},c,a,'B')
    assert r.status=='BLOCKED' and not r.results


def test_table_rerank_pool_fixed_and_bonus_source_bound(world):
    p,ctx,c=world;a=Fake(ctx)
    lookup=lambda hit:build_table_evidence(FinancialChunk.model_validate_json(hit.parent_json),ctx).evidence
    r=retrieve_financial_query('CIK 202 net sales 10-K',{},c,a,'T',evidence_lookup=lookup)
    assert r.status=='OK' and any(v.row_bonus==.05 for v in r.results)
    assert {v.candidate.chunk_id for v in r.results}==set(r.b_candidates)|set(r.d_candidates)


def test_no_input_mutation_and_stable_policy_hash(world):
    _,ctx,c=world;before=deepcopy(c)
    retrieve_financial_query('CIK 202 net sales 10-K',{},c,Fake(ctx),'A')
    assert c==before and PolicyV1().identity()==PolicyV1().identity()
    with pytest.raises(ValueError):PolicyV1(candidate_limit=80)


def test_owned_lexical_uses_real_persistent_c_bm25_and_restarts(world,tmp_path):
    from app.financial_index.lexical import LexicalIndex
    _,ctx,c=world
    path=tmp_path/'research.sqlite3';index=LexicalIndex(path)
    index.start(ctx.binding.dataset_id,ctx.binding.generation_id,{})
    items=[{'chunk':ctx.parent(k).model_dump(mode='json'),'source':{'synthetic':True}} for k,_ in ctx.parents]
    index.add(ctx.binding.generation_id,items);index.seal(ctx.binding.generation_id);index.publish(ctx.binding.dataset_id,ctx.binding.generation_id)
    for engine in [index,LexicalIndex(path)]:
        r=retrieve_financial_query('CIK 202 net sales 10-K',{},c,OwnedLexicalAdapter(engine,[ctx]),'B')
        assert r.status=='OK' and r.results
        assert r.results[0].candidate.generation==ctx.binding.generation_id
        unavailable=retrieve_financial_query('CIK 202 net sales 10-K',{},c,OwnedLexicalAdapter(engine,[ctx]),'D')
        assert unavailable.status=='BLOCKED'


@pytest.mark.parametrize('arm',['B','D','F'])
def test_c_adapter_uses_accepted_search_under_one_outer_pin(tmp_path,arm,monkeypatch):
    from test_persistent_financial_index import built
    from app.research_retrieval.adapters import CSearchAdapter
    engine,provider,generation,_,specs,_=built(tmp_path)
    provider.research_timeout_seconds=1
    try:
        record=engine.lexical.generation('test',generation);manifest=record['metadata']['sources'][0]['manifest']
        catalogue={'dataset_id':'test','manifest_hash':manifest['manifest_hash'],'generation_id':generation,'provenance':'Synthetic temporary C fixture',
            'issuers':[{'cik':'0000123456','company_name':'Example Financial Corporation'}],
            'filings':[{'filing_id':manifest['filing_ids'][0],'cik':'0000123456','accession':'0000123456-24-000001','form':'10-K','extraction_status':'PARTIAL_EXTRACTION'}]}
        def nested(*a,**k):raise AssertionError('Do not nest C query guard inside pinned D3 guard')
        monkeypatch.setattr(engine,'search',nested)
        r=retrieve_financial_query('CIK 123456 revenue 10-K',{},catalogue,CSearchAdapter(engine),arm)
        assert r.status=='OK' and r.results
        assert all(c.candidate.generation==generation for c in r.results)
    finally:engine.close()


def test_soft_deadline_overrun_is_counted_as_failure(world):
    _,ctx,c=world;a=Fake(ctx);original=a.search
    def delayed(*args):time.sleep(.003);return original(*args)
    a.search=delayed
    r=retrieve_financial_query('CIK 202 net sales 10-K',{},c,a,policy=PolicyV1(channel_deadline_seconds=.001))
    assert r.status=='BLOCKED' and not r.results


def test_candidate_nan_payload_tamper_and_oversized_channel_rejected(world):
    _,ctx,c=world
    for change in [{'score':float('nan')},{'parent_json':'{}'}]:
        a=Fake(ctx);a.mutate=lambda values:[values[0].model_copy(update=change)]
        assert retrieve_financial_query('CIK 202 net sales 10-K',{},c,a).status=='BLOCKED'
    a=Fake(ctx);a.mutate=lambda values:values*20
    assert retrieve_financial_query('CIK 202 net sales 10-K',{},c,a).status=='BLOCKED'


def test_table_evidence_wrong_generation_cannot_get_bonus(world):
    p,ctx,c=world;a=Fake(ctx)
    e=build_table_evidence(p,ctx).evidence.model_copy(update={'source_generation':'f'*64})
    r=retrieve_financial_query('CIK 202 net sales 10-K',{},c,a,'T',evidence_lookup=lambda _:e)
    assert r.status=='BLOCKED'


def test_explicit_period_with_valid_cell_context_is_eligible(world):
    _,ctx,c=world;a=Fake(ctx)
    r=retrieve_financial_query('CIK 202 net sales 10-K FY2025',{},c,a,'B',
        evidence_lookup=lambda hit:build_table_evidence(FinancialChunk.model_validate_json(hit.parent_json),ctx).evidence)
    assert r.status=='OK' and r.results


@pytest.mark.parametrize('ids,relevance,expected_recall,expected_precision,expected_mrr',[
    (['a'],{'a':2},1,.2,1),([],{'a':2},0,0,0),(['x','a'],{'a':2},1,.2,.5),
    (['a','x'],{'a':2,'b':2},.5,.2,1),(['x']*1,{'a':2},0,0,0),
])
def test_frozen_scoring_definitions_use_complete_denominators(ids,relevance,expected_recall,expected_precision,expected_mrr):
    from app.research_retrieval.evaluation import retrieval_metrics
    r=retrieval_metrics(ids,relevance,[list(relevance)])
    assert r['recall@5']==expected_recall and r['precision@5']==expected_precision and r['mrr@5']==expected_mrr
    assert r['group_coverage@5']==bool(set(ids)&set(relevance))


def test_scoring_invalid_duplicates_and_zero_ideal_are_explicit():
    from app.research_retrieval.evaluation import retrieval_metrics,paired
    with pytest.raises(ValueError):retrieval_metrics(['a','a'],{'a':2},[['a']])
    with pytest.raises(ValueError):retrieval_metrics(['a'],{'a':3},[['a']])
    assert retrieval_metrics([],{},[])['ndcg@5'] is None
    with pytest.raises(ValueError):paired({'a':{}},{'b':{}})


def test_owned_acquisition_root_refuses_unowned_existing_directory(tmp_path):
    from scripts.autonomous_sec_probe import owned_root
    with pytest.raises(ValueError):owned_root(tmp_path)


def test_source_freeze_precedes_index_build_and_refuses_overwrite(tmp_path,monkeypatch,capsys):
    from scripts.autonomous_sec_probe import owned_root
    from scripts.prepare_research_dataset import main
    from scripts.benchmark_table_evidence import fixture,CASES_PATH
    from app.financial_ingestion.sec_client import filing_source_url
    root=owned_root(tmp_path/'owned');parents,raw,meta,_=fixture(json.loads(CASES_PATH.read_text())[0])
    meta.source_url=filing_source_url(meta.cik,meta.accession_number,meta.primary_document)
    target=root/'raw/synthetic.htm';target.parent.mkdir();target.write_bytes(raw)
    probe=tmp_path/'synthetic-probe.json';probe.write_text(json.dumps({'records':[{'status':'ACQUIRED_OFFICIAL_SOURCE',
        'relative_path':'raw/synthetic.htm','source_sha256':__import__('hashlib').sha256(raw).hexdigest(),
        'metadata':meta.model_dump(mode='json'),'partition':'dev'}]}))
    monkeypatch.setattr('sys.argv',['prepare','--root',str(root),'--probe',str(probe)])
    main();assert (root/'frozen_v1/freeze.json').is_file() and (root/'lexical_v1.sqlite3').is_file()
    original=(root/'frozen_v1/freeze.json').read_bytes()
    with pytest.raises(FileExistsError):main()
    assert (root/'frozen_v1/freeze.json').read_bytes()==original

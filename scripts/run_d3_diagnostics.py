"""Dev/validation only; mechanically source-labelled exact-row diagnostics.

Cannot open heldout. Dense/table unavailability is reported as failure, not a
quality result or an exclusion. No adaptive finalist qualifies from this scope.
"""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import statistics
import time
from app.research_retrieval import retrieve_financial_query
from app.research_retrieval.contracts import PolicyV1
from app.research_retrieval.snapshot import FrozenResearchSnapshot
from app.research_retrieval.evaluation import retrieval_metrics,means,paired
from app.table_evidence.identity import canonical


def code_hashes():
    return {p.as_posix():sha256(p.read_bytes()).hexdigest() for p in sorted(Path('app/research_retrieval').glob('*.py'))}


def evaluate(snapshot,queries,arms):
    records=[]
    for query in queries:
        for arm in arms:
            start=time.perf_counter()
            r=retrieve_financial_query(query['question'],{},snapshot.catalog,snapshot,arm,policy=PolicyV1(top_k=10),evidence_lookup=snapshot.evidence_lookup)
            elapsed=(time.perf_counter()-start)*1000
            ids=[v.candidate.chunk_id for v in r.results]
            metrics=retrieval_metrics(ids,query['relevance'],query['evidence_groups'])
            records.append({'query_id':query['id'],'cik':query['cik'],'arm':arm,'status':r.status,'effective_mode':r.effective_mode,
                'failure_code':r.failure_code,'latency_ms':elapsed,'ranks':[
                    {'id':v.candidate.chunk_id,'rank':v.rank,'score':v.score,'payload_hash':v.candidate.payload_hash,
                     'filing_id':v.candidate.filing_id,'b_rank':v.b_rank,'d_rank':v.d_rank,'b_contribution':v.b_contribution,
                     'd_contribution':v.d_contribution,'row_bonus':v.row_bonus,'role_bonus':v.role_bonus,
                     'source_locator':json.loads(v.candidate.parent_json)['source_location']} for v in r.results],
                'b_pool':r.b_candidates,'d_pool':r.d_candidates,'trace':r.trace,'metrics_failure_inclusive':metrics,
                'source_provenance':'C_VERIFIED_SOURCE' if r.results else 'NO_RETURNED_EVIDENCE',
                'wrong_issuer_count':sum(v.candidate.cik!=query['cik'] for v in r.results),'returned_count':len(r.results),
                'wrong_period_rate':None,'wrong_period_reason':'No explicit observation-period queries in mechanical exact-row set'})
    summaries={}
    for arm in arms:
        rows=[r for r in records if r['arm']==arm];successful=[r for r in rows if r['status']=='OK']
        summaries[arm]={'query_count':len(rows),'success_count':len(successful),'failure_rate':1-len(successful)/len(rows) if rows else None,
            'failure_inclusive_metrics':means([r['metrics_failure_inclusive'] for r in rows]),
            'successful_query_metrics':means([r['metrics_failure_inclusive'] for r in successful]),
            'quality_comparison_eligible':arm=='B','latency_p50_ms':statistics.median([r['latency_ms'] for r in rows]) if rows else None,
            'latency_p95_ms':sorted(r['latency_ms'] for r in rows)[max(0,__import__('math').ceil(.95*len(rows))-1)] if rows else None}
    comparisons={}
    for a,b in [('B','R'),('B','A'),('F','T'),('A','AT')]:
        if a in arms and b in arms:
            left={r['query_id']:r['metrics_failure_inclusive'] for r in records if r['arm']==a}
            right={r['query_id']:r['metrics_failure_inclusive'] for r in records if r['arm']==b}
            comparisons[b+'-'+a]=paired(left,right)
    return {'records':records,'summaries':summaries,'paired_failure_inclusive_differences':comparisons}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True);p.add_argument('--freeze-protocol',action='store_true');args=p.parse_args()
    snapshot=FrozenResearchSnapshot(args.root);root=snapshot.root
    protocol=root/'frozen_v1/evaluation_protocol_v1.json'
    if args.freeze_protocol:
        with protocol.open('x',encoding='utf-8') as f:json.dump({'schema_version':'topic3-evaluation-protocol/v1','code_sha256':code_hashes(),
            'policy_hash':PolicyV1(top_k=10).identity(),'ranking_not_started':True,'heldout_finalists':['B','D','F'],
            'selected_adaptive':None,'why_no_finalist':'Required B/D/F availability, paraphrase strata and D2 real context not satisfied; no tuning authorized on consumed holdout.'},f,indent=2)
        print(json.dumps({'protocol_sha256':sha256(protocol.read_bytes()).hexdigest(),'ranking_executed':False}));return
    config=json.loads(protocol.read_text())
    if code_hashes()!=config['code_sha256']:raise ValueError('EVALUATION_CODE_CHANGED_AFTER_FREEZE')
    queries=[]
    for split in ['dev','validation']:
        data=(root/'frozen_v1'/f'{split}_queries.json').read_bytes()
        if sha256(data).hexdigest()!=snapshot.freeze['query_files'][split]['sha256']:raise ValueError('QUERY_FREEZE_CHANGED')
        queries.extend(json.loads(data))
    result=evaluate(snapshot,queries,snapshot.freeze['arms'])
    print(json.dumps({'schema_version':'topic3-d3-diagnostic/v1','freeze':snapshot.freeze,'protocol_sha256':sha256(protocol.read_bytes()).hexdigest(),
        'partitions_opened':['dev','validation'],'heldout_opened':False,'human_adjudication':False,
        'selection_status':'NO_ELIGIBLE_ADAPTIVE_FINALIST','source_grounded_full_comparison':'BLOCKED',
        'results':result,'limits':['Only automatically labelled exact-row source diagnostics, not a general financial retrieval benchmark.',
          'Failure-inclusive zeros for unavailable channels must not be read as Dense-model quality.','No neural model or new vectors used.']},indent=2))


if __name__=='__main__':main()

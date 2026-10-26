"""One-shot frozen mechanical heldout diagnostic, with fail-closed preflight."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import statistics
from app.research_retrieval.contracts import PolicyV1
from app.research_retrieval.snapshot import FrozenResearchSnapshot
from scripts.run_d3_diagnostics import code_hashes,evaluate

ARMS=('B','D','F')
D4_FILES=tuple(sorted(Path('app/research_qa').glob('*.py')))+(Path('app/research_api.py'),)

def digest_file(path):return sha256(Path(path).read_bytes()).hexdigest()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--preregister',action='store_true')
    args=parser.parse_args()
    snapshot=FrozenResearchSnapshot(args.root);root=snapshot.root
    frozen=root/'frozen_v1';protocol=frozen/'evaluation_protocol_v1.json'
    config=json.loads(protocol.read_text())
    if code_hashes()!=config['code_sha256']:raise ValueError('D3_SCORING_CODE_CHANGED')
    if config['policy_hash']!=PolicyV1(top_k=10).identity() or config['selected_adaptive'] is not None:raise ValueError('FROZEN_POLICY_CHANGED')
    if snapshot.freeze['selected_finalist'] is not None:raise ValueError('ADAPTIVE_FINALIST_CHANGED')
    record_path=frozen/'d5_preregistration_v1.json'
    record={'identity':'d5-heldout-diagnostic/v1','source_manifest':snapshot.freeze['manifest_hash'],
        'generation':snapshot.freeze['generation'],'heldout_query_sha256':snapshot.freeze['query_files']['heldout']['sha256'],
        'protocol_sha256':digest_file(protocol),'d3_code_sha256':code_hashes(),
        'd4_code_sha256':{p.as_posix():digest_file(p) for p in D4_FILES},
        'runner_sha256':digest_file(__file__),'arms':list(ARMS),'selected_adaptive':None,
        'qa_configuration':'deterministic source-bound verifier only; no real SEC numeric QA due D2 size cap',
        'metric_contract':'D3 v1 Recall5/10, Precision5, MRR5, nDCG5, group coverage; failures included and separated',
        'statistical_plan':'report paired B-D/B-F failure-inclusive differences as availability diagnostics; one HD issuer cluster means cluster CI not estimable',
        'human_annotators':0,'no_heldout_tuning':True}
    if args.preregister:
        with record_path.open('x',encoding='utf-8') as out:json.dump(record,out,indent=2)
        print(json.dumps({'prereg_sha256':digest_file(record_path),'heldout_opened':False}));return
    if json.loads(record_path.read_text())!=record:raise ValueError('D5_PREREGISTRATION_OR_CODE_CHANGED')
    marker=frozen/'heldout_access_v1.json'
    with marker.open('x',encoding='utf-8') as out:
        json.dump({'identity':'d5-heldout-access/v1','prereg_sha256':digest_file(record_path),
                   'intent':'single preregistered evaluation; no tuning or rerun under v1'},out)
    path=frozen/'heldout_queries.json';data=path.read_bytes()
    if sha256(data).hexdigest()!=record['heldout_query_sha256']:raise ValueError('HELDOUT_BYTES_CHANGED')
    queries=json.loads(data)
    if len(queries)!=snapshot.freeze['query_files']['heldout']['count']:raise ValueError('HELDOUT_COUNT_CHANGED')
    outcome=evaluate(snapshot,queries,ARMS)
    b=outcome['summaries']['B']
    output={'identity':'d5-heldout-diagnostic/v1','prereg_sha256':digest_file(record_path),
        'heldout_sha256':sha256(data).hexdigest(),'heldout_opened_once':True,'source_clusters':sorted({q['cik'] for q in queries}),
        'human_adjudicators':0,'mechanical_exact_row_oracles':True,'arms':list(ARMS),
        'retrieval':outcome,'bm25_failure_inclusive':b['failure_inclusive_metrics'],
        'cluster_confidence_interval':'NOT_ESTIMABLE_ONE_ISSUER_CLUSTER',
        'adaptive_finalist':'NONE_PRESELECTED','dense_quality':'NOT_MEASURED_CHANNEL_UNAVAILABLE',
        'real_d2_exact_cell_and_period':'NOT_MEASURED_SOURCE_SIZE_UNSUPPORTED',
        'real_d4_answer_quality':'NOT_MEASURED_REAL_NUMERIC_QA_ABSTAINS',
        'limits':['Five auto-labelled exact literal-row queries from one held-out HD filing only; no human adjudication or broad financial benchmark.',
                  'Unavailability zeros cannot estimate Dense model quality or fixed-fusion ranking quality.',
                  'No strategy or threshold changed using these outputs.']}
    destination=Path('docs/topic3/milestone_d/autonomous_execution/D5_FROZEN_HELDOUT_RESULT_v1.json')
    with destination.open('x',encoding='utf-8') as out:json.dump(output,out,indent=2)
    print(json.dumps({'output':str(destination),'prereg_sha256':output['prereg_sha256'],
        'heldout_sha256':output['heldout_sha256'],'query_count':len(queries),'bm25':b,
        'dense_status':outcome['summaries']['D']['success_count'],'fixed_rrf_status':outcome['summaries']['F']['success_count'],
        'source_clusters':output['source_clusters'],'cluster_confidence_interval':output['cluster_confidence_interval']},indent=2))

if __name__=='__main__':main()

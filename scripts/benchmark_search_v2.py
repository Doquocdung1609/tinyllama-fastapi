"""Reproduce frozen Search V2 ablations only on explicitly owned experiment clones."""
import argparse,json,math,random,statistics,sys,time,hashlib
from pathlib import Path
from collections import defaultdict
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import psutil
from app.product.workspace import PdfWorkspace
from app.product.search_v2 import FinancialSearchV2,EXPERIMENTS
from app.product.pdf_extract import folded
from app.product.sec_search import SecResearchIndex

REPO=Path(__file__).resolve().parents[1]
def policy_hash():
 return hashlib.sha256(''.join((REPO/p).read_text(encoding='utf-8') for p in ['app/product/query_intent.py','app/product/search_v2.py']).encode()).hexdigest()

def exact_hit(hit,rel):
 if rel.get('parent_id'):return hit.get('chunk_id',hit.get('parent_id'))==rel['parent_id']
 if (hit.get('document_id'),hit.get('page'))!=(rel['document_id'],rel['page']):return False
 if hit.get('row_id')==rel.get('row_id') and rel.get('row_id'):return True
 # For baseline paragraphs require the actual row value or exact source span on its page.
 values=rel.get('source_values',[])
 return any(v in hit['text'] for v in values) if values else folded(rel['span']) in folded(hit['text'])

def score_query(q,result):
 refs=q['relevant'];hits=result['results'][:10]
 matched=[{i for i,ref in enumerate(refs) if exact_hit(hit,ref)} for hit in hits]
 relevant=[bool(m) for m in matched];positive=bool(refs)
 coverage=lambda k:len(set().union(*matched[:k]))/len(refs) if refs else None
 rr=next((1/(rank+1) for rank,ok in enumerate(relevant[:5]) if ok),0.) if positive else None
 # One row may satisfy several cross-page operands; coverage, not repeated hits, measures recall.
 seen=set();gains=[]
 for indices in matched[:5]:
  gains.append(bool(indices-seen));seen.update(indices)
 dcg=sum((1 if ok else 0)/math.log2(i+2) for i,ok in enumerate(gains))
 ideal=sum(1/math.log2(i+2) for i in range(min(len(refs),5)))
 ndcg=min(1.,dcg/ideal) if ideal else None
 verified=[h for h in hits if h.get('numeric_answer_eligible')]
 wrong_claims=sum(not any(exact_hit(h,r) for r in refs) for h in verified)
 abstained=(result.get('evidence_status')=='NO_SUFFICIENT_EVIDENCE' or not hits)
 return {'recall_at_5':coverage(5),'recall_at_10':coverage(10),'mrr_at_5':rr,'ndcg_at_5':ndcg,
  'exact_evidence_hit_at_1':int(bool(relevant and relevant[0])) if positive else None,
  'wrong_evidence_at_1':int(not relevant or not relevant[0]) if positive else None,
  'precision_at_5':None, # annotations are not exhaustive negatives; do not treat unjudged as false
  'abstention_correct':int(abstained) if q['expected_abstention'] else None,
  'verified_claims':len(verified),'wrong_verified_claims':wrong_claims,
  'unsupported_answer_rate':None,'metric_basis_period_correctness':None,
  'matched_reference_indices':[sorted(indices) for indices in matched],
  'score_limit':'Distinct-reference binary nDCG: repeated hits for the same gold source add no gain. Retrieval locator metrics, not general numeric QA. Column correctness evaluated through reviewed fact tests separately.'}

def percentile(values,p):
 if not values:return None
 values=sorted(values);pos=(len(values)-1)*p;lo=int(pos);return values[lo]+(values[min(lo+1,len(values)-1)]-values[lo])*(pos-lo)

def run(args):
 root=Path(args.root).resolve();marker=root/'search-v2-experiment.json'
 if not marker.exists() or json.loads(marker.read_text())['purpose']!='SEARCH_V2_ISOLATED_EXPERIMENT':raise ValueError('EXPERIMENT_CLONE_MARKER_REQUIRED')
 qrels=REPO/'docs/search_v2/SEARCH_BENCHMARK_QRELS.jsonl';freeze=json.loads((qrels.parent/'BENCHMARK_FREEZE.json').read_text())
 if hashlib.sha256(qrels.read_bytes()).hexdigest()!=freeze['qrels_sha256']:raise ValueError('QRELS_FREEZE_CHANGED')
 lock_path=qrels.parent/'EVALUATION_POLICY_LOCK.json'
 lock={}
 if args.split=='heldout':
  lock=json.loads(lock_path.read_text())
  if lock['policy_sha256']!=policy_hash() or lock['qrels_sha256']!=freeze['qrels_sha256']:raise ValueError('POLICY_OR_LABELS_CHANGED_AFTER_LOCK')
 output=Path(args.output)
 if output.exists():raise ValueError('RESULT_EXISTS_USE_NEW_EXPLICIT_OUTPUT')
 questions=[json.loads(line) for line in qrels.read_text(encoding='utf-8').splitlines()]
 selected=[q for q in questions if q['split']==args.split]
 frozen_policy=policy_hash()
 w=PdfWorkspace(root);sec=None;records=[];peaks=[];started=time.perf_counter()
 try:
  v=FinancialSearchV2(w,root/'search-v2-sidecar');build_start=time.perf_counter();snapshot=v.prepare();build_ms=(time.perf_counter()-build_start)*1000
  if args.sec_root and args.sec_vectors:sec=SecResearchIndex(Path(args.sec_root),Path(args.sec_vectors),Path(args.sec_root))
  warm=next(q for q in selected if q['source']=='PDF')
  for arm in EXPERIMENTS:v.search(warm['query'],'hybrid',10,warm['document_ids'],arm)
  for i,q in enumerate(selected):
   for arm in EXPERIMENTS:
    t=time.perf_counter()
    if q['source']=='SEC':
     if sec is None:records.append({'id':q['id'],'family':q['family'],'arm':arm,'status':'SKIP_SEC_NOT_CONFIGURED'});continue
     # No unapproved SEC index migration: C1 passthrough B0; C2/C3/C4 passthrough B2 explicitly.
     mode={'B0':'bm25','B1':'dense','B2':'hybrid','C1':'bm25','C2':'hybrid','C3':'hybrid','C4':'hybrid'}[arm]
     result=sec.search(q['query'],mode,10,q['ticker'])
    else:result=v.search(q['query'],'hybrid',10,q['document_ids'],arm)
    elapsed=(time.perf_counter()-t)*1000;peaks.append(psutil.Process().memory_info().rss)
    scores=score_query(q,result)
    records.append({'id':q['id'],'family':q['family'],'source':q['source'],'arm':arm,'status':'PASS_EXECUTION',
      'latency_ms':elapsed,'generation':result.get('generation'),'evidence_status':result.get('evidence_status'),
      'reason':result.get('reason'),'metrics':scores,'hits':[{k:h.get(k) for k in ['rank','chunk_id','evidence_id','document_id','page','row_id','source_sha256','numeric_answer_eligible','evidence_match','conflicts']} for h in result['results'][:10]]})
   print(args.split,i+1,'/',len(selected),q['id'],flush=True)
  summaries={}
  for arm in EXPERIMENTS:
   data=[r for r in records if r['arm']==arm and r['status']=='PASS_EXECUTION'];metrics={}
   for name in ['recall_at_5','recall_at_10','mrr_at_5','ndcg_at_5','exact_evidence_hit_at_1','wrong_evidence_at_1','abstention_correct']:
    values=[r['metrics'][name] for r in data if r['metrics'][name] is not None];metrics[name]=statistics.mean(values) if values else None
   metrics.update(precision_at_5=None,metric_basis_period_correctness=None,unsupported_answer_rate=None,
    verified_claims=sum(r['metrics']['verified_claims'] for r in data),wrong_verified_claims=sum(r['metrics']['wrong_verified_claims'] for r in data))
   summaries[arm]={'queries_executed':len(data),'metrics':metrics,'p50_ms':percentile([r['latency_ms'] for r in data],.5),'p95_ms':percentile([r['latency_ms'] for r in data],.95)}
  paired=defaultdict(list)
  for q in selected:
   pair={r['arm']:r for r in records if r['id']==q['id'] and r['status']=='PASS_EXECUTION'}
   if 'B2' in pair and 'C4' in pair and pair['B2']['metrics']['mrr_at_5'] is not None:
    paired[q['family']].append(pair['C4']['metrics']['mrr_at_5']-pair['B2']['metrics']['mrr_at_5'])
  groups=[statistics.mean(values) for values in paired.values()];rng=random.Random(20261028)
  boot=[statistics.mean(rng.choices(groups,k=len(groups))) for _ in range(1000)] if groups else []
  result={'split':args.split,'annotation_independence':freeze['independence_limit'],'qrels_sha256':freeze['qrels_sha256'],'policy_sha256':policy_hash(),
   'evaluation_exposure':'EXPOSED_RETEST_AFTER_CRITICAL_FIX' if lock.get('protocol_deviation') else 'POLICY_LOCKED_FIRST_RUN' if args.split=='heldout' else 'DEVELOPMENT',
   'protocol_deviation':lock.get('protocol_deviation'),
   'queries':len(selected),'summaries':summaries,'records':records,
   'paired_family_bootstrap_C4_minus_B2_MRR':{'families':len(groups),'mean_delta':statistics.mean(groups) if groups else None,'ci95':[percentile(boot,.025),percentile(boot,.975)],'scope':'Provisional family-cluster resampling, not independent human evidence.'},
   'resources':{'elapsed_s':time.perf_counter()-started,'index_prepare_ms':build_ms,'active_sidecar_bytes':snapshot['path'].stat().st_size,'sampled_benchmark_process_peak_rss_bytes':max(peaks) if peaks else None,'free_disk_bytes':psutil.disk_usage(str(root)).free},
   'method_notes':['Same source scope/top10 across arms;B0/B1/B2 unchanged.', 'SEC C1 is B0 passthrough;SEC C2/C3/C4 are B2 passthrough, no SEC improvement claim.',
    'Precision and generic numeric unsupported-answer rates not estimable from non-exhaustive retrieval annotations; null, not zero.',
    'Heldout evaluation allowed only after source policy lock. No independent human reviewer;Gate5 remains PARTIAL.']}
  if policy_hash()!=frozen_policy:raise ValueError('POLICY_CHANGED_DURING_BENCHMARK')
  output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 finally:
  w.close()
  if sec:sec.close()
 return result

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',required=True);p.add_argument('--split',choices=['development','heldout'],required=True);p.add_argument('--output',required=True);p.add_argument('--sec-root');p.add_argument('--sec-vectors');args=p.parse_args();run(args)

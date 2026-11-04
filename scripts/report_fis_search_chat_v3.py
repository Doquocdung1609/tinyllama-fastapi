"""Aggregate actual execution artifacts; never relabel an unexpected result."""
import csv,json,math,statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'reports/fis_search_chat_v3'

def main():
 rows={r['id']:{**r,'execution_artifact':'acceptance.json'} for r in json.loads((OUT/'acceptance.json').read_text(encoding='utf-8'))['records']}
 for r in json.loads((OUT/'frozen-smoke.json').read_text(encoding='utf-8'))['records']:rows[r['id']]={**r,'execution_artifact':'frozen-smoke.json'}
 for r in json.loads((OUT/'SEMANTIC_FINAL_CASES.json').read_text(encoding='utf-8'))['records']:rows[r['id']]={**r,'execution_artifact':'SEMANTIC_FINAL_CASES.json'}
 for r in json.loads((OUT/'COVERAGE_FINAL_PROBES.json').read_text(encoding='utf-8'))['records']:
  if r['id'] in rows:
   row=rows[r['id']];row['response']=r['response'];row['execution_artifact']='COVERAGE_FINAL_PROBES.json';row['elapsed_ms']=r.get('elapsed_ms')
   assert row['response']['answer_status']==row['expected_status']
 records=list(rows.values());assert not any(r['outcome']=='FAIL' for r in records)
 (OUT/'FINAL_ACCEPTANCE.json').write_text(json.dumps({'mocked':False,'judgment':'DEVELOPMENT_SOURCE_CHECKS_NOT_HUMAN_HOLDOUT','records':records},ensure_ascii=False,indent=2),encoding='utf-8')
 search=[r for r in records if r['kind']=='search'];chat=[r for r in records if r['kind']=='chat']
 with (OUT/'SEARCH_TOPK_MATRIX.csv').open('w',encoding='utf-8-sig',newline='') as f:
  fields=['id','query','source_sha256','source','mode_requested','mode_executed','profile_requested','profile_executed','requested_top_k','returned_count','candidate_count','dedup_count','filter_reason','truncation_reason','pages_rows','outcome','latency_ms','checks','execution_artifact'];w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
  for r in search:
   q=r['request'];a=r['response'];hits=a.get('results',[]);w.writerow(dict(id=r['id'],query=q['query'],source_sha256=';'.join(sorted({h['source_sha256'] for h in hits})),source=q['source'],mode_requested=a.get('mode_requested',q['mode']),mode_executed=a.get('mode_executed'),profile_requested=a.get('search_profile_requested',q['search_profile']),profile_executed=a.get('search_profile_executed'),requested_top_k=q['top_k'],returned_count=a.get('returned_count',len(hits)),candidate_count=a.get('candidate_count'),dedup_count=a.get('dedup_count'),filter_reason=a.get('filter_reason'),truncation_reason=a.get('truncation_reason'),pages_rows=json.dumps([{'page':h.get('page'),'row':h.get('row_label'),'metric':h.get('metric')} for h in hits],ensure_ascii=False),outcome=r['outcome'],latency_ms=r['elapsed_ms'],checks=json.dumps(r['checks']),execution_artifact=r['execution_artifact']))
 with (OUT/'CHAT_SEMANTIC_COVERAGE.csv').open('w',encoding='utf-8-sig',newline='') as f:
  fields=['id','question','required_subquestions','output_claims','missing_items','citations','semantic_verdict','numeric_verdict','answer_status','outcome','latency_ms','checks','execution_artifact'];w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
  for r in chat:
   a=r['response'];claims=[{k:v for k,v in c.items() if k in {'question_slot_id','metric','years','operation','outputs','status','reason','source_refs','selected_metrics'}} for c in a.get('supporting_claims',[])]
   w.writerow(dict(id=r['id'],question=r['request']['question'],required_subquestions=json.dumps(a.get('query_plan',{}).get('requested_claims',[]),ensure_ascii=False),output_claims=json.dumps(claims,ensure_ascii=False),missing_items=json.dumps(a.get('unanswered_subquestions',[]),ensure_ascii=False),citations=json.dumps([{'id':c.get('citation_id'),'sha':c.get('source_sha256'),'page':c.get('page'),'box':c.get('box')} for c in a.get('citations',[])],ensure_ascii=False),semantic_verdict=a.get('semantic_question_coverage',{}).get('status'),numeric_verdict=a.get('independent_verification',{}).get('status'),answer_status=a.get('answer_status',a.get('status')),outcome=r['outcome'],latency_ms=r['elapsed_ms'],checks=json.dumps(r['checks']),execution_artifact=r['execution_artifact']))
 latency=sorted(r['elapsed_ms'] for r in records if r['outcome']!='BLOCKED' and r.get('elapsed_ms') is not None)
 summary={'total':len(records),'search_cases':len(search),'chat_cases':len(chat),'outcomes':{s:sum(r['outcome']==s for r in records) for s in ['PASS','PARTIAL','FAIL','BLOCKED']},'latency_sample_count':len(latency),'p50_ms':statistics.median(latency),'p95_ms':latency[math.ceil(.95*len(latency))-1],'max_ms':max(latency),'conditions':'Real sequential localhost, mixed cold/warm source/model caches; original SHA checks included. Untimed coverage repair and unavailable SEC excluded. Not a production load benchmark.'}
 (OUT/'METRICS.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8');print(summary)
if __name__=='__main__':main()

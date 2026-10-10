import json
for fn in ['reports/rag_development_results_details.json','reports/rag_holdout_results_details.json','reports/rag_holdout_h20_details.json','reports/rag_regression_results_details.json']:
 try: rows=json.load(open(fn,encoding='utf-8-sig'))
 except Exception as e: print(fn,e);continue
 print('\n',fn,len(rows))
 for x in rows:
  cid=x['case']['id']; r=x['response']; cg=r.get('claim_grounding',{}); claims=cg.get('claims',[])
  statuses=[c.get('status') for c in claims]
  print(cid,statuses,'citvalid',r.get('citation_validation',{}).get('citation_valid'),'supportpages',[s.get('page') for s in r.get('supporting_sources',[])])

"""Authenticated owner regression through supported API;never prints credentials."""
import argparse,json,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import requests
from scripts.benchmark_search_v3r import scores,summarize

def run(a):
    output=Path(a.output)
    if output.exists():raise ValueError('NEW_RESULT_REQUIRED')
    session=requests.Session();session.headers['Authorization']='Bearer '+Path(a.token_file).read_text(encoding='utf-8-sig').strip()
    def post(path,body):
        r=session.post(a.url+'/studio/'+path,json=body,timeout=120);r.raise_for_status();return r.json()
    if a.qrels:
        rows=[]
        for q in map(json.loads,Path(a.qrels).read_text(encoding='utf-8').splitlines()):
            t=time.perf_counter();r=post('query',{'query':q['query'],'mode':'hybrid','source':'US_SEC' if q['source']=='SEC' else 'USER_UPLOADS','top_k':10,'document_ids':q['document_ids'],'issuer':q.get('ticker',''),'search_profile':'production_v3r'})
            rows.append({'id':q['id'],'arm':'API_V3R','elapsed_ms':(time.perf_counter()-t)*1000,'status':'PASS_EXECUTION','metrics':scores(q,r),'results':r['results'],'evidence_status':r['evidence_status']});print(q['id'],flush=True)
        report={'scope':'EXPOSED_REGRESSION_API','records':rows,'summaries':summarize(rows)}
    else:
        gold=json.loads(Path('docs/search_v3/EVIDENCE_GUARDS_V32.json').read_text(encoding='utf-8'));h='4a92af827aaf1e73e017544d0ff20d0d';b='2bed2b3c312c8149e6a2ff6ab80c694a';docs=[h]*4+[b]*3+[h,h,h,b,b,h,h,h,h,h];rows=[]
        for case,doc in zip(gold['source_fact_cases'],docs,strict=True):
            r=post('query',{'query':case['query'],'mode':'bm25','source':'USER_UPLOADS','top_k':5,'document_ids':[doc],'search_profile':'production_v3r'})
            facts=[f for hit in r['results'] if hit['numeric_answer_eligible'] for f in hit['reviewed_facts']];expected=case['expected']
            correct=bool(facts) and all(all(f[k]==v for k,v in expected.items()) for f in facts) if expected else not facts
            rows.append({'query':case['query'],'status':'PASS' if correct else 'FAIL','expected':expected,'claimed_facts':facts})
        numeric=[]
        for i,case in enumerate(gold['numeric_cases']):
            request={'question':case['question'],'document_ids':[[h],[b],[h]][i],'mode':'numeric','operation':['ABS_CHANGE','RESTATEMENT_CHECK','EXTRACT'][i],
                'current_period':'2024-12-31' if i==1 else '2025-12-31','previous_period':'2025-01-01','statement_scope':'CONSOLIDATED' if i==1 else 'SEPARATE'}
            r=post('analysis',request);correct=r['values']==case['values'] and r['status']==case['answer_status'];numeric.append({'question':case['question'],'status':'PASS' if correct else 'FAIL','result':r})
        entity=[]
        for name in ['Apple','apple']:
            for query in [f'{name} total assets separate as of 31/12/2025',f'Tổng tài sản {name} riêng 31/12/2025']:
                r=post('query',{'query':query,'mode':'bm25','source':'USER_UPLOADS','top_k':5,'document_ids':[h],'search_profile':'production_v3r'})
                entity.append({'query':query,'status':'PASS' if not any(h['numeric_answer_eligible'] for h in r['results']) else 'FAIL'})
        report={'source_fact_cases':rows,'numeric_cases':numeric,'entity_cases':entity,'annotation':'Bounded inherited reviewed source cells;not general financial accuracy.'}
    output.write_text(json.dumps(report,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
    if not a.qrels and any(r['status']!='PASS' for group in ['source_fact_cases','numeric_cases','entity_cases'] for r in report[group]):raise ValueError('LIVE_GUARD_FAILURE')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--url',default='http://127.0.0.1:8110');p.add_argument('--token-file',default='tmp/studio-runtime/access-token.txt');p.add_argument('--qrels');p.add_argument('--output',required=True);run(p.parse_args())

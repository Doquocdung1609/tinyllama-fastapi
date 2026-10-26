"""Sanitized live P6 API checks against explicitly local Uvicorn."""
import argparse
import json
import os
from pathlib import Path
from time import perf_counter
from urllib.parse import urlparse
import requests


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--url',required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();parsed=urlparse(args.url)
    if parsed.scheme!='http' or parsed.hostname not in {'localhost','127.0.0.1'}:
        raise ValueError('LOCAL_RESEARCH_API_REQUIRED')
    token=os.environ['TOPIC3_RESEARCH_API_TOKEN'];headers={'Authorization':'Bearer '+token}
    q="What were P&G's net sales for the three months ended September 30, 2026?"
    cases=[('exact',q,{},'B'),
           ('comparison','Compare P&G net sales for the quarter ended September 30, 2025 and the quarter ended September 30, 2026.',{},'B'),
           ('missing_comparative','Compare P&G net sales for the quarter ended September 30, 2024 and the quarter ended September 30, 2026.',{},'B'),
           ('conflicting_cik',q,{'cik':'0000354950'},'B'),('dense_unavailable',q,{},'D')]
    rows=[]
    for case_id,question,filters,arm in cases:
        start=perf_counter();response=requests.post(args.url+'/research/v1/query',headers=headers,
            json={'workflow':'automatic_real','question':question,'filters':filters,'arm':arm},timeout=30)
        body=response.json();rows.append({'case_id':case_id,'http_status':response.status_code,
            'wall_ms':round((perf_counter()-start)*1000,3),'retrieval_status':body.get('retrieval_status'),
            'answer_status':body.get('answer',{}).get('status'),
            'result_values':body.get('answer',{}).get('result_values',[]),
            'failure_code':body.get('failure_code'),'evidence_count':len(body.get('evidence',[])),
            'source_urls':[e['source_url'] for e in body.get('evidence',[])],
            'locators':[e['locator'] for e in body.get('evidence',[])]})
    unauth=requests.post(args.url+'/research/v1/query',json={'question':q,'workflow':'automatic_real'},timeout=5)
    rows.append({'case_id':'unauthorized','http_status':unauth.status_code})
    overlong=requests.post(args.url+'/research/v1/query',headers=headers,
        json={'question':'x'*2100,'workflow':'automatic_real'},timeout=5)
    rows.append({'case_id':'overlong_question','http_status':overlong.status_code})
    expected={'exact':('SUPPORTED',['23276000000']),'comparison':('SUPPORTED',['22386000000','23276000000']),
        'missing_comparative':('INSUFFICIENT_EVIDENCE',[]),'conflicting_cik':('NEEDS_CLARIFICATION',[]),
        'dense_unavailable':('INSUFFICIENT_EVIDENCE',[])}
    for row in rows[:5]:
        if row['http_status']!=200 or (row['answer_status'],row['result_values'])!=expected[row['case_id']]:
            raise AssertionError('P6_HTTP_CASE_MISMATCH:'+row['case_id'])
    if (unauth.status_code,overlong.status_code)!=(401,422):raise AssertionError('P6_HTTP_VALIDATION_OR_AUTH_MISMATCH')
    result={'schema_version':'topic3-p6-http/v1','health':requests.get(args.url+'/research/v1/health',timeout=5).json(),
            'cases':rows,'token_recorded':False}
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'cases':len(rows),'supported':2,'authorization_status':unauth.status_code,'output':str(args.output)}))


if __name__=='__main__':main()

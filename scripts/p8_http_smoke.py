"""Live local P8 API proof with positive answers and typed refusals."""
import argparse,json,os
from pathlib import Path
import requests

CASES=(
 ('pg_assets',"What were P&G's total assets as of September 30, 2026?",{},'B','SUPPORTED',['133132000000']),
 ('hd_assets',"What were HD total assets as of August 2, 2026?",{},'B','SUPPORTED',['109384000000']),
 ('hd_compare',"Compare HD total assets as of February 1, 2026 and as of August 2, 2026.",{},'B','SUPPORTED',['105095000000','109384000000']),
 ('pg_net_sales',"What were P&G's net sales for the three months ended September 30, 2026?",{},'B','SUPPORTED',['23276000000']),
 ('cost_missing',"What were COST total assets as of May 10, 2026?",{},'B','INSUFFICIENT_EVIDENCE',[]),
 ('cik_conflict',"What were HD total assets as of August 2, 2026?",{'cik':'0000080424'},'B','NEEDS_CLARIFICATION',[]),
 ('fair_value',"What were HD total assets fair value as of August 2, 2026?",{},'B','NEEDS_CLARIFICATION',[]),
 ('dense_unavailable',"What were HD total assets as of August 2, 2026?",{},'D','INSUFFICIENT_EVIDENCE',[]),
)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--url',required=True);p.add_argument('--output',type=Path,required=True)
 a=p.parse_args();assert a.url.startswith('http://127.0.0.1:')
 token=os.environ['TOPIC3_RESEARCH_API_TOKEN'];rows=[]
 for name,q,filters,arm,status,values in CASES:
  resp=requests.post(a.url+'/research/v1/query',headers={'Authorization':'Bearer '+token},
   json={'workflow':'automatic_real','question':q,'filters':filters,'arm':arm},timeout=35)
  body=resp.json();answer=body.get('answer',{})
  if resp.status_code!=200 or answer.get('status')!=status or answer.get('result_values',[])!=values:
   raise AssertionError(f'P8_HTTP_MISMATCH:{name}:{resp.status_code}:{answer}')
  if status=='SUPPORTED' and (not answer.get('source_cells') or not body.get('evidence')):
   raise AssertionError(f'P8_HTTP_MISSING_PROVENANCE:{name}')
  rows.append({'case_id':name,'http_status':resp.status_code,'answer_status':answer['status'],
   'result_values':answer.get('result_values',[]),'failure_code':body.get('failure_code'),
   'generation':body.get('generation'),'source_cells':answer.get('source_cells',[]),
   'citations':body.get('evidence',[])})
 unauthorized=requests.post(a.url+'/research/v1/query',json={'workflow':'automatic_real','question':CASES[0][1]},timeout=5)
 oversized=requests.post(a.url+'/research/v1/query',headers={'Authorization':'Bearer '+token},
  json={'workflow':'automatic_real','question':'x'*2100},timeout=5)
 assert unauthorized.status_code==401 and oversized.status_code==422
 result={'schema_version':'topic3-p8-http/v1','token_recorded':False,'cases':rows,
         'unauthorized_http':unauthorized.status_code,'oversized_http':oversized.status_code}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({'supported':sum(x['answer_status']=='SUPPORTED' for x in rows),
                   'refused':sum(x['answer_status']!='SUPPORTED' for x in rows),
                   'unauthorized':unauthorized.status_code,'oversized':oversized.status_code}))

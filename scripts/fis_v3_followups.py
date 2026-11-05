"""Additional actual multi-turn trials against original Apple source cells."""
import requests,json,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'reports/fis_product_v3'
s=requests.Session();s.headers['Authorization']='Bearer '+(ROOT/'tmp/studio-runtime/access-token.txt').read_text(encoding='utf-8-sig').strip()
threads=[[
 ('What were Services net sales in FY2025?',['109158']),('And in FY2024?',['96169']),('And in FY2023?',['85200']),
 ('So how much did Services grow in absolute terms and percentage?',['10969','12.87'])],
 [('What was net income FY2025?',['112010']),('And in FY2024?',['93736']),('So how much did it grow in absolute terms and percentage?',['18274','19.50'])]]
records=[]
for n,turns in enumerate(threads,1):
 sid=None
 for i,(question,values) in enumerate(turns):
  request={'question':question,'document_ids':['3eb270b22acb7d8d8e9c32a43dc221de'],'session_id':sid};start=time.perf_counter();http=s.post('http://127.0.0.1:18110/studio/chat',json=request,timeout=180);r=http.json();sid=r.get('session_id');checks={'http':http.status_code==200,'values':r.get('values')==values,'coverage':r.get('semantic_question_coverage',{}).get('status')=='COMPLETE','verification':r.get('independent_verification',{}).get('status')=='VERIFIED'}
  records.append({'id':f'M{n}-{i+1}','is_followup':i>0,'request':request,'elapsed_ms':round((time.perf_counter()-start)*1000,2),'checks':checks,'verdict':'PASS' if all(checks.values()) else 'FAIL','response':r})
  (OUT/'followups.json').write_text(json.dumps({'mocked':False,'records':records},ensure_ascii=False,indent=2),encoding='utf-8');print(records[-1]['id'],records[-1]['verdict'],r.get('values'),flush=True)

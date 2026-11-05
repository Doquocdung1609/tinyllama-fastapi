"""Live SEC trials with explicit fiscal-quarter/instant periods from selected catalog."""
import requests,json,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'reports/fis_product_v3'
def main():
 s=requests.Session();s.headers['Authorization']='Bearer '+(ROOT/'tmp/studio-runtime/access-token.txt').read_text(encoding='utf-8-sig').strip()
 catalog=s.get('http://127.0.0.1:18110/studio/sec/catalog').json();records=[]
 for f in catalog['filings']:
  for metric,phrase in [('net sales','for the quarter ended'),('total assets','as of')]:
   question=f"{f['ticker']} {metric} {phrase} {f['report_period']}"
   req={'question':question,'source':'US_SEC','ticker':f['ticker'],'filing_ids':[f['filing_id']]};start=time.perf_counter();http=s.post('http://127.0.0.1:18110/studio/chat',json=req,timeout=180);r=http.json()
   checks={'http':http.status_code==200,'verified_numeric_answer':r.get('status')=='SUPPORTED' and bool(r.get('values')),'filing_isolation':all(c.get('filing_id')==f['filing_id'] for c in r.get('citations',[]))}
   verdict='PASS' if all(checks.values()) else 'PARTIAL' if http.status_code==200 and checks['filing_isolation'] else 'FAIL'
   records.append({'id':f"SEC-P{len(records)+1}",'request':req,'http':http.status_code,'elapsed_ms':round((time.perf_counter()-start)*1000,2),'checks':checks,'verdict':verdict,'response':r})
   (OUT/'sec-precise.json').write_text(json.dumps({'mocked':False,'records':records},ensure_ascii=False,indent=2),encoding='utf-8');print(question,verdict,r.get('values'),flush=True)
if __name__=='__main__':main()

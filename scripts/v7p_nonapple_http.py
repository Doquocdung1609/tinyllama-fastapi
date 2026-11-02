"""Real local scanned-PDF ingestion, bounded polling, no seeded numeric facts."""
import argparse,json,time,hashlib
from pathlib import Path
import requests

def main():
    p=argparse.ArgumentParser();p.add_argument('--pdf',type=Path,required=True);a=p.parse_args()
    token=Path('tmp/studio-runtime/access-token.txt').read_text(encoding='utf-8-sig').strip()
    s=requests.Session();s.headers['Authorization']='Bearer '+token;base='http://127.0.0.1:18110/studio'
    raw=a.pdf.read_bytes();start=time.perf_counter()
    r=s.post(base+'/documents',files={'file':(a.pdf.name,raw,'application/pdf')},timeout=30);r.raise_for_status();doc=r.json()
    stages=[]
    for _ in range(900):
        doc=s.get(base+'/documents/'+doc['id'],timeout=20).json()
        if not stages or stages[-1]['stage']!=doc['stage']:
            stages.append({'stage':doc['stage'],'status':doc['status'],'elapsed_s':round(time.perf_counter()-start,2)})
            print(stages[-1],flush=True)
        if doc['status'] in {'READY','FAILED'}:break
        time.sleep(2)
    evidence={'source_sha256':hashlib.sha256(raw).hexdigest(),'source_filename':a.pdf.name,'document':doc,'stages':stages,'elapsed_s':round(time.perf_counter()-start,2)}
    if doc['status']=='READY':
        for mode in ('bm25','dense','hybrid'):
            r=s.post(base+'/query',json={'query':'doanh thu bán hàng','mode':mode,'source':'USER_UPLOADS','document_ids':[doc['id']],'search_profile':'auto'},timeout=120)
            data=r.json();evidence[mode]={'http_status':r.status_code,'result_count':len(data.get('results',[])),'mode':data.get('mode'),'profile':data.get('search_profile'),'latency_ms':data.get('latency_ms'),'generation':data.get('generation')}
        r=s.post(base+'/chat',json={'question':'Doanh thu năm 2025 là bao nhiêu?','document_ids':[doc['id']]},timeout=120)
        evidence['numeric_attempt']={'http_status':r.status_code,'response':r.json()}
        assert not r.json().get('values'),'Scanned numeric mapping must not be fabricated'
    Path('docs/topic3_v7p/V7P_NONAPPLE_HTTP.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'status':doc['status'],'pages':doc.get('pages'),'chunks':doc.get('chunks'),'elapsed_s':evidence['elapsed_s']}))

if __name__=='__main__':main()

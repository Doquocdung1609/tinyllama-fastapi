"""Sanitized actual HTTP probes; --offline expects isolated transport fault."""
import argparse,json,time,statistics,hashlib,platform,shutil
from pathlib import Path
import requests,psutil

def main():
    p=argparse.ArgumentParser();p.add_argument('--offline',action='store_true');a=p.parse_args()
    s=requests.Session();s.trust_env=False
    s.headers['Authorization']='Bearer '+Path('tmp/studio-runtime/access-token.txt').read_text(encoding='utf-8-sig').strip()
    base='http://127.0.0.1:18110/studio';out={}
    ready=s.get(base+'/readiness',timeout=30);ready.raise_for_status()
    out['ollama']=ready.json()['ollama'];out['workspace']=ready.json()['workspace']
    docs=s.get(base+'/documents',timeout=20).json()['documents'];out['documents']=docs
    apple=next(d for d in docs if d['sha256'].startswith('3eb270b22acb7d8d'))
    out['metadata']=s.get(base+'/documents/'+apple['id']+'/metadata',timeout=10).json()
    out['queries']=[]
    for i in range(1 if a.offline else 5):
        t=time.perf_counter();r=s.post(base+'/chat',json={'question':"What was Apple's net income in fiscal year 2025?",'document_ids':[apple['id']], 'session_id':hashlib.sha256(b'v7p-runtime-probe').hexdigest()[:32]},timeout=120)
        body=r.json();out['queries'].append({'http_status':r.status_code,'elapsed_ms':round((time.perf_counter()-t)*1000,2),'response':body})
        assert r.status_code==200 and body.get('values')==['112010'] and body['status']=='SUPPORTED',body.get('reason')
        if a.offline:assert body['effective_mode']=='bm25' and 'FALLBACK' in body['routing_reason']
    if a.offline:
        assert out['ollama']['status']=='UNAVAILABLE'
        out['fault_method']='Only child API process HTTP_PROXY=127.0.0.1:1 and NO_PROXY empty; real owner Ollama never stopped. API client bypasses proxy. Real HTTP transport-failure injection.'
    else:
        durations=[r['elapsed_ms'] for r in out['queries']]
        out['performance']={'first_after_restart_ms':durations[0],'subsequent_p50_ms':statistics.median(durations[1:]),'subsequent_p95_nearest_rank_ms':max(durations[1:]),'warm_n':4,'cold_definition':'fresh API process; existing model/OS caches not cleared'}
        mem=psutil.virtual_memory();out['resources']={'os':platform.platform(),'python':platform.python_version(),'total_ram':mem.total,'available_ram':mem.available,'disk_free':shutil.disk_usage('.').free}
        out['api_python_rss_snapshot']=[{'pid':p.pid,'rss_bytes':p.memory_info().rss} for p in psutil.process_iter(['name','cmdline']) if 'python' in (p.info['name'] or '').lower() and 'uvicorn' in ' '.join(p.info['cmdline'] or [])]
        file=Path('tmp/topic3/demo-workspace/files')/(apple['id']+'.pdf');times=[]
        for _ in range(10):
            t=time.perf_counter();assert hashlib.sha256(file.read_bytes()).hexdigest()==apple['sha256'];times.append((time.perf_counter()-t)*1000)
        out['raw_hash_ms']={'p50':statistics.median(times),'p95_nearest_rank':max(times),'n':10,'boundary':'full PDF bytes only; not complete provenance or parsing'}
    name='V7P_OFFLINE_HTTP.json' if a.offline else 'V7P_RESTART_PERFORMANCE_HTTP.json'
    Path('docs/topic3_v7p',name).write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'status':'PASS','queries':len(out['queries']),'ollama':out['ollama']['status'],'performance':out.get('performance')}))

if __name__=='__main__':main()

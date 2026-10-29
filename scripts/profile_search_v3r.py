"""Bounded laptop measurements;provenance work remains inside every timed query."""
import argparse,cProfile,pstats,json,time,sys,threading
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import psutil
from app.product.derived_workspace import DerivedPdfWorkspace
from app.product.search_v3r import FinancialSearchV3R
from scripts.benchmark_search_v2 import percentile

def run(a):
    output=Path(a.output)
    if output.exists():raise ValueError('NEW_PROFILE_OUTPUT_REQUIRED')
    w=DerivedPdfWorkspace(Path(a.root));e=FinancialSearchV3R(w,w.root/'profile-index');samples=[];stop=threading.Event();process=psutil.Process();cpu=process.cpu_times()
    if set(a.document or [])-{d['id'] for d in w.list_documents()}:w.close();raise ValueError('UNKNOWN_PROFILE_DOCUMENT_SCOPE')
    def sample():
        while not stop.is_set():
            samples.append({'python_rss':process.memory_info().rss,'available_ram':psutil.virtual_memory().available});stop.wait(.2)
    thread=threading.Thread(target=sample,daemon=True);thread.start();queries=[];nested=[];original=w.search
    def instrument(*args,**kwargs):
        found=original(*args,**kwargs);nested.append(found.get('timings_ms'));return found
    w.search=instrument
    try:
        # A no-prewarm first search measures the path explicitly,then steady-state queries.
        t=time.perf_counter();r=e.search(a.query,'hybrid',10,a.document);cold=(time.perf_counter()-t)*1000
        prepared=e.prewarm()
        profiler=cProfile.Profile();profiler.enable();e.search(a.query,'hybrid',10,a.document);profiler.disable()
        for i in range(10):
            t=time.perf_counter();r=e.search(a.query,'hybrid',10,a.document);queries.append((time.perf_counter()-t)*1000)
        stats=pstats.Stats(profiler);functions=[{'file':Path(f).name,'function':name,'calls':n,'self_s':self_time,'cumulative_s':cumulative} for (f,line,name),(primitive,n,self_time,cumulative,callers) in stats.stats.items()]
        functions.sort(key=lambda v:-v['cumulative_s']);cpu1=process.cpu_times()
        report={'cold_search_without_prewarm_ms':cold,'prewarm_after_cold':prepared,'warm_ms':queries,'warm_p50_ms':percentile(queries,.5),'warm_p95_ms':percentile(queries,.95),
            'nested_workspace_timings_ms':nested,'profile_functions':functions,'resources':{'sampled_python_peak_rss':max(s['python_rss'] for s in samples),'minimum_available_ram':min(s['available_ram'] for s in samples),
            'free_disk_bytes':psutil.disk_usage(str(w.root)).free,'python_cpu_s':cpu1.user+cpu1.system-cpu.user-cpu.system},
            'limits':['Local Qdrant is included in Python RSS;external Ollama/Chrome excluded.','cProfile cumulative phases overlap;do not add cumulative times.','Repeated-query warm sample is not a diverse workload or p99 SLA.']}
        output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    finally:stop.set();thread.join();w.close()

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',required=True);p.add_argument('--query',required=True);p.add_argument('--document',action='append');p.add_argument('--output',required=True);run(p.parse_args())

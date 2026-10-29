"""Before/after exposed regression and bounded resources;never a new held-out claim."""
import argparse,json,sys,time,hashlib,threading,platform,subprocess
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import psutil
from app.product.derived_workspace import DerivedPdfWorkspace
from app.product.controlled_workspace import ControlledPdfWorkspace
from app.product.search_v3r import FinancialSearchV3R
from app.product.search_v3r2 import FinancialSearchV3R2,policy_hash
from app.product.search_v3 import search_sec_v3
from app.product.sec_search import SecResearchIndex
from scripts.benchmark_search_v3r import scores,summarize

def run(a):
    output=Path(a.output);progress=Path(str(output)+'.progress.jsonl')
    if output.exists() or progress.exists():raise ValueError('NEW_REGRESSION_OUTPUT_REQUIRED')
    qs=[];labels={}
    correction_path=Path(a.corrections)
    corrections=json.loads(correction_path.read_text(encoding='utf-8'))['corrections'] if correction_path.exists() else {}
    for filename in a.qrels:
        raw=Path(filename).read_bytes();labels[str(filename)]=hashlib.sha256(raw).hexdigest()
        qs.extend({**json.loads(l),'dataset':Path(filename).stem} for l in raw.decode('utf-8').splitlines())
    if a.ids:qs=[q for q in qs if q['id'] in a.ids.split(',')]
    root=Path(a.root)
    if not (root/'search-v3r2.json').exists():raise ValueError('V3R2_OWNED_CLONE_REQUIRED')
    w=ControlledPdfWorkspace(root) if a.arm=='after' else DerivedPdfWorkspace(root)
    engine=FinancialSearchV3R2(w,root/'v3r2-comparator-index',w.resources) if a.arm=='after' else FinancialSearchV3R(w,root/'v3r-comparator-index')
    sec=None;records=[];samples=[];stop=threading.Event();process=psutil.Process();cpu=process.cpu_times();start=time.perf_counter();nested=[];original=w.search;frozen=policy_hash()
    def measured(*args,**kwargs):
        found=original(*args,**kwargs);nested.append(found.get('timings_ms',{}));return found
    w.search=measured
    def sample():
        while not stop.is_set():
            item={'python_rss':process.memory_info().rss,'available_ram':psutil.virtual_memory().available,'elapsed_s':time.perf_counter()-start}
            for name in ['ollama','chrome','tesseract']:
                total=0
                for p in psutil.process_iter(['name','memory_info']):
                    try:
                        if name in (p.info['name'] or '').lower():total+=p.info['memory_info'].rss
                    except psutil.Error:pass
                item[name+'_rss']=total
            samples.append(item);stop.wait(.5)
    thread=threading.Thread(target=sample,daemon=True);thread.start()
    try:
        if any(q['source']=='SEC' for q in qs):sec=SecResearchIndex(Path(a.sec_root),Path(a.sec_vectors))
        t=time.perf_counter();prepared=engine.prewarm();preparation_ms=(time.perf_counter()-t)*1000
        for q in qs:
            t=time.perf_counter();result=search_sec_v3(sec,q['query'],'hybrid',10,q['ticker']) if q['source']=='SEC' else engine.search(q['query'],'hybrid',10,q['document_ids']);elapsed=(time.perf_counter()-t)*1000
            for h in result['results']:
                if h.get('row_id') and 'source_cells' not in h:
                    row=next((r for r in w.page_evidence(h['document_id'],h['page'])['tables'] if r['id']==h['row_id']),None)
                    if row:h['_evaluation_cells']=row['cells']
            record={'id':q['id'],'dataset':q['dataset'],'arm':a.arm,'query':q['query'],'source':q['source'],'status':'PASS_EXECUTION','elapsed_ms':elapsed,'metrics':scores(q,result),'generation':result.get('generation'),'intent':result.get('intent'),'results':result['results'],'reason':result.get('reason')}
            # Additive correction from original-source inspection;old qrels stay intact.
            if q['id'] in corrections:
                correction=corrections[q['id']];corrected=json.loads(json.dumps(q));corrected['relevant'][correction['reference_index']]['independently_located_cell_box']=correction['independently_located_cell_box']
                record['source_audit_corrected_metrics']=scores(corrected,result);record['annotation_correction']=correction['reason']
            records.append(record)
            with progress.open('a',encoding='utf-8') as f:f.write(json.dumps(record,ensure_ascii=False,separators=(',',':'))+'\n')
            print(a.arm,q['id'],'R5',record['metrics']['digit_locator_recall_at_5'],'cell5',record['metrics']['exact_cell_hit_at_5'],flush=True)
        if a.arm=='after' and frozen!=policy_hash():raise ValueError('POLICY_CHANGED_DURING_REGRESSION')
        second=engine.prewarm();cpu1=process.cpu_times()
        gpu=subprocess.run(['nvidia-smi','--query-gpu=name,memory.total,memory.used','--format=csv,noheader'],capture_output=True,text=True).stdout.strip() if a.gpu else 'NOT_SAMPLED'
        report={'scope':'EXPOSED_REGRESSION_ONLY','arm':a.arm,'policy_sha256':frozen,'qrels_sha256':labels,'prepare_ms':preparation_ms,'prepare':prepared,'repeat_prepare':second,'summaries':summarize(records),
            'by_dataset':{name:summarize([r for r in records if r['dataset']==name]) for name in {r['dataset'] for r in records}},'records':records,'source_correction_sha256':hashlib.sha256(correction_path.read_bytes()).hexdigest() if correction_path.exists() else None,'nested_workspace_timings_ms':nested,
            'resources':{'elapsed_s':time.perf_counter()-start,'cpu_s':cpu1.user+cpu1.system-cpu.user-cpu.system,'python_peak_rss':max(x['python_rss'] for x in samples),'minimum_available_ram':min(x['available_ram'] for x in samples),
            'ollama_peak_rss':max(x['ollama_rss'] for x in samples),'chrome_peak_rss':max(x['chrome_rss'] for x in samples),'free_disk_bytes':psutil.disk_usage(str(root)).free,'samples':samples,'gpu_snapshot':gpu,
            'local_qdrant':'INCLUDED_IN_PYTHON_RSS;not a separate service'},'limits':['Separate process per arm,same copied documents/vectors;unrelated owner applications may affect machine RAM.','All178 prior questions are exposed regression,no independent human review.','Exact-cell original and additive corrected-window scores are separate;no old qrel/result is overwritten.']}
        if hasattr(w,'resources'):report['resource_admission']=w.resources.status()
        output.write_text(json.dumps(report,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
    finally:stop.set();thread.join();w.close();sec.close() if sec else None

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',required=True);p.add_argument('--arm',choices=['before','after'],required=True);p.add_argument('--qrels',action='append',required=True);p.add_argument('--output',required=True);p.add_argument('--ids');p.add_argument('--corrections',default='docs/search_v3r2/SOURCE_ANNOTATION_CORRECTIONS.json');p.add_argument('--sec-root');p.add_argument('--sec-vectors');p.add_argument('--gpu',action='store_true');run(p.parse_args())

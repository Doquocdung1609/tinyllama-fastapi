"""Process hash-pinned evaluation sources in an owned clone, recording actual costs."""
import argparse,hashlib,json,sys,time,threading
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import psutil
from app.product.workspace import PdfWorkspace


def ingest(root,manifest,source_dir,split,output):
    root=Path(root);output=Path(output)
    if output.exists() or not (root/'search-v2-experiment.json').exists():raise ValueError('NEW_RESULT_AND_OWNED_CLONE_REQUIRED')
    sources=[s for s in json.loads(Path(manifest).read_text(encoding='utf-8')) if s['planned_split']==split]
    samples=[];done=threading.Event();process=psutil.Process()
    def sample():
        while not done.is_set():
            samples.append({'rss':process.memory_info().rss,'available_ram':psutil.virtual_memory().available,'disk_free':psutil.disk_usage(str(root)).free})
            done.wait(.25)
    thread=threading.Thread(target=sample,daemon=True);thread.start();w=PdfWorkspace(root);records=[]
    try:
        for source in sources:
            p=Path(source_dir)/(source['sha256']+'.pdf')
            if not p.exists():p=Path(source_dir)/(source['ticker']+'.pdf')
            data=p.read_bytes()
            if hashlib.sha256(data).hexdigest()!=source['sha256']:raise ValueError('SOURCE_SHA_MISMATCH')
            fresh=not any(d['sha256']==source['sha256'] for d in w.list_documents())
            started=time.perf_counter();d=w.add_pdf(p.name,data,source['issuer'],'Báo cáo tài chính hợp nhất',source['report_period']);result=w.process(d['id'])
            records.append({'ticker':source['ticker'],'source_sha256':source['sha256'],'fresh_document':fresh,'elapsed_s':time.perf_counter()-started,'document':result})
            print(source['ticker'],result['status'],round(records[-1]['elapsed_s'],2),'s',flush=True)
    finally:
        w.close();done.set();thread.join(timeout=2)
        report={'records':records,'sampling':'0.25s ingestion process RSS and whole-system free RAM/disk; other desktop apps not controlled',
            'sample_count':len(samples),'process_peak_rss_bytes':max((s['rss'] for s in samples),default=0),
            'minimum_available_ram_bytes':min((s['available_ram'] for s in samples),default=0),'minimum_free_disk_bytes':min((s['disk_free'] for s in samples),default=0)}
        output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',required=True);p.add_argument('--manifest',default='docs/search_v3/SOURCE_MANIFEST.json');p.add_argument('--source-dir',required=True);p.add_argument('--split',required=True);p.add_argument('--output',required=True);a=p.parse_args();ingest(a.root,a.manifest,a.source_dir,a.split,a.output)

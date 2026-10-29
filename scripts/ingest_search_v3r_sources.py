"""Ingest frozen evaluation sources into a new isolated region generation."""
import argparse,json,hashlib,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.product.derived_workspace import DerivedPdfWorkspace

def run(a):
    root=Path(a.root).resolve();repo=Path(__file__).resolve().parents[1];output=Path(a.output)
    if root.exists() or output.exists() or not root.is_relative_to(repo/'studio_workspace') or not root.name.startswith('search-v3r-'):raise ValueError('NEW_ISOLATED_ROOT_REQUIRED')
    sources=json.loads(Path(a.manifest).read_text(encoding='utf-8'));w=DerivedPdfWorkspace(root);records=[]
    try:
        for source in sources:
            raw=Path(source['path']).read_bytes()
            if hashlib.sha256(raw).hexdigest()!=source['sha256']:raise ValueError('SOURCE_SHA_MISMATCH')
            t=time.perf_counter();d=w.add_pdf(source['ticker']+'.pdf',raw,source['issuer'],source['document_type'],source['report_period']);result=w.process(d['id'])
            records.append({'document':result,'elapsed_s':time.perf_counter()-t});print(source['ticker'],result['status'],flush=True)
            if result['status']!='READY':raise ValueError('EXTRACTION_FAILED')
    finally:w.close();output.write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',required=True);p.add_argument('--manifest',required=True);p.add_argument('--output',required=True);run(p.parse_args())

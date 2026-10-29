"""Materialize a new region-extraction generation from stopped,hash-verified parents."""
import argparse,hashlib,json,sqlite3,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.product.workspace import OWNER as PDF_OWNER
from app.product.derived_workspace import DerivedPdfWorkspace


def derive(sources,destination,gate,output):
    repo=Path(__file__).resolve().parents[1];destination=Path(destination).resolve();output=Path(output)
    if destination.exists() or not destination.is_relative_to(repo/'studio_workspace') or not destination.name.startswith('search-v3r-'):
        raise ValueError('NEW_REPO_V3R_DERIVED_ROOT_REQUIRED')
    if output.exists():raise ValueError('NEW_INGESTION_RESULT_REQUIRED')
    if json.loads(Path(gate).read_text(encoding='utf-8'))['gate_B_D']!='PASS_BOUNDED':raise ValueError('BOUNDED_EXTRACTION_GATE_REQUIRED_BEFORE_INDEXING')
    items={};parent_roots=[]
    for source in sources:
        root=Path(source).resolve(strict=True)
        if json.loads((root/'ownership.json').read_text(encoding='utf-8'))['owner']!=PDF_OWNER:raise ValueError('UNOWNED_PARENT')
        database=root/'index.sqlite3';wal=Path(str(database)+'-wal')
        if wal.exists() and wal.stat().st_size:raise ValueError('STOP_AND_CHECKPOINT_PARENT_BEFORE_DERIVING')
        parent_roots.append(str(root))
        with sqlite3.connect(database.as_uri()+'?immutable=1',uri=True) as db:
            db.row_factory=sqlite3.Row
            for row in db.execute("SELECT * FROM documents WHERE status='READY'"):
                doc=dict(row)
                if doc['id'] in items:continue
                raw=(root/'files'/(doc['id']+'.pdf')).read_bytes()
                if hashlib.sha256(raw).hexdigest()!=doc['sha256']:raise ValueError('PARENT_RAW_SOURCE_CHANGED')
                checkpoints=[]
                for p in db.execute('SELECT page,payload,payload_hash FROM page_evidence WHERE document_id=? ORDER BY page',(doc['id'],)):
                    if hashlib.sha256(p['payload'].encode()).hexdigest()!=p['payload_hash']:raise ValueError('PARENT_CHECKPOINT_CHANGED')
                    data=json.loads(p['payload'])
                    if data.get('source_sha256')!=doc['sha256']:raise ValueError('PARENT_CHECKPOINT_SOURCE_CHANGED')
                    checkpoints.append((p['page'],p['payload'].encode(),p['payload_hash']))
                items[doc['id']]={'doc':doc,'raw':raw,'checkpoints':checkpoints}
    w=DerivedPdfWorkspace(destination);records=[]
    try:
        (destination/'search-v3r-experiment.json').write_text(json.dumps({'purpose':'SEARCH_V3R_ISOLATED_DERIVED_GENERATION','parents':parent_roots},indent=2)+'\n')
        for doc_id,item in items.items():
            doc=item['doc'];started=time.perf_counter()
            added=w.add_pdf(doc['filename'],item['raw'],doc['issuer'],doc['document_type'],doc['report_period'])
            parent=destination/'parents'/doc_id;parent.mkdir(parents=True,exist_ok=True)
            for number,raw,digest in item['checkpoints']:(parent/f'p{number}-{digest}.json').write_bytes(raw)
            result=w.process(added['id']);records.append({'document':result,'elapsed_s':time.perf_counter()-started,'parent_checkpoints':len(item['checkpoints'])})
            print(doc['issuer'],result['status'],result.get('extraction_coverage_status'),round(records[-1]['elapsed_s'],2),'s',flush=True)
            if result['status']!='READY':raise ValueError('DERIVED_INGESTION_FAILED_RETAIN_FOR_INSPECTION')
    finally:
        w.close();output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps({'root':str(destination),'records':records,'model_policy':'Existing locked Nomic768;new isolated Qdrant/FTS only;no reviewed facts auto-migrated'},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',action='append',required=True);p.add_argument('--destination',required=True);p.add_argument('--gate',default='docs/search_v3r/EXTRACTION_COVERAGE_RAW.json');p.add_argument('--output',required=True);a=p.parse_args();derive(a.source,a.destination,a.gate,a.output)

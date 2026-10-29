"""Copy stopped derived snapshots/vectors into a new owner root;no OCR or model pull."""
import argparse,hashlib,json,shutil,sqlite3,sys
from pathlib import Path
from contextlib import closing
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.product.derived_workspace import DerivedPdfWorkspace
from app.product.controlled_workspace import ControlledPdfWorkspace,OWNER,MARKER
from app.product.workspace import COLLECTION,DIGEST,_point_id,_validate_vector
from app.product.pdf_extract import folded
from qdrant_client import QdrantClient,models

def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def clone(sources,destination,output):
    repo=Path(__file__).resolve().parents[1];target=Path(destination).resolve();out=Path(output)
    if target.exists() or out.exists() or not target.is_relative_to(repo/'studio_workspace') or not target.name.startswith('search-v3r2-'):raise ValueError('NEW_V3R2_OWNER_ROOT_REQUIRED')
    parents=[Path(s).resolve(strict=True) for s in sources];inventories={}
    for p in parents:
        if not (p/'derived-generation.json').is_file():raise ValueError('DERIVED_PARENT_REQUIRED')
        wal=Path(str(p/'index.sqlite3')+'-wal')
        if wal.exists() and wal.stat().st_size:raise ValueError('STOP_PARENT_BEFORE_CLONING')
        inventories[str(p)]={str(f.relative_to(p)):digest(f) for f in p.rglob('*') if f.is_file()}
    target.mkdir(parents=True)
    for name in ['files','generations','parents','qdrant']:
        if (parents[0]/name).exists():shutil.copytree(parents[0]/name,target/name)
    for name in ['ownership.json','derived-generation.json','index.sqlite3']:shutil.copy2(parents[0]/name,target/name)
    (target/MARKER).write_text(json.dumps({'owner':OWNER,'baseline_commit':'3ba5e5e0f138fd2c1fd41c34c8b1262d74c308a9','parents':[str(p) for p in parents],'copy_policy':'Exact source/checkpoint/review/vector cloning;no new financial certification'},indent=2)+'\n',encoding='utf-8')
    w=ControlledPdfWorkspace(target);records=[]
    try:
        for parent in parents[1:]:
            temp=repo/'tmp/search-v3r2/vector-parents'/target.name/parent.name
            if temp.exists():raise ValueError('NEW_PRIVATE_VECTOR_COPY_REQUIRED')
            shutil.copytree(parent/'qdrant',temp);vectors=QdrantClient(path=str(temp))
            try:
                with closing(sqlite3.connect((parent/'index.sqlite3').as_uri()+'?immutable=1',uri=True)) as source:
                    source.row_factory=sqlite3.Row
                    for doc in source.execute("SELECT * FROM documents WHERE status='READY'"):
                        if w.document(doc['id']):continue
                        raw=parent/'files'/(doc['id']+'.pdf')
                        if digest(raw)!=doc['sha256']:raise ValueError('PARENT_RAW_SOURCE_CHANGED')
                        shutil.copy2(raw,w.files/raw.name)
                        for r in source.execute('SELECT payload,payload_hash FROM page_evidence WHERE document_id=?',(doc['id'],)):
                            if hashlib.sha256(r['payload'].encode()).hexdigest()!=r['payload_hash']:raise ValueError('PARENT_CHECKPOINT_CHANGED')
                        chunks=list(source.execute('SELECT * FROM chunks WHERE document_id=? ORDER BY id',(doc['id'],)))
                        for c in chunks:
                            if hashlib.sha256(c['text'].encode()).hexdigest()!=c['text_hash']:raise ValueError('PARENT_CHUNK_CHANGED')
                        with closing(w._connect()) as db,db:
                            for table in ['documents','page_evidence','chunks','extraction_generations','reviewed_facts']:
                                key='id' if table=='documents' else 'document_id';rows=source.execute(f'SELECT * FROM {table} WHERE {key}=?',(doc['id'],)).fetchall()
                                for r in rows:db.execute(f'INSERT INTO {table} VALUES('+','.join('?' for _ in r)+')',tuple(r))
                            for c in chunks:
                                db.execute('INSERT INTO chunks_fts VALUES(?,?)',(c['id'],c['text']));db.execute('INSERT INTO chunks_fts_vi VALUES(?,?)',(c['id'],folded(c['text'])))
                            for r in source.execute('SELECT * FROM fact_review_history'):db.execute('INSERT OR IGNORE INTO fact_review_history VALUES(?,?,?)',tuple(r))
                        for manifest in (parent/'generations').glob('*.json'):
                            if digest(manifest)!=manifest.stem:raise ValueError('PARENT_MANIFEST_CHANGED')
                            shutil.copy2(manifest,target/'generations'/manifest.name)
                        points=[]
                        for start in range(0,len(chunks),100):
                            batch=chunks[start:start+100];expected={c['id']:c for c in batch};got=vectors.retrieve(COLLECTION,ids=[_point_id(c['id']) for c in batch],with_payload=True,with_vectors=True)
                            if len(got)!=len(batch):raise ValueError('PARENT_VECTOR_MISSING')
                            for point in got:
                                payload=point.payload or {};c=expected.get(payload.get('chunk_id'))
                                if not c or payload.get('source_hash')!=doc['sha256'] or payload.get('model_digest')!=DIGEST or payload.get('text_hash')!=c['text_hash'] or payload.get('document_id')!=doc['id']:raise ValueError('PARENT_VECTOR_SOURCE_CHANGED')
                                _validate_vector(point.vector);points.append(point)
                            w._vector_client().upsert(COLLECTION,points=[models.PointStruct(id=p.id,vector=p.vector,payload=p.payload) for p in got],wait=True)
                        copied=w._vector_client().retrieve(COLLECTION,ids=[p.id for p in points],with_payload=True,with_vectors=True)
                        before={str(p.id):p.model_dump(mode='json') for p in points};after={str(p.id):p.model_dump(mode='json') for p in copied}
                        # Qdrant version/shard metadata is operational;vector and provenance must match.
                        if {k:v['payload'] for k,v in before.items()}!={k:v['payload'] for k,v in after.items()}:raise ValueError('CLONED_VECTOR_PAYLOAD_CHANGED')
                        delta=max((abs(a-b) for key in before for a,b in zip(before[key]['vector'],after[key]['vector'])),default=0)
                        if delta>2e-7:raise ValueError('CLONED_VECTOR_VALUES_CHANGED')
                        records.append({'document_id':doc['id'],'source_sha256':doc['sha256'],'chunks':len(chunks),'copied_payload_exact':True,'vector_max_abs_difference':delta,
                            'vector_policy':'Existing float32 vectors via supported Qdrant API;COSINE renormalization may round;no model inference or source overwrite'})
            finally:vectors.close()
        w._revalidate_ready();w.verify_generation();docs=w.list_documents()
        if any(d['status']!='READY' for d in docs):raise ValueError('CLONE_VALIDATION_FAILED')
        for p in parents:
            if inventories[str(p)]!={str(f.relative_to(p)):digest(f) for f in p.rglob('*') if f.is_file()}:raise ValueError('PARENT_CHANGED_DURING_CLONE')
        out.write_text(json.dumps({'root':str(target),'parent_inventory_sha256':{p:hashlib.sha256(json.dumps(i,sort_keys=True).encode()).hexdigest() for p,i in inventories.items()},'documents':docs,'appended':records,'status':'PASS_SOURCE_AND_BOUNDED_VECTOR_COPY'},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print('Cloned',len(docs),'READY documents;prior sources/checkpoints/reviews/vectors preserved')
    finally:w.close()

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',action='append',required=True);p.add_argument('--destination',required=True);p.add_argument('--output',required=True);a=p.parse_args();clone(a.source,a.destination,a.output)

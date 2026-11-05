"""Product-owned EDGAR library. Discovery metadata never comes from client URLs."""
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps,lru_cache
from hashlib import sha256
from pathlib import Path
from threading import Lock,Thread
import json,os,sqlite3,subprocess,sys,time
from fastapi import APIRouter,Depends,HTTPException,Query
from pydantic import BaseModel,Field,ConfigDict
from app.config import ROOT_DIR,get_settings
from app.financial_ingestion.sec_client import SECClient,validate_user_agent,RateLimiter

active=ContextVar('product_sec_index',default=None)
lock=Lock()
submission_lock=Lock()
request_limiter=RateLimiter(1)
def serialize_submission(fn):
    @wraps(fn)
    def call(*args,**kwargs):
        with submission_lock:return fn(*args,**kwargs)
    return call
def root():
    p=Path(os.getenv('STUDIO_WORKSPACE_DIR',str(ROOT_DIR/'studio_workspace')))/'sec-user-library';p.mkdir(parents=True,exist_ok=True);return p
@contextmanager
def db():
    c=sqlite3.connect(root()/'library.sqlite3',timeout=20);c.row_factory=sqlite3.Row
    c.execute('CREATE TABLE IF NOT EXISTS filings (id TEXT PRIMARY KEY,metadata TEXT NOT NULL,status TEXT NOT NULL,reason TEXT,updated REAL NOT NULL)')
    c.execute('CREATE TABLE IF NOT EXISTS job_events (seq INTEGER PRIMARY KEY AUTOINCREMENT,filing_id TEXT NOT NULL,status TEXT NOT NULL,reason TEXT,created REAL NOT NULL)')
    try:yield c;c.commit()
    finally:c.close()
def rows():
    with db() as c:return [dict(r) for r in c.execute('SELECT * FROM filings ORDER BY updated DESC')]
def update(key,status,reason=None):
    with db() as c:
        stamp=time.time();c.execute('UPDATE filings SET status=?,reason=?,updated=? WHERE id=?',(status,reason,stamp,key))
        c.execute('INSERT INTO job_events (filing_id,status,reason,created) VALUES (?,?,?,?)',(key,status,reason,stamp))
def client():
    path=root()/'private-contact.json'
    ua=json.loads(path.read_text(encoding='utf-8'))['user_agent'] if path.exists() else get_settings().sec_user_agent
    result=SECClient(ua,requests_per_second=1,timeout_seconds=25,max_retries=1)
    result.rate_limiter=request_limiter
    return result
def paths(key):
    parent=root()/key
    return parent/'p7-isolated-review-user-product',parent/'t3-p10-isolated-vectors-user-product'
@lru_cache(maxsize=8)
def _index(key, state):
    from app.product.sec_search import SecResearchIndex
    a,b=paths(key)
    return SecResearchIndex(a,b,a,lexical_only=state=='LEXICAL_READY')


def index(key):
    return _index(key,indexed_generation(key)['state'])
def select(filing_ids):
    if not filing_ids:return None
    wanted = set(filing_ids)
    partitions = []
    from app.product.api import _sec_cached
    try:
        base = _sec_cached()
    except (OSError, ValueError, RuntimeError):
        base = None
    if base is not None:
        ids = wanted & {row['filing_id'] for row in base.catalog_rows}
        if ids:
            partitions.append(ScopedIndex(base, sorted(ids)))
            wanted -= ids
    for row in rows():
        filing_id = json.loads(row['metadata'])['filing_id']
        if row['status'] in {'READY','LEXICAL_READY'} and filing_id in wanted:
            partitions.append(index(row['id']))
            wanted.remove(filing_id)
    if wanted:
        raise HTTPException(409, detail={'code':'SEC_FILING_NOT_READY', 'filing_ids':sorted(wanted)})
    return partitions[0] if len(partitions) == 1 else FederatedIndex(partitions)


class FederatedIndex:
    def __init__(self, partitions):
        self.partitions = tuple(partitions)
        self.catalog_rows = [dict(row, generation=part.identity['generation'])
                             for part in partitions for row in part.catalog_rows]

    def catalog(self):
        return {'status':'READY', 'filings':self.catalog_rows}

    def search(self, query, mode, top_k, ticker='', report_period=''):
        return federated_search(self, lambda part: part.search(query, mode, top_k, ticker, report_period), top_k)


def federated_search(index, search, top_k):
    """Merge local ranks deterministically without comparing cross-index scores."""
    from time import perf_counter
    start = perf_counter()
    responses = []
    for part in index.partitions:
        result = search(part)
        if result.get('status') == 'NO_ELIGIBLE_FILING':
            continue
        generation = part.identity['generation']
        responses.append((generation, result))
    merged = [(hit['rank'], generation, hit['chunk_id'], hit)
              for generation, result in responses for hit in result['results']]
    merged.sort(key=lambda item: item[:3])
    hits = [dict(hit, rank=rank, generation=generation, partition_rank=local_rank)
            for rank, (local_rank, generation, _, hit) in enumerate(merged[:top_k], 1)]
    first = responses[0][1] if responses else {}
    return {**first, 'results':hits, 'status':'READY',
            'generation':sha256(json.dumps(sorted(g for g, _ in responses)).encode()).hexdigest(),
            'generations':[g for g, _ in responses],
            'candidate_count':sum(r.get('candidate_count', len(r['results'])) for _,r in responses),
            'latency_ms':(perf_counter()-start)*1000, 'partition_fusion':'LOCAL_RANK_THEN_GENERATION'}


def partitions(index):
    return index.partitions if isinstance(index, FederatedIndex) else (index,)


def for_hit(index, hit):
    matches = [part for part in partitions(index) if hit['chunk_id'] in part.by_id
               and (not hit.get('generation') or hit['generation'] == part.identity['generation'])]
    if len(matches) != 1:
        raise ValueError('SOURCE_GENERATION_NOT_REGISTERED')
    return matches[0]


class ScopedIndex:
    def __init__(self,base,ids):self.base=base;self.ids=ids
    def __getattr__(self,name):return getattr(self.base,name)
    @property
    def catalog_rows(self):return [r for r in self.base.catalog_rows if r['filing_id'] in self.ids]
    @property
    def parents(self):return [r for r in self.base.parents if r['chunk'].filing_id in self.ids]
    @property
    def by_id(self):return {k:v for k,v in self.base.by_id.items() if v['chunk'].filing_id in self.ids}
    def catalog(self):return {**self.base.catalog(),'filings':self.catalog_rows}
    def search(self,*args,**kwargs):return self.base.search(*args,**kwargs,_filing_ids=self.ids)

def scoped(fn):
    @wraps(fn)
    def call(payload,*args,**kwargs):
        selected=select(getattr(payload,'filing_ids',[]));token=active.set(selected or active.get())
        try:return fn(payload,*args,**kwargs)
        finally:active.reset(token)
    return call
def indexed_generation(key):
    """Read the product publication receipt without opening vector handles."""
    source, vectors = paths(key)
    freeze = json.loads((source/'frozen_v1/freeze.json').read_text(encoding='utf-8'))
    vector_path = vectors/'generation_manifest.json'
    manifest = json.loads(vector_path.read_text(encoding='utf-8')) if vector_path.is_file() else {}
    if manifest.get('state')!='READY':
        manifest = json.loads((source/'lexical-publication.json').read_text(encoding='utf-8'))
        if manifest.get('state')!='LEXICAL_READY':
            raise ValueError('SEC_LEXICAL_PUBLICATION_MISMATCH')
    if any(manifest[k]!=freeze[k] for k in ('generation','manifest_hash')):
        raise ValueError('PRODUCT_GENERATION_MISMATCH')
    return manifest


def catalog():
    from app.product.api import _sec_cached
    try:result=_sec_cached().catalog()
    except Exception as e:result={'status':'UNAVAILABLE','reason':str(e),'filings':[]}
    generations=[{k:result.get(k) for k in ('dataset_id','generation','manifest_hash','parents','dense_vectors')}] if result['filings'] else []
    result={**result,'filings':[{**f,'generation':result.get('generation'),'ownership':'SHARED_DEMO'} for f in result['filings']]}
    for row in rows():
        if row['status'] in {'READY','LEXICAL_READY'}:
            try:
                detail=indexed_generation(row['id'])
                metadata=json.loads(row['metadata'])
                parents=detail.get('parent_count',detail.get('parents',0))
                generations.append({**{k:detail.get(k) for k in ('dataset_id','generation','manifest_hash')},
                                    'parents':parents,'dense_vectors':detail.get('completed_points',0)})
                result['filings'].append({
                    'ticker':metadata['ticker'],'cik':metadata['cik'],'issuer':metadata['company_name'],
                    'accession':metadata['accession_number'],'filing_id':metadata['filing_id'],'form':metadata['form_type'],
                    'report_period':metadata['report_date'],'source_url':metadata['source_url'],'chunks':parents,
                    'raw_sha256':next(g['raw_hash'] for g in json.loads((paths(row['id'])[0]/'frozen_v1/freeze.json').read_bytes())['source_groups']
                                      if g['accession']==metadata['accession_number']),
                    'library_id':row['id'],'ownership':'USER_PRODUCT','generation':detail['generation'],
                    'dense_ready':detail['state']=='READY','index_status':detail['state']})
            except Exception:update(row['id'],'RETRYABLE','PRODUCT_INDEX_OR_SOURCE_VALIDATION_FAILED')
    if result['filings']:result['status']='READY'
    result.update(generations=generations,parents=sum(g.get('parents') or 0 for g in generations),dense_vectors=sum(g.get('dense_vectors') or 0 for g in generations),generation_scope='DEFAULT_DEMO_OR_EXPLICIT_FEDERATED_SELECTION')
    return result
def for_reference(reference,secret):
    from app.product.sec_viewer import decode_reference
    from app.product.api import _sec_cached
    data=decode_reference(reference,secret)
    try:base=_sec_cached()
    except Exception:base=None
    if base is not None and data['generation']==base.identity['generation']:return base
    for row in rows():
        if row['status'] in {'READY','LEXICAL_READY'}:
            try:
                generation=indexed_generation(row['id'])['generation']
            except (OSError,ValueError,KeyError):
                continue
            if data['generation']==generation:return index(row['id'])
    raise ValueError('SOURCE_GENERATION_NOT_REGISTERED')
def process(key):
    # One worker process at a time on 8 GB machines; crash state is durable.
    with lock:
        result=subprocess.run([sys.executable,'-m','app.product.sec_library_worker',key],cwd=ROOT_DIR,
            stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        if result.returncode:update(key,'RETRYABLE','PROCESS_INTERRUPTED_OR_RESOURCE_LIMIT')

def router(require_token):
    r=APIRouter(prefix='/sec/library',dependencies=[Depends(require_token)])
    class Contact(BaseModel):
        user_agent:str=Field(min_length=12,max_length=240)
    class Import(BaseModel):
        model_config=ConfigDict(extra='forbid')
        discovery_id:str=Field(pattern=r'^[a-f0-9]{24}$')
    @r.on_event('startup')
    def recover():
        import portalocker
        with (root()/'import-worker.lock').open('a+') as stream:
            try:portalocker.lock(stream,portalocker.LOCK_EX|portalocker.LOCK_NB)
            except portalocker.LockException:return
            try:
                with db() as c:c.execute("UPDATE filings SET status='RETRYABLE',reason='PROCESS_RESTARTED_RETRY_IMPORT' WHERE status IN ('DOWNLOADING','EXTRACTING','INDEXING')")
            finally:portalocker.unlock(stream)
    @r.get('')
    def listing():
        path=root()/'private-contact.json'
        return {'contact_configured':path.exists() or bool(get_settings().sec_user_agent),
            'filings':[{**{k:v for k,v in x.items() if k!='metadata'},'metadata':json.loads(x['metadata'])} for x in rows()]}
    @r.get('/sec47')
    def recovery_catalog():
        path=root()/'sec47-status.json'
        if not path.is_file():
            return {'filings':[]}
        audit=json.loads(path.read_text(encoding='utf-8'))
        ready={f['accession']:f for f in catalog()['filings']}
        return {'filings':[{**f,'search_ready':f['accession'] in ready,
                            'dense_ready':ready.get(f['accession'],{}).get('dense_ready',False),
                            'generation':ready.get(f['accession'],{}).get('generation')} for f in audit]}
    @r.get('/jobs/{key}/events')
    def events(key:str):
        with db() as c:return {'events':[dict(row) for row in c.execute('SELECT status,reason,created FROM job_events WHERE filing_id=? ORDER BY seq',(key,))]}
    @r.post('/contact')
    def contact(body:Contact):
        ua=validate_user_agent(body.user_agent);p=root()/'private-contact.json';p.write_text(json.dumps({'user_agent':ua}),encoding='utf-8');return {'configured':True}
    @r.get('/discover')
    def discover(query:str=Query(default='',min_length=1,max_length=120),form:str='10-Q',
                 report_end:str=Query(default='',max_length=10,pattern=r'^$|^\d{4}-\d{2}-\d{2}$'),
                 filed_from:str=Query(default='',max_length=10,pattern=r'^$|^\d{4}-\d{2}-\d{2}$'),
                 filed_to:str=Query(default='',max_length=10,pattern=r'^$|^\d{4}-\d{2}-\d{2}$')):
        if form not in {'10-K','10-Q','10-K/A','10-Q/A','20-F','6-K'}:raise HTTPException(422,detail={'code':'UNSUPPORTED_FORM'})
        try:
            sec=client()
            try:
                mapping=sec.get_json('https://www.sec.gov/files/company_tickers.json')
                q=query.strip().upper()
                exact=[v for v in mapping.values() if q==str(v['ticker']).upper() or q.lstrip('0')==str(v['cik_str'])]
                matched=exact or [v for v in mapping.values() if q.lower() in v['title'].lower()]
                matched=list({str(v['cik_str']):v for v in matched}.values())
                if len(matched)!=1:return {'status':'SELECT_COMPANY','companies':matched[:20],'filings':[]}
                company=matched[0];filings=sec.discover(str(company['cik_str']),ticker=company['ticker'],forms=[form],limit=50,date_from=filed_from or None,date_to=filed_to or None,additional_forms={'20-F','6-K'})
                if report_end:filings=[f for f in filings if f.report_date==report_end]
            finally:sec.session.close()
            items=[]
            with db() as c:
                for m in filings:
                    key=sha256(m.filing_id.encode()).hexdigest()[:24]
                    c.execute('INSERT OR IGNORE INTO filings VALUES (?,?,?,NULL,?)',(key,m.model_dump_json(),'DISCOVERED',time.time()))
                    items.append({'discovery_id':key,**m.model_dump(mode='json')})
            return {'status':'OK','filings':items}
        except Exception as e:
            code='SEC_CONTACT_REQUIRED' if not listing()['contact_configured'] else 'SEC_DISCOVERY_UNAVAILABLE'
            if getattr(e,'status_code',None):code='SEC_HTTP_'+str(e.status_code)
            raise HTTPException(409,detail={'code':code,'retryable':True}) from e
    @r.post('/import')
    @serialize_submission
    def start(body:Import):
        with db() as c:row=c.execute('SELECT * FROM filings WHERE id=?',(body.discovery_id,)).fetchone()
        if not row:raise HTTPException(404,detail={'code':'DISCOVER_OFFICIAL_FILING_FIRST'})
        from app.product.api import _sec_cached
        try:existing=_sec_cached().catalog_rows
        except Exception:existing=[]
        if json.loads(row['metadata'])['filing_id'] in {f['filing_id'] for f in existing}:
            return {'id':row['id'],'status':'READY','duplicate':True,'store':'EXISTING_DEMO'}
        if row['status'] in {'READY','DOWNLOADING','EXTRACTING','INDEXING'}:return {'id':row['id'],'status':row['status'],'duplicate':True}
        # Removing a library entry never destroys its authenticated generation.
        # Re-add validates that generation instead of rebuilding it with today's date.
        source_root,vector_root=paths(row['id'])
        if (vector_root/'generation_manifest.json').is_file():
            try:
                from app.product.sec_search import SecResearchIndex
                restored=SecResearchIndex(source_root,vector_root,source_root)
                valid=json.loads(row['metadata'])['filing_id'] in {f['filing_id'] for f in restored.catalog_rows}
                restored.close()
                if valid:
                    update(row['id'],'READY');return {'id':row['id'],'status':'READY','reused_authenticated_generation':True}
            except Exception:pass
        if any(r['status'] in {'DOWNLOADING','EXTRACTING','INDEXING'} for r in rows()):raise HTTPException(429,detail={'code':'SEC_IMPORT_BUSY_WAIT_FOR_CURRENT_JOB'})
        update(row['id'],'DOWNLOADING');Thread(target=process,args=(row['id'],),daemon=True).start()
        return {'id':row['id'],'status':'DOWNLOADING'}
    @r.delete('/{key}')
    def remove(key:str):
        with db() as c:
            row=c.execute('SELECT status FROM filings WHERE id=?',(key,)).fetchone()
            if not row:raise HTTPException(404,detail={'code':'USER_FILING_NOT_FOUND'})
            if row['status'] in {'DOWNLOADING','EXTRACTING','INDEXING'}:raise HTTPException(409,detail={'code':'IMPORT_IN_PROGRESS'})
            c.execute('UPDATE filings SET status=?,updated=? WHERE id=?',('CANCELLED',time.time(),key))
        return {'removed_from_library':True,'raw_retained_for_audit':True}
    return r

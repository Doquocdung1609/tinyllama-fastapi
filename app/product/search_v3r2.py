"""Targeted label/unit hardening on the existing FTS/Qdrant/V3 scoring contracts."""
from collections import OrderedDict
from contextlib import closing
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
from threading import RLock
from time import perf_counter
import gc,json,os,re,sqlite3
from app.product.search_v2 import FinancialSearchV2,VERSION as SOURCE_VERSION
from app.product.search_v3 import FinancialSearchV3,intent_for,metrics_in
from app.product.search_v3r import _scope,_label_metric,_spatial_label
from app.product.financial_labels import normalize_label,label_metrics,statement_candidate,specialized_profit,source_row_candidate
from app.product.source_units import header_unit,cell_unit,numeric_syntax,word_units
from app.product.pdf_extract import folded

VERSION='financial-source-precision-v3r3.0'
MAX_CACHE_ENTRIES=30000
MAX_INDEX_BYTES=192*1024*1024

def file_hash(path):
    h=sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(256*1024),b''):h.update(block)
    return h.hexdigest()

def policy_hash():
    files=['search_v3r2.py','financial_labels.py','source_units.py','analysis.py','search_v3.py','query_intent.py']
    return sha256(json.dumps({p:sha256(Path(__file__).with_name(p).read_text(encoding='utf-8').encode()).hexdigest() for p in files},sort_keys=True).encode()).hexdigest()

class CompactRegionIndex:
    def __init__(self,workspace,root):
        self.workspace=workspace;self.root=Path(root);self.source=FinancialSearchV2(workspace,self.root/'source-records');self._lock=RLock();self._cache=None;self.builds=0

    def _verify_source(self):
        w=self.workspace
        if hasattr(w,'verify_generation'):w.verify_generation()
        docs=[d for d in w.list_documents() if d['status']=='READY'];pages=[];chunks=[]
        # Iterate actual payloads one page at a time. No hash/ancestry check is skipped.
        with closing(w._connect()) as db:
            for r in db.execute('SELECT document_id,page,payload,payload_hash FROM page_evidence ORDER BY document_id,page'):
                if sha256(r['payload'].encode()).hexdigest()!=r['payload_hash']:raise ValueError('PDF_PAGE_EVIDENCE_HASH_MISMATCH')
                pages.append((r['document_id'],r['page'],r['payload_hash']))
            for r in db.execute('SELECT id,text,text_hash FROM chunks ORDER BY id'):
                if sha256(r['text'].encode()).hexdigest()!=r['text_hash']:raise ValueError('PDF_CHUNK_SOURCE_MISMATCH')
                chunks.append((r['id'],r['text_hash']))
        for doc in docs:
            if file_hash(w.files/(doc['id']+'.pdf'))!=doc['sha256']:raise ValueError('PDF_SOURCE_HASH_MISMATCH')
        signature=sha256(json.dumps({'version':SOURCE_VERSION,'docs':[(d['id'],d['sha256'],d['issuer'],d['report_period'],d['document_type']) for d in docs],
            'pages':pages,'chunks':chunks},sort_keys=True).encode()).hexdigest()
        return docs,signature

    def prepare(self):
        with self._lock:
            docs,signature=self._verify_source()
            if self._cache and signature==self._cache['source_signature']:
                if file_hash(self._cache['path'])!=self._cache['file_sha256']:raise ValueError('V3R2_INDEX_BYTES_CHANGED')
                source=self.source._cache
                if not source or file_hash(source['path'])!=source['file_sha256']:raise ValueError('V2_INDEX_BYTES_CHANGED')
                return self._cache
            # A changed source rebuilds a new immutable file. Old generations stay intact.
            self.source._cache=None;original=self.source.prepare()
            if original['signature']!=signature:raise ValueError('SOURCE_CHANGED_DURING_PREPARATION')
            if len(original['entries'])>MAX_CACHE_ENTRIES:raise ValueError('REGION_INDEX_CACHE_LIMIT_EXCEEDED')
            identity={'version':VERSION,'source_generation':original['generation'],'policy_sha256':policy_hash()}
            generation=sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest();entries=[];pages=OrderedDict();contexts={};units_cache=OrderedDict()
            for old in original['entries']:
                e=dict(old);key=(e['document_id'],e['page']);context=contexts.setdefault(e['context'][:600],e['context'][:600])
                e.update(context=context,statement_type=statement_candidate(context),scope=_scope(context) or e.get('scope'),unit_header=header_unit(context))
                if e['kind']=='row':
                    if key not in pages:
                        pages[key]=self.workspace.page_evidence(*key)
                        while len(pages)>2:pages.popitem(last=False)
                    page=pages[key];row=next(r for r in page['tables'] if r['id']==e['row_id']);words=row.get('header_word_candidates',[])
                    headers='\n'.join(h['text'] for h in row.get('header_candidates',[]))
                    context=contexts.setdefault(page['text'][:600]+'\n'+headers,page['text'][:600]+'\n'+headers)
                    e.update(context=context,statement_type=statement_candidate(context),scope=_scope(context) or e.get('scope'),unit_header=header_unit(context))
                    if re.search(r'bao cao ket qua.{0,35}kinh doanh',folded(context)):
                        e['statement_type']='INCOME_STATEMENT'
                    unit_key=json.dumps(words,sort_keys=True)
                    if unit_key not in units_cache:
                        units_cache[unit_key]=word_units(words)
                        while len(units_cache)>64:units_cache.popitem(last=False)
                    raw=e['row_label'];candidate=source_row_candidate(raw,e['statement_type']);spatial=normalize_label(_spatial_label(page,row))
                    concepts=label_metrics(raw)
                    # Source-anchored VAS codes and damaged labels can supply a
                    # provisional retrieval candidate, never a reviewed value.
                    if candidate!=normalize_label(raw):
                        concepts=sorted(set(concepts)|set(label_metrics(candidate)))
                    if not specialized_profit(raw):
                        concepts=_label_metric(candidate,e['statement_type'],concepts)
                        concepts=_label_metric(spatial,e['statement_type'],concepts)
                    e.update(metrics=concepts,source_label_candidate=candidate,spatial_label_candidate=spatial,label_normalization={'raw':raw,'retrieval_candidate':candidate,'raw_changed':False,'policy':'CONTROLLED_RETRIEVAL_CANDIDATE_NOT_CERTIFIED_SOURCE_TEXT'},
                        source_region=row.get('source_region'),region_id=row.get('region_id'),region_status='SOURCE_CHECKPOINT',source_cells=[])
                    for raw_cell in row['cells']:
                        cell={k:v for k,v in raw_cell.items() if k!='column_header_candidates'}
                        cell.update(unit_evidence=cell_unit(cell,words,context,units_cache[unit_key]),numeric_syntax=numeric_syntax(cell['text']),source_header_reference=e['page_evidence_sha256'])
                        e['source_cells'].append(cell)
                    e.pop('cells',None)
                else:e['metrics']=metrics_in(normalize_label(e['text']))
                entries.append(e)
            self.root.mkdir(parents=True,exist_ok=True);target=self.root/(generation+'.sqlite3')
            if not target.exists():
                temporary=self.root/(generation+f'.{os.getpid()}.tmp')
                try:
                    with closing(sqlite3.connect(temporary)) as db,db:
                        db.executescript('CREATE TABLE evidence(id TEXT PRIMARY KEY,payload TEXT);CREATE VIRTUAL TABLE fts USING fts5(id UNINDEXED,label,body,context);CREATE TABLE identity(payload TEXT);')
                        db.execute('INSERT INTO identity VALUES(?)',(json.dumps(identity,sort_keys=True),))
                        for e in entries:
                            db.execute('INSERT INTO evidence VALUES(?,?)',(e['evidence_id'],json.dumps(e,ensure_ascii=False,sort_keys=True)))
                            db.execute('INSERT INTO fts VALUES(?,?,?,?)',(e['evidence_id'],folded(e.get('source_label_candidate',e['row_label'])),folded(e['text']),folded(normalize_label(e['context']))))
                    if temporary.stat().st_size>MAX_INDEX_BYTES:raise ValueError('REGION_INDEX_CACHE_LIMIT_EXCEEDED')
                    os.replace(temporary,target)
                finally:
                    if temporary.exists():temporary.unlink()
            if target.stat().st_size>MAX_INDEX_BYTES:raise ValueError('REGION_INDEX_CACHE_LIMIT_EXCEEDED')
            with closing(sqlite3.connect(target)) as db:
                if json.loads(db.execute('SELECT payload FROM identity').fetchone()[0])!=identity:raise ValueError('V3R2_INDEX_IDENTITY_CHANGED')
                expected={e['evidence_id']:e for e in entries};count=0
                for eid,payload in db.execute('SELECT id,payload FROM evidence'):
                    if json.loads(payload)!=expected.get(eid):raise ValueError('V3R2_INDEX_SOURCE_CHANGED')
                    count+=1
                if count!=len(entries):raise ValueError('V3R2_INDEX_SOURCE_CHANGED')
                expected_fts=sorted((e['evidence_id'],folded(e.get('source_label_candidate',e['row_label'])),folded(e['text']),folded(normalize_label(e['context']))) for e in entries)
                if sorted(db.execute('SELECT id,label,body,context FROM fts'))!=expected_fts:raise ValueError('V3R2_FTS_SOURCE_CHANGED')
            self._cache={'generation':generation,'signature':generation,'source_signature':signature,'documents':docs,'entries':entries,'path':target,'file_sha256':file_hash(target)};self.builds+=1
            # Keep only source verification metadata,not a second full entry corpus.
            self.source._cache={k:v for k,v in original.items() if k!='entries'};self.source._cache['entries']=[]
            pages.clear();units_cache.clear();del original,expected_fts,expected;gc.collect()
            return self._cache

    def cache_stats(self):return {'builds':self.builds,'entries':len(self._cache['entries']) if self._cache else 0,'max_entries':MAX_CACHE_ENTRIES,'max_index_bytes':MAX_INDEX_BYTES,'retained_page_views':0,'retained_source_entries':0}

class FinancialSearchV3R2(FinancialSearchV3):
    def _metric_ranking_adjustment(self,entry,intent,query):
        # A known, different metric is weaker than an unclassified source row.
        # This only changes ordering; source evidence and eligibility are untouched.
        if intent.metrics and entry['metrics'] and not set(intent.metrics).intersection(entry['metrics']):return -12
        # A source row can carry the exact requested phrase even when damaged OCR
        # prevents safe ontology classification. Keep it unreviewed.
        if entry['kind']=='row' and not intent.metrics and specialized_profit(query):
            label=normalize_label(entry.get('source_label_candidate') or entry['row_label']).lower()
            phrase=normalize_label(query).lower()
            if len(label)>=12 and label in phrase:return 4
        return 0

    def __init__(self,workspace,index_root,resources=None):
        self.workspace=workspace;self.base=CompactRegionIndex(workspace,index_root);self.resources=resources;self._last_entries={}

    def _source_entries(self,snapshot,docs):
        entries=[dict(e) for e in snapshot['entries'] if e['document_id'] in docs];self._last_entries={e['evidence_id']:e for e in entries};return entries

    def _query_intent(self,query):
        normalized=normalize_label(query);intent,quarters=intent_for(normalized)
        if specialized_profit(normalized):return replace(intent,metrics=()),quarters
        metrics=label_metrics(normalized)
        if not metrics and 'profit for the year' in normalized.lower():metrics=['net_income']
        if metrics and not intent.metrics:
            from app.product.query_intent import METRICS
            kinds={METRICS[m][0] for m in metrics}
            intent=replace(intent,metrics=tuple(metrics),statement=intent.statement if intent.statement_explicit else next(iter(kinds)) if len(kinds)==1 else None)
        return intent,quarters

    def _run_search(self,*args,**kwargs):
        with self.base._lock:
            result=super().search(*args,**kwargs);docs={d['id']:d for d in self.base._cache['documents']}
            result.update(profile='V3R2',index_version=VERSION,cache=self.base.cache_stats())
            for hit in result['results']:
                source=self._last_entries.get(hit['evidence_id'],{});doc=docs[hit['document_id']]
                for key in ['source_label_candidate','label_normalization','source_cells','source_region','region_id','region_status']:
                    if key in source:hit[key]=source[key]
                if 'source_cells' in hit:
                    hit['source_cells']=[{**c,'financial_evidence_status':'FINANCIAL_EVIDENCE_REVIEWED' if hit['numeric_answer_eligible'] and any(f['source_display']==c['text'] and f['box']==c.get('box') for f in hit.get('reviewed_facts',[])) else 'FINANCIAL_EVIDENCE_REVIEW_PENDING'} for c in hit['source_cells']]
                hit['extraction_coverage_status']=doc.get('extraction_coverage_status','LEGACY_COVERAGE_NOT_ASSESSED');hit['coverage_warnings']=doc.get('coverage_warnings',[])
                hit['derived_generation']=doc.get('derived_generation')
            return result

    def search(self,*args,**kwargs):
        if self.resources:
            with self.resources.claim('SEARCH',minimum_mb=256,timeout=10):return self._run_search(*args,**kwargs)
        return self._run_search(*args,**kwargs)

    def prewarm(self):
        start=perf_counter()
        if self.resources:
            with self.resources.claim('INDEX_PREPARATION',minimum_mb=768):snapshot=self.base.prepare()
        else:snapshot=self.base.prepare()
        return {'status':'READY','generation':snapshot['generation'],'prepare_ms':round((perf_counter()-start)*1000,2),'cache':self.base.cache_stats()}

"""Opt-in region-context index. V3 weights/safety remain intact;new source fields only."""
from contextlib import closing
from dataclasses import replace
from hashlib import sha256
import json,os,re,sqlite3
from pathlib import Path
from threading import RLock
from time import perf_counter

from app.product.search_v2 import FinancialSearchV2,scope_of,statement_kind,unit_header
from app.product.search_v3 import FinancialSearchV3,row_metrics,metrics_in,intent_for
from app.product.pdf_extract import folded

VERSION='financial-region-search-v3r.1'


def _kind(text):
    t=folded(text);kind=statement_kind(text)
    if re.search(r'consolidated statements? of financial position',t):return 'BALANCE_SHEET'
    if 'statements of comprehensive income' in t or 'statements of profit or loss' in t:return 'INCOME_STATEMENT'
    if 'statements of cash flows' in t:return 'CASH_FLOW'
    return kind


def _scope(text):
    t=folded(text)
    if re.search(r'\bconsolidated\b',t) and not re.search(r'\bunconsolidated\b',t):return 'CONSOLIDATED'
    return scope_of(text)


def _spatial_label(page,row):
    line=min(page['lines'],key=lambda l:abs(l['reading_y']-row['reading_y']),default=None)
    if not line:return row['row_label']
    words=sorted(line['words'],key=lambda w:w['rx']);chosen=[];end=None
    for w in words:
        if chosen and end is not None and w['rx']-end>max(25,w['rh']*3):break
        chosen.append(w['text']);end=w['rx']+w.get('rw',pymupdf_width(w))
    return ' '.join(chosen).strip()


def pymupdf_width(w):return w['box'][2]-w['box'][0]


def _label_metric(label,kind,base):
    if base or kind!='INCOME_STATEMENT':return base
    # Exact spatial source-label concepts;continuing/discontinued and attributable
    # profit rows remain distinct from the whole-year total.
    t=folded(label).strip(' .:-')
    return {'profit for the year':['net_income'],'net earnings':['net_income'],'sales':['net_revenue'],'revenue':['net_revenue'],
        'profit before tax from continuing operations':['pretax_income'],'earnings before income taxes':['pretax_income']}.get(t,base)


class RegionContextIndex:
    def __init__(self,workspace,root,aliases=False):
        self.workspace=workspace;self.root=Path(root);self.aliases=aliases;self._lock=RLock();self._cache=None
        self.source=FinancialSearchV2(workspace,self.root/'source-records')

    def prepare(self):
        if hasattr(self.workspace,'verify_generation'):self.workspace.verify_generation()
        original=self.source.prepare()
        identity={'version':VERSION,'source_generation':original['generation'],'aliases':self.aliases,
            'code_sha256':sha256(Path(__file__).read_text(encoding='utf-8').encode()).hexdigest()}
        generation=sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()
        if self._cache and self._cache['generation']==generation:
            if sha256(self._cache['path'].read_bytes()).hexdigest()!=self._cache['file_sha256']:raise ValueError('REGION_INDEX_BYTES_CHANGED')
            return self._cache
        pages={};entries=[]
        for source in original['entries']:
            e=dict(source)
            key=(e['document_id'],e['page'])
            if key not in pages:pages[key]=self.workspace.page_evidence(*key)
            page=pages[key]
            if e['kind']=='row':
                row=next(r for r in page['tables'] if r['id']==e['row_id']);rid=row.get('region_id')
                region=next((r for r in page.get('regions',[]) if r['id']==rid),None)
                headers='\n'.join(h['text'] for h in row.get('header_candidates',[]))
                e.update(region_id=rid,source_region=row.get('source_region'),source_label_candidate=_spatial_label(page,row),
                    source_cells=row['cells'],region_status=region.get('status') if region else 'NATIVE_SOURCE',context=page['text'][:600]+'\n'+headers)
            e['statement_type']=_kind(e['context']);e['scope']=_scope(e['context']) or e.get('scope');e['unit_header']=unit_header(e['context'])
            base=row_metrics(e['row_label']) if e['kind']=='row' else metrics_in(e['text'])
            e['metrics']=_label_metric(e.get('source_label_candidate',''),e['statement_type'],base) if self.aliases else base
            entries.append(e)
        self.root.mkdir(parents=True,exist_ok=True);path=self.root/(generation+'.sqlite3')
        if not path.exists():
            temporary=self.root/(generation+f'.{os.getpid()}.tmp')
            try:
                with closing(sqlite3.connect(temporary)) as db,db:
                    db.executescript('CREATE TABLE evidence(id TEXT PRIMARY KEY,payload TEXT); CREATE VIRTUAL TABLE fts USING fts5(id UNINDEXED,label,body,context); CREATE TABLE identity(payload TEXT);')
                    db.execute('INSERT INTO identity VALUES(?)',(json.dumps(identity,sort_keys=True),))
                    for e in entries:
                        db.execute('INSERT INTO evidence VALUES(?,?)',(e['evidence_id'],json.dumps(e,ensure_ascii=False,sort_keys=True)))
                        db.execute('INSERT INTO fts VALUES(?,?,?,?)',(e['evidence_id'],folded(e.get('source_label_candidate',e['row_label'])),folded(e['text']),folded(e['context'])))
                os.replace(temporary,path)
            finally:
                if temporary.exists():temporary.unlink()
        with closing(sqlite3.connect(path)) as db:
            if json.loads(db.execute('SELECT payload FROM identity').fetchone()[0])!=identity:raise ValueError('REGION_INDEX_IDENTITY_CHANGED')
            stored={i:json.loads(p) for i,p in db.execute('SELECT id,payload FROM evidence')}
            if stored!={e['evidence_id']:e for e in entries}:raise ValueError('REGION_INDEX_SOURCE_CHANGED')
            expected=sorted((e['evidence_id'],folded(e.get('source_label_candidate',e['row_label'])),folded(e['text']),folded(e['context'])) for e in entries)
            if sorted(db.execute('SELECT id,label,body,context FROM fts'))!=expected:raise ValueError('REGION_FTS_SOURCE_CHANGED')
        self._cache={**original,'generation':generation,'signature':generation,'path':path,'file_sha256':sha256(path.read_bytes()).hexdigest(),'entries':entries}
        return self._cache


class FinancialSearchV3R(FinancialSearchV3):
    def __init__(self,workspace,index_root,region_context=True,aliases=True):
        super().__init__(workspace,index_root)
        self.region_context=region_context;self.aliases=aliases;self._entry_cache=None;self._last_entries={}
        if region_context:self.base=RegionContextIndex(workspace,index_root,aliases)

    def _source_entries(self,snapshot,docs):
        if self._entry_cache is None or self._entry_cache[0]!=snapshot['generation']:
            values=[dict(e) if self.region_context else dict(e,metrics=row_metrics(e['row_label']) if e['kind']=='row' else metrics_in(e['text'])) for e in snapshot['entries']]
            self._entry_cache=(snapshot['generation'],values)
        entries=[dict(e) for e in self._entry_cache[1] if e['document_id'] in docs]
        self._last_entries={e['evidence_id']:e for e in entries}
        return entries

    def _query_intent(self,query):
        intent,quarters=intent_for(query)
        if self.aliases and not intent.metrics:
            q=folded(query)
            metric='net_income' if 'profit for the year' in q and not any(t in q for t in ['continuing','discontinued','attributable']) else None
            if metric:intent=replace(intent,metrics=(metric,),statement='INCOME_STATEMENT')
        return intent,quarters

    def prewarm(self):
        start=perf_counter()
        with self.base._lock:
            snapshot=self.base.prepare();self._source_entries(snapshot,{d['id']:d for d in snapshot['documents']})
        return {'status':'READY','generation':snapshot['generation'],'prepare_ms':round((perf_counter()-start)*1000,2)}

    def search(self,*args,**kwargs):
        # V3 holds this same reentrant lock;metadata enrichment cannot race another query.
        with self.base._lock:
            result=super().search(*args,**kwargs)
            result.update(profile='V3R',index_version=VERSION)
            result['generation']=sha256((VERSION+result['generation']+str(self.region_context)+str(self.aliases)).encode()).hexdigest()
            for hit in result['results']:
                e=self._last_entries.get(hit['evidence_id'],{});doc=self.workspace.document(hit['document_id'])
                for key in ['region_id','source_region','source_label_candidate','source_cells','region_status']:
                    if key in e:hit[key]=e[key]
                hit['extraction_coverage_status']=doc.get('extraction_coverage_status','LEGACY_COVERAGE_NOT_ASSESSED')
                hit['coverage_warnings']=doc.get('coverage_warnings',[]);hit['derived_generation']=doc.get('derived_generation')
            return result

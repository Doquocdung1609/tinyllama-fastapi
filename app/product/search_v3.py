"""Source retrieval, context validation and numeric eligibility are separate decisions.

V2 implementations and source generations are immutable comparators. This adapter
reuses authenticated source records, never automatically certifies extracted cells.
"""
from contextlib import closing
from dataclasses import replace
from hashlib import sha256
from time import perf_counter
import json
import re
import sqlite3
from difflib import SequenceMatcher
from functools import lru_cache

from app.product.analysis import eligible_facts
from app.product.pdf_extract import folded
from app.product.query_intent import understand, METRICS, STOP, metric_matches, lexical_terms
from app.product.search_v2 import FinancialSearchV2, statement_kind, scope_of

VERSION = 'financial-search-v3.2'
ALIASES = {
    'assets': ['total of assets', 'assets in total'],
    'equity': ['total equity', 'owners equity', 'shareowners equity'],
    'net_revenue': ['net revenues', 'net operating revenues'],
    'financial_revenue': ['finance income', 'financial revenue'],
    'pretax_income': ['income before income taxes', 'profit before income tax'],
    'operating_cashflow': ['net cash provided by operating activities'],
}


def metrics_in(text):
    value = folded(text)
    return sorted(set(metric_matches(text)) | {m for m, terms in ALIASES.items()
        if any(re.search(r'(?<!\w)' + re.escape(t) + r'(?!\w)', value) for t in terms)})


@lru_cache(maxsize=8192)
def row_metrics(text):
    exact=metrics_in(text)
    if exact:return exact
    words=re.findall(r'\w+',folded(text));found=[]
    for metric,(_,aliases) in METRICS.items():
        for alias in aliases:
            term=folded(alias);n=len(term.split())
            if len(term)<10:continue
            for i in range(max(0,len(words)-n+1)):
                span=' '.join(words[i:i+n])
                if SequenceMatcher(None,term,span).ratio()>=.90:found.append(metric)
    # Ambiguous fuzzy concepts stay unclassified. Raw label is never rewritten.
    return sorted(set(found)) if len(set(found))==1 else []


def intent_for(query):
    intent = understand(query)
    metrics = metrics_in(query)
    if intent.operation == 'ACCOUNTING_IDENTITY':
        metrics = ['assets', 'liabilities', 'equity']
    q = folded(query)
    quarters = sorted(set(re.findall(r'\b(?:quy|quarter)\s+(iv|iii|ii|i|[1-4])\b', q)))
    months = {name: i for i, name in enumerate(
        ['january','february','march','april','may','june','july','august','september','october','november','december'], 1)}
    dates = list(intent.dates)
    for month, day, year in re.findall(r'\b('+'|'.join(months)+r')\s+(\d{1,2}),?\s+((?:19|20)\d{2})\b', q):
        from datetime import date
        try: dates.append(date(int(year), months[month], int(day)).isoformat())
        except ValueError: dates.append('INVALID_DATE')
    statements = {METRICS[m][0] for m in metrics}
    intent = replace(intent, metrics=tuple(metrics), dates=tuple(sorted(set(dates))),
        statement=intent.statement if intent.statement_explicit else next(iter(statements)) if len(statements)==1 else None)
    return intent, quarters


def entity_conflict(query, docs):
    """Resolve known source aliases; unresolved query terms block numeric eligibility.

    This deliberately conservative vocabulary guard is not a named-entity model.
    Unknown terms retain related retrieval, including ordinary unseen paraphrases.
    """
    q = folded(query)
    aliases = {}
    for doc in docs:
        words = re.sub(r'^(cong ty me|cong ty co phan|tap doan|ngan hang)\s+', '', folded(doc['issuer']))
        ticker = next((t for t in re.split(r'[^a-z0-9]+', folded(doc['filename'])) if t.isalpha() and 2<=len(t)<=7), '')
        aliases[doc['id']] = [a for a in [words, ticker] if len(a)>1]
    known = {doc_id for doc_id, names in aliases.items() if any(re.search(r'(?<!\w)'+re.escape(n)+r'(?!\w)', q) for n in names)}
    ignored = {'VND','USD','BCTC','OCR','RRF','AI','SEC','PDF','VND','KRW'}
    entity_text=re.sub(r'\b(?:quy|quarter)\s+(?:iv|iii|ii|i)\b','',query,flags=re.IGNORECASE)
    acronyms = set(re.findall(r'\b[A-Z]{2,7}\b', entity_text)) - ignored
    known_words = {w for names in aliases.values() for n in names for w in n.split()}
    unknown = any(folded(a) not in known_words for a in acronyms)
    clause = re.search(r'\b(?:cua|of|for)\s+(.+?)(?=\s+(?:tai|ngay|nam|cuoi|dau|la|bao|quy|as|on|in|separate|consolidated|at)\b|[?!.]|$)', q)
    if clause:
        generic = set('cong ty me doanh nghiep ngan hang nay da duoc chon tat ca tai lieu vao the company parent selected this all total assets year'.split())
        unknown = unknown or bool(set(re.findall(r'[^\W\d_]+', clause[1])) - generic - known_words)
    vocabulary=set(STOP)|known_words|set('find show tell get search source sources statement statements consolidated separate unconsolidated original restated unrestated adjustment at on end beginning year quarter january february march april may june july august september october november december i ii iii iv vnd usd krw balance sheet income cash flow accounting identity total liabilities equity tong tim cho biet xem tra cuu trich dan bang can doi bang chung nguon bao cao hop nhat rieng cong ty me cua vao tai thoi diem ket thuc cuoi dau nam ngay thang quy so lieu muc phan trinh bay lai sau dieu chinh da cong bo chua khong phai va hay la bao nhieu tang giam so voi kiem phuong trinh ke toan ket qua hoat dong kinh doanh toan bo tu trong duoc chon tai lieu nay'.split())
    for _,terms in METRICS.values():
        for term in terms:vocabulary.update(folded(term).split())
    for terms in ALIASES.values():
        for term in terms:vocabulary.update(folded(term).split())
    unknown=unknown or bool({word for word in re.findall(r'[^\W\d_]+',q) if len(word)>1}-vocabulary)
    return known, unknown


def validate_entry(entry, intent, quarters, unknown_entity):
    conflicts = []
    context = folded(entry['context'])
    if unknown_entity: conflicts.append('ENTITY_NOT_PROVEN')
    if intent.metrics and not set(intent.metrics)&set(entry['metrics']): conflicts.append('METRIC_NOT_MATCHED')
    if intent.scope == 'AMBIGUOUS' or intent.basis == 'AMBIGUOUS': conflicts.append('AMBIGUOUS_SCOPE_OR_BASIS')
    if intent.scope and entry['scope'] != intent.scope: conflicts.append('SCOPE_NOT_PROVEN')
    if intent.statement_explicit and entry['statement_type'] != intent.statement: conflicts.append('REQUESTED_STATEMENT_NOT_PROVEN')
    if intent.years and any(y not in context for y in intent.years): conflicts.append('PERIOD_NOT_PROVEN')
    if intent.dates:
        def date_present(value):
            if value == 'INVALID_DATE': return False
            year, month, day = value.split('-')
            return (value in context or '/'.join([day,month,year]) in context or
                bool(re.search(r'\b'+day.lstrip('0')+r'\s+thang\s+'+month.lstrip('0')+r'\s+nam\s+'+year, context)))
        if not all(date_present(d) for d in intent.dates): conflicts.append('EXACT_DATE_NOT_PROVEN')
    if quarters:
        numbers = {'i':'1','ii':'2','iii':'3','iv':'4'}
        if not all(re.search(r'\bquy\s+(?:'+re.escape(q)+'|'+numbers.get(q,q)+r')\b', context) for q in quarters):
            conflicts.append('QUARTER_NOT_PROVEN')
    if intent.basis: conflicts.append('REQUESTED_BASIS_NOT_REVIEWED')
    if intent.unit and entry.get('unit_header') != intent.unit: conflicts.append('UNIT_NOT_PROVEN')
    return conflicts


def compatible_facts(entry, intent, quarters, facts, unknown_entity):
    if unknown_entity or not intent.metrics or entry['kind']!='row' or intent.scope=='AMBIGUOUS' or intent.basis=='AMBIGUOUS': return []
    bound = [f for f in facts if f['document_id']==entry['document_id'] and f['row_id']==entry['row_id'] and f['metric'] in intent.metrics
        and (not intent.scope or f['statement_scope']==intent.scope) and (not intent.basis or f['basis']==intent.basis)
        and (not intent.unit or f['unit']==intent.unit) and (not intent.dates or f['period'] in intent.dates)
        and (not intent.years or f['period'][:4] in intent.years)]
    if intent.statement_explicit and entry['statement_type']!=intent.statement: return []
    if intent.dates and not set(intent.dates)<={f['period'] for f in bound}: return []
    if intent.years and not set(intent.years)<={f['period'][:4] for f in bound}: return []
    if not intent.scope and len({f['statement_scope'] for f in bound})>1: return []
    if not intent.basis and len({f['basis'] for f in bound})>1: return []
    if not intent.dates and intent.operation=='LOOKUP' and len({f['period'] for f in bound})>1: return []
    if quarters:
        numbers={'i':1,'ii':2,'iii':3,'iv':4}
        wanted={numbers.get(q,int(q) if q.isdigit() else 0) for q in quarters}
        # Duration statements need an explicitly reviewed start/end, not just a filing's year.
        if any(not f.get('period_start') or (int(f['period'][5:7])+2)//3 not in wanted or
            int(f['period_start'][5:7]) != (int(f['period'][5:7])-1)//3*3+1 for f in bound): return []
    return bound


class FinancialSearchV3:
    def _metric_ranking_adjustment(self, entry, intent, query):
        return 0

    def __init__(self, workspace, index_root):
        self.workspace=workspace
        self.base=FinancialSearchV2(workspace,index_root)

    def _source_entries(self,snapshot,docs):
        return [dict(e,metrics=row_metrics(e['row_label']) if e['kind']=='row' else metrics_in(e['text'])) for e in snapshot['entries'] if e['document_id'] in docs]

    def _query_intent(self,query):return intent_for(query)

    def search(self, query, mode='hybrid', top_k=5, document_ids=None):
        if mode not in {'bm25','dense','hybrid'} or not 1<=top_k<=20 or not 2<=len(query)<=2000: raise ValueError('INVALID_V3_SEARCH_REQUEST')
        started=perf_counter(); intent,quarters=self._query_intent(query)
        with self.base._lock:
            snapshot=self.base.prepare()
            requested=set(document_ids or [d['id'] for d in snapshot['documents']])
            known,unknown=entity_conflict(query,snapshot['documents'])
            if known: requested &= known
            docs={d['id']:d for d in snapshot['documents'] if d['id'] in requested}
            result={'status':'READY','mode':mode,'profile':'V3','index_version':VERSION,'generation':sha256((VERSION+snapshot['generation']+json.dumps(sorted(docs))).encode()).hexdigest(),
                'intent':{**intent.public(),'quarters':quarters,'entity_scope':{'resolved_document_ids':sorted(docs),'unrecognized_name':unknown}},
                'results':[],'evidence_status':'NO_SUFFICIENT_EVIDENCE','latency_ms':0,
                'score_semantics':'ORDINAL_RETRIEVAL_SCORE_NOT_NUMERIC_ANSWER_CONFIDENCE'}
            entries=self._source_entries(snapshot,docs)
            for e in entries:
                # Source-title pattern tolerates intervening OCR tokens; ranking context
                # only, never a repaired/certified column heading.
                if re.search(r'bao cao ket qua.{0,35}kinh doanh',folded(e['context'])):
                    e['statement_type']='INCOME_STATEMENT'
            candidate_scopes={e['scope'] for e in entries if e['kind']=='row' and set(e['metrics'])&set(intent.metrics)}-{None}
            scope_ambiguous=not intent.scope and len(candidate_scopes)>1
            terms=lexical_terms(query,intent)+[a for m in intent.metrics for a in ALIASES.get(m,[])]
            expression=' OR '.join('"'+t.replace('"','""')+'"' for t in terms)
            scores={}
            if expression and docs:
                with closing(sqlite3.connect(snapshot['path'])) as db:
                    for eid,score in db.execute('SELECT id,bm25(fts,0,4,1,.2) FROM fts WHERE fts MATCH ? ORDER BY bm25(fts,0,4,1,.2),id LIMIT 500',(expression,)):
                        scores[eid]=-float(score)
            dense_ids={}
            if docs and mode!='bm25':
                found=self.workspace.search(query,mode,20,list(docs))
                dense_ids={h['chunk_id']:i for i,h in enumerate(found['results'],1)}
            facts=eligible_facts(self.workspace,list(docs))
            ranked=[]
            for e in entries:
                metric_hit=bool(set(e['metrics'])&set(intent.metrics))
                if not (metric_hit or e['evidence_id'] in scores or e['chunk_id'] in dense_ids): continue
                conflicts=validate_entry(e,intent,quarters,unknown)
                bound=compatible_facts(e,intent,quarters,facts,unknown)
                if scope_ambiguous:
                    bound=[]
                    conflicts.append('CLARIFY_SEPARATE_OR_CONSOLIDATED')
                if bound:
                    conflicts=[c for c in conflicts if c not in {'PERIOD_NOT_PROVEN','EXACT_DATE_NOT_PROVEN','REQUESTED_BASIS_NOT_REVIEWED','UNIT_NOT_PROVEN','SCOPE_NOT_PROVEN','QUARTER_NOT_PROVEN'}]
                score=min(scores.get(e['evidence_id'],0),10)+20*metric_hit+5*(metric_hit and e['kind']=='row')
                if intent.statement: score+=6 if e['statement_type']==intent.statement else -2
                score-=4*len(conflicts)
                score+=self._metric_ranking_adjustment(e,intent,query)
                score+=2*bool(bound)+(1/(60+dense_ids[e['chunk_id']]) if e['chunk_id'] in dense_ids else 0)
                ranked.append((score,e,conflicts,bound))
            ranked.sort(key=lambda r:(-r[0],r[1]['evidence_id']))
            # Multi-source operands receive one representative each before duplicate metrics.
            if len(intent.metrics)>1:
                picked=[];seen=set()
                for item in ranked:
                    new=(set(item[1]['metrics'])&set(intent.metrics))-seen
                    if new and item[1]['kind']=='row':picked.append(item);seen.update(new)
                ranked=picked+[r for r in ranked if r not in picked]
            for rank,(score,e,conflicts,bound) in enumerate(ranked[:top_k],1):
                doc=docs[e['document_id']];verified=bool(bound) and not conflicts
                text=e['text'];box=e['box']
                if verified:
                    text=e['row_label']+' | '+' | '.join(f"{f['source_display']} {f['unit']} · {f['period']} · {f['basis']}" for f in bound);box=bound[0]['box']
                result['results'].append({'rank':rank,'score':score,'chunk_id':e['chunk_id'],'evidence_id':e['evidence_id'],
                    'document_id':doc['id'],'issuer':doc['issuer'],'filename':doc['filename'],'document_type':doc['document_type'],'report_period':doc['report_period'],
                    'page':e['page'],'row_id':e['row_id'],'row_label':e['row_label'],'metric_ids':e['metrics'],'statement_scope':e['scope'],'statement_type':e['statement_type'],
                    'unit_header':e['unit_header'],'text':text[:1400],'box':box,'source_sha256':doc['sha256'],'page_evidence_sha256':e['page_evidence_sha256'],
                    'numeric_answer_eligible':verified,'reviewed_facts':bound if verified else [],'conflicts':conflicts,
                    'verification':'LOCALLY_REVIEWED_SOURCE_CELL' if verified else None,
                    'evidence_match':'REVIEWED_ANSWER_EVIDENCE' if verified else 'MATCHED_UNVERIFIED_ROW' if not conflicts and e['kind']=='row' else 'RELATED_PASSAGE',
                    'validation_status':'COMPATIBLE_REVIEWED_CELL' if verified else 'UNVERIFIED_OR_CONTEXT_INCOMPLETE',
                    'provenance_status':'VERIFIED_LOCAL_PDF_BYTES','source_kind':'PDF'})
            result['evidence_status']='REVIEWED_ANSWER_EVIDENCE' if any(h['numeric_answer_eligible'] for h in result['results']) else 'RELATED_UNVERIFIED_EVIDENCE' if result['results'] else 'NO_SUFFICIENT_EVIDENCE'
            result['reason']='NUMERIC_ANSWER_REQUIRES_REVIEWED_MATCHING_CELLS' if result['evidence_status']!='REVIEWED_ANSWER_EVIDENCE' else None
            if unknown:result['reason']='ENTITY_OR_QUERY_CONTEXT_NOT_PROVEN; RELATED_SOURCES_ARE_NOT_AN_ANSWER'
            result['latency_ms']=round((perf_counter()-started)*1000,2)
            return result


def search_sec_v3(index,query,mode='hybrid',top_k=5,ticker='',report_period=''):
    """Rerank authenticated immutable parents; no new SEC generation or verified values."""
    from app.financial_index.corpus import verified_source
    started=perf_counter();intent,_=intent_for(query)
    baseline=index.search(query,mode,20,ticker,report_period)
    selected={r['filing_id']:r for r in index.catalog_rows if (not ticker or r['ticker']==ticker.upper()) and (not report_period or r['report_period']==report_period)}
    ranks={h['chunk_id']:i for i,h in enumerate(baseline['results'],1)};scored=[]
    table_concepts={}
    for p in index.parents:
        c=p['chunk'];key=(c.filing_id,c.source_location.table_id)
        if c.source_location.table_id:table_concepts.setdefault(key,set()).update(metrics_in(c.metadata.get('row_label','')))
    words=set(re.findall(r'\w+',folded(query)))
    for parent in index.parents:
        c=parent['chunk']
        if c.filing_id not in selected:continue
        label=c.metadata.get('row_label','');exact=bool(set(metrics_in(label))&set(intent.metrics))
        if not exact and parent['cid'] not in ranks:continue
        section=folded(c.source_location.section or '')
        kind=statement_kind(section)
        if 'earnings' in section or 'operations' in section or 'income' in section:kind='INCOME_STATEMENT'
        concepts=table_concepts.get((c.filing_id,c.source_location.table_id),set())
        if kind=='UNKNOWN' and 'net_revenue' in concepts and concepts&{'net_income','pretax_income'}:
            # Incomplete SEC heading context: infer candidate statement relevance from
            # authenticated sibling row concepts. Never upgrade column verification.
            kind='INCOME_STATEMENT'
        score=20*exact+8*(kind==intent.statement if intent.statement else False)+sum(w in folded(c.text) for w in words)/max(1,len(words))
        score+=3*any(folded(label)==folded(alias) for m in intent.metrics for alias in METRICS[m][1]+ALIASES.get(m,[]))
        if intent.years:score+=2*all(y in c.text for y in intent.years)
        if parent['cid'] in ranks:score+=1/(60+ranks[parent['cid']])
        scored.append((score,parent,kind))
    scored.sort(key=lambda r:(-r[0],r[1]['cid']))
    hits=[]
    for rank,(score,p,kind) in enumerate(scored[:top_k],1):
        c=p['chunk'];canonical=verified_source(p['frozen'],cache=index._cache,generation=index.identity['generation'])
        if p['cid'] not in canonical or canonical[p['cid']].model_dump(mode='json')!=c.model_dump(mode='json'):raise ValueError('SEC_PARENT_SOURCE_CHANGED')
        doc=selected[c.filing_id]
        hits.append({'rank':rank,'score':score,'chunk_id':p['cid'],'evidence_id':p['cid'],'text':c.text[:1800],'source_kind':'SEC',
            'ticker':doc['ticker'],'issuer':doc['issuer'],'report_period':doc['report_period'],'source_sha256':doc['raw_sha256'],'source_url':doc['source_url'],
            'filing_id':c.filing_id,'accession':doc['accession'],'source_location':c.source_location.model_dump(mode='json'),
            'statement_type':kind,'statement_type_basis':'SOURCE_SECTION_OR_SIBLING_ROW_CONCEPT_CANDIDATE','metric_ids':metrics_in(c.metadata.get('row_label','')),'numeric_answer_eligible':False,'reviewed_facts':[],
            'evidence_match':'RELATED_PASSAGE','conflicts':['SEC_COLUMN_NOT_REVIEWED'],'provenance_status':'VERIFIED_LOCAL_SEC_SOURCE_BYTES'})
    return {**baseline,'results':hits,'profile':'V3','generation':sha256((VERSION+index.identity['generation']).encode()).hexdigest(),
        'intent':intent.public(),'evidence_status':'RELATED_UNVERIFIED_EVIDENCE' if hits else 'NO_SUFFICIENT_EVIDENCE',
        'reason':'SEC_SOURCE_RETRIEVAL_ONLY; NO_NUMERIC_COLUMN_CERTIFICATION','latency_ms':round((perf_counter()-started)*1000,2)}

"""Read-only native-cell candidates and source headings; never writes an index."""
from functools import lru_cache
from contextlib import closing
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from datetime import datetime
import json
import re
import pymupdf
from app.product.pdf_extract import folded

VERSION='ORIGINAL_NATIVE_CELLS_V2'
NUMBER=re.compile(r'^\(?[+-]?\d[\d,]*(?:\.\d+)?\)?%?$')

def cell_id(c):
    keys=('document_id','source_sha256','page','box','header_box','row_label','metric','period','value_raw','unit','statement_scope','basis')
    return 'cellv2_'+sha256(json.dumps({k:c.get(k) for k in keys},sort_keys=True).encode()).hexdigest()[:28]

def lines(words):
    out=[]
    for w in sorted(words,key=lambda w:(w[1],w[0])):
        group=next((g for g in out[-3:] if abs(g[0]-w[1])<2),None)
        if group is None:group=[w[1],[]];out.append(group)
        group[1].append(w)
    return [(y,sorted(ws,key=lambda w:w[0])) for y,ws in out]

def union_box(ws):return [min(w[0] for w in ws),min(w[1] for w in ws),max(w[2] for w in ws),max(w[3] for w in ws)]

def metric_for(label,section,percent):
    name=folded(re.sub(r'\s*\(\d+\)\s*$','',label)).strip(' :')
    direct={'total net sales':'net_revenue','net income':'net_income','operating income':'operating_income',
        'gross margin':'gross_profit','total gross margin':'gross_profit','total assets':'assets',
        'total gross margin percentage':'gross_margin_percentage'}
    if name in direct:return direct[name]
    if name in {'products','services'}:
        suffix='gross_margin_percentage' if percent and 'gross margin' in section else 'gross_margin' if 'gross margin' in section else 'cost_of_sales' if 'cost of sales' in section else 'net_sales' if 'net sales' in section else None
        return name+'_'+suffix if suffix else None
    if name in {'americas','europe','greater china','japan','rest of asia pacific','u.s.'} and 'net sales' in section:
        return ('us' if name=='u.s.' else name.replace(' ','_'))+'_net_sales'
    return None

@lru_cache(maxsize=4)
def _native_catalog(path,source_hash,document_id):
    """Candidates are bound to source bytes; the independent gate reopens cells."""
    if sha256(Path(path).read_bytes()).hexdigest()!=source_hash:raise ValueError('PDF_SOURCE_HASH_MISMATCH')
    result=[]
    with pymupdf.open(path) as pdf:
        texts=[p.get_text() for p in pdf]
        annual=next(((i+1,t) for i,t in enumerate(texts) if re.search(r'CONSOLIDATED STATEMENTS OF (?:OPERATIONS|INCOME)',t)),None)
        dates={}
        if annual:
            for month,day,year in re.findall(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s*(20\d{2})',annual[1][:1200]):
                dates[year]=datetime.strptime(f'{month} {day} {year}','%B %d %Y').date().isoformat()
        if annual:
            for y,words in lines(pdf[annual[0]-1].get_text('words')):
                years=[v for v in words if re.fullmatch(r'20\d{2}',v[4])]
                if len(years)<2:continue
                centers=[(v[0]+v[2])/2 for v in years];gap=min(b-a for a,b in zip(centers,centers[1:]))
                for v,center in zip(years,centers):
                    nearby=pdf[annual[0]-1].get_text(clip=pymupdf.Rect(center-gap/2,max(0,v[1]-40),center+gap/2,v[3]+1))
                    ds=re.findall(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?',nearby)
                    if len(ds)==1:dates[v[4]]=datetime.strptime(f'{ds[0][0]} {ds[0][1]} {v[4]}','%B %d %Y').date().isoformat()
        currency_proof=next(((i+1,t) for i,t in enumerate(texts) if re.search(r'net sales and gross margins as expressed in U\.S\. dollars',t,re.I)),None)
        for page_no,page in enumerate(pdf,1):
            if page.rotation:continue
            rows=lines(page.get_text('words'));page_text=texts[page_no-1]
            for ri,(y,ws) in enumerate(rows):
                years=[w for w in ws if re.fullmatch('20[0-9]{2}',w[4])]
                if not 2<=len(years)<=4 or len({w[4] for w in years})!=len(years):continue
                if any(NUMBER.fullmatch(w[4]) and w not in years for w in ws):continue
                centers=[(w[0]+w[2])/2 for w in years];gap=min(b-a for a,b in zip(centers,centers[1:]))
                if gap<25:continue
                above=[(ry,rws) for ry,rws in rows[max(0,ri-10):ri] if y-ry<150]
                header_text=' '.join(w[4] for _,rws in above for w in rws)
                if not re.search(r'net sales|gross margin|statements|balance sheet',header_text,re.I):continue
                if not re.search(r'\bmillions\b',header_text,re.I):continue
                default_section='net sales' if re.search(r'net sales',header_text,re.I) else ''
                section=default_section;section_box=union_box([w for _,rws in above for w in rws]) if above else None
                heading=header_text.strip();last_y=y
                for ry,rws in rows[ri+1:]:
                    if ry-y>630 or ry-last_y>55:break
                    raw_line=' '.join(w[4] for w in rws)
                    if any(re.fullmatch('20[0-9]{2}',w[4]) for w in rws) and len([w for w in rws if re.fullmatch('20[0-9]{2}',w[4])])>=2:break
                    numerics=[]
                    for w in rws:
                        if not NUMBER.fullmatch(w[4]):continue
                        k=min(range(len(centers)),key=lambda k:abs(w[2]-centers[k]))
                        if abs(w[2]-centers[k])>gap*.48:continue
                        has_percent=w[4].endswith('%') or any(v[4]=='%' and 0<=v[0]-w[2]<8 for v in rws)
                        numerics.append((k,w,has_percent))
                    if any(not v for _,_,v in numerics):numerics=[n for n in numerics if not n[2]]
                    if len(numerics)!=len(years) or len({k for k,_,_ in numerics})!=len(years):
                        if not numerics and re.search(r'net sales:|cost of sales:|gross margin(?: percentage)?:',raw_line,re.I):section=folded(raw_line);section_box=union_box(rws)
                        if not numerics and raw_line.endswith(':'):section=folded(raw_line);section_box=union_box(rws)
                        last_y=ry;continue
                    first_x=min(w[0] for _,w,_ in numerics)
                    label=' '.join(w[4] for w in rws if w[2]<first_x and w[4] not in {'$','€','£'})
                    percent=all(v for _,_,v in numerics)
                    if not label or any(v!=percent for _,_,v in numerics):last_y=ry;continue
                    metric=metric_for(label,section,percent)
                    if not metric:last_y=ry;continue
                    for k,w,is_percent in numerics:
                        year=years[k][4]
                        if year not in dates or not annual:continue
                        if not is_percent and not currency_proof and not re.search(r'USD|U\.S\. dollars',header_text,re.I):continue
                        box=list(w[:4]);raw=w[4]
                        if is_percent and not raw.endswith('%'):
                            mark=next(v for v in rws if v[4]=='%' and 0<=v[0]-w[2]<8);box=[*box[:2],mark[2],max(box[3],mark[3])];raw+='%'
                        c={'document_id':document_id,'source_sha256':source_hash,'source_kind':'PDF','page':page_no,
                            'box':box,'cell_bbox':box,'row_box':union_box(rws),'header_box':list(years[k][:4]),
                            'section_box':section_box,'section_text':section,'table_heading':heading,
                            'row_label':label,'metric':metric,'metric_canonical_name':metric,'value_raw':raw,
                            'period':year,'fiscal_year':int(year),'period_end':dates[year],'period_type':'INSTANT' if metric=='assets' else 'FY',
                            'statement_scope':'CONSOLIDATED','scope_source_page':annual[0],
                            'currency':'PERCENT' if is_percent else 'USD','scale':'1' if is_percent else '1000000',
                            'unit':'%' if is_percent else 'MILLION_USD','currency_source_page':currency_proof[0] if currency_proof else page_no,
                            'basis':'AS_REPORTED','extraction_method':'NATIVE','text':raw_line,
                            'verification_status':'NATIVE_CANDIDATE','extraction_version':VERSION}
                        c['citation_id']=cell_id(c);c['evidence_id']=c['citation_id'];result.append(c)
                    last_y=ry
    return result

def native_catalog(w,document_ids):
    out=[]
    for doc_id in document_ids:
        d=w.document(doc_id);path=w.source_file(doc_id)
        for c in _native_catalog(str(path),d['sha256'],doc_id):out.append({**c,'filename':d['filename'],'issuer':d.get('issuer','')})
    return out

_heading_cache={}

def section_evidence(w,document_ids,plan):
    """Find literal headings in authenticated stored extraction, including OCR."""
    hits=[]
    for doc_id in document_ids:
        d=w.document(doc_id);w.source_file(doc_id)
        with closing(w._connect()) as db:
            manifest=tuple(tuple(r) for r in db.execute('SELECT page,payload_hash FROM page_evidence WHERE document_id=? ORDER BY page',(doc_id,)))
        key=(str(w.root),doc_id,d['sha256'],manifest)
        if key not in _heading_cache:
            if len(_heading_cache)>=8:_heading_cache.clear()
            _heading_cache[key]=[(page,w.page_evidence(doc_id,page)) for page in range(1,d['pages']+1)]
        for page,e in _heading_cache[key]:
            lines_=e.get('lines',[])
            for line in lines_:
                f=folded(line['text'])
                if plan.metric=='geography_definition' and plan.intent=='EXPLAIN':match=bool(re.search(r'includes both north and south america',f))
                elif plan.intent=='DOCUMENT_IDENTITY':match=bool(re.search(r'bao cao tai chinh (?:rieng|hop nhat)|can doi ke toan cong ty me|consolidated (?:financial|statements)',f))
                elif plan.section=='BALANCE_SHEET':match=bool(re.search(r'bang can doi ke toan|balance sheets?',f))
                elif plan.section=='INCOME_STATEMENT':match=bool(re.search(r'bao cao ket qua.*kinh doanh|statements of operations',f))
                else:match=False
                if not match:continue
                box=line.get('box');cid='heading_'+sha256(json.dumps([d['sha256'],page,box,line['text']]).encode()).hexdigest()[:24]
                scope='SEPARATE' if re.search(r'rieng|cong ty me|parent',f) else 'CONSOLIDATED' if 'consolidated' in f or 'hop nhat' in f else 'UNKNOWN'
                hits.append({'document_id':doc_id,'source_sha256':d['sha256'],'page':page,'source_kind':'PDF','text':line['text'],
                    'row_label':line['text'],'filename':d['filename'],'box':box,'statement_scope':scope,'citation_id':cid,'evidence_id':cid,
                    'extraction_method':e.get('method'),'numeric_status':'NOT_APPLICABLE',
                    'highlight_status':'NATIVE_GEOMETRY' if e.get('method')=='NATIVE' else 'HIGHLIGHT_UNVERIFIED'})
    hits.sort(key=lambda h:(h['page'],len(h['text'])))
    return hits[:4]

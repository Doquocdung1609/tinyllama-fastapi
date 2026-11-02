"""Bounded native PDF geometry recovery; candidates are not certified answers.

No OCR confidence, inferred reporting currency, or neighboring page heading can
promote a candidate to a financial fact. This adapter retains source geometry
for the subsequent verifier without writing reviewed_facts.
"""
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
import re

import pymupdf

VERSION = 'native-financial-geometry/v1'
NUMBER = re.compile(r'^(?:-?\d{1,3}(?:,\d{3})+|-?\d+)(?:\.\d+)?$|^\(\d[\d,]*(?:\.\d+)?\)$')


def recover_retrieved_tables(workspace, document_ids, hits):
    output=[]
    for document_id in document_ids:
        selected=[h for h in hits if h.get('document_id')==document_id and h.get('page')]
        if not selected:continue
        doc=workspace.document(document_id)
        if not doc or doc['status']!='READY':raise ValueError('PDF_DOCUMENT_NOT_READY')
        mapping={}
        for hit in selected:
            if hit.get('source_sha256')!=doc['sha256']:raise ValueError('NATIVE_RETRIEVAL_SOURCE_MISMATCH')
            mapping.setdefault(int(hit['page']),[]).append(hit['chunk_id'])
        tables=recover_native_tables(workspace.source_file(document_id),list(mapping),doc['sha256'],mapping)
        for table in tables:table['document_id']=document_id
        output.extend(tables)
    return output


def _lines(words):
    rows=[]
    for word in sorted(words,key=lambda w:(w[1],w[0])):
        row=next((r for r in reversed(rows[-3:]) if abs(r[0]-word[1])<2),None)
        if row is None:
            row=[word[1],[]];rows.append(row)
        row[1].append(word)
    return [(y,sorted(ws,key=lambda w:w[0])) for y,ws in rows]


def recover_native_tables(path, pages, expected_hash, chunk_ids_by_page=None):
    """Recover only aligned annual native tables on explicitly retrieved pages.

    Currency UNKNOWN is deliberate for a bare dollar sign. No issuer/currency
    assumption is taken from a filename or a US filing form.
    """
    path=Path(path)
    if path.stat().st_size>20*1024*1024:raise ValueError('NATIVE_SOURCE_SIZE_LIMIT')
    if sha256(path.read_bytes()).hexdigest()!=expected_hash:
        raise ValueError('NATIVE_SOURCE_HASH_MISMATCH')
    if len(set(pages))>12:raise ValueError('NATIVE_RECOVERY_PAGE_BUDGET')
    output=[]
    with pymupdf.open(path) as pdf:
        for number in sorted(set(pages)):
            if not 1<=number<=len(pdf):raise ValueError('NATIVE_SOURCE_PAGE_INVALID')
            page=pdf[number-1]
            if page.rotation:continue
            words=page.get_text('words')
            if len(words)>12000:continue
            rows=_lines(words)
            for i,(y,words) in enumerate(rows):
                years=[w for w in words if re.fullmatch(r'(?:19|20)\d{2}',w[4])]
                if len(years)<2 or len(years)>5 or len({w[4] for w in years})!=len(years):continue
                if any(NUMBER.fullmatch(w[4]) and w not in years for w in words):continue
                centers=[(w[0]+w[2])/2 for w in years]
                gap=min(b-a for a,b in zip(centers,centers[1:]))
                if gap<30:continue
                above=[(ry,ws) for ry,ws in rows[:i] if 0<y-ry<110]
                headings=[(ry,' '.join(w[4] for w in ws)) for ry,ws in above
                          if re.search(r'statements? of|segment.*performance|balance sheets?',
                                       ' '.join(w[4] for w in ws),re.I)]
                if not headings:continue
                heading_y,heading=headings[-1]
                context='\n'.join(' '.join(w[4] for w in ws) for ry,ws in above if ry>=heading_y)
                # A narrative may span a heading/header; preserve it for audit.
                scale='1000000' if re.search(r'\bmillions?\b',context,re.I) else None
                currency='USD' if re.search(r'\bUSD\b|U\.S\. dollars?',context,re.I) else 'UNKNOWN'
                scope='SEGMENT' if re.search('segment',heading,re.I) else 'CONSOLIDATED' if re.search('consolidated',heading,re.I) else 'UNKNOWN'
                cells=[];last_y=y
                for ry,ws in rows[i+1:]:
                    if ry-last_y>(40 if cells else 50):break
                    if ry-y>350:break
                    numeric=[w for w in ws if NUMBER.fullmatch(w[4])]
                    values=[]
                    for w in numeric:
                        if any(other[4]=='%' and 0<=other[0]-w[2]<8 for other in ws):continue
                        near=min(range(len(years)),key=lambda k:abs(w[2]-centers[k]))
                        if abs(w[2]-centers[near])>gap*.48:continue
                        if any(v['column']==near for v in values):values=[];break
                        raw=w[4];negative=raw.startswith('(')
                        value=Decimal(raw.strip('()').replace(',',''))*(-1 if negative else 1)
                        values.append({'column':near,'year':int(years[near][4]),'raw_value':raw,
                            'value':str(value),'box':list(w[:4]),'header_box':list(years[near][:4])})
                    if len(values)!=len(years):
                        if not numeric and ' '.join(w[4] for w in ws).endswith(':'):
                            last_y=ry
                            continue
                        if cells:break
                        last_y=ry
                        continue
                    first_x=min(w[0] for w in numeric if any(list(w[:4])==v['box'] for v in values))
                    label=' '.join(w[4] for w in ws if w[2]<first_x and w[4] not in {'$','€','£'})
                    if not label:break
                    last_y=ry
                    for v in values:
                        v.update(row_label=label,source_sha256=expected_hash,page=number,
                            table_heading=heading,statement_scope=scope,scale=scale,currency=currency,
                            source_excerpt=' '.join(w[4] for w in ws),header_context=context,
                            retrieved_chunk_ids=list((chunk_ids_by_page or {}).get(number,[])),
                            status='TABLE_CONTEXT_INCOMPLETE' if not scale or currency=='UNKNOWN' or scope=='UNKNOWN'
                                else 'SOURCE_CELL_CANDIDATE')
                    cells.extend(values)
                if cells:
                    output.append({'version':VERSION,'page':number,'heading':heading,'cells':cells,
                        'period_semantics':'HEADER_YEAR_ONLY_REQUIRES_FISCAL_BINDING',
                        'verification_status':'CANDIDATES_NOT_ELIGIBLE_FACTS'})
    return output

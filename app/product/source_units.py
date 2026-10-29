"""Source unit candidates with raw text/boxes. No amount conversion or certification."""
import re
from app.product.pdf_extract import folded
from app.product.analysis import parse_number

VERSION='source-unit-evidence-v3r2.1'

def units_in(text):
    value=folded(text);found=[];occupied=[]
    patterns=[(None,'KRW',None,r'\b(?:krw\s+(?:million|thousand|billion)s?|(?:million|thousand|billion)s?(?:\s+of)?\s+(?:krw|korean won))\b'),
        (None,'USD',None,r'\b(?:usd\s+(?:thousand|billion)s?|(?:thousand|billion)s?(?:\s+of)?\s+usd)\b'),
        ('TRIEU_VND','VND','1000000',r'\b(?:vnd\s+millions?|millions?(?:\s+of)?\s+vnd|trieu\s+(?:dong|vnd))\b'),
        ('NGHIN_VND','VND','1000',r'\b(?:vnd\s+thousands?|thousands?(?:\s+of)?\s+vnd|nghin\s+(?:dong|vnd))\b'),
        ('TY_VND','VND','1000000000',r'\bty\s+(?:dong|vnd)\b'),
        ('MILLION_USD','USD','1000000',r'\b(?:usd\s+millions?|millions?(?:\s+of)?\s+(?:usd|u\.?s\.? dollars?))\b'),
        ('VND','VND','1',r'\b(?:vnd|dong)\b'),('KRW','KRW','1',r'\b(?:krw|(?:korean\s+)?won)\b'),
        ('USD','USD','1',r'\b(?:usd|(?:u\.?s\.?\s+)?dollars?)\b')]
    for unit,currency,scale,pattern in patterns:
        for m in re.finditer(pattern,value):
            if any(m.start()<b and m.end()>a for a,b in occupied):continue
            occupied.append(m.span());found.append({'unit':unit,'currency':currency,'multiplier':scale,'source_text':text[m.start():m.end()],
                'status':'SOURCE_UNIT_CANDIDATE_NOT_REVIEWED' if unit else 'UNSUPPORTED_SOURCE_SCALE','span':list(m.span())})
    return found

def header_unit(text):
    candidates=units_in(text);units={c['unit'] for c in candidates}
    return next(iter(units)) if len(units)==1 else None

def word_units(words):
    """Only join adjacent header tokens on the same source baseline."""
    groups=[]
    for word in sorted(words,key=lambda w:(round(w['box'][1]/4),w['box'][0])):
        b=word['box'];group=next((g for g in reversed(groups) if abs(g[-1]['box'][1]-b[1])<4 and 0<=b[0]-g[-1]['box'][2]<=15),None)
        if group is None:groups.append([word])
        else:group.append(word)
    found=[]
    for group in groups:
        # Parse each small token window so one row containing KRW and USD does not
        # acquire a single shared currency box.
        for i in range(len(group)):
            for width in (3,2,1):
                subset=group[i:i+width]
                if len(subset)!=width:continue
                text=' '.join(w['text'] for w in subset);matches=units_in(text)
                for m in matches:
                    if m['span']!=[0,len(folded(text))]:continue
                    box=[min(w['box'][0] for w in subset),min(w['box'][1] for w in subset),max(w['box'][2] for w in subset),max(w['box'][3] for w in subset)]
                    found.append({**m,'source_text':text,'box':box})
    # Prefer the actual scaled source phrase over its contained bare currency.
    unique=[]
    for c in found:
        if any(c['currency']==o['currency'] and c['multiplier']=='1' and o['multiplier']!='1' and o['box'][0]<=c['box'][0] and o['box'][2]>=c['box'][2] and abs(o['box'][1]-c['box'][1])<4 for o in found):continue
        if not any(o['unit']==c['unit'] and o['box']==c['box'] for o in unique):unique.append(c)
    return unique

def cell_unit(cell,words,context,parsed=None):
    candidates=list(parsed) if parsed is not None else word_units(words)
    currency=cell.get('currency_candidate',{}).get('unit')
    if currency:candidates=[c for c in candidates if c['currency']==currency]
    if candidates and cell.get('box'):
        x=(cell['box'][0]+cell['box'][2])/2
        distance=lambda c:abs((c['box'][0]+c['box'][2])/2-x)
        candidates.sort(key=distance);best=candidates[0]
        tied=[c for c in candidates if abs(distance(c)-distance(best))<5]
        if len({c['unit'] for c in tied})==1:return {**best,'selection_basis':'SOURCE_HEADER_WORDS_COLUMN_GEOMETRY'}
        return {'unit':None,'status':'AMBIGUOUS_SOURCE_UNIT','candidates':tied}
    all_candidates=units_in(context);units={c['unit'] for c in all_candidates}
    if len(units)==1:return {**all_candidates[0],'selection_basis':'UNIQUE_EXPLICIT_PAGE_HEADER;COLUMN_NOT_SEPARATELY_CERTIFIED'}
    return {'unit':None,'status':'AMBIGUOUS_SOURCE_UNIT' if units else 'SOURCE_UNIT_NOT_PROVEN','candidates':all_candidates}

def numeric_syntax(raw):
    if not raw.strip() or raw.strip() in {'-','—','–'}:return {'status':'BLANK_NOT_ZERO','valid_conventions':[]}
    readings={}
    for locale in ('vi_VN','en_US'):
        try:readings[locale]=parse_number(raw,locale)
        except ValueError:pass
    status='VALID_SYNTAX_UNREVIEWED' if readings and len(set(readings.values()))==1 else 'AMBIGUOUS_NUMERIC_FORMAT' if readings else 'INVALID_NUMERIC_FORMAT'
    return {'status':status,'valid_conventions':list(readings),'financial_evidence_status':'FINANCIAL_EVIDENCE_REVIEW_PENDING'}

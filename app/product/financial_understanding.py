"""Versioned product slots. Raw Vietnamese is retained for unit disambiguation."""
from dataclasses import asdict, dataclass
from contextlib import closing
from collections import Counter
import json
from hashlib import sha256
import re
from app.product.pdf_extract import folded

VERSION = 'FINANCIAL_QUERY_UNDERSTANDING_V1'
ALIASES = {
    'BIDV': ('bidv', 'bid', 'ngan hang tmcp dau tu va phat trien viet nam'),
    'HPG': ('hpg', 'hoa phat'), 'AAPL': ('aapl', 'apple'),
    'MSFT': ('msft', 'microsoft'), 'NVDA': ('nvda', 'nvidia'),
    'TSLA': ('tsla', 'tesla'), 'AMZN': ('amzn', 'amazon'),
}
METRICS = {
    'retained_earnings': ('loi nhuan sau thue chua phan phoi', 'retained earnings'),
    'net_income': ('loi nhuan sau thue', 'net income', 'net profit'),
    'net_revenue': ('doanh thu', 'net sales', 'revenue'),
    'assets': ('tong tai san', 'tong cong tai san', 'total assets'),
    'operating_cashflow': ('dong tien hoat dong', 'operating cash'),
}

def issuers(text):
    q = folded(text).replace('_',' ').replace('+',' ')
    return [key for key, aliases in ALIASES.items() if any(
        re.search(r'(?<!\w)' + re.escape(alias) + r'(?!\w)', q) for alias in aliases)]

def document_profile(w, doc):
    """Source-backed display projection; never rewrites stored user metadata."""
    pages=[]
    if hasattr(w,'_connect'):
        with closing(w._connect()) as db:
            rows=db.execute('SELECT payload,payload_hash FROM page_evidence WHERE document_id=? ORDER BY page LIMIT 8',(doc['id'],)).fetchall()
        for row in rows:
            if sha256(row['payload'].encode()).hexdigest()!=row['payload_hash']:raise ValueError('PDF_PAGE_EVIDENCE_HASH_MISMATCH')
            pages.append(json.loads(row['payload']))
    elif hasattr(w,'page_evidence'):
        try:pages=[w.page_evidence(doc['id'],1)]
        except ValueError:pass
    source_ids=issuers(' '.join(p.get('text','')[:6000] for p in pages[:2]))
    identity=source_ids or issuers(doc.get('filename',''))
    if not identity and not hasattr(w,'source_file'):identity=issuers(doc.get('issuer',''))
    years=[];scopes=set()
    for p in pages:
        q=folded(p.get('text',''))
        if re.search(r'bao cao|bang can doi|financial statements|statements of',q):
            years.extend(re.findall(r'\bnam\s+(20\d{2})\b',q))
            if re.search(r'hop nhat|consolidated',q):scopes.add('CONSOLIDATED')
            if re.search(r'\brieng\b|cong ty me|parent company',q):scopes.add('SEPARATE')
    counts=Counter(years);ranked=counts.most_common()
    year=ranked[0][0] if ranked and (len(ranked)==1 or ranked[0][1]>ranked[1][1]) else None
    return {'identities':identity,'identity_method':'SOURCE_TEXT_ALIAS' if source_ids else 'FILENAME_ALIAS' if identity else 'UNKNOWN',
        'report_year':year,'statement_scopes':sorted(scopes)}

def requested_unit(text):
    # Bare ASCII "dong" is deliberately ambiguous; dòng/đóng/động are not currency.
    q = text.casefold()
    if re.search(r'\b(?:vnd|đồng)\b', q):
        f = folded(q)
        return 'TY_VND' if re.search(r'\bty dong\b', f) else 'TRIEU_VND' if 'trieu dong' in f else 'VND'
    iso=re.search(r'\b(eur|cad|aud|hkd|jpy|cny|gbp)\b',q)
    if iso:return iso[1].upper()
    f = folded(q)
    if re.search(r'\b(?:trieu|ty|nghin) dong\b', f):
        return 'TRIEU_VND' if 'trieu dong' in f else 'TY_VND' if 'ty dong' in f else 'NGHIN_VND'
    if re.search(r'\busd\b|dollars?', q): return 'USD'
    if '%' in q or re.search(r'\bpercent(?:age)?\b|phan tram', f): return '%'
    return None

@dataclass(frozen=True)
class FinancialQueryUnderstanding:
    raw_text: str
    intent: str
    issuer_mentions: list[str]
    metric: str | None
    metric_phrases: tuple[str, ...]
    years: list[str]
    period_type: str | None
    scope: str | None
    basis: str | None
    requested_unit: str | None
    version: str = VERSION
    def public(self): return asdict(self)

def understand(text):
    q = folded(text)
    metric = next((m for m, aliases in METRICS.items() if any(a in q for a in aliases)), None)
    if re.search(r'tim (?:dong|doan|nguon)|\b(?:find|locate)\b|trang (?:pdf|nao)|doan nguon|\bevidence\b', q): intent = 'FIND_EVIDENCE'
    elif re.search(r'nhung so lieu|liet ke.*dieu chinh|restatement|list.*adjust', q): intent = 'RESTATEMENT_LIST'
    elif re.search(r'khac nhau bao nhieu|so voi|chenh lech|compare|difference|growth|tang.*phan tram', q): intent = 'COMPARE_PERIODS'
    elif re.search(r'tom tat|tong quan|summary|summarize|overview|nghien cuu', q): intent = 'SUMMARIZE'
    elif re.search(r'giai thich|vi sao|explain|why', q): intent = 'EXPLAIN'
    elif re.search(r'bao nhieu|how much|how many|what was|what were|gia tri|\bvalue\b', q) or metric: intent = 'EXTRACT_VALUE'
    else: intent = 'FIND_EVIDENCE'
    scope = 'CONSOLIDATED' if re.search(r'hop nhat|consolidated', q) else 'SEPARATE' if re.search(r'\brieng\b|cong ty me|parent company|separate', q) else None
    if re.search(r'(?:rieng|cong ty me).*(?:hop nhat)|(?:hop nhat).*(?:rieng|cong ty me)', q): scope = None
    basis = 'ORIGINAL' if re.search(r'truoc dieu chinh|original|da cong bo', q) else 'RESTATED' if re.search(r'trinh bay lai|restated', q) else 'ADJUSTMENT' if 'dieu chinh' in q else None
    period = next((v for p, v in [(r'quy 1|\bq1\b', '3M'), (r'6 thang|six months', '6M'), (r'9 thang|nine months', '9M'), (r'\bfy\b|\bfiscal\b|\bnam\b', 'FY')] if re.search(p, q)), None)
    return FinancialQueryUnderstanding(text, intent, issuers(text), metric, METRICS.get(metric, ()), sorted(set(re.findall(r'\b20\d{2}\b', q))), period, scope, basis, requested_unit(text))

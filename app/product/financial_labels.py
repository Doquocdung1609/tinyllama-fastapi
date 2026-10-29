"""Retrieval-only English label candidates; never rewrite checkpoint text or amounts."""
import re
import unicodedata
from functools import lru_cache
from app.product.search_v3 import metrics_in,row_metrics

VERSION='financial-label-candidates-v3r2.1'

@lru_cache(maxsize=2048)
def normalize_label(raw):
    value=unicodedata.normalize('NFKC',raw)
    value=re.sub(r"[’‘`´']",'',value)
    # Missing fi glyphs are observed as a control character or whitespace in native
    # PDF text. Only a constrained financial phrase becomes a retrieval candidate.
    value=re.sub(r'\bpro[\s\x00-\x1f]+t(?=\s+(?:before\s+(?:income\s+)?tax|after\s+tax|for\s+the\s+(?:year|period)|or\s+loss)\b)',
        'profit',value,flags=re.I)
    return re.sub(r'\s+',' ',value).strip()

def specialized_profit(text):
    t=normalize_label(text).lower()
    return bool(re.search(r'\b(?:profit|net income|net earnings)\b',t) and
        re.search(r'\b(?:attributable|non.?controlling|minority|discontinued|continuing)\b',t))

def label_metrics(raw):
    text=normalize_label(raw);t=text.lower()
    if specialized_profit(text):return []
    if re.search(r'\bliabilities\s+and\s+(?:(?:owners|shareholders|stockholders|total)\s+)?equity\b',t):return ['total_funding']
    if re.search(r'\b(?:owners|shareholders|stockholders|shareowners|total)\s+equity\b',t):return ['equity']
    return metrics_in(text) or row_metrics(text)

def statement_candidate(context):
    text=normalize_label(context).lower()
    if re.search(r'\b(?:consolidated\s+)?statements? of financial position\b',text):return 'BALANCE_SHEET'
    if re.search(r'\bstatements? of (?:comprehensive income|profit or loss|income)\b',text):return 'INCOME_STATEMENT'
    if re.search(r'\bstatements? of cash flows?\b',text):return 'CASH_FLOW'
    from app.product.search_v2 import statement_kind
    return statement_kind(text)

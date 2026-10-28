"""Versioned, issuer-independent financial vocabulary. No document answers here."""
from dataclasses import dataclass,asdict
import re
from app.product.pdf_extract import folded

ONTOLOGY_VERSION='financial-intent-v2.1'
# Distinct concepts, rather than a bag of ambiguous single financial words.
METRICS={
 'assets':('BALANCE_SHEET',['tổng tài sản','tổng cộng tài sản','quy mô tài sản','toàn bộ tài sản','total assets']),
 'fixed_assets':('BALANCE_SHEET',['tài sản cố định','fixed assets','property plant and equipment']),
 'intangible_assets':('BALANCE_SHEET',['tài sản cố định vô hình','tài sản vô hình','intangible assets']),
 'current_assets':('BALANCE_SHEET',['tài sản ngắn hạn','current assets']),
 'noncurrent_assets':('BALANCE_SHEET',['tài sản dài hạn','noncurrent assets','non-current assets']),
 'cash_equivalents':('BALANCE_SHEET',['tiền và các khoản tương đương tiền','tiền và tương đương tiền','cash and cash equivalents']),
 'cash_balance':('BALANCE_SHEET',['số dư tiền','cash balance']),
 'liabilities':('BALANCE_SHEET',['nợ phải trả','total liabilities']),
 'current_liabilities':('BALANCE_SHEET',['nợ ngắn hạn','current liabilities']),
 'noncurrent_liabilities':('BALANCE_SHEET',['nợ dài hạn','noncurrent liabilities']),
 'other_liabilities':('BALANCE_SHEET',['nợ phải trả khác','other liabilities']),
 'other_noncurrent_assets':('BALANCE_SHEET',['tài sản dài hạn khác','other noncurrent assets']),
 'equity':('BALANCE_SHEET',['vốn chủ sở hữu','shareholders equity','stockholders equity']),
 'total_funding':('BALANCE_SHEET',['tổng nguồn vốn','tổng cộng nguồn vốn','liabilities and equity']),
 'inventory':('BALANCE_SHEET',['hàng tồn kho','hàng kho tồn','inventories','inventory']),
 'investment_property':('BALANCE_SHEET',['bất động sản đầu tư','investment property']),
 'net_revenue':('INCOME_STATEMENT',['doanh thu thuần','doanh thu bán hàng thuần','net sales','net revenue']),
 'financial_revenue':('INCOME_STATEMENT',['doanh thu hoạt động tài chính','doanh thu tài chính','financial income']),
 'pretax_income':('INCOME_STATEMENT',['lợi nhuận kế toán trước thuế','lợi nhuận trước thuế','profit before tax']),
 'net_income':('INCOME_STATEMENT',['lợi nhuận sau thuế','lãi sau thuế','net income','profit after tax']),
 'operating_cashflow':('CASH_FLOW',['lưu chuyển tiền thuần từ hoạt động kinh doanh','dòng tiền từ hoạt động kinh doanh','tiền từ hoạt động kinh doanh','operating cash flow','operating cash']),
 'net_cashflow':('CASH_FLOW',['lưu chuyển tiền thuần trong kỳ','dòng tiền thuần trong kỳ','net cash flow']),
}

def metric_matches(text):
 value=folded(text);matches=[]
 for metric,(_,aliases) in METRICS.items():
  for alias in aliases:
   term=folded(alias)
   if re.search(r'(?<!\w)'+re.escape(term)+r'(?!\w)',value):matches.append((metric,term))
 # A longer concept consumes its nested alias; e.g. intangible vs fixed assets.
 return sorted({m for m,t in matches if not any(t!=other and t in other for _,other in matches)})

STOP=set('cua cong ty tai ngay la bao nhieu hay cho biet vui long xin mot nhung cac trong nam va voi theo bang duoc tu what were was the of as at for in please how much'.split())

@dataclass(frozen=True)
class FinancialIntent:
 metrics:tuple[str,...]
 dates:tuple[str,...]
 years:tuple[str,...]
 scope:str|None
 basis:str|None
 statement:str|None
 unit:str|None
 operation:str
 period_reference:str|None=None
 statement_explicit:bool=False
 evidence_requirement:str='SOURCE_ROW_PERIOD_UNIT_SCOPE; numeric verification is separate'

 def public(self):return {**asdict(self),'ontology_version':ONTOLOGY_VERSION}

def understand(query):
 q=folded(query);metrics=metric_matches(q);dates=[]
 for day,month,year in re.findall(r'\b(\d{1,2})[/-](\d{1,2})[/-]((?:19|20)\d{2})\b',q):
  try:
   from datetime import date
   dates.append(date(int(year),int(month),int(day)).isoformat())
  except ValueError:dates.append('INVALID_DATE')
 dates+=re.findall(r'\b(?:19|20)\d{2}-\d{2}-\d{2}\b',q)
 def phrase(value):return re.search(r'(?<!\w)'+re.escape(value)+r'(?!\w)',q) is not None
 scopes=[s for s,aliases in [('SEPARATE',['rieng','cong ty me','separate','unconsolidated']),('CONSOLIDATED',['hop nhat','consolidated'])] if any(phrase(a) for a in aliases)]
 bases=[b for b,aliases in [('RESTATED',['trinh bay lai','sau dieu chinh','restated']),('ORIGINAL',['da cong bo','so goc','original','unrestated']),('ADJUSTMENT',['muc dieu chinh','phan dieu chinh','adjustment'])] if any(phrase(a) for a in aliases)]
 if re.search(r'\b(?:khong(?:\s+phai)?|not)\s+(?:la\s+)?(?:hop nhat|consolidated|rieng|separate)\b',q):scopes=['AMBIGUOUS']
 if re.search(r'\b(?:khong(?:\s+phai)?|chua|not)\s+(?:la\s+)?(?:trinh bay lai|restated|da cong bo|original)\b',q):bases=['AMBIGUOUS']
 operation='LOOKUP'
 if any(t in q for t in ['chenh lech','tang bao nhieu','giam bao nhieu','so voi','so sanh','compare','difference']):operation='CHANGE'
 if any(t in q for t in ['tang truong','growth','ty le thay doi']):operation='GROWTH'
 if any(t in q for t in ['ty trong','chiem bao nhieu','ratio','phan tram']):operation='RATIO'
 if any(t in q for t in ['phuong trinh ke toan','co bang tong tai san']):operation='ACCOUNTING_IDENTITY'
 statements={METRICS[m][0] for m in metrics}
 requested_statement=next((kind for kind,terms in [('BALANCE_SHEET',['bang can doi','balance sheet']),('INCOME_STATEMENT',['ket qua kinh doanh','ket qua hoat dong kinh doanh','income statement']),('CASH_FLOW',['bao cao luu chuyen tien te','cash flow statement']),('NOTES',['thuyet minh','notes to financial'])] if any(term in q for term in terms)),None)
 unit=next((u for u,a in [('TRIEU_VND','trieu dong'),('NGHIN_VND','nghin dong'),('TY_VND','ty dong'),('USD','usd'),('VND','vnd'),('%','%')] if a in q),None)
 years=sorted(set(re.findall(r'\b(?:19|20)\d{2}\b',q)));reference=None
 if not dates and len(years)==1:
  if any(t in q for t in ['cuoi nam','end of year']):reference='CALENDAR_YEAR_END';dates.append(years[0]+'-12-31')
  elif any(t in q for t in ['dau nam','beginning of year']):reference='CALENDAR_YEAR_BEGINNING';dates.append(years[0]+'-01-01')
 return FinancialIntent(tuple(metrics),tuple(sorted(set(dates))),tuple(years),
  scopes[0] if len(scopes)==1 else 'AMBIGUOUS' if scopes else None,bases[0] if len(bases)==1 else 'AMBIGUOUS' if bases else None,
  requested_statement or (next(iter(statements)) if len(statements)==1 else None),unit,operation,reference,bool(requested_statement))

def lexical_terms(query,intent):
 # Controlled synonyms supplement phrases; never require all query tokens.
 phrases=[folded(a) for m in intent.metrics for a in METRICS[m][1]]
 tokens=[t for t in re.findall(r'\w+',folded(query)) if t not in STOP and not t.isdigit() and len(t)>1][:24]
 return list(dict.fromkeys(phrases+tokens))[:40]

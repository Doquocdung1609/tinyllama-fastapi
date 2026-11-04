# Read-only port from PR #36 A5; research originals remain unchanged.
"""Versioned bilingual accounting terms for opt-in C4R retrieval.

Aliases identify an intent, not an equivalence between nearby accounting facts.
The original question is retained; the English expansion is only a search view.
"""

from __future__ import annotations

from dataclasses import dataclass
import re

from app.financial_query.normalizer import normalize_question
from app.research_retrieval.faith_r import ISSUER_ALIASES


@dataclass(frozen=True)
class MetricTerm:
    code: str
    search_phrase: str
    patterns: tuple[str, ...]
    statement: str
    value_kind: str = "AMOUNT"


# Longer, narrower expressions precede broader ones. Distinct metrics remain distinct.
METRICS = (
    MetricTerm("GROSS_MARGIN_PERCENT", "gross profit margin percentage", (r"\b(?:gross margin|gross profit margin)\s*(?:percentage|percent|ratio)\b", r"\b(?:gross margin|gross profit margin)\s*%", r"\bbiên lợi nhuận gộp\b"), "INCOME", "PERCENT"),
    MetricTerm("NET_REVENUE", "net sales revenue", (r"\bnet sales\b", r"\bnet revenue\b", r"\bdoanh thu thuần\b"), "INCOME"),
    MetricTerm("SEGMENT_REVENUE", "reportable segment revenue", (r"\breportable segment (?:revenue|sales)\b", r"\bdoanh thu (?:phân khúc|bộ phận)\b"), "SEGMENT"),
    MetricTerm("TOTAL_REVENUE", "total revenue sales", (r"\btotal (?:net )?(?:revenue|sales)\b", r"\bdoanh thu\b", r"\brevenue\b"), "INCOME"),
    MetricTerm("COST_OF_SALES", "cost of sales cost of revenue", (r"\bcost of (?:sales|revenue|goods sold)\b", r"\bcogs\b", r"\bgiá vốn hàng bán\b"), "INCOME"),
    MetricTerm("GROSS_PROFIT", "gross profit", (r"\bgross profit\b", r"\blợi nhuận gộp\b"), "INCOME"),
    MetricTerm("OPERATING_INCOME", "operating income operating profit", (r"\boperating (?:income|profit)\b", r"\blợi nhuận (?:từ )?hoạt động kinh doanh\b"), "INCOME"),
    MetricTerm("OPERATING_EXPENSES", "operating expenses", (r"\boperating expenses?\b", r"\bchi phí hoạt động\b"), "INCOME"),
    MetricTerm("R_AND_D", "research and development", (r"\bresearch and development\b", r"\br&d\b", r"\bnghiên cứu và phát triển\b"), "INCOME"),
    MetricTerm("SG_AND_A", "selling general and administrative expense", (r"\b(?:selling,? general and administrative|sg&a)\b", r"\bchi phí bán hàng và quản lý\b"), "INCOME"),
    MetricTerm("SELLING_EXPENSE", "selling and marketing expense", (r"\bselling (?:expense|and marketing)\b", r"\bchi phí bán hàng\b"), "INCOME"),
    MetricTerm("PRETAX_INCOME", "income before income taxes", (r"\b(?:pretax|pre-tax) (?:income|profit)\b", r"\bprofit before tax\b", r"\blợi nhuận trước thuế\b"), "INCOME"),
    MetricTerm("NET_INCOME_ATTRIBUTABLE", "net income attributable to shareholders", (r"\b(?:net income|profit) attributable to\b", r"\blợi nhuận sau thuế thuộc về\b"), "INCOME"),
    MetricTerm("NET_INCOME", "net income profit after tax", (r"\bnet income\b", r"\bprofit after tax\b", r"\blợi nhuận sau thuế\b"), "INCOME"),
    MetricTerm("DILUTED_EPS", "diluted earnings per share", (r"\bdiluted (?:earnings per share|eps)\b", r"\blãi suy giảm trên cổ phiếu\b"), "INCOME", "PER_SHARE"),
    MetricTerm("EPS", "earnings per share", (r"\b(?:basic )?(?:earnings per share|eps)\b", r"\blãi cơ bản trên cổ phiếu\b"), "INCOME", "PER_SHARE"),
    MetricTerm("OPERATING_CASH_FLOW", "net cash provided by operating activities", (r"\b(?:net )?cash (?:flow|provided by|from) operating activities\b", r"\blưu chuyển tiền thuần từ hoạt động kinh doanh\b"), "CASH_FLOW"),
    MetricTerm("INVESTING_CASH_FLOW", "net cash used in investing activities", (r"\b(?:net )?cash (?:flow|used in|from) investing activities\b", r"\blưu chuyển tiền thuần từ hoạt động đầu tư\b"), "CASH_FLOW"),
    MetricTerm("FINANCING_CASH_FLOW", "net cash from financing activities", (r"\b(?:net )?cash (?:flow|from) financing activities\b", r"\blưu chuyển tiền thuần từ hoạt động tài chính\b"), "CASH_FLOW"),
    MetricTerm("CAPEX", "capital expenditures purchases of property plant and equipment", (r"\b(?:capital expenditures?|capex|purchases? of property)\b", r"\bchi tiêu vốn\b", r"\bmua sắm tài sản cố định\b"), "CASH_FLOW"),
    MetricTerm("TOTAL_ASSETS", "total assets", (r"\btotal assets\b", r"\btổng tài sản\b"), "BALANCE"),
    MetricTerm("TOTAL_LIABILITIES", "total liabilities", (r"\btotal liabilities\b", r"\btổng nợ phải trả\b"), "BALANCE"),
    MetricTerm("SHAREHOLDERS_EQUITY", "total shareholders equity", (r"\b(?:total )?(?:shareholders|stockholders)[’']? equity\b", r"\bvốn chủ sở hữu\b"), "BALANCE"),
    MetricTerm("ACCOUNTS_RECEIVABLE", "accounts receivable", (r"\baccounts receivable\b", r"\bphải thu khách hàng\b"), "BALANCE"),
    MetricTerm("CURRENT_ASSETS", "total current assets", (r"\bcurrent assets\b", r"\btài sản ngắn hạn\b"), "BALANCE"),
    MetricTerm("CURRENT_LIABILITIES", "total current liabilities", (r"\bcurrent liabilities\b", r"\bnợ ngắn hạn\b"), "BALANCE"),
    MetricTerm("INVENTORY", "inventories", (r"\binventor(?:y|ies)\b", r"\bhàng tồn kho\b"), "BALANCE"),
    MetricTerm("FIXED_ASSETS", "property plant and equipment", (r"\bproperty,? plant and equipment\b", r"\btài sản cố định\b"), "BALANCE"),
    MetricTerm("PROPERTY_EQUIPMENT_NET", "property and equipment net", (r"\bproperty and equipment,? net\b",), "BALANCE"),
    MetricTerm("CASH_EQUIVALENTS", "cash and cash equivalents", (r"\bcash and cash equivalents\b", r"\btiền và các khoản tương đương tiền\b"), "BALANCE"),
    MetricTerm("ACCOUNTS_PAYABLE", "accounts payable", (r"\baccounts payable\b", r"\bphải trả người bán\b"), "BALANCE"),
)

EXTRA_ISSUERS = {"HPG": ("hòa phát", "hoa phat", "hpg"), "BIDV": ("bidv", "ngân hàng đầu tư và phát triển việt nam")}
ISSUERS = {**ISSUER_ALIASES, **EXTRA_ISSUERS}


def _has(q: str, pattern: str) -> bool:
    return re.search(pattern, q, re.I) is not None


def detect_metric(q: str) -> tuple[MetricTerm | None, tuple[str, ...]]:
    matches = [term for term in METRICS if any(_has(q, p) for p in term.patterns)]
    if any(m.code == "COST_OF_SALES" for m in matches):
        remainder = re.sub(r"\bcost of (?:sales|revenue|goods sold)\b|\bcogs\b|\bgiá vốn hàng bán\b", "", q)
        if not re.search(r"\b(?:revenue|sales|doanh thu)\b", remainder):
            matches = [m for m in matches if m.code != "TOTAL_REVENUE"]
    # Stronger, longer term consumes a contained weak one (net revenue vs revenue).
    if matches:
        primary = matches[0]
        if re.search(r"\btotal net sales\b", q):
            matches = [m for m in matches if m.code != "NET_REVENUE"]
        elif primary.code == "NET_REVENUE":
            matches = [m for m in matches if m.code != "TOTAL_REVENUE"]
        elif primary.code == "GROSS_MARGIN_PERCENT":
            matches = [m for m in matches if m.code != "GROSS_PROFIT"]
        elif primary.code == "SEGMENT_REVENUE":
            matches = [m for m in matches if m.code != "TOTAL_REVENUE"]
        elif primary.code == "NET_INCOME_ATTRIBUTABLE":
            matches = [m for m in matches if m.code != "NET_INCOME"]
        elif primary.code == "DILUTED_EPS":
            matches = [m for m in matches if m.code != "EPS"]
    if len(matches) > 1:
        return None, tuple(m.code for m in matches)
    return (matches[0] if matches else None), ()


def normalized_view(question: str) -> str:
    return normalize_question(question)

"""Retain the raw question; normalize only a matching view. Never evaluate text."""
import re
import unicodedata
from decimal import Decimal

from app.financial_query.contracts import NumericConstraintV1

MAX_QUESTION_LENGTH = 2000


def normalize_question(question: str) -> str:
    if not isinstance(question, str) or not 2 <= len(question) <= MAX_QUESTION_LENGTH:
        raise ValueError("INVALID_QUESTION_LENGTH_OR_TYPE")
    if any(unicodedata.category(c) in {"Cc", "Cf", "Cs"} and c not in "\t\r\n" for c in question):
        raise ValueError("UNSUPPORTED_CONTROL_CHARACTER")
    normalized = " ".join(unicodedata.normalize("NFC", question).split()).casefold()
    if len(normalized) < 2:
        raise ValueError("EMPTY_QUESTION")
    return normalized


def matching_text(text: str) -> str:
    # No NFKC/transliteration: a confusable ticker is not a verified ticker.
    return " ".join(unicodedata.normalize("NFC", text).split()).casefold()


_NUMBER = r"(?:[0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)(?:\.[0-9]+)?"
_NUMERIC = re.compile(
    rf"(?<![\w.,])(?P<currency>USD\s*|\$\s*)?(?P<num>\([−+\-]?{_NUMBER}\)|[−+\-]?{_NUMBER})"
    r"\s*(?P<scale>thousand(?:s)?|million(?:s)?|billion(?:s)?)?"
    r"\s*(?P<unit>percentage points?|percent|%|USD/share|USD|per.share)?(?![\w.,])", re.I)


def numeric_constraints(text: str) -> tuple[list[NumericConstraintV1], list[str]]:
    numbers, unresolved = [], []
    for match in _NUMERIC.finditer(text):
        raw = match.group(0).strip()
        token = match['num']
        # Bare years/counts/dates are not automatically monetary predicates.
        if not (match['currency'] or match['scale'] or match['unit'] or '.' in token or ',' in token or token.startswith(('(', '-', '−', '+'))):
            continue
        paren = token.startswith('(')
        inner = token.strip('()').replace('−', '-')
        if paren and re.fullmatch(r'(?:19|20|21)[0-9]{2}', inner) and not (match['currency'] or match['scale'] or match['unit']):
            continue
        if paren and inner.startswith(('-', '+')):
            unresolved.append("CONFLICTING_NUMERIC_SIGNS")
            continue
        value = Decimal(inner.replace(',', ''))
        sign = "PARENTHESES" if paren else "MINUS" if inner.startswith('-') else "PLUS" if inner.startswith('+') else "NONE"
        if paren:
            value = value.copy_negate()  # exact; unary minus obeys Decimal context precision
        scale = (match['scale'] or '').lower().rstrip('s')
        multiplier = Decimal({'thousand': '1000', 'million': '1000000', 'billion': '1000000000'}.get(scale, '1'))
        u = (match['unit'] or '').lower()
        if (match['currency'] or match['scale']) and (u in {'%', 'percent'} or u.startswith('percentage')):
            unresolved.append('CONFLICTING_NUMERIC_UNITS')
        if u in {'usd', 'usd/share', 'per share', 'per-share'} and re.match(r'\s+(?:thousands?|millions?|billions?)\b', text[match.end():], re.I):
            unresolved.append('UNSUPPORTED_UNIT_ORDER')
        unit = ('PERCENTAGE_POINTS' if u.startswith('percentage') else 'PERCENT' if u in {'%', 'percent'}
                else 'USD_PER_SHARE' if u in {'usd/share', 'per share', 'per-share'} else 'USD' if match['currency'] or u == 'usd' else 'UNKNOWN')
        numbers.append(NumericConstraintV1(raw=raw, value=value, multiplier=multiplier, unit=unit, sign_source=sign))
    # Fail closed on malformed grouping/scientific expressions rather than parse a suffix.
    if re.search(r"\b[0-9]+,[0-9]{1,2}(?![0-9])|[0-9](?:e[+\-]?[0-9]|\*\*|/0)", text, re.I):
        unresolved.append("UNSUPPORTED_NUMERIC_SYNTAX")
    if any(c.isdecimal() and c not in '0123456789' for c in text) or re.search(r'[–—][0-9]', text):
        unresolved.append('UNSUPPORTED_NUMERIC_FORMAT')
    if re.search(r'\b(?:eur|jpy|gbp|cad|cny)\b|[€£¥]', text, re.I):
        unresolved.append('UNSUPPORTED_CURRENCY')
    return numbers, sorted(set(unresolved))

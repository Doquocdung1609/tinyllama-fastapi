"""Small versioned vocabulary: related concepts are never query rewrites."""
import re
from app.financial_query.contracts import MetricMentionV1

TERMINOLOGY_VERSION = "financial-terminology/v1"
# phrase, canonical, relationship, related (no issuer-specific equivalence inferred)
ENTRIES = (
    ('net income attributable to parent company', 'net income attributable to parent', 'SYNONYM', ['net income']),
    ('net income attributable to parent', 'net income attributable to parent', 'EXACT', ['net income']),
    ('net income attributable to noncontrolling interests', 'net income attributable to noncontrolling interests', 'EXACT', ['net income']),
    ("basic earnings per share", "basic EPS", "SYNONYM", []),
    ("diluted earnings per share", "diluted EPS", "SYNONYM", []),
    ("basic eps", "basic EPS", "SYNONYM", []),
    ("diluted eps", "diluted EPS", "SYNONYM", []),
    ("earnings per share", "EPS", "EXACT", ["basic EPS", "diluted EPS"]),
    ("eps", "EPS", "SYNONYM", ["basic EPS", "diluted EPS"]),
    ("net cash provided by operating activities", "operating cash flow", "SYNONYM", []),
    ("operating cash flow", "operating cash flow", "EXACT", []),
    ("operating profit", "operating profit", "AMBIGUOUS", ["operating income"]),
    ("profit", "profit", "AMBIGUOUS", ["net income", "operating income", "gross profit"]),
    *((x, x, "EXACT", ["net sales"] if x == "revenue" else ["revenue"] if x == "net sales" else [])
      for x in ("revenue", "net sales", "net income", "operating income", "total assets", "total liabilities",
                "gross profit", "current liabilities", "revenue recognition policy")),
)


def resolve_terms(text: str) -> list[MetricMentionV1]:
    matches, used = [], set()
    for phrase, canonical, relationship, related in sorted(ENTRIES, key=lambda e: (-len(e[0]), e[0])):
        for m in re.finditer(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", text):
            if any(i in used for i in range(*m.span())):
                continue
            used.update(range(*m.span()))
            attribution_unknown = canonical == 'net income' and re.match(r'\s+attributable\b', text[m.end():])
            matches.append((m.start(), MetricMentionV1(raw=m.group(), canonical=canonical,
                relationship='AMBIGUOUS' if attribution_unknown else relationship,
                related_concepts=related, rule_id=f"TERM:{phrase}")))
    return [m for _, m in sorted(matches, key=lambda pair: pair[0])]

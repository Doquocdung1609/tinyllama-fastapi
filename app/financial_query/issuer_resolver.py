"""Exact, corpus-bound entity recognition; contradictions override precedence."""
import re
from app.financial_query.contracts import IssuerMentionV1, Status, canonical_cik
from app.financial_query.normalizer import matching_text


def extract_issuers(question, catalog):
    text = matching_text(question)
    mentions, occupied = [], set()
    for m in re.finditer(r"\bcik\s*:?\s*([A-Za-z0-9]+)\b", text):
        cik = canonical_cik(m[1])
        candidates = [i.cik for i in catalog.issuers if i.cik == cik]
        mentions.append(IssuerMentionV1(text=m.group(), kind="CIK", candidate_ciks=candidates))
        occupied.update(range(*m.span()))
    vocabulary = {}
    for issuer in catalog.issuers:
        for kind, aliases in (("TICKER", issuer.tickers), ("NAME", [issuer.company_name]), ("ALIAS", issuer.verified_aliases)):
            for alias in aliases:
                key = matching_text(alias)
                vocabulary.setdefault(key, []).append((kind, issuer.cik))
    precedence = {"TICKER": 0, "NAME": 1, "ALIAS": 2}
    for alias in sorted(vocabulary, key=lambda x: (-len(x), x)):
        for m in re.finditer(r"(?<!\w)" + re.escape(alias) + r"(?!\w)", text):
            if any(i in occupied for i in range(*m.span())):
                continue
            candidates = vocabulary[alias]
            mentions.append(IssuerMentionV1(text=m.group(), kind=min((k for k, _ in candidates), key=precedence.get),
                candidate_ciks=sorted({c for _, c in candidates})))
            occupied.update(range(*m.span()))
    # Unknown explicit symbols are retained, not silently ignored beside a UI filter.
    for m in re.finditer(r"\b[A-Z][A-Z0-9.\-]{1,9}\b", question):
        token = m.group()
        # Raw/normalized positions differ after whitespace/Unicode normalization;
        # use whole-token vocabulary membership rather than raw positional offsets.
        if token.lower() in vocabulary or token in {"CIK", "USD", "EPS", "FY", "GAAP", "Q1", "Q2", "Q3", "Q4"} or re.fullmatch(r"FY[0-9]{4}", token):
            continue
        if token in {'10-K', '10-Q'}:
            continue
        occurrences = list(re.finditer(r'(?<!\w)' + re.escape(token.casefold()) + r'(?!\w)', text))
        if any(not all(i in occupied for i in range(*p.span())) for p in occurrences):
            mentions.append(IssuerMentionV1(text=token, kind="UNKNOWN", candidate_ciks=[]))
    for m in re.finditer(r"\b(?:for|issuer|ticker|company)\s+([a-z][a-z0-9.\-]*)", text):
        if not any(i in occupied for i in range(*m.span(1))) and m[1] not in {'the', 'two', 'year', 'fiscal', 'calendar'}:
            mentions.append(IssuerMentionV1(text=m[1], kind="UNKNOWN", candidate_ciks=[]))
    # A UI filter must not turn "Tesla net income" into another issuer's scope
    # simply because Tesla is absent from this catalog. Unsupported leading
    # name-like words are unresolved; this is intentionally not fuzzy NER.
    for m in re.finditer(r"\b([a-z][a-z0-9.\-]*)(?:['’]s)?\s+(?=(?:net sales|net income|operating income|revenue|total assets|current liabilities|earnings per share)\b)", text):
        if not any(i in occupied for i in range(*m.span(1))) and m[1] not in {
                'show', 'find', 'the', 'compare', 'what', 'was', 'is', 'its', 'and', 'for', 'in', 'about', 'explain', 'annual', 'consolidated'}:
            mentions.append(IssuerMentionV1(text=m[1], kind="UNKNOWN", candidate_ciks=[]))
    for m in re.finditer(r'\b([a-z][a-z0-9.\-]*)\s+and\s+([a-z][a-z0-9.\-]*)\b', text):
        known = [any(i in occupied for i in range(*m.span(group))) for group in (1, 2)]
        if any(known) and not all(known):
            group = 1 if not known[0] else 2
            mentions.append(IssuerMentionV1(text=m[group], kind='UNKNOWN', candidate_ciks=[]))
    unique = {(m.kind, m.text, tuple(m.candidate_ciks)): m for m in mentions}
    return sorted(unique.values(), key=lambda m: (m.kind, m.text, m.candidate_ciks))


def resolve_issuer(mentions, filters, catalog, accessions):
    constraints, reasons = [], []
    if filters.cik:
        constraints.append({i.cik for i in catalog.issuers if i.cik == filters.cik})
        reasons.append("FILTER_CIK")
    if filters.ticker:
        symbol = matching_text(filters.ticker)
        constraints.append({i.cik for i in catalog.issuers if symbol in [matching_text(t) for t in i.tickers]})
        reasons.append("FILTER_TICKER")
    for mention in mentions:
        if mention.kind == 'UNKNOWN':
            return None, Status.NEEDS_CLARIFICATION, ["UNKNOWN_ISSUER_MENTION"]
        constraints.append(set(mention.candidate_ciks))
        reasons.append(f"QUERY_{mention.kind}")
    ids = set(filters.filing_ids)
    if ids:
        matched = [f for f in catalog.filings if f.filing_id in ids]
        if {f.filing_id for f in matched} != ids:
            return None, Status.NO_ELIGIBLE_EVIDENCE, ["FILING_NOT_IN_CATALOG"]
        constraints.append({f.cik for f in matched})
        reasons.append("FILTER_FILING_MEMBERSHIP")
    if accessions:
        matched = [f for f in catalog.filings if f.accession in accessions]
        if {f.accession for f in matched} != set(accessions):
            return None, Status.NO_ELIGIBLE_EVIDENCE, ["ACCESSION_NOT_IN_CATALOG"]
        constraints.append({f.cik for f in matched})
        reasons.append("QUERY_ACCESSION_MEMBERSHIP")
    if not constraints:
        return None, Status.NEEDS_CLARIFICATION, ["ISSUER_REQUIRED"]
    if any(not c for c in constraints):
        return None, Status.NO_ELIGIBLE_EVIDENCE, ["ISSUER_NOT_IN_CATALOG"]
    # Collisions remain ambiguous unless another explicit constraint disambiguates.
    possible = set.intersection(*constraints)
    if len(possible) != 1:
        return None, Status.NEEDS_CLARIFICATION, ["ISSUER_CONFLICT" if not possible else "ISSUER_COLLISION"]
    return next(i for i in catalog.issuers if i.cik in possible), Status.RESOLVED, sorted(set(reasons))

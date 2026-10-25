"""Rule precedence and parsing only. No corpus lookup or network dependency."""
import re
from app.financial_query.contracts import IntentCategory as C, QueryIntentV1
from app.financial_query.normalizer import normalize_question, numeric_constraints
from app.financial_query.period_resolver import extract_periods
from app.financial_query.terminology import resolve_terms


def parse_query(question: str) -> QueryIntentV1:
    text = normalize_question(question)
    periods, dates, unresolved = extract_periods(text)
    numbers, numeric_unresolved = numeric_constraints(text)
    unresolved.extend(numeric_unresolved)
    if re.search(r"\b(not|except|excluding|without|rather than)\b", text):
        unresolved.append("NEGATED_CONSTRAINT_REQUIRES_CLARIFICATION")
    if re.search(r'\b(before|after|since|until|between|through|prior to|at least|at most|greater than|less than|more than)\b', text):
        unresolved.append('RANGE_OPERATOR_REQUIRES_CLARIFICATION')
    metrics = resolve_terms(text)
    forms = sorted(set(m.upper() for m in re.findall(r"(?<!\w)10-[kq](?:/a)?(?!\w)", text)))
    if re.search(r'\bannual report\b', text) and not forms:
        unresolved.append('EXPLICIT_FORM_REQUIRED')
    accessions = sorted(set(re.findall(r"(?<![0-9])[0-9]{10}-[0-9]{2}-[0-9]{6}(?![0-9])", text)))
    original = bool(re.search(r"\b(original|originally)\b", text))
    amended = bool(re.search(r"\b(amended|amendment)\b", text) or any(f.endswith('/A') for f in forms))
    if original and amended:
        unresolved.append("CONFLICTING_AMENDMENT_PREFERENCE")
    amendment = "ORIGINAL" if original else "AMENDED" if amended else "UNSPECIFIED"
    if len(forms) > 1:
        unresolved.append("CONFLICTING_FORMS")
    if any(m.relationship == 'AMBIGUOUS' for m in metrics):
        unresolved.append("AMBIGUOUS_METRIC")
    compare = bool(re.search(r"\b(compare|versus|vs|difference|change|growth)\b", text))
    if len(periods) > 1 and not compare:
        unresolved.append("MULTIPLE_PERIODS_WITHOUT_COMPARISON")
    if {'INSTANT', 'DURATION'} <= {p.kind for p in periods}:
        unresolved.append('INSTANT_DURATION_CONFLICT')
    if any(p.kind == 'CALENDAR_YEAR' for p in periods) and any(p.kind.startswith('FISCAL_') for p in periods):
        unresolved.append('FISCAL_CALENDAR_COMPARABILITY_UNRESOLVED')
    if compare and len(periods) < 2:
        unresolved.append("COMPARISON_PERIODS_REQUIRED")
    tags = []
    tests = (
        (C.CROSS_SECTION, bool(re.search(r"\b(across sections|cross.section|cash flow and income|income and cash flow)\b", text))),
        (C.PERIOD_COMPARISON, compare),
        (C.FINANCIAL_TERMINOLOGY, bool(re.search(r"\b(policy|meaning|define|definition|what does .* mean)\b", text))),
        (C.FINANCIAL_TABLE, bool(re.search(r"\b(table|balance sheet|row|column|segment|statement)\b", text))),
        (C.EXACT_FINANCIAL_VALUE, bool(metrics or numbers)),
        (C.SEMANTIC_PARAPHRASE, bool(re.search(r"\b(earned|owed|brought in|made money|financial|filing|annual report)\b", text) or forms or accessions)),
    )
    for tag, matched in tests:
        if matched:
            tags.append(tag)
    unsupported = bool(re.search(r"\b(buy stock|sell stock|investment advice|predict|forecast|weather|write code|execute|ignore previous instructions)\b", text))
    category = C.UNSUPPORTED if unsupported or not tags else C.AMBIGUOUS if unresolved else tags[0]
    rules = [f"INTENT:{t.value}" for t in tags]
    rules.extend(m.rule_id for m in metrics)
    if unsupported:
        rules.append("UNSUPPORTED_TASK")
    operation = ("PERCENTAGE_POINTS" if 'percentage point' in text else "RELATIVE_CHANGE" if re.search(r"\b(growth|percent change)\b", text)
                 else "DIFFERENCE" if 'difference' in text else "COMPARE") if compare else None
    units = [unit for phrase, unit in (("usd", "USD"), ("$", "USD"), ("thousand", "THOUSANDS"), ("million", "MILLIONS"),
              ("billion", "BILLIONS"), ("%", "PERCENT"), ("percent", "PERCENT"), ("percentage point", "PERCENTAGE_POINTS"),
              ("per share", "PER_SHARE"), ("eps", "PER_SHARE")) if phrase in text]
    return QueryIntentV1(original_question=question, normalized_question=text, category=category,
        secondary_intents=tags[1:] if category == (tags[0] if tags else None) else tags,
        metric_mentions=metrics, forms=forms, accessions=accessions, filing_dates=dates,
        reporting_periods=periods, amendment_preference=amendment, numerical_constraints=numbers,
        comparison_operation=operation, unresolved_slots=sorted(set(unresolved)),
        matched_rule_ids=sorted(set(rules)), unit_mentions=sorted(set(units)))

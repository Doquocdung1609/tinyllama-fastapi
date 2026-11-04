# Read-only port from PR #36 A5; research originals remain unchanged.
"""Opt-in C4R A5: scope-safe financial retrieval over immutable original chunks.

No prior FAITH-R arm, corpus payload or index is modified. Every search attempt
has an explicit outcome, including empty/error outcomes.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import re
import time
from typing import Any

from app.product.sec_ontology_v8 import ISSUERS, MetricTerm, detect_metric, normalized_view


@dataclass(frozen=True)
class A5Plan:
    original: str
    matching_view: str
    search_query: str
    issuer: str | None
    form: str | None
    fiscal_year: int | None
    requested_years: tuple[int, ...]
    quarter: int | None
    duration_months: int | None
    period_end: str | None
    metric: str | None
    metric_search_phrase: str | None
    statement: str | None
    value_kind: str | None
    scope: str | None
    currency: str | None
    unit: str | None
    intent: str
    unresolved: tuple[str, ...]


@dataclass(frozen=True)
class A5Filter:
    tickers: list[str] | None = None
    document_types: list[str] | None = None
    fiscal_periods: list[str] | None = None
    sections: None = None
    sectors: None = None
    geographies: None = None
    filing_date_start: None = None
    filing_date_end: None = None

    def is_empty(self) -> bool:
        return not (self.tickers or self.document_types or self.fiscal_periods)


@dataclass(frozen=True)
class A5Result:
    arm: str
    status: str
    query_plan: dict
    attempts: list[dict]
    hits: list[dict]
    candidate_pool_ids: list[str]
    candidate_scanned: int
    elapsed_ms: float


def plan_query(question: str) -> A5Plan:
    q = normalized_view(question)
    issuers = [ticker for ticker, aliases in ISSUERS.items()
               if any(re.search(r"(?<!\w)" + re.escape(alias) + r"(?!\w)", q) for alias in aliases)]
    forms = re.findall(r"(?<!\w)(?:10-k|10-q|20-f|6-k)(?!\w)", q)
    form = forms[0].upper() if len(set(forms)) == 1 else None
    years = tuple(sorted({int(y) for y in re.findall(r"(?<!\d)((?:19|20)\d{2})(?!\d)", q)}))
    date = re.search(r"(?<!\d)((?:19|20)\d{2})[-/](\d{1,2})[-/](\d{1,2})(?!\d)", q)
    end = (f"{date.group(1)}-{int(date.group(2)):02d}-{int(date.group(3)):02d}" if date else None)
    if end is None:
        vn_date = re.search(r"(?<!\d)(\d{1,2})[-/](\d{1,2})[-/]((?:19|20)\d{2})(?!\d)", q)
        if vn_date:
            end = f"{vn_date.group(3)}-{int(vn_date.group(2)):02d}-{int(vn_date.group(1)):02d}"
    if end:
        try:
            datetime.strptime(end, "%Y-%m-%d")
        except ValueError:
            end = None
    quarter_match = re.search(r"\bq\s*([1-4])\b|\b(?:quarter|quý)\s*(?:number\s*)?([1-4])\b", q)
    quarter = int(next(x for x in quarter_match.groups() if x)) if quarter_match else None
    duration = (3 if re.search(r"\bthree months\b|\b3 months\b|\b3 tháng\b|\bba tháng\b", q) else
                6 if re.search(r"\bsix months\b|\b6 months\b|\b6 tháng\b|\bsáu tháng\b", q) else
                9 if re.search(r"\bnine months\b|\b9 months\b|\b9 tháng\b|\bchín tháng\b", q) else
                3 if quarter else 12 if re.search(r"\bfiscal year\b|\bfull year\b|\bnăm tài chính\b|\bcả năm\b", q) else None)
    metric, conflicts = detect_metric(q)
    narrative = bool(re.search(r"\b(?:policy|accounting treatment|describe|explain|disclose|disclosure|corporate changes|corporate action|chính sách|giải thích)\b", q))
    intent = "NARRATIVE_POLICY" if narrative and metric is None else "FINANCIAL_NUMERIC" if metric else "UNKNOWN"
    scope = ("CONSOLIDATED" if re.search(r"\bconsolidated\b|\bhợp nhất\b", q) else
             "PARENT" if re.search(r"\bparent(?: company| only)?\b|\bcông ty mẹ\b|\briêng\b", q) else None)
    currency = "VND" if re.search(r"\bvnd\b|\bđồng\b", q) else "USD" if re.search(r"\busd\b|\bdollars?\b", q) else None
    unit = ("BILLION" if re.search(r"\bbillions?\b|\btỷ\b", q) else
            "MILLION" if re.search(r"\bmillions?\b|\btriệu\b", q) else
            "PERCENT" if re.search(r"\bpercent(?:age)?\b|%|\bphần trăm\b", q) else None)
    unresolved = []
    if len(issuers) != 1:
        unresolved.append("ISSUER_AMBIGUOUS_OR_ABSENT")
    if len(set(forms)) > 1:
        unresolved.append("FORM_CONFLICT")
    if conflicts:
        unresolved.append("METRIC_CONFLICT:" + ",".join(conflicts))
    if re.search(r"\bgross margin\b", q) and metric is None:
        unresolved.append("GROSS_MARGIN_AMOUNT_OR_RATIO_UNCLEAR")
    if re.search(r"\bdòng kinh doanh\b|\bbusiness line\b", q):
        unresolved.append("BUSINESS_LINE_NOT_VERIFIED_REPORTABLE_SEGMENT")
    if metric is None and not narrative:
        unresolved.append("METRIC_AMBIGUOUS_OR_ABSENT")
    if len(years) > 1 and end is None:
        # Comparatives are kept, but no single period is asserted.
        unresolved.append("MULTI_PERIOD_COMPARISON")
    issuer = issuers[0] if len(issuers) == 1 else None
    search = " ".join(x for x in (issuer, metric.search_phrase if metric else "", form or "",
                                   str(years[-1]) if years else "", "quarter" if quarter else "") if x)
    return A5Plan(question, q, search or question, issuer, form,
                  years[0] if len(years) == 1 else None, years, quarter, duration,
                  end, metric.code if metric else None,
                  metric.search_phrase if metric else None,
                  metric.statement if metric else None,
                  metric.value_kind if metric else None, scope, currency, unit,
                  intent, tuple(unresolved))


def retrieval_filters(plan: A5Plan) -> A5Filter:
    # Index B has Q-YYYY-MM and several incorrect FY values. Fiscal metadata
    # is evidence for ranking only, never a hard filter in this version.
    return A5Filter(tickers=[plan.issuer] if plan.issuer else None,
                    document_types=[plan.form] if plan.form else None)


def _accession(hit: dict) -> str:
    return hit.get("accession_number") or hit.get("document_id", "").split("_")[-1]


def _hit(result: Any) -> dict:
    return {"chunk_id": result.chunk_id, "ticker": result.ticker,
            "document_type": result.document_type, "fiscal_period": result.fiscal_period,
            "filing_date": result.filing_date, "section": result.section,
            "score": float(result.score), "text": result.text,
            "source_url": result.source_url, "accession_number": _accession(result.model_dump())}


def feature_audit(hit: dict, plan: A5Plan, report_dates: dict[str, str] | None = None) -> dict:
    body = hit.get("text", "").split("\n\n", 1)[-1]
    low = body.casefold()
    terms = plan.metric_search_phrase.split() if plan.metric_search_phrase else []
    metric_terms = [x for x in terms if len(x) >= 4 and x not in {"total", "profit", "income"}]
    metric_match = any(re.search(r"\b" + re.escape(x) + r"\b", low) for x in metric_terms)
    section = (hit.get("section") or "").casefold()
    financial_section = bool(re.search(r"financial statements|item 8|item 1\. financial|statements of", section))
    administrative = bool(re.search(r"exhibit|risk factors|signatures|item 15", section))
    accession = _accession(hit)
    report_end = (report_dates or {}).get(accession)
    period = (hit.get("fiscal_period") or "").casefold()
    period_match = bool(plan.period_end and report_end == plan.period_end)
    if not plan.period_end and plan.fiscal_year:
        period_match = f"{plan.fiscal_year}" in period or bool(report_end and report_end.startswith(str(plan.fiscal_year)))
    if plan.period_end and report_end and report_end != plan.period_end:
        period_conflict = True
    elif plan.fiscal_year and report_end and not report_end.startswith(str(plan.fiscal_year)):
        period_conflict = True
    else:
        period_conflict = False
    table_like = bool("|" in body and re.search(r"\|\s*\$?\s*\(?\d[\d,.]*\)?", body))
    # A row/cell is only a candidate. No value is verified from the pipe test.
    return {"issuer": hit.get("ticker") == plan.issuer if plan.issuer else None,
            "form": hit.get("document_type") == plan.form if plan.form else None,
            "report_date": report_end, "period_match": period_match,
            "period_conflict": period_conflict, "financial_section": financial_section,
            "administrative_section": administrative, "metric_term_present": metric_match,
            "table_like_candidate": table_like, "verification_status": "CANDIDATE_ONLY"}


def _ordering(features: dict, baseline_rank: int) -> tuple:
    return (-int(features["issuer"] is True), -int(features["form"] is True),
            int(features["period_conflict"]), -int(features["period_match"]),
            -int(features["financial_section"]), int(features["administrative_section"]),
            -int(features["metric_term_present"]), -int(features["table_like_candidate"]),
            baseline_rank)


class OriginalChunkSidecarA5:
    """Read-only bounded selector; records the scan cost and keeps original IDs."""

    def __init__(self, client: Any, collection: str = "financial_docs"):
        self.payloads = []
        offset = None
        while True:
            batch, offset = client.scroll(collection, offset=offset, limit=256,
                                          with_payload=True, with_vectors=False)
            self.payloads.extend(p.payload for p in batch)
            if offset is None:
                break

    def find(self, plan: A5Plan, quota: int, report_dates: dict[str, str]) -> tuple[list[dict], int]:
        if not plan.issuer or not plan.metric:
            return [], 0
        examined, candidates = 0, []
        for p in self.payloads:
            examined += 1
            if p.get("ticker") != plan.issuer or (plan.form and p.get("document_type") != plan.form):
                continue
            row = {key: p.get(key) for key in ("chunk_id", "ticker", "document_type",
                   "fiscal_period", "filing_date", "section", "text", "source_url",
                   "accession_number")}
            row["score"] = 0.0
            feat = feature_audit(row, plan, report_dates)
            if feat["metric_term_present"] and feat["financial_section"]:
                candidates.append((row, feat))
        candidates.sort(key=lambda pair: (_ordering(pair[1], 0), pair[0]["chunk_id"]))
        return [row for row, _ in candidates[:quota]], examined


def execute_a5(engine: Any, question: str, budget: int = 20,
               report_dates: dict[str, str] | None = None,
               sidecar: Any | None = None, use_fallback: bool = True) -> A5Result:
    if not 1 <= budget <= 100:
        raise ValueError("INVALID_A5_BUDGET")
    started = time.perf_counter()
    plan = plan_query(question)
    if plan.issuer is None or plan.intent == "UNKNOWN" or any(x.startswith("METRIC_CONFLICT") for x in plan.unresolved):
        return A5Result("A5", "ABSTAIN_QUERY_UNRESOLVED", asdict(plan), [], [], [], 0,
                        round((time.perf_counter() - started) * 1000, 3))
    filters = retrieval_filters(plan)
    attempts, candidates, seen = [], [], set()
    methods = [(plan.search_query, "bm25_dense", "expanded")]
    if use_fallback:
        methods.append((question, "sparse_dense", "same_scope_fallback"))
    for query, method, label in methods:
        begin = time.perf_counter()
        try:
            found = engine.search(query, method=method, k=min(budget * 3, 60),
                                  filters=filters, prefetch_k=60)
            rows = [_hit(r) for r in found]
            status, reason = ("COMPLETED_WITH_HITS" if rows else "COMPLETED_EMPTY"), None
        except Exception as exc:
            rows, status, reason = [], "ERROR", f"{type(exc).__name__}:{exc}"
        attempts.append({"label": label, "method": method, "query": query,
                         "filters": asdict(filters), "status": status,
                         "returned": len(rows), "reason": reason,
                         "elapsed_ms": round((time.perf_counter() - begin) * 1000, 3)})
        for row in rows:
            if row["chunk_id"] not in seen and (plan.issuer is None or row["ticker"] == plan.issuer):
                candidates.append(row)
                seen.add(row["chunk_id"])
        if len(candidates) >= min(budget * 3, 60):
            break
    scanned = 0
    sidecar_rows: list[dict] = []
    if sidecar is not None:
        begin = time.perf_counter()
        try:
            extra, scanned = sidecar.find(plan, max(1, budget // 4), report_dates or {})
            sidecar_rows = extra
            status, reason = ("COMPLETED_WITH_HITS" if extra else "COMPLETED_EMPTY"), None
        except Exception as exc:
            extra, status, reason = [], "ERROR", f"{type(exc).__name__}:{exc}"
        attempts.append({"label": "bounded_original_sidecar", "method": "payload_scan",
                         "query": plan.search_query, "filters": asdict(filters),
                         "status": status, "returned": len(extra), "reason": reason,
                         "scanned": scanned, "elapsed_ms": round((time.perf_counter()-begin)*1000, 3)})
        for row in extra:
            if row["chunk_id"] not in seen and row["ticker"] == plan.issuer:
                candidates.append(row)
                seen.add(row["chunk_id"])
    cap = min(budget * 3, 60)
    if sidecar is not None:
        # Reserve explicit slots. The original v1 candidate[:60] truncation
        # silently discarded every appended sidecar row when base returned 60.
        reserve = min(max(1, budget // 4), cap)
        internal = candidates[:cap - reserve]
        included = {r["chunk_id"] for r in internal}
        for row in sidecar_rows:
            if row["chunk_id"] not in included and len(internal) < cap:
                internal.append(row)
                included.add(row["chunk_id"])
        internal += [r for r in candidates if r["chunk_id"] not in included][:cap-len(internal)]
    else:
        internal = candidates[:cap]
    audited = [(row, feature_audit(row, plan, report_dates), rank)
               for rank, row in enumerate(internal, 1)]
    audited.sort(key=lambda x: _ordering(x[1], x[2]))
    hits = [{"rank": i, **row, "feature_audit": features,
             "baseline_candidate_rank": rank, "verification_status": "CANDIDATE_ONLY"}
            for i, (row, features, rank) in enumerate(audited[:budget], 1)]
    status = "COMPLETED_WITH_HITS" if hits else "ERROR" if any(a["status"] == "ERROR" for a in attempts) else "COMPLETED_EMPTY"
    return A5Result("A5", status, asdict(plan), attempts, hits,
                    [x["chunk_id"] for x in internal], scanned,
                    round((time.perf_counter() - started) * 1000, 3))

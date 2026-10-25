# D1 implementation report

Authorization: `TOPIC3_MILESTONE_D1_CONTRACTS_AND_DETERMINISTIC_IMPLEMENTATION_AUTHORIZED`.
Scope: deterministic Python query interpretation and metadata scope resolution only.

## Baseline and dependency

Base: `d1d5195b26f77d8fb25c830229c4c3693d4b638f`, fetched `origin/codex/topic3-milestone-b-sec-corpus`. Accepted C merge `69e6866552d15571858b44707d59a453443fae9c` verified as ancestor. Clean worktree before branch creation. D1 branch `codex/topic3-milestone-d1-query-understanding` was created directly from that accepted target, not from research PR #9.

PR #9 was independently inspected: Draft/open/unmerged, HEAD `bcd5728afda4207e79ebf789edd73594aab60bbe`; all13 blueprint documents were present. Design references reviewed:01,03,04,08,11,13. None of their13 files is copied into this branch. They remain accessible on the separate research branch/PR. New D1 reports reside in this subdirectory only.

Actual C inspected: `financial_ingestion/schemas.py`, registry, SEC identity/amendment linkage in pipeline/client, search filters in `api/financial_index.py`, current fixtures and persistent/hardening/legacy tests. Existing schema uses Pydantic v2 with `extra=forbid`; D1 follows this convention without changing existing schemas.

## Modules and interfaces

| Actual module under `app/financial_query/` | Responsibility |
|---|---|
| `contracts.py` | Strict versioned Pydantic objects, enum statuses/categories, Decimal constraints, CIK/filing/catalog membership and linkage validation |
| `normalizer.py` | Raw question retained; NFC/whitespace/casefold matching view, bounded input, ASCII numeric parsing with signs/units; no NFKC confusable conversion |
| `intent_classifier.py` | Standalone `parse_query(question)`; explicit rule precedence, secondary tags, terminology/period/numeric extraction; no catalog lookup |
| `issuer_resolver.py` | Whole-token verified CIK/ticker/name/alias recognition, collision/intersection/conflict handling; unknown symbols/name-like phrases stay unresolved |
| `filing_resolver.py` | Explicit accession/form/date/version constraints; no latest-file selection or amendment synthesis |
| `period_resolver.py` | Separate filing dates and financial periods; match only typed supplied column metadata; incomplete metadata retained as uncertain |
| `terminology.py` | Small `financial-terminology/v1` dictionary with exact/synonym/ambiguous relationships; related concepts are never rewrites |
| `catalog.py` | Pure `catalog_from_verified_metadata(manifest, structured_filings, generation_id=None)` adapter; no registry constructor, I/O or index opening |
| `scope_resolver.py`, `__init__.py` | Narrow public `resolve_financial_query(question, explicit_filters, corpus_catalog, generation_identity=None)` interface and ordered trace |

Input: a bounded question, `ExplicitFiltersV1` or matching dictionary (or null), and `CorpusCatalogV1` or matching dictionary. Output: `ScopeResolutionResultV1`. Catalogs/filters are revalidated; no caller object is mutated. The caller supplies a trusted metadata snapshot. No external lookup is performed to decide whether an absent company exists outside the corpus.

Example (synthetic fixture, executable after loading that catalog):

```python
from app.financial_query import resolve_financial_query
result = resolve_financial_query(
    "Alpha net sales 10-K FY2024", {}, catalog,
    generation_identity=catalog.generation_id,
)
assert result.status.value == "RESOLVED"
```

The matched filing is the synthetic2026 accession containing the explicit2024 comparative-column metadata. This tests the filing-year/column-year distinction; it is not a financial retrieval result.

## Contracts and statuses

- `QueryIntentV1`: `financial-query-intent/v1`; original and matching text, category/secondary tags, issuer/metric mentions, forms/accessions, separate filing date/report periods, amendment request, Decimal numeric predicates, units, requested operation, unresolved slots and rule IDs.
- `ResolvedScopeV1`: `financial-resolved-scope/v1`; dataset/manifest/generation, CIK/aliases, explicit filing membership/forms, dates/period requirements, matched column source references, amendment selection, warnings/reasons/status.
- `ScopeResolutionResultV1`: `financial-scope-result/v1`; intent, optional scope, status, clarification questions, warnings and deterministic stage trace. Invalid questions may have null intent; valid-but-invalid-filter input may retain its parsed intent. No malformed value is echoed in error diagnostics.
- `CorpusCatalogV1`: `financial-query-catalog/v1`; trusted snapshot with issuers, verified aliases and filing membership. Typed `ColumnPeriodV1` requires a source reference. Fixtures declare their synthetic provenance. No fake confidence probabilities are present.

Statuses remain distinct: `RESOLVED` means metadata scope is explicit; `NEEDS_CLARIFICATION` covers ambiguity/conflict/metadata gaps; `UNSUPPORTED` means no supported financial intent/task; `NO_ELIGIBLE_EVIDENCE` means no match within the supplied known catalog/complete typed period coverage; `INVALID_INPUT` means validation/generation identity failure. An unresolved scope can expose retained candidate filings for audit, but is never relabeled resolved.

**RESOLVED is not proof that a metric/value/unit was found in a document.** D1 does not retrieve or inspect supporting rows. Metric/unit-bearing questions propagate `METRIC_AND_UNIT_EVIDENCE_NOT_VERIFIED_BY_D1`. Numerical predicates are captured, not evaluated against source values; a D2/D3 consumer would need additional authorized evidence validation.

## Intent compatibility and precedence

| D1 category | Blueprint taxonomy | Precedence after ambiguity/unsupported checks |
|---|---|---:|
| CROSS_SECTION | cross_section |1|
| PERIOD_COMPARISON | comparison |2|
| FINANCIAL_TERMINOLOGY | terminology |3|
| FINANCIAL_TABLE | table |4|
| EXACT_FINANCIAL_VALUE | exact |5|
| SEMANTIC_PARAPHRASE | paraphrase |6|
| AMBIGUOUS | ambiguous | unresolved parsed constraints dominate |
| UNSUPPORTED | unsupported boundary | unsupported task/no recognized supported intent dominates |

Secondary intent tags preserve other matched classes. This is a small English lexical classifier, not general semantic understanding. Scope ambiguity (e.g. duplicate ticker) can occur after a syntactically exact-value classification; result status communicates it separately.

## Conservative resolution choices

Contradictory entity constraints are errors even though recognition prefers explicit CIK, ticker, exact name then verified alias. A ticker collision may be disambiguated by a validated CIK; it is never treated as globally unique. No issuer is inferred merely because the catalog contains only one issuer. An explicit known accession can establish its issuer through catalog membership, recorded in the trace.

Forms10-K/10-Q/10-K/A/10-Q/A and exact accessions are supported. A queried10-K explicitly selects that form; it is not silently replaced by a10-K/A. Without an explicit version selection, coexisting original/amended candidates require clarification. Missing amendment linkage also requires clarification, even for an explicitly requested amendment. Multiple originals can be returned as an explicit candidate set with warning; no latest-file assumption or merged statement is made.

`FY2025`, `Q2 FY2025`, calendar year, explicit year/quarter-ended dates and as-of instants stay distinct. Relative/bare years, negated constraints, contradictory periods, fiscal/calendar comparisons and instant/duration comparisons require clarification. Filed-in/on expressions constrain filing date only. Explicit financial-period filters are interpreted as financial scope requirements and are **not** blindly forwarded into C's filing-level fiscal-year filter.

Blueprint discrepancy resolved minimally: accepted C metadata has filing fiscal fields and free-text `FinancialTable.reporting_periods`, not universally verified typed cell/column-period links. The adapter preserves raw labels but sets `column_periods_complete=False` and creates no typed column claims. Period-specific resolution remains incomplete until a caller supplies separately verified column metadata. D1 does not implement D2 table parsing or infer fiscal calendars from tickers.

## Verification and limitations

See [test and benchmark report](D1_TEST_AND_BENCHMARK_REPORT.md) for exact commands/results, [40 cases](D1_SCOPE_RESOLUTION_CASES.md) for fixture oracles and [compatibility/risk](D1_COMPATIBILITY_AND_RISK_REPORT.md) for gate evidence. No LLM, retrieval ranking, vector generation, API/UI wiring or production-default change is included. This interface is opt-in and is not imported by existing production routes.

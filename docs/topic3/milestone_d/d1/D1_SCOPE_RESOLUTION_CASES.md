# D1 scope-resolution cases

All cases below are **synthetic deterministic fixtures**, not SEC evidence, retrieval benchmarks or held-out evaluation. Source: `tests/fixtures/financial_query/catalog.json` and `cases.json`. The catalog contains three invented issuers (Alpha/Beta/Gamma), six invented filings, a duplicate ticker DUP, explicit December/June fiscal year-end metadata, one linked original/amended pair, one unlinked amendment, typed comparative-column metadata and a partial filing with incomplete period metadata. Hashes/IDs are synthetic labels, not evidence of real financial facts.

The expected columns below are fixture oracles independently asserted by `test_source_authored_scope_cases`, including exact eligible membership where given. `NONE` means no resolved membership is asserted; unresolved results may retain candidates for audit. Classification and resolution status are separate: a syntactically exact-value question may still have an ambiguous issuer/version.

| Case | Input question | Explicit filters | Expected category | Expected status | Expected filing accessions / failure reason |
|---|---|---|---|---|---|
| C01 | Alpha net sales 10-K FY2025 | `{}` | EXACT_FINANCIAL_VALUE | RESOLVED | 0000000101-26-000001 |
| C02 | ALP net income 10-K FY2024 | `{}` | EXACT_FINANCIAL_VALUE | RESOLVED | 0000000101-26-000001 |
| C03 | CIK 101 total assets 10-K | `{}` | EXACT_FINANCIAL_VALUE | RESOLVED | 0000000101-26-000001 |
| C04 | Alpha Example Corporation revenue 10-K | `{}` | EXACT_FINANCIAL_VALUE | RESOLVED | 0000000101-26-000001 |
| C05 | DUP revenue 10-K | `{}` | EXACT_FINANCIAL_VALUE | NEEDS_CLARIFICATION | NONE; ISSUER_COLLISION |
| C06 | ABC revenue 10-K | `{}` | EXACT_FINANCIAL_VALUE | NEEDS_CLARIFICATION | NONE; UNKNOWN_ISSUER_MENTION |
| C07 | Beta revenue 10-K | `{"ticker":"ALP"}` | EXACT_FINANCIAL_VALUE | NEEDS_CLARIFICATION | NONE; ISSUER_CONFLICT |
| C08 | revenue 10-K | `{}` | EXACT_FINANCIAL_VALUE | NEEDS_CLARIFICATION | NONE; ISSUER_REQUIRED |
| C09 | CIK 999 revenue 10-K | `{}` | EXACT_FINANCIAL_VALUE | NO_ELIGIBLE_EVIDENCE | NONE; ISSUER_NOT_IN_CATALOG |
| C10 | Alpha revenue FY2025 | `{}` | EXACT_FINANCIAL_VALUE | NEEDS_CLARIFICATION | NONE; AMENDMENT_SELECTION_REQUIRED |
| C11 | Alpha revenue 10-K/A FY2025 | `{}` | EXACT_FINANCIAL_VALUE | RESOLVED | 0000000101-26-000002; warning PARTIAL_EXTRACTION |
| C12 | Alpha revenue original FY2025 | `{}` | EXACT_FINANCIAL_VALUE | RESOLVED | 0000000101-26-000001 |
| C13 | Alpha revenue 10-Q/A Q2 FY2025 | `{}` | EXACT_FINANCIAL_VALUE | NEEDS_CLARIFICATION | NONE; AMENDMENT_LINKAGE_MISSING |
| C14 | Alpha revenue 10-Q Q2 FY2025 | `{}` | EXACT_FINANCIAL_VALUE | RESOLVED | 0000000101-25-000003 |
| C15 | Alpha revenue 10-K filed in February 2026 | `{}` | EXACT_FINANCIAL_VALUE | RESOLVED | 0000000101-26-000001 |
| C16 | Alpha revenue 10-K filed in 2027 | `{}` | EXACT_FINANCIAL_VALUE | NO_ELIGIBLE_EVIDENCE | NONE; NO_MATCHING_FILING |
| C17 | Alpha revenue 10-K FY2027 | `{}` | EXACT_FINANCIAL_VALUE | NO_ELIGIBLE_EVIDENCE | NONE; REQUESTED_PERIOD_NOT_IN_CATALOG |
| C18 | Alpha revenue 10-K 2025 | `{}` | AMBIGUOUS | NEEDS_CLARIFICATION | NONE; UNQUALIFIED_PERIOD |
| C19 | Alpha net income last year | `{}` | AMBIGUOUS | NEEDS_CLARIFICATION | NONE; RELATIVE_PERIOD_REQUIRES_REFERENCE |
| C20 | Beta revenue 10-K calendar year 2025 | `{}` | EXACT_FINANCIAL_VALUE | NO_ELIGIBLE_EVIDENCE | NONE; REQUESTED_PERIOD_NOT_IN_CATALOG |
| C21 | Alpha revenue 10-K year ended December 31, 2025 | `{}` | EXACT_FINANCIAL_VALUE | RESOLVED | 0000000101-26-000001 |
| C22 | Alpha total assets 10-K as of December 31, 2025 | `{}` | EXACT_FINANCIAL_VALUE | RESOLVED | 0000000101-26-000001 |
| C23 | Alpha revenue 10-Q quarter ended June 30, 2025 | `{}` | EXACT_FINANCIAL_VALUE | RESOLVED | 0000000101-25-000003 |
| C24 | Compare Alpha operating income 10-K FY2024 vs FY2025 | `{}` | PERIOD_COMPARISON | RESOLVED | 0000000101-26-000001 |
| C25 | Compare Alpha operating income for two fiscal years | `{}` | AMBIGUOUS | NEEDS_CLARIFICATION | NONE; COMPARISON_PERIODS_REQUIRED |
| C26 | Alpha revenue 10-K FY2025 FY2024 | `{}` | AMBIGUOUS | NEEDS_CLARIFICATION | NONE; MULTIPLE_PERIODS_WITHOUT_COMPARISON |
| C27 | Gamma revenue 10-K FY2025 | `{}` | EXACT_FINANCIAL_VALUE | NEEDS_CLARIFICATION | NONE; COLUMN_PERIOD_METADATA_INCOMPLETE; warning PARTIAL_EXTRACTION |
| C28 | Find Alpha revenue recognition policy in the 10-K | `{}` | FINANCIAL_TERMINOLOGY | RESOLVED | 0000000101-26-000001 |
| C29 | What does Alpha balance sheet say about current liabilities 10-K? | `{}` | FINANCIAL_TABLE | RESOLVED | 0000000101-26-000001 |
| C30 | Alpha earned money in its annual report 10-K | `{}` | SEMANTIC_PARAPHRASE | RESOLVED | 0000000101-26-000001 |
| C31 | Alpha cash flow and income across sections 10-K | `{}` | CROSS_SECTION | RESOLVED | 0000000101-26-000001 |
| C32 | Alpha predict stock price | `{}` | UNSUPPORTED | UNSUPPORTED | NONE; NO_SUPPORTED_FINANCIAL_INTENT |
| C33 | Alpha operating profit 10-K | `{}` | AMBIGUOUS | NEEDS_CLARIFICATION | NONE; AMBIGUOUS_METRIC |
| C34 | Alpha revenue 10-K FY2025 | `{"fiscal_year":2024}` | EXACT_FINANCIAL_VALUE | NEEDS_CLARIFICATION | NONE; PERIOD_FILTER_CONFLICT |
| C35 | Alpha revenue 10-K | `{"form_type":"10-Q"}` | EXACT_FINANCIAL_VALUE | NEEDS_CLARIFICATION | NONE; FORM_FILTER_CONFLICT |
| C36 | Alpha revenue 10-K 0000000101-26-999999 | `{}` | EXACT_FINANCIAL_VALUE | NO_ELIGIBLE_EVIDENCE | NONE; ACCESSION_NOT_IN_CATALOG |
| C37 | revenue 0000000101-26-000001 | `{}` | EXACT_FINANCIAL_VALUE | RESOLVED | 0000000101-26-000001 |
| C38 | Alpha revenue 10-K original amended | `{}` | AMBIGUOUS | NEEDS_CLARIFICATION | NONE; CONFLICTING_AMENDMENT_PREFERENCE |
| C39 | Alpha revenue 10-K 10-Q | `{}` | AMBIGUOUS | NEEDS_CLARIFICATION | NONE; CONFLICTING_FORMS |
| C40 | Alpha revenue 10-K USD (1,250) million | `{}` | EXACT_FINANCIAL_VALUE | RESOLVED | 0000000101-26-000001 |

CIK/filing membership: Alpha `0000000101`, Beta `0000000202`, Gamma `0000000303`; full filing IDs have form `sec:<CIK>:<accession>`. C02 requires the2024 comparative column in the filing submitted in2026; it must not be excluded by filing year. C20 intentionally lacks calendar-year evidence despite a matching fiscal label. C27 retains incomplete candidate metadata and propagates partial extraction rather than claim exact column resolution. C37 derives issuer only from a validated explicit accession.

Additional focused tests cover raw/normalized text, Decimal signs/units, malformed expressions, issuer-filter collisions, generation drift, serialization/determinism, catalog reordering, adapter correspondence, unknown company beside a UI filter, Unicode confusables, control characters, path/SQL/instruction-like strings and source-object nonmutation. See `tests/test_financial_query.py`. These examples are development correctness fixtures; they are not a source-grounded D5 dataset or evidence of financial retrieval gains.

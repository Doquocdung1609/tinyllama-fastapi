# D1 independent-style adversarial review

Review date: 2026-10-25. Authorization: `TOPIC3_MILESTONE_D1_INDEPENDENT_SECURITY_CORRECTNESS_AND_INTEGRATION_REVIEW`.

## Identity, state and scope

This is a fresh adversarial pass by the same Codex system that authored D1, **not independent human review**. Original implementation conclusions were not treated as proof: new tests were run against the original Python source before repairs, then against the repaired tree. No merge/integration authorization is inferred from this report.

Original PR #10 review HEAD: `4506e3e0346ce1107fefe90d2cc2e57e8bdfa3f5`, Draft/open/unmerged, head `codex/topic3-milestone-d1-query-understanding`, base `codex/topic3-milestone-b-sec-corpus`. Target was `d1d5195b26f77d8fb25c830229c4c3693d4b638f`; accepted C merge `69e6866552d15571858b44707d59a453443fae9c` remains an ancestor. PR #9 was Draft/open/unmerged at `bcd5728afda4207e79ebf789edd73594aab60bbe`. GitHub discussion/review timeline returned no comments. No competing source/target commits were present at preflight or candidate construction.

A dedicated managed review worktree starts at the exact original HEAD. Initial repairs are commit `901a4d389aedbdc69d0d744d437c95cdc113097e`; full-lexeme closure is `812dca898bcf4f304e72c5bfa1c44eb67f8f272a`. A second managed worktree tests integration candidates. Main and accepted target refs are not checked out or modified for integration. Final documentation-only delivery SHA and final-head CI identity are recorded in PR #10/final delivery, avoiding a self-referential SHA inside its own commit.

## Original 19-file inventory and review checklist

All listed paths are repository-relative. Production module inspection included complete bodies, exception boundaries, call graph and validation behavior, not just reports.

| Original file | Reviewed invariants / conclusion |
|---|---|
| `app/financial_query/__init__.py` | Export only; no service/index initialization; unchanged |
| `app/financial_query/catalog.py` | Pure supplied-object adapter; manifest content hash/membership/raw+normalized metadata hash/version correspondence; no byte authentication or registry I/O; unchanged |
| `app/financial_query/contracts.py` | Typed versions/statuses, CIK/filing/linkage/duplicate validation, frozen containers and limits; F07/F08 repaired |
| `app/financial_query/filing_resolver.py` | Explicit accession/form/date constraints, orphan amendment warnings, no latest-file or synthesized amendment; unchanged; caller status priority corrected in scope layer |
| `app/financial_query/intent_classifier.py` | Precedence, secondary tags, full form tokens, qualifiers and unit tokens; F02/F09 repaired |
| `app/financial_query/issuer_resolver.py` | Exact alias boundaries, collisions/intersections, no identity precedence override, CIK token validation; F01 repaired |
| `app/financial_query/normalizer.py` | Raw retention, NFC, control/surrogate limits, Decimal precision, numeric syntax/units; F04/F05 repaired |
| `app/financial_query/period_resolver.py` | Filing-date/period separation, typed column matching, uncertainty retention; F03 repaired; no fiscal-calendar inference |
| `app/financial_query/scope_resolver.py` | Ordered trace, intake revalidation, generation check, status priority, membership/warnings; F06/F08 repaired |
| `app/financial_query/terminology.py` | Exact/synonym/related distinction, longer phrases, attribution qualifier; F09 repaired |
| `tests/test_financial_query.py` | Read all114 tests; reproduced114 PASS on original source; untouched |
| `tests/fixtures/financial_query/catalog.json` | Three synthetic issuers, duplicate ticker, six filings, typed/incomplete columns and linked/orphan amendments; untouched |
| `tests/fixtures/financial_query/cases.json` | Forty expected outcomes, classified separately from scope status; untouched |
| `scripts/benchmark_financial_query.py` | Fixed fixture reads, bounded fixed-argument subprocess, warm/fresh-process boundaries, no query-controlled command or index; untouched |
| `docs/topic3/milestone_d/d1/D1_IMPLEMENTATION_REPORT.md` | Architecture/contracts/limits checked against code; historical evidence retained, review addendum appended |
| `docs/topic3/milestone_d/d1/D1_SCOPE_RESOLUTION_CASES.md` | All40 cases checked against fixtures; development correctness cases, not real SEC evidence; untouched |
| `docs/topic3/milestone_d/d1/D1_TEST_AND_BENCHMARK_REPORT.md` | Original counts/timing boundaries preserved; no repaired-code timing claim |
| `docs/topic3/milestone_d/d1/D1_COMPATIBILITY_AND_RISK_REPORT.md` | Trust/compatibility statements checked; review qualification appended |
| `docs/topic3/milestone_d/d1/D1_RESOLVER_BENCHMARK.json` | Historical D1 fixture measurement, not current repaired-code benchmark; bytes retained |

Also inspected accepted `financial_ingestion/schemas.py`, `pipeline.validate_metadata_identity`, SEC CIK/accession helpers, registry initialization, and `financial_index/corpus.verified_source`. D1 intentionally uses stricter query CIK parsing than the legacy helper that strips nondigits; accepted C code was not changed.

## Demonstrated findings and repairs

No CRITICAL defect was demonstrated. Four HIGH and five MEDIUM findings below were actionable. HIGH means wrong scope or corrupted numeric intent in D1's core contract; D1 remains opt-in, so this is not a claim of exploitation through a production route. All examples are synthetic and use the existing synthetic catalog unless stated otherwise.

### F01 — HIGH: CIK prefix acceptance

- File/function: `app/financial_query/issuer_resolver.py::extract_issuers`.
- Contract/preconditions: explicit CIK must be wholly valid; catalog contains CIK202.
- Reproducer: `resolve_financial_query("CIK 202.9 revenue 10-K", {}, catalog)`; also `202/101`.
- Expected: `INVALID_INPUT`; observed original: `RESOLVED` for CIK `0000000202`, having silently discarded the suffix.
- Repair: validate the entire CIK token, allowing only trailing sentence punctuation. No external identity lookup or permissive nondigit stripping.
- Regression: `test_review_counterexamples[F01-cik-decimal/F01-cik-path]`; alias-equivalence controls retain leading-zero support.

### F02 — HIGH: unsupported/malformed filing identity silently ignored or truncated

- File/function: `intent_classifier.py::parse_query`.
- Preconditions: Beta has10-K but no20-F.
- Reproducer: `Beta revenue 20-F`; `Beta revenue 10-k/ab`; later suffix controls `10-k.a`, `10-k_b`, and `revenue prefix0000000202-25-000001`.
- Expected: typed unresolved form; observed: `RESOLVED`10-K, either with no extracted form or a truncated10-K token.
- Repair: inspect whole supported-family form lexemes and add `UNSUPPORTED_OR_MALFORMED_FORM` for unsupported variants; accessions must be standalone tokens, never an embedded substring used to infer issuer. Malformed accession-containing tokens clarify. No new filing-form coverage is asserted.
- Regression: F02 counterexamples. `10-q2` was already rejected on the original source through period ambiguity; it remains a negative control, not an additional claimed original failure.

### F03 — HIGH: malformed period request disappears

- File/function: `period_resolver.py::extract_periods`.
- Preconditions: Beta's typed FY2025 column is present.
- Reproducer: `Beta revenue 10-K q5 FY2025`, lowercase `fy2025q2` or `fy2025.1`; bare year2200 also escaped the old year guard.
- Expected: clarification, not a whole-year/unrestricted scope. Observed: FY2025/all-filing `RESOLVED`.
- Repair: detect unconsumed fiscal/quarter/calendar-shaped tokens and cover the schema's upper year boundary. Supported grammar remains unchanged; compact/malformed variants are rejected conservatively. The guard excludes the Q in a10-Q form before an accession.
- Regression: F03 counterexamples and all-four-quarter/January-fiscal/comparative controls.

### F04 — HIGH: parenthetical Decimal precision loss

- File/function: `normalizer.py::numeric_constraints`.
- Reproducer: `USD (123456789012345678901234567890.123456789)`; repeat under Decimal precision6/28/50.
- Expected: exact negative value preserving every digit. Observed under precision28: `-1.234567890123456789012345679E+29`; precision6 loses more digits.
- Repair: `Decimal.copy_negate()` instead of context-sensitive unary minus. No arithmetic evaluation added.
- Regression: `test_F04_parenthetical_decimal_preserves_all_digits_independent_of_context`.

### F05 — MEDIUM: numeric predicate/unit loss

- File/function: `normalizer.py::numeric_constraints`.
- Reproducers: `Beta revenue 10-K 1,250.75` → empty numeric list; `125.50 USD million` → multiplier1; `USD 12%` → percent with currency discarded.
- Expected: preserve an untyped formatted number as unit UNKNOWN, or request clarification for unsupported unit order/conflicting units. No assumed currency/equivalence.
- Repair: capture unsigned decimal/grouped literals; block unsupported currency-before-scale suffix order and conflicting amount/percent modifiers. Bare unqualified integer counts/years remain conservative, not assumed monetary values.
- Regression: F05 fixtures, unsigned-value test and six required numeric examples.

### F06 — MEDIUM: conflict downgraded to absence

- File/function: `scope_resolver.py::resolve_financial_query`.
- Reproducer: query `Beta revenue 10-K`, filters `{form_type:10-Q,fiscal_year:2025}`.
- Expected: `NEEDS_CLARIFICATION` for `FORM_FILTER_CONFLICT`. Observed: period matching on an empty candidate list replaced it with `NO_ELIGIBLE_EVIDENCE` and removed clarification questions.
- Repair: return empty-candidate filing conflicts immediately; never overwrite a retained clarification with a missing-period result.
- Regression: F06 fixture; restriction-monotonicity/status controls.

### F07 — MEDIUM: inconsistent shared-accession metadata accepted

- File/function: `contracts.py::CorpusCatalogV1.membership`.
- Preconditions/reproducer: copy Alpha's accession onto Beta but retain Beta's contradictory filing/report dates; the old catalog validated and Beta resolved.
- Expected: `INVALID_INPUT` for contradictory submission metadata. Repair: shared accession entries must agree on form, filed date and report end. Consistent joint-registrant entries remain allowed, and subject CIK is never derived from accession prefix.
- Regression: `test_F07_inconsistent_duplicate_accession_is_invalid` plus a consistent joint-registrant/ambiguous-accession control.
- Qualification: this is **not** a universal rule that every repeated accession across CIKs is invalid. SEC describes accession as a submission identifier and documents co-registrant submissions: [SEC accession guidance](https://www.sec.gov/submit-filings/filer-support-resources/how-do-i-guides/prepare-submit-my-form-id-application), [SEC filer manual](https://www.sec.gov/file/edgarfm-vol2-v76). D1 checks structural correspondence, not authentic co-registrant status.

### F08 — MEDIUM: catalog complexity lacks effective text/tree budget

- File/functions: `contracts.py::Contract`, `scope_resolver.py` intake.
- Reproducer: put a100,000-character string in `raw_column_labels`; the old resolver accepts it as `RESOLVED`. Many nested labels were otherwise unconstrained despite question length limits.
- Expected: bounded intake. Repair: max4,000 characters/string; pre-serialization iterative budget of100,000 nodes,2,000,000 total string characters, depth12 and50,000 items/container; cycles rejected. No truncation or I/O.
- Regression: F08 text-limit, cycle/malformed-catalog and bounded-runtime tests. This is private-library hardening, not a demonstrated public-service DoS or a worst-case CPU guarantee.

### F09 — MEDIUM: metric qualifier and unit substring semantics

- Files/functions: `terminology.py::resolve_terms`, `intent_classifier.py::parse_query`.
- Reproducers: `net income attributable to parent` became plain exact `net income`; `12 percentage points` added both PERCENT and POINTS; `steps` added PER_SHARE via substring `eps`.
- Expected: preserve attribution, distinguish units, avoid substring inference. Repair: qualified attribution entries remain distinct from net income; unrecognized attribution is ambiguous; unit mentions use token patterns.
- Regression: F09 tests and distinct-multiple-metric controls. No row presence/unit/financial amount is verified by these dictionary changes.

## Trust and integration interpretation

Three distinct boundaries: (1) Pydantic structural validation, (2) metadata lineage/membership correspondence, (3) cryptographic source-byte verification. D1 implements1 and parts of2; it **does not implement3**. A valid-looking forged hash or alias supplied in a trusted catalog remains accepted, as a deliberate boundary test demonstrates. Upstream C provenance must authenticate source artifacts/metadata before any future consumer treats them as evidence.

`RESOLVED` is metadata scope only. Unresolved `eligible_filing_ids` are retained candidates, not verified evidence; consumers must gate on the result status. Matched refs are caller-supplied typed metadata references, not checked citations. Missing fiscal calendars, free-text-only period labels, partial extraction and orphan amendments remain explicit limitations. No financial answer or retrieval-quality claim is permitted.

Before repairs: original114 tests passed while the final new56-test inventory failed22 and passed34. Four full-lexeme suffix/embedded-token cases also failed on the intermediate repaired delivery (4 FAIL/52 PASS); these were closed in `812dca8`. After closure:114 original+56 review tests pass. Full/local/core/candidate results and exact candidate identity are in the companion reports. All original524 accepted-baseline Git blobs remain identical; D1 runtime additions/repairs are opt-in and no API/UI/retrieval default changed.

## Owner recommendation and gates

Recommendation: **MILESTONE_D1_ACCEPTANCE_RECOMMENDED_WITH_LIMITATIONS**, subject to the final delivery-head revalidation recorded in PR #10/final report. Repaired delivery `2bdeb0d54adc6c3c2d1af8fdd4d48951dc165973` passed [core run40176378480](https://github.com/Doquocdung1609/tinyllama-fastapi/actions/runs/40176378480); logs show temporary test-merge `ab1a5d4413e7d80c93a509525ac87b1aa363f787` with the exact accepted target,360 PASS/1 SKIP/3 deselected/1 warning. This subsequent documentation-only gate record does not change tested Python/fixtures; its own current-head CI is checked again at delivery and recorded outside the commit in PR metadata. No recommendation authorizes a merge. No unresolved HIGH/CRITICAL finding is retained after the nine repairs; broader English NER, authentic catalog acquisition and live source/LLM/UI verification remain outside demonstrated coverage.

| Gate | Status | Evidence |
|---|---|---|
| IR01 | VERIFIED |Exact PR #10/#9/base refs and empty comment timeline at preflight; re-fetch before push |
| IR02 | VERIFIED |Complete19-file/module checklist above and accepted-interface inspection |
| IR03 | VERIFIED_WITH_LIMITATIONS |F01, alias/collision/permutation/unrelated-addition controls; bounded grammar |
| IR04 | VERIFIED_WITH_LIMITATIONS |F02/F07, original amendment/accession tests; no synthesized parent/version merge |
| IR05 | VERIFIED_WITH_LIMITATIONS |F03, four quarters, January fiscal/comparative/free-text-only tests; no column-byte authentication |
| IR06 | VERIFIED_WITH_LIMITATIONS |F04/F05/F09 regressions; metadata scope never proves numeric evidence |
| IR07 | VERIFIED_WITH_LIMITATIONS |F06, invalid-input/empty-resolved/status tests; candidate-field semantics documented |
| IR08 | VERIFIED_WITH_LIMITATIONS |Adapter tamper controls and forged-catalog dependency test; source bytes not authenticated by D1 |
| IR09 | VERIFIED_WITH_LIMITATIONS |No-I/O/exec/SQL/network controls, input/cycle budgets; no public-service security certification |
| IR10 | VERIFIED_WITH_LIMITATIONS |Seeded20 permutations, aliases, restriction/no-mutation/bounds tests; finite test domain |
| IR11 | VERIFIED |Nine findings, before-source22 failures and permanent regression fixtures; repaired including full-lexeme closure |
| IR12 | VERIFIED |Focused, full and core commands/results in adversarial/integration reports |
| IR13 | VERIFIED_WITH_LIMITATIONS |Repaired delivery CI360 PASS/1 SKIP/3 deselected, exact source/target confirmed in logs; final documentation-head CI rechecked in PR #10 delivery record |
| IR14 | VERIFIED_WITH_LIMITATIONS |Candidate `9c212968…` compiled, full361/3SKIP and core361/3deselected; fixture paths, no new live product acceptance |
| IR15 | VERIFIED_WITH_LIMITATIONS |All524 existing baseline tracked blobs identical; no owner corpus/index opened; no new physical-disk audit of owner history |
| IR16 | VERIFIED |PR #10 Draft/open/unmerged at verified checkpoint; rechecked at delivery |
| IR17 | VERIFIED |PR #9 Draft/open/unmerged, exact original HEAD retained |
| IR18 | VERIFIED |No main/target modification, no D2–D5 or default/API/UI/dependency change |

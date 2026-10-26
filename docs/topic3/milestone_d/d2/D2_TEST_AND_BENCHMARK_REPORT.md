# D2 deterministic tests and representation measurements

Date: 2026-10-26. All new sources/values are synthetic development fixtures. No C consumed holdout, owner corpus, real model, GPU or retrieval-quality experiment is used.

## Commands, environment and actual results

Existing configured venv, Windows11 build10.0.26300, Python3.13.2; Pydantic2.13.5, pytest8.4.2, FastAPI0.142.2, Starlette1.7.0, httpx0.28.1, qdrant-client1.20.0. No package installation or dependency changes. `SCORE_THRESHOLD=0.55`, `RUN_REAL_MEDIA_TESTS=0`. Commands run from the isolated D2 worktree; `python` means that configured interpreter. The runtime source hashes measured are recorded in [measurement JSON](D2_REPRESENTATION_MEASUREMENTS.json); final Git source/CI identities are in the Draft PR delivery record.

| Command | Actual outcome |
|---|---|
| `python -m compileall -q app scripts` | Exit0 |
| `python -m pytest -q tests/test_table_evidence.py --tb=short` | **98 PASS,0 FAIL,0 SKIP**,1.97s |
| `python -m pytest -q tests/test_financial_query.py tests/test_financial_query_review.py` | **170 PASS,0 FAIL,0 SKIP**,1.11s |
| `python -m pytest -q` | **463 PASS,0 FAIL,3 SKIP,1 warning**,34.95s |
| `python -m pytest -q -m "not integration"` | **463 PASS,0 FAIL,0 SKIP,3 deselected,1 warning**,48.65s |
| `python -m scripts.benchmark_table_evidence` | Six families/13 values plus bounded100-row experiment; JSON stdout captured in the new D2 directory |
| `git diff --check` | Exit0; staged/final delivery checks repeated before push |

Three skips remain existing opt-in real-media tests; core deselects them. The warning is existing Starlette/httpx TestClient deprecation. No test was disabled/rewritten. Existing C financial ingestion/search/index/security/provenance and legacy Chat/RAG temporary-fixture paths remain covered by full regression. This is not a fresh live UI/Ollama acceptance check.

## Test-first and adversarial record

Six source/mapping oracles were authored before package implementation. Initial focused run failed collection with `ModuleNotFoundError: app.table_evidence` (one collection error), establishing the feature was absent, not a reproduced old C defect. First minimal implementation passed10 tests. Expanded suite exposed three fixture-source membership failures: C's accepted parser treated all-text N/A/NaN/scientific-text rows as headers before a data row. Supplemental fixtures now precede those unchanged cells with a numeric control row; no accepted parser change or weakened raw/value assertion. Very long parameter IDs also caused Windows test setup errors; bounded human-readable IDs fixed the test harness without reducing input sizes.

After65 tests passed, additional structural/security/metamorphic cases increased coverage to88. New currency/unit conflict cases reproduced **2 FAIL/1 PASS**: `USD 12%` and USD header against EUR table context had been incorrectly verified. Conservative guards were added; the three permanent cases now pass. Schema/status/quarter tests brought the inventory to97. A98th isolated-files integration test reproduces accepted C `verified_source` reconstruction against the same synthetic raw/structured/chunk bytes and rejects tampered raw bytes. Intake type guards also reject untyped source metadata/bindings. Final runtime implementation is commit `64890ecaccf8d375c0b7b8c35e080fa4f7ce7839`; later delivery adds documentation only. Intermediate453-PASS runs with88 D2 tests and462-PASS runs with97 D2 tests are historical development runs, not substituted for final463-PASS evidence.

Three temporary in-process mutants were rejected by existing source/value oracles: reversed header-column lookup, forced EPS million multiplier, and dropped negative sign. No mutant flag or altered source is committed. Final98 cases cover the24 requested groups: contracts, hashes, physical mapping, multi-level/spans, periods/comparatives, units/EPS/sign/precision/missing values, inline conflicts, measurement/entity labels, footnotes, partial extraction, source/generation tampering, determinism/copy isolation, expansion and malformed data. A12-permutation header oracle checks grounded order; no-I/O guards deny open/eval/exec/socket/SQLite calls during builder/bundle use.

## Representation correctness and denominators

Primary fixture:6 tables/parents,6 families,13 financial value cells (plus6 preserved text-label cells). Exact oracles are in `cases.json`; supplemental ambiguity/conflict fixtures remain in the test suite rather than being excluded to inflate a score.

| Measure | Result and denominator |
|---|---|
| Exact physical cell origin |13/13 value cells |
| Raw value preservation |13/13 value cells |
| Unit/multiplier correctness |13/13 value cells |
| Source-locator completeness |13/13 value cells |
| Canonical parent payload correspondence |6/6 parents, relative to synthetic trusted anchors; not authentication of real SEC evidence |
| Typed period bindings |11/13 values have correct typed periods; **2/13 unresolved** (segment dollar/percent changes) |
| Period outcome correctness |13/13 including the two explicitly expected unresolved results; this is **not**100% typed-period coverage |
| Safe-context coverage |11/13 value cells VERIFIED_CONTEXT,2/13 PARTIAL_CONTEXT; table results5/6 verified,1/6 partial |
| Missing typed units |0/13 in the six primary fixtures; separate missing-unit test stays partial |
| Partial source extraction |0/6 primary fixtures; separate headerless-source case explicitly propagates PARTIAL_EXTRACTION |
| Explicit conflicted-case detection |11/11 conflict-status oracles:3 inline sign/scale,4 metric-basis,1 header-period,3 currency/dimension cases |
| Unsupported/invalid cases |All dedicated oracles pass, including non-table parent and missing physical-row/identity/context cases; no claim of exhaustive real-SEC detection |

Segment change-column raw numbers/roles/units are retained, but a source fiscal operand period is not invented. Cash-flow net income is not reclassified as operating cash flow. EPS remains USD/share ×1. Parent text/raw JSON are retained, not reconstructed from a compact projection. Every result is a structural evidence view, not a financial answer.

## Timing, size and memory

Primary measurements: six fixtures, five warmups each,100 measured builds each =600 warm samples; prepared context excluded. Median p50; p95 nearest-rank order statistic `ceil(0.95*n)-1`. First calls are after imports/context setup, **not cold process or cold disk**.

| Boundary | p50 / p95 |
|---|---|
| Warm single-parent view,600 samples |3.171 /4.667 ms |
| First build per fixture after imports,6 samples |3.252 /7.654 ms |
| Separate first context reconstruction,6 samples |1.956 /2.309 ms |
| Five-parent bundle in100-row fixture,20 samples, **with tracemalloc enabled** |191.576 /241.479 ms |

100-row source:5205 raw bytes,303 physical cells,5 selected parents. Context reconstruction with tracing:232.633ms; peak Python allocations2,103,411 bytes (about2.01MiB), not process RSS or whole-machine memory. Last serialized five-parent bundle59,547 bytes. Other local regression activity was not isolated from these timing samples, so they are descriptive local observations, not a clean throughput comparison. Context reconstruction and repeated full-table deserialization have visible overhead; no persistent cache or optimization claim is introduced. These bounded synthetic measurements do not establish worst-case catalog/source scaling or a resource guarantee on arbitrary hardware.

Across the six primary parents: full parent JSON24,744 bytes; parent display text4,039 bytes; full D2 results72,165 bytes; compact presentation12,401 bytes. Thus full results are about2.92× parent JSON, while compact is about0.50× parent JSON **but3.07× display text**. Full view deliberately retains original JSON/text and typed evidence; compact alone cannot replace authenticated parent context. Reduced byte count is not retrieval-quality improvement and no token/truncation/model experiment is claimed.

Raw fixture SHA256 is recorded for this checkout; canonical fixture hash `a3a23c63d2e9ee8b3b69977c17bfdeaf553bfd20f3b9ebcdfed7641ee40f7a42` is portable across LF/CRLF checkouts. Measurement JSON records implementation file SHA256 values and CPU/OS. New measurements apply only to this D2 synthetic workload; historical C/D1 measurements remain unchanged. No source-grounded held-out claims, p-values, answer accuracy or Hybrid-superiority claim follows.

## Acceptance gates

| Gate | Status | Concrete evidence |
|---|---|---|
| D2-01 | VERIFIED |Fetched exact accepted base32c4a48; D1 merge ancestry; untouched target/main refs |
| D2-02 | VERIFIED |Actual schemas/chunker/html_parser/corpus code audit; gap matrix in implementation report |
| D2-03 | VERIFIED |`contracts.py`; serialization/version/immutability/status tests |
| D2-04 | VERIFIED |`source.py`, full canonical parent digest; tamper and six-family assertions |
| D2-05 | VERIFIED |`builder.py` physical origins; exact locator, merged body and sorted-period tests |
| D2-06 | VERIFIED_WITH_LIMITATIONS |Two-level rowspan/colspan header oracle; full source required, nested/continuation restrictions |
| D2-07 | VERIFIED_WITH_LIMITATIONS |Six-family period oracle, quarter/calendar/invalid-header/permutation tests;11/13 typed coverage |
| D2-08 | VERIFIED_WITH_LIMITATIONS |Decimal/sign/unit/EPS and inline/currency conflict tests; finite supported grammar |
| D2-09 | VERIFIED_WITH_LIMITATIONS |All six families tested using synthetic fixtures; real retained-source validation NOT_TESTED |
| D2-10 | VERIFIED |Explicit11 conflict-status oracles and missing/partial/headerless cases |
| D2-11 | VERIFIED_WITH_LIMITATIONS |Byte/hash/metadata tamper and self-declared-context controls; trusted upstream anchor still required |
| D2-12 | VERIFIED_WITH_LIMITATIONS |Immediate group/budget/cross-source tests; stricter same-table expansion, no cross-table continuation |
| D2-13 | VERIFIED |98 focused tests, permanent counterexamples, three rejected mutants |
| D2-14 | VERIFIED |463 full PASS/3SKIP and463 core PASS/3deselected |
| D2-15 | VERIFIED_WITH_LIMITATIONS |Measurement JSON/script;600 warm builds,100-row bounded workload; Python peak only |
| D2-16 | VERIFIED_WITH_LIMITATIONS |All550 pre-existing baseline tracked files unchanged; no fresh hash audit of untracked owner disk |
| D2-17 | VERIFIED |Existing production files unchanged; no external app module imports D2 |
| D2-18 | PARTIAL at document creation |Final Draft PR URL/HEAD/CI and open/unmerged status verified in PR delivery record after publication |

Final owner-review readiness depends on completing D2-18 and inspecting final-head CI at delivery. Documents cannot certify a not-yet-created PR. All exact delivery identities/outcomes are appended to the PR body without rewriting this measurement record. No merge authorization is implied.

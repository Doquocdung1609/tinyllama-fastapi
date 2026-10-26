# D1 tests and fixture benchmark

## Environment and scope

Measured2026-10-25, Python3.13.2, Windows11 build10.0.26300, Intel Core i5-10300H @2.50GHz (CIM processor name). Owner venv used. No dependency changes, paid service, SEC acquisition, GPU/model inference or index build was needed for D1. Synthetic fixture:3 issuers,6 filings,40 representative case oracles; catalog/case canonical-LF hashes and unrounded timings are in [benchmark JSON](D1_RESOLVER_BENCHMARK.json).

## Actual commands/results

Commands shown relative to repository root; `python` below is the configured `.venv` interpreter.

| Command | Actual outcome |
|---|---|
| `python -m pytest -q tests/test_financial_query.py` | **114 passed**,0 failed,0 skipped,0.69s; final focused run |
| `python -m pytest -q -rs` | **309 passed,3 skipped,1 warning**,38.24s; full run after final code changes |
| `python -m compileall -q app/financial_query scripts/benchmark_financial_query.py` | Exit0 |
| `python -m scripts.benchmark_financial_query` | Exit0; all measured fixture statuses checked against40 case oracles |
| `git diff --check` | Exit0; staged diff checked again before commit |
| `git diff --exit-code d1d5195b26f77d8fb25c830229c4c3693d4b638f -- app/api app/financial_index app/financial_ingestion app/services client.py reports` | Exit0, existing production paths and reports unchanged |

The original accepted full-suite195 PASS baseline plus114 added D1 tests equals309 PASS. Intermediate focused/full runs were superseded by safety-case additions and final input revalidation; one accidentally overlapping duplicate full run was interrupted and is not counted as a passing run. An intermediate malformed-container test produced a Pydantic serialization diagnostic; the final resolver serializes caller objects without emitting their invalid contents, then revalidates and rejects them. Final results above have only the pre-existing warning. No test was deleted, disabled or modified to obtain a passing baseline.

Three skips: `tests/test_media_integration.py` real-local-media inference tests, gated by `RUN_REAL_MEDIA_TESTS=1`. Existing warning: Starlette TestClient deprecates its current `httpx` usage and suggests `httpx2`; D1 did not alter these dependencies. No new live financial UI, Ollama response or financial-answer correctness was tested/claimed by this milestone.

## D1 coverage

40 parameterized source-authored synthetic case oracles cover issuer CIK/ticker/exact name/alias, collision/unknown/conflict, explicit form/accession, linked/orphan amendments, separate filing dates, fiscal/calendar/instant/duration/comparative periods, missing evidence and partial extraction. Additional tests cover strict contracts, schema versions/roundtrip, deterministic traces, Unicode/whitespace/sign/Decimal/unit handling, terminology non-equivalence, mixed intent precedence, invalid generation/filter/catalog, malformed numeric expressions, unknown name beside UI filter, negation, instant/duration conflicts, blank aliases, SQL/path/instruction-like text, no socket creation, catalog order invariance/nonmutation and pure adapter correspondence.

All new tests require no live Ollama, GPU, Qdrant, SEC access or owner SQLite. Existing full-suite fixture/integration behavior was preserved. Synthetic cases are correctness checks, not independent financial-retrieval evaluation or D5 held-out evidence.

## Resolver-only performance

One warmup sweep over40 cases, then25 fixed-order repetitions =1,000 warm requests; one query at a time. Each resolver call includes input/catalog/filter validation, parsing, lookup, scope validation and result construction; no API serialization/network/retrieval/source rehash is included. P95 uses nearest-rank convention. Allocation instrumentation is run separately from timings.

| Boundary | Samples | p50 | p95 |
|---|---:|---:|---:|
| Warm resolver,40 mixed cases |1,000|0.431ms|0.585ms|
| First resolver call C01 in a fresh process |10|5.177ms|7.668ms|
| Fresh-process wall time including Python startup/imports/fixture loading/C01 |10|366.484ms|441.496ms|

Tracemalloc peak for a separate40-case sweep:37,668 bytes (not total process memory). Process RSS after run:35,041,280 bytes, including interpreter/dependencies/catalog. It is a single post-run observation, not peak RSS or per-request incremental memory. Full raw environment/measurements are in JSON. Fresh process does not imply cold OS filesystem/model caches. Fixed case order and a small synthetic catalog limit inference; large-corpus performance is not established. Measurements were repeated after final input and range/conjunction safety changes; this JSON is the final-code fixture run, not a replacement for any frozen C benchmark. Earlier development-code runs had warm p50/p95 of0.442/0.790ms and0.693/1.477ms; they are not matched-code speed comparisons and no improvement claim is made.

Do not compare these numbers to C's HTTP, service search, provenance cache or end-to-end timings. No retrieval-quality or overall-search latency improvement is claimed. The D1 acceptance result concerns deterministic correctness, safety and compatibility only.

## Delivery and CI

Implementation commit: `8c49d041228ab18ca131af753f2c0b0446447cdc`. [Draft PR #10](https://github.com/Doquocdung1609/tinyllama-fastapi/pull/10) targets the exact accepted base. A subsequent documentation-only delivery-record commit does not change tested Python/fixtures. Exact final source HEAD/current CI status are recorded in PR metadata and the final delivery report. This document records local evidence and does not assert a CI result from an older commit. The unchanged core workflow compiles and runs the deterministic suite on the PR; platform-dependent Tesseract/media selection may differ from Windows counts.

## Later adversarial review evidence

The preceding309-PASS/114-focused counts and benchmark JSON are preserved as original implementation evidence. They do not establish correctness of cases absent from that suite. Fresh tests found18 failures on the original HEAD, with34 controls passing. After targeted repairs, the original114 and new52 tests pass; local full regression reports361 PASS/3 SKIP/1 warning and core361 PASS/3 deselected/1 warning. Exact review commands, environment, before/after results, candidate identities and final-head CI are recorded in the [adversarial report](D1_ADVERSARIAL_TEST_REPORT.md), [candidate report](D1_INTEGRATION_CANDIDATE_REPORT.md) and PR #10 delivery record. No old numerical measurement has been overwritten or relabeled as a repaired-code speed result.

Follow-up token-boundary coverage expands the review inventory to56 (22 FAIL/34 PASS on original source). After implementation `812dca8`, all56+114 focused tests pass; full365 PASS/3 SKIP/1 warning and core365 PASS/3 deselected/1 warning. Final candidate/CI are rerun for this runtime revision; earlier361/360 counts remain intermediate observations only. No new resolver latency or retrieval-quality claim is made.

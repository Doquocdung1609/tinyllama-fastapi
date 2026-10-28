# Search V2 evaluation — 2026-10-28T17:57:35.833517+00:00

**Status: PROVISIONAL / NOT LOCKED.**70 source-annotated questions:32 development,38 heldout; four real reports (HPG/BIDV PDF and PG/HD SEC). Existing reported HPG failure is development. SHA of labels `041f12981fc0a935e07ebb829008824cb64b8e74dc72d60b75ae572e30ce529d`; frozen policy `582c6821964fead8812348322e27daf97ea52dc08c51a93850e2f095fbf3b4cf`. The original heldout was executed after policy lock. A subsequent English wrong-company probe found a safety defect; the critical name guard was fixed. These v2.6 numbers are an exposed-label retest, not a new unseen test. No weights were tuned to heldout labels; the original first-run results remain archived. Single Codex source annotation is **not independent human review**, and source documents/ontology were inspected during the audit. This is not a fully blinded or issuer-disjoint test. Some negative families overlap across splits: ambiguous_basis, missing_period, wrong_company. Do not generalize the numbers to unseen issuers or arbitrary financial accuracy.

## Development,32 queries

| Arm | Recall@5 | Recall@10 | MRR@5 | nDCG@5 | top1 outside labels | abstention | p50/p95 ms |
|---|---:|---:|---:|---:|---:|---:|---:|
| B0 | 0.500 | 0.577 | 0.452 | 0.464 | 0.577 | 0.000 | 65.3/245.0 |
| B1 | 0.423 | 0.500 | 0.257 | 0.297 | 0.808 | 0.000 | 145.5/264.9 |
| B2 | 0.538 | 0.577 | 0.360 | 0.405 | 0.769 | 0.000 | 147.3/340.2 |
| C1 | 0.923 | 0.962 | 0.798 | 0.829 | 0.269 | 0.333 | 126.1/240.3 |
| C2 | 0.731 | 0.731 | 0.667 | 0.683 | 0.385 | 0.500 | 118.3/323.4 |
| C3 | 0.962 | 0.962 | 0.849 | 0.878 | 0.231 | 0.333 | 325.7/376.2 |
| C4 | 0.962 | 0.962 | 0.849 | 0.878 | 0.231 | 1.000 | 316.2/387.0 |

## Reused test,38 queries — critical-fix retest, not independent heldout

| Arm | Recall@5 | Recall@10 | MRR@5 | nDCG@5 | top1 outside labels | abstention | p50/p95 ms |
|---|---:|---:|---:|---:|---:|---:|---:|
| B0 | 0.333 | 0.500 | 0.218 | 0.229 | 0.867 | 0.000 | 63.3/319.3 |
| B1 | 0.044 | 0.122 | 0.028 | 0.027 | 1.000 | 0.000 | 145.6/267.2 |
| B2 | 0.089 | 0.256 | 0.084 | 0.061 | 0.933 | 0.000 | 149.8/376.6 |
| C1 | 0.700 | 0.778 | 0.519 | 0.565 | 0.600 | 0.500 | 121.3/292.5 |
| C2 | 0.778 | 0.778 | 0.778 | 0.774 | 0.233 | 0.750 | 115.4/389.5 |
| C3 | 0.778 | 0.778 | 0.800 | 0.782 | 0.200 | 0.500 | 328.0/392.7 |
| C4 | 0.744 | 0.756 | 0.767 | 0.749 | 0.233 | 1.000 | 326.9/403.3 |


Positive retrieval metrics exclude expected-abstention questions. Recall covers distinct gold locators; nDCG uses binary distinct-reference gain (duplicates add no gain). Exact source hit uses matching row ID or source value/span on the correct document/page; SEC uses a previously authenticated parent locator. Some OCR-derived labels remain provisional. Wrong-evidence-at1 is **outside the annotation reference set**, not independently adjudicated misinformation. Precision@5 is null because negative labels are not exhaustive, not silently zero. Generic unsupported numeric answer rate cannot be inferred from retrieval snippets.

Separate real-source guard matrix:7 positive reviewed-cell cases and10 unsupported/ambiguous cases; metric/basis/period correctness=1.000, numeric-claim abstention correctness=1.000, unsupported verified numeric claim rate=0.000. Three Decimal checks (HPG change, BIDV restatement identity, future-period refusal) were also executed. These bounded checks are not a70-question financial-answer accuracy estimate. Numeric expected values are missing for many retrieval-only annotations, explicitly null.

Paired heldout C4−B2 family-cluster MRR delta/95% bootstrap: `{'families': 8, 'mean_delta': 0.6395833333333334, 'ci95': [0.375, 0.9041666666666667], 'scope': 'Provisional family-cluster resampling, not independent human evidence.'}`. Only8 positive families and repeated paraphrases: uncertainty estimates are provisional. No statistical claim of broad significance.

## Resource measurements

Final development: `{'elapsed_s': 52.25706610002089, 'index_prepare_ms': 1128.430200042203, 'active_sidecar_bytes': 3694592, 'sampled_benchmark_process_peak_rss_bytes': 233611264, 'free_disk_bytes': 40072802304}`. Heldout: `{'elapsed_s': 53.0372341000475, 'index_prepare_ms': 965.6207999796607, 'active_sidecar_bytes': 3694592, 'sampled_benchmark_process_peak_rss_bytes': 231837696, 'free_disk_bytes': 40069107712}`. Warm-up was run before timed requests, timings include safety checks and actual model queries. The benchmark-process RSS excludes external Ollama runners, browser and other apps; it is not total laptop RAM. New sidecar size/preparation time are measured; old chunks/vectors/OCR are reused for the benchmark. Fresh Prebuilt ingestion and process measurements are reported separately after the real browser run. GPU on this machine is RTX3050 Laptop4GB; no GTX1650Ti test claim.

Historical benchmark files are unchanged. Actual per-query failures, hashes and rank IDs are retained. SEC C arms are passthrough, not upgraded source parsing. A lower-complexity C1 is reported alongside C4. Hybrid can lose to BM25; see failure analysis and UI's unchanged baseline comparison.

Final v2.6 validation:643backendPASS,7frontendPASS,buildPASS; extra source-title statement/unit candidates and explicit statement conflicts tested. The38-query v2.6 result is exposed-label retest. Original v2.3 policy source archive matches its first-run hash.

Original run bytes (including superseded diagnostics and first test) are retained in MEASURED_RUN_SNAPSHOTS.zip; per-entry hashes are in its manifest. Final result JSON files use one record per line without changing any measured values.

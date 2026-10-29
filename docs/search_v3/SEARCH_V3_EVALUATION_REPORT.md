# Search V3 evaluation — 2026-10-29

**SEARCH_V3_PARTIAL. No LOCK_CANDIDATE / no LOCKED claim.**84 new questions:24 development,36 exposed regression,24 final source-unseen test. All8arms use the same questions,selected documents and gold references in each split. Frozen V2's70 queries are separate regression only. The policy-first final test was executed once without subsequent retrieval/intent/eligibility/UI policy changes. Policy SHA `28df50bf06395496cd54340a8f0e944acf9403c52cf2b9c0752fc70ccda64ccb`. Zero independent human adjudications; these are provisional Codex visual source annotations, not independently human-validated accuracy.

The first V3.1 freeze was invalidated before its planned36-query test: a no-preposition Apple probe wrongly inherited an HPG reviewed cell. The unsafe policy and labels are archived. The36 labels were demoted to exposed regression. The final REE/SEM sources were opened only after the repaired V3.2 freeze; SOURCE_OPEN_AUDIT.json records the sequence. Corporate-family independence is limited:Samsung Electronics and Samsung Electro-Mechanics are distinct,affiliated issuers. Common concepts/query constructions remain across splits; family IDs prevent direct source-target paraphrase split leakage,not all semantic dependence.

## Development (24)

|Arm|R@1|R@5|R@10|MRR@5|nDCG@5|p50/p95 ms|
|---|---:|---:|---:|---:|---:|---:|
|B0|0.150|0.183|0.333|0.177|0.171|175.4/190.5|
|B1|0.017|0.183|0.233|0.129|0.116|272.4/298.9|
|B2|0.117|0.233|0.333|0.208|0.192|280.3/300.1|
|C1|0.200|0.500|0.650|0.278|0.332|270.3/304.9|
|C2|0.450|0.600|0.600|0.500|0.525|260.2/291.7|
|C3|0.450|0.700|0.700|0.529|0.571|720.1/759.5|
|C4|0.450|0.600|0.600|0.500|0.525|716.7/764.3|
|V3|0.533|0.817|0.883|0.704|0.706|1221.9/1300.3|

## Exposed retest (36)

|Arm|R@1|R@5|R@10|MRR@5|nDCG@5|p50/p95 ms|
|---|---:|---:|---:|---:|---:|---:|
|B0|0.031|0.188|0.219|0.082|0.108|112.3/205.7|
|B1|0.031|0.062|0.094|0.037|0.043|200.0/328.7|
|B2|0.000|0.125|0.156|0.049|0.069|212.5/328.5|
|C1|0.094|0.344|0.375|0.182|0.222|250.6/318.6|
|C2|0.188|0.375|0.406|0.267|0.294|239.3/317.8|
|C3|0.219|0.469|0.562|0.312|0.351|513.4/837.1|
|C4|0.156|0.219|0.219|0.180|0.189|509.3/831.8|
|V3|0.292|0.719|0.781|0.483|0.544|1506.1/2353.2|

## Final source-unseen test (24)

|Arm|R@1|R@5|R@10|MRR@5|nDCG@5|p50/p95 ms|
|---|---:|---:|---:|---:|---:|---:|
|B0|0.056|0.056|0.111|0.056|0.056|71.4/102.3|
|B1|0.000|0.000|0.000|0.000|0.000|170.3/208.7|
|B2|0.000|0.056|0.056|0.011|0.021|191.0/217.7|
|C1|0.056|0.222|0.278|0.104|0.133|182.8/206.2|
|C2|0.000|0.111|0.111|0.037|0.056|170.5/205.8|
|C3|0.000|0.167|0.167|0.050|0.078|406.7/508.1|
|C4|0.000|0.111|0.111|0.042|0.059|405.4/508.7|
|V3|0.296|0.315|0.389|0.333|0.320|1351.1/1940.6|

## Meaning of the metrics

Recall measures distinct labelled source references,not probability of a correct numeric answer. Repeated hits add no nDCG gain. Top1 outside labels is an unjudged/missed gold source,not necessarily financial misinformation. Negatives are not exhaustive;Precision@5 remains null. Exact row/source hit@1 is in the recorded JSON. Exact-cell accuracy and general wrong-period/wrong-basis rates are null where no reviewed column ground truth was exercised;do not silently turn them into zero errors. Wrong-document@1 is only the selected-document filter check,not independent issuer correctness.

Retrieval false abstention means empty results for a positive query. V3 retaining related passages makes that zero here,but does not remove relevance misses. Answer false abstention is evaluated only on explicitly product-reviewed positive cells;it is not computable for unreviewed positive rows. Six final negative questions all declined verified numeric eligibility. No new SEM/REE positive cell was product-reviewed;therefore positive answer accuracy on the final test is **not established**. The separate17-case real-source guard matrix (7positive/10negative),3Decimal checks and4additional entity probes PASS;these bounded regressions do not establish unseen financial accuracy.

Development V3 eligibility correctness is1.000 on6labelled cases (2reviewed asset questions and4negative questions),with0false abstentions on those2reviewed positives. Other development positives remain unjudged for numeric eligibility. Report denominators from each result JSON;do not pool conditional rates with retrieval scores. The old V2 `abstention_correct` field treats related unverified evidence as non-abstention and is retained for diagnostic compatibility;use the distinct V3 `correct_numeric_abstention` for numeric safety.

Every requested stratum (seen/unseen,PDF type,language,tabular/narrative,exact/paraphrase,single/multi-page,positive/no-answer) is separately available under `stratified` in each result file. The final test contains18positive/6negative questions,including2narrative and2multi-page questions. Clean text-native Samsung Electronics appears only in exposed retest. Original image inspection found final REE to be scanned pages with an existing imperfect OCR layer,and SEM financial tables to be images under native headers. Acquisition character-count guesses were superseded by these visual classifications before final labels/test. No broad independent clean-native or corporate-family generalization claim. Two final documents,single annotator and small strata do not justify statistical significance.

## Extraction coverage failure

SOURCE_COVERAGE_AUDIT.json verifies all7labelled REE values are in checkpoints. All7labelled SEM statement values exist visibly in the raw PDF table images but are absent from extracted checkpoints. SEM pages7/8/9 retain enough native header/footer text to take the native extraction path;image table bodies are lost. READY denotes completion of the current pipeline,not financial-data completeness. This is an extraction failure,not evidence that ranking alone can recover absent values. No OCR repair was made using final test labels,and no document was relabelled to make a gate pass. Remaining REE/narrative misses and conservative vocabulary refusals are retained in actual records.

## Resource conditions

Timings are post-warm-up local laptop observations,not isolated-server benchmarks. The first part of the final run overlapped the end of the exposed retest;Ollama/desktop background activity can affect latency. No broad speed significance claim. Benchmark-process RSS excludes external Ollama/browser. Actual Prebuilt first cold search in screenshot01 took23,308.28ms including lazy sidecar construction/caches;warm benchmark latency must not conceal this wait. GPU confirmed RTX3050Laptop4GB,not GTX1650Ti. New public sources were ingested into owned clones without replacing owner PDFs/models/accepted SEC generations.

Development (24): `{"elapsed_s": 111.86780700000236, "prepare_ms": 10989.799899980426, "active_index_bytes": 21970944, "benchmark_process_peak_rss_bytes": 240123904, "free_disk_bytes": 35943870464}`.

Exposed retest (36): `{"elapsed_s": 173.47688650002237, "prepare_ms": 13799.145700002555, "active_index_bytes": 21970944, "benchmark_process_peak_rss_bytes": 241922048, "free_disk_bytes": 35976691712}`.

Final source-unseen test (24): `{"elapsed_s": 96.01690609997604, "prepare_ms": 10892.7238000324, "active_index_bytes": 16760832, "benchmark_process_peak_rss_bytes": 229212160, "free_disk_bytes": 35954266112}`.

Windows live resource samples: `{"elapsed_s": 115.28145739994943, "sample_count": 458, "api_sampled_peak_rss_bytes": 380878848, "api_os_peak_working_set_bytes": 403496960, "minimum_available_ram_bytes": 3488362496, "maximum_whole_system_used_ram_bytes": 12865294336, "minimum_free_disk_bytes": 35893678080, "physical_ram_bytes": 16353656832, "condition": "Real Windows Prebuilt/Chromium smoke;0.25s sampling;includes launcher idle and desktop background apps. API memory excludes Ollama/browser;whole-system RAM includes them. RTX3050Laptop4GB confirmed with Win32_VideoController."}`.

Fresh FOX36-page scan ingestion216.37s;Samsung Electronics88pages36.41s. Final REE36pages32.69s;SEM88pages20.33s. CEO29-page scan225.55s in development. These are actual extraction/index elapsed times,not pure OCR CPU time. Some mixed-image financial pages incorrectly bypassed OCR;their short elapsed time is not a quality success. See ingestion JSON,checkpoints and SOURCE_COVERAGE_AUDIT. No embedding-only latency distribution was instrumented by the V3 harness;existing local Nomic requests are included in Dense/Hybrid totals and not misreported as a separate measured p95.

## Reproduce

Use `scripts/acquire_search_v3_sources.py --destination <new-folder>` with SOURCE_MANIFEST.json for hash-pinned public files. Existing URLs may change bytes;the script refuses SHA drift. Clone a stopped workspace with `prepare_search_v2_workspace.py` into a new `studio_workspace/search-v2-*` path. Process documents using `ingest_search_v3_sources.py` with the recorded split and new output path. Raw owner source PDFs and accepted SEC product snapshots are local prerequisites;historical data absent on this laptop is not certified.

```
.\.venv\Scripts\python.exe scripts/benchmark_search_v3.py --root studio_workspace/search-v2-v3-20261029 --qrels docs/search_v3/SEARCH_V3_QRELS.jsonl --split development --output tmp/search-v3/dev-replay.json
.\.venv\Scripts\python.exe scripts/benchmark_search_v3.py --root studio_workspace/search-v2-v3-20261029 --qrels docs/search_v3/SEARCH_V3_QRELS.jsonl --split regression --output tmp/search-v3/retest-replay.json
.\.venv\Scripts\python.exe scripts/benchmark_search_v3.py --root studio_workspace/search-v2-v3-final-20261029 --qrels docs/search_v3/SEARCH_V3_QRELS.jsonl --split locked_test --output tmp/search-v3/locked-replay.json
```

All outputs must be new paths. Replaying an already viewed test does not create a new unseen test. Use `replay_search_v3_regression.py` for unchanged70V2 questions and the accepted local SEC roots. Policy hashes use canonical UTF8/universal-newline source text;label/artifact hashes preserve original measured bytes. The owner source's complete eight-file hash inventory remains unchanged;final checks are in INTEGRITY_VERIFICATION.json. The owner remains acceptance authority.

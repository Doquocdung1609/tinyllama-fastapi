# Regression and evaluation

Final policy SHA256 `7526a38571b72ffcc5ea59eb85dca9f1f942a5a191b3e424f4e8ddfea8b1c809`. Full raw before/after evidence: BEFORE_178_RESULTS.json, AFTER_178_COMPATIBILITY_RESULTS.json. FINAL_PAIRED_REGRESSION_COMPARISON.json records all source gains/losses. Same copied nine PDFs/vectors for both arms; existing SEC source roots remain unchanged. Old single-document PNJ/ACB scores have a different candidate corpus and are not a causal before/after comparator.

178 exposed questions = 84 V3 + 70 V2 + 24 PNJ/ACB V3R. Existing V1 tests/contracts remain in the backend suite. Old result files and labels are preserved. Fresh unseen-source generalization: SKIP, no new held-out set. These questions cannot support new held-out claims.

| Metric | Before | Final after |
|---|---|---|
| Source digit+locator Recall@5 (142 positives) | 0.8802816901408451 | 0.9014084507042254 |
| Exact-cell Hit@5 (16 cell-labelled positives, old windows) | 0.6875 | 0.8125 |
| Source MRR@5 (142 positives) | 0.7913145539906103 | 0.8124413145539906 |
| Wrong document Top-1 (168 classified) | 0 | 0 |
| Wrong classified metric Top-1 (117/120 classified) | 0.008547008547008548 | 0.03333333333333333 |
| Numeric negative abstention (36) | 1 | 1 |
| Numeric eligibility correctness (24 explicit cases) | 1 | 1 |
| Wrong verified claims (178) | 0 | 0 |
| Query latency p50 ms | 1641.23 | 1503.35 |
| Query latency p95 ms | 1835.09 | 1838.53 |

No source Recall@5 losses; three gains are ACB equity, pretax and net income. Original exact-cell 11/16→13/16; corrected ACB net-income window separately raises final to14/16. PNJ net income and ACB cash remain misses on the combined corpus in both arms; not hidden by corrected labels.

Positive false abstention: 0/2 explicit numeric-eligible positive cases. The other source-positive unreviewed cases do not authorize numbers; absence of a numeric answer is intentional until review. Numeric negative abstention is36/36, while the old legacy empty-retrieval `abstention_correct` is2/36: related source passages may still be returned. Do not conflate the two.

Wrong period and wrong basis rates: NOT_MEASURED by these qrels (null, zero denominators), not zero errors. Separate context/eligibility regression tests and human source packet are required. Wrong classified-metric Top-1 worsened; detailed four cases and safe ineligibility are disclosed in ACB report. Overall financial accuracy remains PARTIAL.

Local validation: baseline671 backend/9 frontend/build PASS; final706 backend PASS (one existing Starlette/httpx deprecation warning),10 frontend PASS, TypeScript/Vite build PASS; four Windows Chrome live scenarios PASS. Initial development run and initial Chrome selector failures are retained privately/public raw as appropriate. Initial Chrome failures selected default ACB instead of SEM and used shortened issuer ACB instead of recorded issuer; fixture selectors were corrected, product data were not changed.

Benchmark command (separate process per arm; API must release owned Qdrant first):
```powershell
.venv\Scripts\python.exe scripts/benchmark_search_v3r2.py --root studio_workspace/search-v3r2-owner-r2-20261029 --arm after --qrels docs/search_v3r/NEW_TEST_QRELS.jsonl --qrels docs/search_v3/SEARCH_V3_QRELS.jsonl --qrels docs/search_v2/SEARCH_BENCHMARK_QRELS.jsonl --output docs/search_v3r2/NEW_UNIQUE_RESULT.json --sec-root tmp/studio-runtime/sec/p7-isolated-review-product-20261028 --sec-vectors tmp/studio-runtime/sec/t3-p10-isolated-vectors-product-20261028 --gpu
```

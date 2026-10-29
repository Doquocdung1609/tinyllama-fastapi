# Search V3 ablations

B0 original BM25;B1 original locked Nomic768 Dense;B2 original fixed RRFk60. C1 V2 fielded lexical,C2 V2 row pool,C3 V2 union/reranking,C4 V2 hard eligibility-related filtering. V3 retains related source candidates,uses controlled/fuzzy row concepts as unverified candidates,diversifies multi-metric operands,and validates numeric eligibility separately. It reuses immutable V2 sidecars;no new retrieval architecture/model. SEC C arms retain V2 passthrough;V3 only reranks authenticated parents,without replacing accepted generations or certifying numeric columns. No company/page/value-specific routing in production.

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

## Sources lost by C4 after C3 found one

- v3t001 / test_fox_assets: `Hard metric/scope/period/row filter;see source conflicts`.
- v3t003 / test_fox_liabilities: `Hard metric/scope/period/row filter;see source conflicts`.
- v3t005 / test_fox_equity: `Hard metric/scope/period/row filter;see source conflicts`.
- v3t007 / test_fox_net_revenue: `Hard metric/scope/period/row filter;see source conflicts`.
- v3t011 / test_fox_financial_revenue: `Hard metric/scope/period/row filter;see source conflicts`.
- v3t020 / test_samsung_assets: `Hard metric/scope/period/row filter;see source conflicts`.
- v3t022 / test_samsung_liabilities: `Hard metric/scope/period/row filter;see source conflicts`.
- v3t028 / test_samsung_inventory: `Hard metric/scope/period/row filter;see source conflicts`.

C4 can hide a relevant row because a date/header/scope is unproven or query terms trigger clarification. V3 keeps it visibly unverified;it does not treat higher retrieval recall as permission to give its numbers. Some V3 passages are irrelevant and intentionally remain outside numeric eligibility. New-source extraction losses affect every arm;no statistical model-superiority or financial-answer-accuracy claim follows from these retrieval gains. Exact unit/period/basis correctness requires product-reviewed cells or an independent column audit. New SEM native-header/image-table loss is not solved by reranking.

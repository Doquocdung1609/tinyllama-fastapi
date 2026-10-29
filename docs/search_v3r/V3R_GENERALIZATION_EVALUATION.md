# V3R post-freeze generalization — PROVISIONAL_AGENT_ANNOTATED

**Overall status remains PARTIAL.** No independent human reviewer participated. Policy SHA `2b87405221010745d1d4a3f4981ace28092a2bc48de02b73afcb2c7504e338f7` was frozen at 2026-10-29T06:50:43.667771+00:00. Only afterward were new PDFs acquired and 24 questions labelled from original page images. NEW_TEST_SEAL.json records the label hash before search results were opened. The sources were PNJ's 28-page Q4/2025 scanned consolidated report and ACB's 78-page 2022 annual-report financial section, with native financial tables. ACB's historical period is intentional; “new” means previously unseen by this development process, not recently published.

The two document-scoped roots each ran their 12 questions once. The combined report only aggregates those raw runs; it does not rerun queries. Questions include exact source cells, current/prior periods, a rotated statement, and wrong issuer/period/currency/scope contexts. The benchmark also prepares unused comparator sidecars as part of its existing harness setup; only A3 issues the new test queries. No code/config/index-policy changes followed the test.

|Document type|Positive / numeric-negative questions|R@1|R@5|R@10|MRR@5|nDCG@5|Cell locator hit@5|p50 / p95 ms|
|---|---:|---:|---:|---:|---:|---:|---:|---:|
|scanned|8 / 4|0.8750|1.0000|1.0000|0.9167|0.9375|1.0000|574.1 / 1586.9|
|text-native|8 / 4|0.3750|0.6250|0.7500|0.5000|0.5327|0.6250|908.7 / 2051.5|
|Combined|16 / 8|0.6250|0.8125|0.8750|0.7083|0.7351|0.8125|816.6 / 2492.8|

New mixed-financial-image source validation: **SKIP**. SEM is exposed development evidence and is not counted as new generalization. Several candidate public downloads failed (403/404) or exceeded a bounded file budget before any source-specific benchmark; acquisition failures are recorded rather than replacing low-scoring test results.

All 16 annotated values remain present in extracted source cells. PNJ retrieves 8/8 checked source cells within top five, including annual rather than quarter-only income columns. ACB retrieves 5/8: `v3r-acb-06` equity, `-07` pretax and `-08` net income miss. Native font text loses the “fi” in Profit (rendered text “Pro t”); the source owners’ equity wording is not fully covered by frozen label matching. Exact visual source text and unmodified checkpoint labels are retained in NEW_SOURCE_EXTRACTION_AUDIT.json. English VND-million scaling is also not fully represented by the existing unit-header helper. These findings are not repaired after test exposure.

Cell hit here means the actual signed amount is in the correct document/page and independently located original-image cell window. “Independently located” means located without search output by this same agent; it does **not** mean a second human. It does not certify every header/scale in a returned row.

Wrong document at one: 0/24 under explicit document scope. Wrong classified metric at one: 1/14 classified positive hits; 2/16 positive top hits are unclassified. Wrong period/basis and generic numeric financial accuracy remain unjudged/null. Retrieval empty-result false abstention is 0/16, but three source answers are still missed at top five. All 8 negative contexts correctly withheld numeric answers; zero of the 24 new questions produced a reviewed numeric claim. Positive answer false-abstention is not estimable because none of these new cells has an audited product review. Showing related evidence in negative cases is not a failure of numeric abstention.

This is a small, source-correlated, single-agent-labelled test: two reports, not a representative cross-industry evaluation. Source-local success and 8/8 abstentions do not establish broad financial accuracy. Gate E remains PARTIAL and Gate G awaits owner/independent source review.

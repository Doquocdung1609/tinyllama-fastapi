# V3R retrieval ablation

All 84 V3 questions are exposed regression, including the former final 24. Same questions, selected documents, top ten and V3 scoring weights are used in four arms. No company/page/value routing was added. A0 remains old extraction; A1 uses recovered checkpoints plus the versioned fragment layout; A2 adds source-region/header indexing; A3 adds narrowly defined IFRS label aliases. The region index also caches derived metrics after source validation. It does not grant numeric eligibility.

|Arm|Original exact R@5|Signed-digit source locator R@5|Original MRR@5|Signed-digit locator MRR@5|
|---|---:|---:|---:|---:|
|A0_OLD_V3|0.6429|0.6429|0.5076|0.5076|
|A1_NEW_V3|0.6857|0.7190|0.5271|0.5450|
|A2_REGION|0.7190|0.7714|0.6488|0.6905|
|A3_REGION_LABELS|0.7476|0.8143|0.6631|0.7119|

Locator equivalence is evaluation-only, preserves the sign and requires the same document/page and matching source-cell digits. It never repairs OCR data. Original literal metrics remain published beside it. These are source retrieval scores, not general numeric-answer accuracy.

The initial layout lost CEO's two-row image fragment. ABLATION_84_RESULTS.json and ABLATION_84_RESCORED.json preserve that failed development result. ABLATION_84_FINAL_LAYOUT_RESULTS.json records the repaired layout: no A0-positive query loses top-five source coverage. The seven missing SEM values are now represented in source cells; some source questions still rank incorrectly. Header/region context and exact source-label concepts add gains beyond recovering words alone. The source-label alias arm is justified by the A2/A3 comparison; no new reranker or ranking weights were introduced.

BASELINE_V3_RANK_COMPARISON.json confirms identical A0 top-ten evidence IDs for **84/84** against the prior published V3 snapshots. The 70 older V2 questions were also replayed through the supported API: R@5 0.9821, R@10 1.0000, MRR@5 0.9211 over 56 source-positive questions. All 14 numeric-negative cases withheld numeric claims; related passages were often still shown, intentionally. No wrong verified claim was observed in these bounded replays.

The live owner guard adds 17/17 source/period/scope/basis/unit cases, 3/3 Decimal or abstention cases and 4/4 unknown-company probes. The original HPG asset change remains 16,877,702,175,961 VND; BIDV original plus adjustment minus revised remains exactly zero. These use prior audited cells, not new OCR certification.

The final development matrix was started before the verifier JSON-parsing optimization and ran concurrently with owner/API/Chrome checks. Its latency values remain raw observations of that earlier development process and must not be presented as final frozen-policy latency. Dedicated optimized profiling and actual final API smoke are separate in V3R_PERFORMANCE_REPORT.md. Source checks were retained in both implementations; the optimization removes duplicate JSON parsing, not hash verification.

Wrong-period/basis rates for arbitrary retrieved rows, exhaustive precision and general financial answer error remain null where unjudged. A row can contain several periods, currencies or bases. Zero observed wrong numeric claims is not a general accuracy guarantee.

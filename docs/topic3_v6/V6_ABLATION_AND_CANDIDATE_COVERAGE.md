# Exposed-development ablation and candidate coverage

All results here use the 15 **exposed and incompletely judged** P7L/F10 cases. They are exploratory, not a sealed test. Source: `docs/topic3_v5/recovery_live/ablation_summary.json`, `candidate_coverage.json`, `posthoc_repair.json`, and V6 `V6_EXPOSED_FEATURE_ABLATION.json`. The V6 feature-removal script reorders the *saved* A3 Top-10 pool without a new Qdrant search and asserts exact reproduction of frozen A4.

| Arm | Known-positive Top-1 / Top-3 / Top-10 | What changes |
|---|---:|---|
| A0 recovered A unfiltered | 1 / 4 / 8 | Original BM25+Dense hybrid, wrong fiscal metadata |
| A1 corrected B unfiltered | 1 / 4 / 8 | Metadata corrected but not filtered |
| A2 B issuer/year filter | 3 / 7 / 14 | Target filing Top-1 rises from 3/15 to 15/15; relevance labels remain incomplete |
| A3 A2 plus sidecar | 3 / 7 / 15 | One known-positive chunk enters Top-10, at extra full-corpus payload scan cost |
| A4 A3 plus six-feature rank | 10 / 14 / 15 | Ranking only; no new candidate or certified value |
| A5 A4 plus status | 10 / 14 / 15 | All financial cells still `UNVERIFIED` |
| A4R post hoc | 13 / 14 / 15 | Same 15 pools; one Amazon FY2023 regression to UNJUDGED; no independent claim |

Feature-removal counterfactual on the **same A3 Top-10 pools**, known-positive Top-1: full A4 **10/15**; without issuer **10/15** (A2 already filters issuer); without fiscal feature **10/15** (A2 already hard-filters one year); without table-row candidate **9/15**; without all metric-relation/row features **3/15**; without year appearing anywhere in chunk body **10/15**. This does not prove metric features generalize; the cases and incomplete labels were exposed. A4 has **no actual column-year alignment feature** and **no unit feature**, so “without column-year” and “without unit” ablations are inapplicable. A4R has a post-hoc nearby-year phrase signal, not verified column mapping.

For candidate budgets 10/20/50/100 on B, known-positive entry is A2 **14/15 at 10** and **15/15 at 20/50/100**; A3 **15/15 at all four budgets**. Unknown positions grow with k; these are known-positive lower bounds, not Recall. A3's extra scan changes compute, so its one-case gain does not isolate ranking. At k=100 prefetch grows to 100 rather than the author's default 50. Candidate count/output budget is held equal **within** each A2/A3 pair; source corpus and index point count are identical. Unverified table rows cannot be used as answer cells.

The saved A3 pools were also reranked with frozen A4 at budgets 10/20/50/100 (`V6_EXPOSED_BUDGET_ABLATION.json`). The script reproduces all 15 frozen A4@10 rankings exactly. Known-positive Top-1 is **10/15, 10/15, 10/15, 9/15** as budget grows. Top-3 is **14/15, 13/15, 14/15, 14/15**. Thus a larger pool does **not** monotonically improve rank and can introduce a top-rank regression. Unjudged positions grow from **71** at k=10 to **1,354** at k=100. Rerank-only median time rises from **0.795 ms** to **7.744 ms**, excluding the much larger Qdrant/embedding cost. These results remain exposed-development observations and cannot be presented as independent effectiveness estimates.

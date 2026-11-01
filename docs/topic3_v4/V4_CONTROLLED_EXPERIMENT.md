# Controlled experiment and its limits

The V4 UI exposes, but does not rerun or relabel, the frozen PR #29 research runs. Source artifacts: `docs/topic3/01_REPRODUCTION/RETRIEVAL_RESULTS.json`, `docs/topic3/03_IMPROVEMENTS/STRUCTURE_BM25_RESULTS.json`, and the three corresponding structure ablation JSONs.

| Arm | Index points | Known source target @1 | @5 | @10 | Local Qdrant p50/query |
|---|---:|---:|---:|---:|---:|
| Author BM25 R0 | 121 | 0/4 | 3/4 | 3/4 | 3.997 ms |
| Structure BM25 I1 | 1,241 | 4/4 | 4/4 | 4/4 | 13.802 ms |

On the *same 1,241 source chunks*, row-only text had 0/4 targets @1, removing issuer context had 2/4, removing period context had 0/4, and full context had 4/4. These are exposed development targets prepared by machine, not human-reviewed independent gold. The R0-versus-I1 comparison also changes chunk count, boundaries, IDF and context; the ablations do not isolate boundary and count effects. No new equal-count control was completed in V4. The 6-query medians exclude embedding, API and browser time. No statistical significance or financial answer accuracy is claimed.

The held-out/human-reviewed gate remains open. This is `RESEARCH_PARTIAL`, even though the UI makes the prior evidence inspectable.

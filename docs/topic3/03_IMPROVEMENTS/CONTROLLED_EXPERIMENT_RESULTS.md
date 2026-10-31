# Controlled exposed comparison

| Run | Chunks | Known target @1 | @5 | @10 | Local Qdrant p50/query |
|---|---:|---:|---:|---:|---:|
| R0 author BM25 | 121 | 0/4 | 3/4 | 3/4 | 3.997 ms |
| I1 full structure BM25 | 1,241 | 4/4 | 4/4 | 4/4 | 13.802 ms |

Raw results: `../01_REPRODUCTION/RETRIEVAL_RESULTS.json` and `STRUCTURE_BM25_RESULTS.json`. Both runs use the same two SEC HTML files, six exact questions, sparse BM25 model and cached query vectors. The method of chunk creation differs, altering the number of points and IDF distribution. The p50 is over six query calls and excludes loading, embedding and HTTP transport; it is **not** end-to-end product latency. Four target IDs were machine-prepared before retrieval and not human reviewed; this comparison is restricted to an exposed development set. It cannot establish a statistically reliable improvement or financial answer correctness.

The full structure index took 3.266 seconds after the source chunks were already extracted. This is local embedded Qdrant; server payload-filter performance was not assessed. Full row/period/issuer ablation is recorded in `../04_ABLATION/ABLATION_STUDY.md`. No measured result is claimed for query rewriting, region OCR, verified arithmetic or an independently held-out set.

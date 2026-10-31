# Bounded author-method benchmark on two SEC filings

**Classification: `METHODOLOGICAL_REPLICATION`, `PROVISIONAL_UNREVIEWED`.** This is not the author's 47-filing/8,609-chunk/25-query run. The locked corpus is two 2026 SEC 10-Q HTML snapshots (P&G and Home Depot), parsed with the pinned author's unmodified HTML parser and 500/100 chunker into **121 chunks**. The three genuine FastEmbed generators produced BGE-small 384d, Qdrant/bm25 and SPLADE vectors in separate processes. An isolated embedded Qdrant collection contains 121 three-vector points. Sources, chunk IDs, model cache file hashes, vectors and index manifest are preserved. No production Nomic index or V3R3 workspace was changed.

Six source-located questions were frozen in `PROVISIONAL_SOURCE_QRELS.jsonl` before retrieval: four positive row/column targets and two unsupported queries. Labels were located from source and author chunks by Codex; **none is independent human gold**, and relevant chunk coverage may be incomplete. The two negatives are not counted as retrieval misses or evidence of numeric abstention. Same index, exact query, no issuer prefilter, top-10 and prefetch-50 were used for every arm. R5 (three-way RRF) is an extension requested by this project, outside the author's five core retrievers. R6 uses the pinned author's deterministic stage-2 code on top-20 SPLADE+Dense candidates; it is not neural inference.

| Arm | Known target @1 | @5 | @10 | Provisional MRR@10 | Qdrant p50 ms |
|---|---:|---:|---:|---:|---:|
| R0 BM25 | 0/4 | 3/4 | 3/4 | 0.30000 | 3.997 |
| R1 Dense | 0/4 | 1/4 | 1/4 | 0.08333 | 0.457 |
| R2 SPLADE | 0/4 | 1/4 | 2/4 | 0.16667 | 6.571 |
| R3 BM25 + Dense RRF | 0/4 | 2/4 | 3/4 | 0.22321 | 4.620 |
| R4 SPLADE + Dense RRF | 0/4 | 1/4 | 1/4 | 0.12500 | 7.351 |
| R5 three-way RRF | 0/4 | 1/4 | 3/4 | 0.19792 | 11.099 |
| R6 author deterministic Stage-2 | 1/4 | 2/4 | 3/4 | 0.34167 | 27.823 |

These are **known-target locator counts**, not exhaustive Recall@k or independently judged financial answer accuracy. The underlying result and each Top-10 ID are in `RETRIEVAL_RESULTS.json`; denominators are four source-positive questions. No arm showed a generalizable advantage on this tiny, author-mismatched sample. For Home Depot total assets, R4 missed the target in Top-10 while its Top-20 candidates contained it; the author's Stage-2 promoted it to Rank 1. For P&G net sales, most arms favored segment discussion over the consolidated statement row, so table precision remains unresolved.

The query p50 above is **Qdrant time excluding model load and embedding**. Separate real query embedding times are in `tmp/topic3/replication/*_query_manifest.json`: warm Dense calls 17–21 ms, SPLADE 40–48 ms and BM25 below 0.1 ms after initial model load. The first call is much slower. Offline document embedding took BM25 2.22 s (89.7 MiB process peak), Dense 28.35 s (753.77 MiB), SPLADE 123.55 s (**5,516.5 MiB process peak**, minimum available system RAM **0.8 MiB**). The latter is operationally unsafe on this host while other applications run; query-only SPLADE with one thread peaked at 617.32 MiB. A document rerun must use smaller batches or defer under low RAM. Index upsert after embeddings took 0.283 s; this excludes parsing/model inference. Embedded Qdrant warns that local payload indexes do not provide server payload-index behavior.

The author's original benchmark computes relevance from returned text and cannot provide an independent denominator. Its reported 96% is not compared numerically to the table above. The original model snapshots are hashed locally in `MODEL_CACHE_MANIFEST.json`, but the author's historical model revisions and corpus manifest are unavailable, so `EXACT_REPRODUCTION` is not supported.

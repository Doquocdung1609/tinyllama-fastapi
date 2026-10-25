# Milestone C architecture

Integrated code: `bde80f6d672f1744b54ec669300a86844139c54f`; verified B acceptance/base commit: `c84c060d1bbf507b01badb8073f22cbf53b9b7ec`. PR #7 is integrated and both candidate/merged regressions passed before this work began.

## Existing path and bottleneck

`financial_search_service.bm25_rank` tokenizes every eligible chunk, constructs Counters, corpus document frequencies and average length for each request. Legacy `/financial/search` uses PDF/RAG's production-facing Qdrant adapter, not SEC staging. Its deterministic positive-IDF BM25 uses k1=1.5/b=0.75 and RRF k=60. Existing routes remain compatible; a dataset-aware SEC index is added to the same FastAPI/Streamlit application.

## Options and decision

| Option | Fidelity / persistence | Incremental/publication | Maintenance and Windows |
|---|---|---|---|
| SQLite FTS5 | Durable, optimized; built-in BM25 has different IDF, negative-score ordering and tokenizer semantics | Strong transactions, efficient updates | Excellent support; matching legacy financial aliases/filter-local scoring requires care |
| Serialized in-memory BM25 | Can preserve formula | Usually full reserialization; stale caches and memory duplication | Simple small-corpus start; unsafe pickle is unacceptable |
| SQLite postings + explicit BM25 | Exact controllable positive-IDF formula, term frequencies and lengths persist | Reuse immutable chunk postings, generation membership/stats, atomic active pointer | No new dependency; inspectable JSON/SQL, Python 3.12/3.13 and Windows support |

Choose SQLite postings with explicit BM25. Query scoring reads postings for query terms and precomputed corpus statistics, not full text tokenization. Metadata-filtered queries compute aggregate counts over the filtered membership in SQL, retaining filter-local BM25 semantics. Raw scores are not combined with cosine; fusion uses ranks. FTS5 was evaluated, not chosen or mislabeled as numerically equivalent. Sources: https://sqlite.org/fts5.html and the inspected legacy source.

## Lifecycle and consistency

Generation identity covers dataset name, immutable manifest hashes, deterministic sampling policy, tokenizer/scoring version and embedding identity/dimension. BUILDING/FAILED generations are not query-ready. Frozen source descriptors include raw/structured/chunks paths and hashes. Build validates manifests, raw/normalized hashes and source chunk context. Insertion is bounded by filing/batch. New generations reuse unchanged chunk postings and cached embeddings; publication materializes membership/DF and a separate Qdrant collection, then atomically switches the SQLite active pointer only after complete dense membership validation. Prior generations and collections are retained.

Dense collections are dedicated `financial_c_<generation>` collections in a separate local Qdrant directory. Never reuse/delete `knowledgebase`. Embedding identity includes installed model digest and actual vector dimension. Inputs use an explicit bounded prefix/truncation policy, while original display/source text remains unchanged. Recovery resumes idempotent staged records and cached vectors; partial builds keep the last READY generation active. Local Qdrant requires one owning process per directory: CLI builds close clients before the API opens them; API build/search share a client. No paid service or model download is introduced.

## Queries, failure, rollback

Query a named dataset and optional explicit generation, with company/filing/form/fiscal filters, BM25/dense/hybrid modes, bounded candidates, deterministic tie-breaking and deduplication. Return source identities, period/table context, generation/mode/ranks and verified provenance. Dense-model/generation/membership mismatches fail closed; hybrid degradation is opt-in and explicitly reported. BM25-only needs no Ollama request. Provenance validates selected evidence against frozen source artifacts, not the active B chunk registry.

Rollback selects a retained READY generation after integrity checks; no destructive replacement or cleanup of historical vectors. Source PARTIAL status remains visible. Building an index does not certify financial completeness or financial-answer accuracy.

Query-time provenance reparses each returned filing against hash-pinned artifacts. This preserves source validation across restarts without an unchecked long-lived cache, but adds end-to-end latency. Benchmarks separate that cost from embedding and retrieval. API instances share one lazily opened local Qdrant client behind locks and close it at shutdown. Unsupported tokenizer/index versions fail closed rather than being served with current scoring semantics.

## Benchmark plan

Compare original per-query lexical baseline, formula-matched persistent lexical, dense and RRF hybrid on identical source-grounded query sets and snapshots. Financial-token aliases are evaluated separately from the unchanged legacy tokenizer. Use full Apple 566 chunks plus a deterministic, query-independent bounded Tesla original/amendment subset if full dense indexing is too expensive. Record exact manifests and selected IDs. Separate build/embedding/incremental/restart/cold/warm/retrieval/provenance times, p50/p95, throughput, peak RSS and disk. Judge a small auditable query set against original source locators, not LLM answers. Report limited statistical power and NOT_MEASURED where appropriate; no performance claims precede measurements.

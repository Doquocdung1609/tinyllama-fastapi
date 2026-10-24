# Topic 3 — Financial Intelligence Hybrid Search

## What has been implemented

A standalone retrieval-only endpoint, POST /financial/search, adds **real Okapi BM25**, Qdrant dense search, equal-weight rank fusion (RRF k=60), and an optional **local** Cross-Encoder reranker. This stays separate from the existing /rag/query so its Vietnamese learning-document heuristics and conversational features continue working. The endpoint returns precise document/page/source references, text, BM25, cosine, RRF, reranker scores, and per-stage timings. Scores are ranking signals, **not calibrated confidence probabilities**.

Four method names: bm25, dense, hybrid, hybrid_rerank. BM25 works without Ollama. Dense and hybrid require a working embedding provider and indexed Qdrant. Hybrid_rerank requires a real local model and fails explicitly if unavailable: no fake reranking. Strict document_ids scope is mandatory.

## Real document workflow

1. Upload financial report PDFs with /documents/upload; wait until READY and obtain document_id.
2. Search the indexed reports:

~~~bash
curl -X POST http://127.0.0.1:8000/financial/search \
  -H 'Content-Type: application/json' \
  -d '{"query":"How did operating cash flow change in 2024?","document_ids":["REPLACE_WITH_REAL_ID"],"method":"hybrid","top_k":5}'
~~~

3. For a company/ticker/year/form filter, metadata must be explicitly indexed as ticker, fiscal_year, and/or form_type on the corresponding chunks. Missing metadata never gets guessed from the filename. Currently those metadata fields are not consistently produced by the legacy PDF pipeline; add a dedicated filing ingestion pipeline next.
4. To use hybrid_rerank, install the optional sentence-transformers package and put an appropriate, licensed Cross-Encoder model in a local directory. Set FINANCIAL_RERANKER_PATH to that directory. Runs on CPU and does not silently download models; pin the model revision in benchmark reports.

## Evaluation (separate gold labels; no oracle leakage)

Create a frozen, independently annotated held-out file using **real indexed chunk IDs**:

~~~json
[
  {"id":"q001","query":"Question written by annotator","document_ids":["ACTUAL_DOCUMENT_ID"],"relevant_chunk_ids":["ACTUAL_RELEVANT_CHUNK_ID"]}
]
~~~

The block above is a *template*, not a completed evaluation dataset. No oracle answers or qrels are sent to the search endpoint.

~~~bash
python scripts/financial_retrieval_benchmark.py --cases /path/to/heldout.json --methods bm25 dense hybrid --ks 1 3 5 10
~~~

Only include hybrid_rerank when its model is installed. Benchmark writes per-case CSV and summary JSON, with Recall@k, Precision@k, MRR@k, nDCG@k, median and p95 end-to-end latency. It rejects comparisons when methods report different corpus snapshot hashes. Compare against the **same corpus, qrels, embedding model and cutoffs**; tune on dev only, never the locked test set.

## Production gaps (do not call this deployed finance production)

- Proper SEC EDGAR / XBRL ingestion with issuer, form, accession number, filing timestamps, source URLs, fiscal periods, restatements and change tracking, subject to SEC fair-access requirements.
- Filing metadata production. Qdrant now receives an ANN prefilter when indexed ticker/year/form metadata exists, but the legacy PDF ingestion path does not consistently create those fields.
- A persistent/scalable lexical inverted index. Current in-process BM25 scans all selected indexed chunks per query: correct baseline, not yet a big-data scaling solution.
- User-level ACL/authentication, audit logs, rate limiting, data ownership, retention, backups, resilience and load tests. A document ID is **not** a security boundary.
- Human-verified filing-level annotations, held-out corpus, QA of source extraction, table/number integrity, evaluation at several corpus sizes, statistical uncertainty.
- Optional answer layer from AI_agent_Demo: use only grounded Analyst/Calculator ideas after retrieval benchmarks. Keep the answer key out of production prompts and Critic agents. Deterministic finance calculations require explicit source values and units.

## Original RAG scoring distinction

Legacy rag_service._lexical_candidates is a custom lexical **heuristic**, not BM25; its lexical=1.50, semantic=.02 fusion weights are not an unbiased BM25 vs semantic baseline. The new endpoint is a separate evaluation path, not a stealth modification to existing users' answers.

Milestone A audit evidence and the merge recommendation are in
[`docs/topic3/MILESTONE_A_AUDIT.md`](topic3/MILESTONE_A_AUDIT.md) and
[`docs/topic3/PR1_REVIEW.md`](topic3/PR1_REVIEW.md).

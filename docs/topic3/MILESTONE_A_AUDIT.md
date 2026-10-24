# Topic 3 — Milestone A audit

## Decision

**Milestone A audit work: VERIFIED COMPLETE.**

**PR #1 merge/production readiness: NOT APPROVED.** The retrieval increment is
testable and its existing application regression passes, but it is not yet a
production financial search platform. Persistent lexical indexing, a real SEC
corpus, independent qrels, access control, and a tested reranker remain outside
the verified implementation.

No merge or close action was taken on PR #1. Milestones B–G were not started.

## Audited state

| Item | Inspected value | Status |
|---|---|---:|
| Main repository | `Doquocdung1609/tinyllama-fastapi` | VERIFIED |
| Remote main at audit start | `ceaa8acfcfaea8056e45b859a0fc44d6381fb22a` | VERIFIED |
| Local pre-audit main | `d59a9a9f2a75a9c7f37766916010f83b50608ca0` | VERIFIED |
| Working branch | `codex/topic3-milestone-a-pr1` | VERIFIED |
| PR #1 | Draft, open, not merged; 11 files, 12 commits | VERIFIED |
| PR #1 head | `76336f4b36ee398a354de52abd74c6a4347eedb0` | VERIFIED |
| PR #1 base | `main` at `ceaa8acfcfaea8056e45b859a0fc44d6381fb22a` | VERIFIED |
| GitHub checks | No checks/statuses returned | VERIFIED |
| Local merge tree | Clean merge tree generated; no textual conflict | VERIFIED |
| Reference repository | `Doquocdung1609/AI_agent_Demo` at `87681e11c3c38975a091993c0455a4cf3b0cf422` | VERIFIED |

GitHub reported PR #1 as draft and `mergeable=false`; the local three-way merge
tree was clean. Because no CI checks exist, this audit does not interpret the
GitHub flag as evidence that the code is safe to merge.

## What PR #1 actually implements

- Retrieval-only `POST /financial/search` endpoint.
- Query-time Okapi BM25 over explicitly selected document chunks.
- Existing Qdrant dense search using the configured embedding provider.
- Equal-weight reciprocal-rank fusion with `k=60`.
- Optional local CPU Cross-Encoder, disabled unless a local model path exists.
- Retrieval evaluator with qrels stored outside the runtime request.
- Fourteen deterministic unit/API tests at the original PR head.

It deliberately does not replace `/rag/query` or its answer-generation path.

## Repairs completed during the audit

| Defect | Change | Verification | Status |
|---|---|---|---:|
| Dense metadata was post-filtered after ANN and could lose eligible candidates | Added Qdrant payload prefilter for document scope plus ticker/year/form metadata | Unit inspection of Qdrant `Filter`; search-service propagation test | VERIFIED |
| RRF could count duplicate IDs twice within one channel | Added per-channel deduplication and positive-`k` validation | Deterministic duplicate-hit test | VERIFIED |
| Financial numeric forms such as `1,496.5` and `1.496,5` did not normalize to the same lexical term | Added NFKC plus locale-tolerant numeric aliases | Tokenization tests | VERIFIED |
| Search accepted whitespace-only queries/IDs in direct and API paths | Added fail-closed validation | API and service tests | VERIFIED |
| Benchmark lacked Precision@k and only evaluated one cutoff | Added Precision and cutoffs 1/3/5/10 | Hand-checkable metric test and live script execution | VERIFIED |
| Methods could unknowingly use different corpus states | Added deterministic corpus snapshot hash and evaluator equality check | Snapshot-change test; live methods reported the same hash | VERIFIED |
| Latency mixed embedding and ANN time and omitted corpus/reranker load | Separated corpus, lexical, embedding, ANN, fusion, reranker-load and rerank timings | Live response inspected | VERIFIED |
| Benchmark ordering always favored the same cold/warm method position | Rotated method order by case | Code inspection and live execution | VERIFIED |

## Real local integration evidence

The endpoint was run against the preserved production collection, not a mocked
Qdrant client:

- Qdrant: online, collection `knowledgebase`, 1,947 vectors, dimension 768.
- Application metadata: 3 documents and 1,947 chunks.
- Ollama embeddings: `nomic-embed-text` through the configured local provider.
- Query: `đổi mới tài chính có mấy loại`.
- Scope: one existing 249-page financial-innovation lecture PDF.
- Manually checked relevant chunk: `...-00578`, page 155.
- Corpus snapshot for all three methods:
  `75daf612e00312ff51bbfc77945176e35e2ac8967a4fb52d1ccb9869cdde240f`.

| Method | Relevant rank | Recall@1 | Recall@3 | Recall@10 | One-query wall latency |
|---|---:|---:|---:|---:|---:|
| BM25 | 3 | 0 | 1 | 1 | 315.9 ms |
| Dense | not in top 10 | 0 | 0 | 0 | 3,864.1 ms |
| Hybrid RRF | 1 | 1 | 1 | 1 | 2,379.2 ms |

This is a **development integration smoke case**, not an independent benchmark;
it is one previously investigated question from a non-SEC document. It proves
that the endpoint, Ollama embedding path, Qdrant path, evaluator, and provenance
work together. It does not prove that Hybrid is generally best.

The optional reranker returned HTTP 503 with an explicit local-model-path error.
No model was downloaded. The reranker remains BLOCKED for real inference.

## Reference repository audit

`AI_agent_Demo` contains useful ideas, but no component was copied during
Milestone A:

- `classify_question` is a rule-based English intent classifier. It is useful as
  a candidate baseline, but has no Vietnamese coverage or independent accuracy
  report.
- `chunk_text_table_aware` preserves Markdown tables, but has no page/bbox/stable
  evidence IDs and can create very large chunks.
- BM25 and semantic embeddings are session-memory indexes; neither is persistent
  or version-synchronized.
- Its hybrid method normalizes scores and applies fixed 0.4/0.6 weights, so it is
  not a fair BM25/Dense/RRF baseline.
- Analyst/Critic/Calculator repeatedly call the same local LLM. The Critic is not
  an independent judge and answers are not citation-validated.
- The two recorded JSON runs cover only the first 10 TAT-QA development
  questions (7/10 then 9/10). One later run still loses a negative sign. These
  are QA development results, not retrieval metrics or sealed holdout evidence.
- `tatqa_dataset_test.json` has 1,669 questions without public answers in the
  checked file; it cannot be scored locally as a labeled holdout.

Selective reuse is therefore deferred to Milestone G after retrieval passes.

## Completion matrix

| Milestone A requirement | Status |
|---|---:|
| Inspect both repositories and actual PR diff | VERIFIED |
| Review BM25, Dense, RRF, reranker, filters | VERIFIED |
| Check evaluation fairness | VERIFIED; gaps repaired where in scope |
| Check persistence/scaling/security/integration risk | VERIFIED |
| Fix well-supported in-scope defects | VERIFIED |
| Run targeted and full regression | VERIFIED |
| Run real local API/Qdrant/Ollama smoke | VERIFIED |
| Real Cross-Encoder inference | BLOCKED — no approved local model |
| Independent SEC financial benchmark | NOT IMPLEMENTED — Milestones B–D |
| Persistent lexical index | NOT IMPLEMENTED — Milestone C |
| Production access control/rate limiting | NOT IMPLEMENTED — Milestone F |

## Reproduction

See `REGRESSION_TEST_REPORT.md` for exact commands and results. The synthetic
BM25 scaling data is in `reports/topic3_bm25_scaling.csv`; it is labeled as a
performance probe, not financial relevance evidence.

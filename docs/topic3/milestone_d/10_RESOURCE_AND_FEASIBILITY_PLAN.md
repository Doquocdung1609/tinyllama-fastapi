# Local resource and feasibility plan

**Planning estimates, not measurements.** Owner baseline: 8 GB system RAM, GTX1650Ti with4 GB VRAM, existing Python/Ollama/Qdrant/SQLite stack. No paid APIs, cloud compute, model downloads, new index builds or destructive stress tests are authorized here.

## Minimum viable research budget

| Resource | Proposed operating envelope | Measurement / stop condition later |
|---|---|---|
| Corpus | 16–20 filings, planned pilot cap10,000 parent chunks; full sources retained, inclusion policy fixed before qrels | If cap exceeded, revise source-independent selection protocol before query authoring; never remove hard gold rows after observing ranks |
| RAM | One API/index owner and one worker; research process peak RSS target≤3 GB, total machine use target≤7 GB | Stop on sustained paging, OOM, total usage>90% for60s; avoid co-resident indexing, UI, generator and embedding processes |
| GPU | Existing embedding model; optional existing Qwen2.5 3B used sequentially, not assumed simultaneous residency | Stop on GPU OOM/driver errors; record CPU fallback separately, do not hide slower trials |
| Embeddings | Existing768-dimensional Nomic identity, no fine-tuning | 10k×768×4 ≈30.7 MB raw float32 per representation; Qdrant payload/index/collection overhead is extra and must be measured |
| Disk | Research-only namespace allowance2 GB incremental initially; preserve all owner history | Preflight free disk≥5 GB beyond owner reserved space; stop if allowance/free-space floor violated; no automatic historical cleanup |
| Concurrency | 1 query baseline; optional2 after safety/memory pass | No build/query load saturation experiments until isolation and resource budget approved |
| Answer calls | Optional D4 one local draft per question, selected evidence≤5 results/20 parents | Input≤6,000 characters only if actual token context fits; otherwise abstain/compact with coverage retained; output≤512 tokens, deadline60s |
| Retrieval timeout | Proposed per-request deadline15s, single embedding request | Count timeouts/failures, no silent exclusions; revise threshold only before freeze |

Raw vector arithmetic is a lower bound, not a Qdrant disk forecast. A full retained generation can duplicate membership/payload even when embeddings are reused. Do not infer near-zero rebuild cost from C incremental caching. Proposed experiment creates at most one new compatible representation at a time and keeps C intact; cleanup policy requires explicit protected-generation review, dry run and owner approval for any owner-data removal.

## Cost boundaries

Existing BM25 B needs no embedding call; F normally needs one. R/A can avoid it for deterministic exact cases, but the avoided-call rate is unknown until evaluated. T/AT add compact-view assembly for≤20 candidates and a fixed arithmetic score bonus; expected CPU-only overhead is a hypothesis. Numeric verifier is bounded by≤8 operands/depth3 and should be small relative to model time, but must be measured. No numeric latency improvement is promised.

Use existing `nomic-embed-text` only with frozen digest/prefix/context identity. Paper model capacities do not replace actual runtime metadata. Existing Qwen2.5 3B is an optional prose generator; if absent/incompatible, D1–D3 still viable and D4 blocks. Do not pull `llama3` or a70B model because the related paper uses it. Neural cross-encoder reranking, learned routers, extra vector families and multi-agent critics are postponed unless the simple experiment fails and the owner approves added resources.

## Effort estimates and feasibility risk

| Work | Estimated focused effort | Risk / reduction |
|---|---:|---|
| Source availability, split audit and freeze | 2–4 days | Real amendments/filing quality may be unavailable; pre-ranking protocol amendment or blocked stratum |
| Human qrels144 questions + adjudication | 3–6 days, including at least24 annotation hours | Availability of second reviewer; reduce declared scope before freeze, not pretend dual review |
| D1 contracts/rules/tests | 2–3 days | Fiscal/calendar and comparative columns dominate errors; explicit clarification first |
| D2 views/invariants | 3–5 days | Header conflicts and footnotes; candidate-time view first, defer re-embedding |
| D3 bounded strategies/traces | 3–4 days | Rule/weight overfitting; seven-arm cap, one finalist |
| D4 optional source-bound QA | 4–6 days | Small-model hallucination/low coverage; deterministic extract/compare before prose |
| D5 evaluation/report | 3–5 days | Small issuer cluster count and timing variability; descriptive uncertainty, preserve negatives |

Approximate total20–33 focused days with some annotation overlap, not a committed delivery date. Owner/supervisor review and SEC availability add elapsed time. Minimum retrieval experiment can omit D4 and neural components. No additional monetary budget is assumed. If full qrels or memory budgets cannot be met, request a reduced **preregistered** pilot; do not drop failing methods or hard examples after scores exist.

## Operational verification plan, not execution evidence

Reuse isolated test corpus/index paths; capture owner historical manifests and protected collection inventory read-only before/after any future experiment. Run deterministic contract/provenance/auth/rollback tests, then bounded real search. Measure build wall time, embedding calls/reuse, disk per generation, restart behavior, peak RSS/VRAM and stage latencies as 08. Server Qdrant requires its own deployment decision; local locks are not distributed coordination. No production, multi-node, disaster-recovery or enterprise-security claim follows from this envelope.

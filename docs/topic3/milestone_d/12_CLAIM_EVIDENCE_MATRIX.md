# Claim, evidence and novelty matrix

**Design only.** Status labels describe evidence maturity, not project marketing. C findings are inherited accepted evidence, not rerun D findings. Literature evidence applies to the source's experimental setting. Every D hypothesis below is untested here.

## Traceability

| RQ / status | Hypothesis and proposed component | Baseline / metric | Required data and evidence | Permitted claim after test / disallowed claim | Failure condition |
|---|---|---|---|---|---|
| C / already demonstrated within accepted scope | Persistent BM25, generation isolation, provenance and security controls exist | Actual source + accepted regression/integration reports | Accepted merge and baseline refs in01, C acceptance/freeze | “Controlled local pilot accepted with limitations”; not production/distributed/security certification | New regression or provenance failure invalidates corresponding acceptance assumption |
| C / already observed | BM25 is recommended on evaluated corpus; Hybrid not consistently better | Historical14 and repaired issuer evaluation, R@5/MRR/nDCG | Frozen artifacts/hashes in C freeze; distinct generations | Report actual limited-corpus scores; not general financial-search superiority or fresh D replication | Broader fresh evaluation may differ; do not rewrite original result |
| Literature / externally reported | Rank fusion, dual encoders, semantic table matching, reranking and adaptive RAG can help in their reported settings | Primary studies in02, their datasets | Primary publication records/methods/results | Attribute findings to source setting; not claim our 3B/SEC/local system reproduced them | Different task/model/split may not transfer |
| D1 / proposed, not evaluated | Deterministic scope/intent reduces wrong-context evidence; query-understanding/resolver | Explicit-filter-only C, slot/scope accuracy and false exclusions, R@5 | New manually labeled period/amendment/intent cases; paired identical corpus; source-based oracle scope | “On specified split, resolver changed X/Y errors”; not universally understands financial queries | More false exclusions/wrong scope, no useful gain, excessive clarification |
| D2 / proposed, not evaluated | Compact header/cell views preserve evidence and improve selection; table-evidence adapter | Same C rows/model/candidates; cell coverage, R@5, truncation and bytes | Six families with source coordinates, lossless tests, matched candidate/representation experiment | “Specific view improved measured trade-off”; not first row-aware financial retriever, not full SEC extraction | Missing headers/footnotes, wrong period/unit or no quality/cost value |
| D3 / proposed, not evaluated | Conservative adaptation helps paraphrases without material exact-query loss; router/fallback/RRF | B/D/F; paired R@5/nDCG, exact guardrail, latency | Fresh issuer splits, seven-arm dev cap, one finalist, frozen config and traces | “Selected strategy met pilot guardrails”; not Hybrid generally superior or learned optimal routing | Guardrail failure, Dense cost without gain, holdout tuning or source/filter confound |
| D4 / proposed, not evaluated | Source-bound verifier reduces accepted numeric errors; deterministic operand checker | Same draft/bundle verifier off/on; supported accuracy, coverage, unsupported claims | Human source-cell truth, sign/unit/period checks, paired offline ablation | “Checker blocked specified wrong claims at reported coverage”; not certified financial-answer correctness or autonomous analyst | Wrong numbers pass, true answers rejected excessively, always abstains, unsafe execution |
| D5 / proposed, not evaluated | Bounded architecture has useful local quality/cost trade-off | Same corpus and workload B/D/F; p50/p95/RSS/VRAM/disk/failure rate | Exact runtime/config, separate service/HTTP/cold/warm, repeat logs | “Feasible under stated local workload”; not multi-node scale or production readiness | OOM, budget/deadline failure or no Pareto advantage |
| Speculative / unsupported | Large multi-agent critics, neural router or cross-encoder would outperform simpler design | Not included in minimum matrix | Separate approval, resources and independent experiment | At present only “possible later research”; no performance assertion | Cost/complexity without independent benefit |

## Scientific contribution boundary

Potential project-specific contribution: a reproducible evaluation of query-aware Hybrid retrieval over versioned SEC evidence, preserving row/cell-period semantics and exposing cost/provenance failures on modest hardware, with optional source-bound numeric verification. This is a research question about a defensible system combination and its failure modes. Global algorithmic novelty, patentability and superiority over the literature are not established by this review.

Already-existing ideas must be acknowledged: B/C row-aware chunking and persistent hybrid fusion; published semantic table retrieval, adaptive RAG and calculator agents. A paper-style report must separate these from newly implemented/tested components and disclose negative outcomes. A convincing negative result retaining BM25 can satisfy the research objective without adding an agent.

## Evidence integrity ledger

Canonical historical hashes are referenced, not regenerated or overwritten:

| Artifact identity | SHA256 recorded in accepted C freeze |
|---|---|
| Original14 query set | `b98e125698a0c10db83c03327654264234326706d7256287e2189983d8757d86` |
| Intermediate16 | `39196ad6b304e5f79975c8bfb3573d593a3ef0052ccd55135bd1dbd2face6555` |
| Issuer corpus | `1944ca03db486354ad5f77b15b19993795d33f56b1255de338e82ca74b5c8b9f` |
| Issuer query set | `c8aedd619f362208fcb097c197f351b117aaa7e2c3bfd758ef97c56df842792a` |
| Issuer heldout report | `7ee95bbefe47f2f92a3b99b48d886686a5fd41d0ee5017bf8ec8299015ee632e` |
| C measurements | `9925a0f6cab569a36e0ceef0e1d53613c9e2306f67dae005b83faca5bac95554` |

These use the canonical convention documented in [C freeze](../MILESTONE_C_SCIENTIFIC_EVIDENCE_FREEZE.md), not an assertion that CRLF checkout raw bytes hash identically. Existing deployed embedding identity is Nomic digest `0a109f422b47e3a30ba2b10eca18548e944e8a23073ee3f3e947efcf3c45e59f`,768 dimensions, asymmetric `search_document: ` / `search_query: ` prefixes. New representation/config requires new identities and new evidence. No D source/query-set/model freeze exists yet, and no D empirical contribution is claimed.

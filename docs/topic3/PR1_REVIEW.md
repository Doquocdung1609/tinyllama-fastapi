# Topic 3 — PR #1 review

PR: `#1 — Topic 3: auditable financial BM25 + dense + RRF + optional Cross-Encoder`

Review target: `76336f4b36ee398a354de52abd74c6a4347eedb0` against
`ceaa8acfcfaea8056e45b859a0fc44d6381fb22a`.

## Recommendation

**HOLD / DO NOT MERGE YET.** The original PR is a useful development increment,
but it has no CI checks and does not include the fixes or audit evidence on the
Milestone A branch. Even after those fixes, it must remain labeled research/
development until Milestones B–F provide real filings, a persistent lexical
index, independent qrels, ACLs, and operational evidence.

## Review of all 11 changed files

| File | Finding | Status |
|---|---|---:|
| `.env.example` | Local reranker path is explicit; no silent model download | VERIFIED |
| `README.md` | Correctly labels endpoint development-only | VERIFIED |
| `app/api/financial.py` | Good bounded schema and explicit scope; whitespace validation was missing and is fixed on audit branch | VERIFIED after fix |
| `app/services/financial_search_service.py` | Core formulas are sound; post-ANN metadata filtering, duplicate RRF hits, numeric normalization, provenance and timing defects were fixed | VERIFIED after fix |
| `docs/FINANCIAL_SEARCH_TOPIC3.md` | Honest production caveats; updated for true metadata prefilter and multi-k metrics | VERIFIED after fix |
| `main.py` | Router integration is minimal and does not alter legacy `/rag/query` | VERIFIED |
| `requirements-financial-rerank.txt` | Heavy dependency isolated and optional; version range not a fully reproducible lock | PARTIAL |
| `scripts/financial_retrieval_benchmark.py` | No gold sent to runtime; initially lacked Precision/multi-k/snapshot parity and method-order control; repaired | VERIFIED after fix |
| `tests/test_financial_api.py` | Deterministic contract tests; mocks search implementation | VERIFIED unit/API only |
| `tests/test_financial_benchmark.py` | Metrics are hand-checkable; expanded to Precision | VERIFIED unit only |
| `tests/test_financial_search.py` | Covers formulas/scope/failure; dependencies are stubbed; expanded for prefilter/dedup/numbers/snapshot/validation | VERIFIED unit only |

## Formula review

### Okapi BM25

The implementation uses:

`IDF(t) = log(1 + (N - df(t) + 0.5) / (df(t) + 0.5))`

and:

`score(D,Q) = Σ IDF(t) * tf(t,D)*(k1+1) / (tf(t,D) + k1*(1-b+b*|D|/avgdl))`

with `k1=1.5`, `b=0.75`. This is a valid positive-IDF Okapi BM25
variant. Repeated query terms are intentionally collapsed, which is a common
short-query variant but must be held constant across experiments.

The formula is correct; the scalability architecture is not. It tokenizes every
eligible chunk and recomputes document frequency and average length on each
request. The measured 5,000-chunk warm P50 is 1,079.902 ms on this machine.

### Reciprocal Rank Fusion

The implementation uses equal-weight `Σ 1/(60 + rank)`. It combines positions,
not incomparable cosine and BM25 raw scores. The audit added per-channel ID
deduplication so a malformed repeated result cannot contribute twice.

There is no evidence that `k=60` or equal channel weight is optimal for the
future finance corpus. These must be tuned on development data only.

### Dense retrieval and metadata

Document scope is applied inside Qdrant and checked again locally. The original
PR applied ticker/year/form only after ANN candidate generation, which could
silently remove relevant candidates. The audit branch now creates Qdrant nested
payload filters and maps case-insensitive API values back to exact indexed values.

Production verification is still PARTIAL because the existing generic PDF
chunks do not contain filing metadata. Unit tests verify the actual Qdrant filter
object; a real SEC corpus is required for end-to-end filter recall.

### Cross-Encoder

The loader is local-only, CPU-only and fails closed. This is appropriate for the
4 GB VRAM constraint. No approved local checkpoint exists, so quality, latency,
RAM, licensing and failure behavior under real inference are BLOCKED.

## Findings

| Severity | Finding | Resolution |
|---|---|---|
| P0 | No independent financial corpus/qrels; method superiority cannot be claimed | NOT IMPLEMENTED; Milestones B/D |
| P0 | No document-level authorization; IDs are not security boundaries | NOT IMPLEMENTED; Milestone F |
| P1 | Dense metadata post-filter could reduce recall | FIXED on audit branch |
| P1 | BM25 rebuilt per query; linear cost and no persistent index | NOT IMPLEMENTED; Milestone C |
| P1 | Evaluator omitted Precision@k/multiple cutoffs and corpus parity proof | FIXED on audit branch |
| P1 | Existing production chunks may lack exact source IDs/bboxes | PARTIAL; requires versioned re-index policy |
| P1 | No shared lexical/vector index generation or atomic commit | NOT IMPLEMENTED; Milestone C |
| P2 | RRF could double-count duplicate IDs in a channel | FIXED on audit branch |
| P2 | Locale-formatted financial numbers could tokenize differently | FIXED on audit branch |
| P2 | Timing underreported corpus/reranker stages | FIXED on audit branch |
| P2 | Whitespace-only direct/API input | FIXED on audit branch |
| P2 | Optional dependency uses a range rather than a model/package lockfile | PARTIAL |

## Test-claim classification

- Original PR claim “14 tests passed” is VERIFIED, but all 14 are deterministic
  unit/API tests with Qdrant/embedding/search dependencies stubbed.
- Full repository regression at the original head is VERIFIED: 86 passed,
  3 skipped.
- Audit branch result is VERIFIED: 94 passed, 3 skipped.
- Real Qdrant and Ollama embedding integration is VERIFIED for one development
  smoke case.
- Cross-Encoder integration, SEC metadata filtering, concurrent load, and
  independently sealed retrieval quality remain BLOCKED or NOT IMPLEMENTED.

## Merge conditions

1. Apply or cherry-pick the audit fixes onto the intended PR branch.
2. Add CI that runs the deterministic full suite.
3. Preserve the development-only label and explicit missing-production caveats.
4. Do not claim SEC, ACL, persistent BM25, or reranker readiness.
5. Re-run the full regression at the final PR head.

These conditions permit merging a research increment; they do not constitute
Topic 3 production acceptance.

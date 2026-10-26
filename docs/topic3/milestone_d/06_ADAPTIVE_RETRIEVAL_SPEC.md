# Bounded adaptive retrieval experiment

**Proposal; no policies have been tuned or run.** Accepted C BM25 remains the recommended baseline. Fresh data in 08 is required. Seven retrieval configurations total; no unconstrained weight/model search. A learned router and neural reranker are excluded from this first matrix.

## Shared settings

Same source membership, explicit/resolved filters, model identity and canonical parent IDs for all arms. C-compatible k1=1.5, b=0.75; candidate budget40 per channel; top5 primary/top10 secondary; RRF k60. Dense uses the existing Nomic digest/prefix contract; record effective Ollama token/context settings and truncation. BM25 ties by chunk ID; Dense ties by canonical chunk ID after backend retrieval; record raw backend cutoff/ties. Never assume sorting returned candidates makes the unseen tie boundary deterministic.

Deduplicate within each channel by canonical parent ID before assigning rank. Union channels by canonical ID. RRF score `wB/(60+rB) + wD/(60+rD)`, absent rank contributes zero; sort decreasing score then ID. Weighted scores are not probabilities. Derived views do not each receive separate votes. Filter eligibility is computed before channel ranking, with response-level period/cell checks after retrieval. No reranker can restore filtered-out gold evidence.

| ID / method | Exact flow / rule | Suitable cases and failure risk | Incremental cost estimate (unmeasured) |
|---|---|---|---|
| B lexical | BM25→top40→top5/10 | Exact financial labels; vocabulary mismatch remains | C lexical cost, no model call; no new index |
| D dense | One query embedding→matching generation→top40 | Paraphrases; numbers/units/tables may collide | One embedding + Qdrant; existing vector index |
| F fixed fusion | B and D→equal weights1/1 RRF→top5/10 | Complementary signals; shared weak candidates can win | D cost + lexical + O(80 log80) local fusion |
| R deterministic router | If exact/explicit numeric/table-label intent → B; otherwise D for paraphrase/terminology; comparison/cross-section → F; ambiguous scope never searches | Isolates intent selection with unchanged row view; misrouting loses the other channel's evidence | 0 or1 embedding by route; no extra model/index |
| T table rerank only | F on C rows; rerank its top20 with fixed table rule below, then top5/10 | Ambiguous headers/row roles; parser errors can harm | Up to20 compact views; CPU/metadata cost only; no new vectors |
| A adaptive fusion only | B first. Exact intent with ≥5 positive BM25 candidates and unambiguous scope returns B. Otherwise retrieve D; exact/table/comparison uses weights2/1, paraphrase/terminology/cross-section uses1/1 | Conservative cost; “five hits” is a weak sufficiency heuristic, not proof of relevance | Zero or1 embedding; same storage as F |
| AT combined | A plus identical table rerank of its top20 | Tests interaction with table processing | A cost + bounded CPU view work |

These rules are **predeclared candidate rules**, not claims that BM25 score/count is calibrated. Multi-label intent precedence: unresolved scope stops; cross-section/comparison before exact; table label exact only if explicit row label is recognized; all unknown intents use B and log unknown (not silently claim adaptive improvement).

Table rerank rule, frozen for T and AT: `final = normalized_base + 0.05*row_match + 0.05*header_role_match`; normalize by maximum nonnegative score within the candidate list (all zero → zero). Row match is1 only for an explicit exact/approved alias row-label match; header-role match is1 only for all explicitly requested measurement-role tokens (e.g. fair/carrying/basic/diluted) matching selected column paths; missing request →0. No model scores, no use of gold relevance. Scope violations are ineligible rather than a soft penalty. Text-only candidates get zero bonuses. Tie by original rank then canonical ID. Candidate IDs remain fixed for each paired rerank comparison. If later dev results justify another weight, replace this single candidate under a logged protocol amendment **before validation**, not add a hidden eighth arm.

Candidate pool sizes and reordering limits must be saved per request. A result absent from the union cannot be “fixed” by fusion. Conditional fallback never expands issuer/form/period scope. B/D channel failures count as failures in scientific comparisons. Operational fallback may return B with `effective_mode=BM25_DEGRADED` and failure reason if Dense is optional; exclude neither the failure nor its latency from reports. Hash/identity failures cannot be bypassed by another channel using the same compromised source.

## Overlap-bias diagnosis

For every query retain B/D rank40 lists, union, intersection, per-candidate contributions and source periods, top5 winner/loser swaps, marginal relevant coverage and canonical duplicates. For each F error ask: was gold absent, below rank40, present but demoted, scope-wrong, or invalid? Record shared irrelevant promotions and each side's reciprocal contribution. Compare F vs B and A vs F on matched queries, not cherry-picked wins. Consumed WMT margin case is a design motivation only; thresholds are not optimized on it. Include single-channel relevant hits and overlapping irrelevant hits as regression fixtures, clearly outside future heldout scores.

## Selection and falsification

All seven arms can be compared on dev; select at most one candidate beyond B/D/F for validation/holdout. Selection order: no provenance or scope safety regression; exact-query Recall@5 within0.02 of B on validation; overall Recall@5 within0.02 of B and positive nDCG@5 difference; paraphrase Recall@5 target +0.05 over B; warm service p95 ≤1.5×F and resource caps in10. These are proposed decision margins, not powered promises. Report intervals; passing point thresholds alone does not establish superiority. If no candidate passes, retain B and publish negative findings. Freeze selected config before holdout, evaluate once; no router repairs using those labels without retiring that holdout.

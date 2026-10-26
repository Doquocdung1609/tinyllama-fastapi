# Ablation and error-analysis plan

**Not executed.** Seven bounded retrieval arms from 06; new dataset and freeze in 08 required first. Representation-vs-routing effects are separated. Query scope resolution is identical across all retrieval arms; a separate D1 paired on/off experiment isolates its effect. No answer model is part of retrieval ranking comparisons.

| Arm | Channel/fusion | Table processing | Controlled interpretation |
|---|---|---|---|
| B | BM25 only | C row chunks | Strong accepted lexical baseline |
| D | Dense only | C row chunks | Semantic channel control, same model identity |
| F | Fixed equal RRF | C row chunks | Fusion control; B/D candidate pools logged |
| R | Deterministic query router | None beyond C rows | Routing without new table processing; compare against its selected B/D/F route per query and aggregate controls |
| T | F unchanged | Fixed compact-view table rerank | T−F isolates table reranking on identical candidate lists |
| A | BM25-first conditional Dense / weighted RRF | None beyond C rows | Adaptive retrieval without table processing; A−F is a policy bundle effect, not proof of which subrule caused it |
| AT | A unchanged | Same table rerank as T | AT−A isolates table processing within A; AT−T isolates adaptive policy with table processing fixed |

The interaction contrast `(AT−A)−(T−F)` tests whether table processing behaves differently under the adaptive policy; it is not automatically causal under a small observational query sample. R vs F changes channel selection and is reported as a whole strategy. Conditional fallback and weighting are components of A; per-query trace analysis separates which rule fired, but no extra post-hoc weight grid is introduced. A future one-subrule study requires a protocol amendment and new untouched data.

Optional later D2 representation study is a separate experiment, not an eighth hidden matrix arm: C full row vs compact row embeddings, same B/D/F strategy fixed, new representation generation, same source set/model/prefix/truncation and qrels. First run on development only; if selected for confirmatory evaluation, substitute for an existing candidate before validation rather than expanding the experiment budget. Do not compare a compact, larger corpus to the sampled C corpus and attribute difference to representation.

## Optional answer ablation (D4 only)

8. Frozen retriever + frozen evidence bundle + single answer draft, no numerical checks: offline diagnostic only, unchecked output never labeled verified.
9. Exact same draft/bundle + deterministic source-bound verifier: isolate acceptance/rejection/formatting effect; count both errors prevented and correct answers lost.

Use identical model/prompt/draft artifacts for the primary verifier ablation; calling a stochastic model twice would confound the comparison. A calculator/critic or new answer model is a separate later question. Compare at matched answer coverage and include total-query accuracy so always-abstain cannot win. Gold-evidence QA may diagnose reasoning separately but is labeled oracle-context and excluded from retrieval end-to-end claims.

## Error taxonomy and manual review

Every query gets an outcome record with ranked canonical parent IDs, source scope, channel scores/ranks/RRF contributions, effective route, source verification, table header/period mapping, truncation flags, latency and error category. Inspect all regressions of a selected candidate versus B, all provenance/scope violations, all unanswerable/ambiguous cases and all wrong verified numeric claims. Also inspect a fixed seeded sample of successes; do not examine only embarrassing Dense examples or favorable Hybrid wins.

| Error | Evidence needed to assign it |
|---|---|
| Corpus/extraction gap | Supporting source absent or missing required table/header in structured artifacts |
| Scope/resolution error | Gold exists but issuer/filing/period/amendment filter excluded it |
| Lexical mismatch | Relevant row in eligible corpus; no adequate term match, compare literal/alias tokens |
| Dense mismatch | Eligible gold and matching vector identity; compare rank/input/prefix/length; embedding limitation remains hypothesis without controlled representation test |
| Truncation | Required source text position beyond actual submitted/effective token window; character length alone insufficient |
| Fusion demotion/overlap | Gold in candidate union but loses top-k; show shared irrelevant promotion and contribution arithmetic |
| Table semantics | Wrong row group/header/measurement basis/unit despite matching label |
| Provenance/identity | Hash, generation, payload or source correspondence fails |
| Arithmetic/claim | Correct evidence retrieved but wrong operands, sign, scale, period, calculation or unsupported prose |
| Ground-truth defect | Independent source adjudication shows missing alternative relevance or incorrect expected value |

Root causes may coexist. Record confirmed observation, tested counterfactual and remaining hypothesis separately. For example, a long row plus poor Dense rank is correlation; rerunning only that row with a shorter view is a development diagnostic, not unbiased gain. If qrels are revised, version and rerun all arms as 08 requires.

Freeze error rubric before holdout. Two reviewers assign categories blind to method names where feasible; record agreement and disagreements. Archive raw traces and original scores before explanatory reruns. After final holdout failure, keep findings, retire that holdout for tuning and request a new evaluation split if changes are proposed. Negative results can still support a useful contribution about where adaptive Hybrid is unnecessary or harmful.

# Optional evidence-grounded financial answering

**Future D4 proposal, separately authorized only after retrieval gates.** No agent or financial-answer endpoint is implemented here. Evidence retrieval validity and answer correctness have separate denominators and metrics. The minimum useful product may remain evidence search if answer safety/coverage cannot be established.

## Supported bounded answer types

| Type | Required evidence | Output and limit |
|---|---|---|
| Single figure with source | One unambiguous verified cell/period/unit/row role | Exact displayed figure, unit, issuer, period, accession, locator and warning |
| Two-period comparison | Two verified compatible cells and explicit operation | Both source figures, typed calculation, displayed precision and citations |
| Explain line item | Verified definition/accounting-policy text and relevant row if numeric | Bounded explanation; no general knowledge substituted as filing policy |
| Section summary | Selected verified paragraphs/rows covering each claim | Per-claim citations; unsupported conclusions removed or abstained |

Initial operations: extract, subtract, add at most8 operands, ratio, relative percent change. No forecasting, valuation, trading, investment advice, autonomous actions or open-ended code. Multi-hop financial inference beyond these operations is unsupported.

## Evidence-first process

1. Resolve scope and retrieve using a frozen method, pinning generation. Validate every source and view. Keep at most5 selected results/20 parents; never truncate away required header/unit/footnote to make room for a fluent draft.
2. Assemble a coverage map: requested entity, line item, measurement basis, periods and each operand → verified cell or paragraph span. Missing required slots produce abstention before calling a model.
3. Deterministic extraction handles single figures and supported comparisons first. A later optional local Qwen2.5 3B call may draft prose using only a bounded evidence bundle; record exact digest/options/prompt hash/context settings. No new model download is required. Input instructions embedded in filings are untrusted data. At most one draft call; critic is an optional separately measured ablation, not minimum architecture.
4. Draft claims must list evidence IDs and operand IDs. A free-form number absent from verified operands or an allowed calculation is rejected. Citation assembly is deterministic from verified source metadata; never accept an LLM-invented URL, accession, row or cell.
5. Run checks below. Presenter emits supported claims or a typed abstention; it cannot display “verified” for a failed draft. Store stage timings, check reasons and coverage, excluding secrets.

## Deterministic numeric verifier contract

Input is a typed operation tree, not Python/SQL/program text. Leaf references must resolve to cell IDs of verified source parents in the current bundle. Allowed nodes are explicitly enumerated above; maximum8 leaves, depth3, decimal precision28, at most30 significant operand digits and absolute decimal exponent≤12; reject nonfinite values and out-of-bound intermediates. No exponentiation, loops, imports, function calls, `eval`, filesystem/network or model-selected execution. These are proposed bounds to be tested, not current guarantees.

Each operand preserves raw display text, parentheses/minus, inline sign/scale/format, unitRef/contextRef, header path, period/segment and numeric decoder version. Apply sign once; a dash/blank is unknown unless source explicitly defines it as zero. Percent raw `12%` is ratio0.12 with displayed percent12; USD/share is distinct from USD. Header and inline-tag conflicts, ambiguous thousands/decimal conventions or missing scale fail verification. Do not infer a currency because another row has `$`.

Before calculation check: same issuer/entity basis and consolidated/segment scope; same original/amended policy; compatible currency/unit/multiplier; duration versus instant; aligned fiscal periods/durations; definition consistency. Ratios may divide compatible amounts into dimensionless values; per-share denominators require explicit shares. Zero denominator → unsupported. Relative change `(new-old)/old*100` is permitted only for compatible evidence and explicit request; zero or negative base produces a qualified/unsupported result under the initial policy, not a misleading growth percentage. Percentage-point difference is `new_percent-old_percent`, not relative change. No automatic FX conversion, annualization or fiscal-calendar interpolation.

Synthetic verifier fixture: old margin `12%`, new `10%`, both verified synthetic cells. Points result `−2 percentage points`; relative change `−16.666…%`. Round only for display using a frozen decimal rounding rule (half-even initially); retain exact Decimal/intermediate trace. This is not a company fact. Answers compare to ground truth at the source's stated precision/unit; never use the demo's blanket2% tolerance. Human adjudication handles ambiguous rounded inputs and materiality separately.

## Failure/abstention matrix

| Condition | Required behavior |
|---|---|
| Missing evidence or unsupported period | State which issuer/period/operand is absent; do not invent figure |
| Conflicting filings / original versus amendment differ | Show separately cited versions if requested; otherwise clarify selection, no silent merge |
| Unit/sign/scale/measurement basis unresolved | Evidence-only result with reason; no verified number |
| Partial table extraction | Display warning; proceed only if required cells, headers and footnotes are intact and unambiguous; otherwise abstain |
| Source hash or generation mismatch | Fail closed; do not generate from stale cache |
| Unsupported arithmetic / malformed model output | Reject typed expression; return evidence or abstention |
| Summary contains uncited claim | Remove unsupported claim and record rejection; if central claim absent, abstain |
| Deadline/model unavailable | Deterministic extract if fully supported; otherwise evidence-only with error, never fabricated prose |

Uncertainty states are source completeness, scope ambiguity, conflict and unsupported operation. Model confidence is not a substitute for evidence. “Verified calculation” means arithmetic on the specified checked operands, not certification that the filing, extraction or investment conclusion is economically correct.

## Later evaluation and tests

Use independently annotated source figures, units, signs, periods, acceptable rounding and citation spans. Judge claims blind to method. Compare identical retrieved bundles/drafts with verifier on/off in offline analysis; unchecked arm is never promoted as a live verified answer mode. Report total-query supported-answer accuracy, conditional accuracy at matched coverage, unsupported-claim rate, appropriate and inappropriate abstention, and reason breakdown. A verifier that abstains on every question does not pass utility acceptance. Test wrong cell/period, tampered source, amendments, parentheses/sign twice, scale conflicts, percentages, EPS exceptions, blank/dash, zero/negative denominator, decimal bounds, prompt injection and false citations. Deterministic fixtures are necessary but do not establish end-to-end answer quality.

# ACB root cause and targeted repair

Scope: exposed regression only; no new generalization claim. Base PR #26 SHA `3ba5e5e0f138fd2c1fd41c34c8b1262d74c308a9`. Original ACB PDF SHA256 `4279e4856d41db46abcffd38a7cbf4eaa299940dc2139625688d5ef14e46d61f`.

## Original source and pipeline diagnosis

- PDF page 8, TOTAL OWNERS’ EQUITY: curly possessive punctuation and owners-equity vocabulary were not consistently mapped to equity by the original English label path. Generic liabilities-and-equity must remain total funding rather than equity.
- PDF page 10: visual original says Profit, but custom font FEFC5DA6A43 native spans are `Pro` + U+0006 + `t before tax` (y463.1864–473.0084), and corresponding after-tax line y535.6875–545.5095. Checkpoints expose `Pro t`. See `ACB_NATIVE_FONT_AND_SOURCE_AUDIT.json` and source_images/ACB-p10.png. Original text, glyphs and source cells are unchanged.
- Query intent is normalized separately from source preservation. Only a constrained financial phrase admits the broken Pro-t candidate. NFKC ligatures and apostrophes are handled generically. Specialized attributable/minority/continuing/discontinued profit does not become total net income. Existing multi-metric intent retains all operands.
- Lexical FTS indexes the candidate label/context alongside unchanged body. Same Qdrant vectors and Nomic digest are reused; this is not a new dense model or vector retraining. Dense chunk retrieval alone does not repair a broken row label. Existing V3 evidence scorer still decides source matching/period/scope and numeric eligibility; repaired labels add relevant row candidates. No per-issuer/page/value/query-ID rule is present in runtime code.
- Regression includes SEM, Samsung, PNJ, HPG, BIDV, CEO, REE, FPT and existing SEC cases, plus synthetic possessive, specialized-profit and multi-operand counterexamples. No new source-specific rules were added.

## Same nine-document before/after

| Exposed case | Original PDF locator | Raw current amount | Before source R@5 / MRR@5 | After source R@5 / MRR@5 | Exact cell |
|---|---|---|---|---|---|
| v3r-acb-06 | p8 x396–459 y540–556 | 58,438,663 VND million | 0.0 / 0.000 | 1.0 / 0.333 | 1.0 |
| v3r-acb-07 | p10 x400–460 y463–478 | 17,114,208 VND million | 0.0 / 0.000 | 1.0 / 1.000 | 1.0 |
| v3r-acb-08 | p10 x401–460 y531–551 | 13,688,193 VND million | 0.0 / 0.000 | 1.0 / 1.000 | 0.0 old window; 1.0 corrected window |

ACB equity enters at rank 3, not rank 1. Before/after Top-10, source labels, boxes, metrics, conflicts, rank scores and provenance are retained in `BEFORE_178_RESULTS.json` and `AFTER_178_COMPATIBILITY_RESULTS.json`; API owner-scope outputs are in HUMAN_AUDIT_CASES.json. They are retrieval evidence, not independently approved answers.

## Annotation defect and development failures

The old v3r-acb-08 cell window y513–529 lies above actual net-income text. The additive SOURCE_ANNOTATION_CORRECTIONS.json records y531–551 from original source. Old qrels and scores remain unchanged; original exact-cell metric remains 0 for this case, while the separately named corrected metric is 1. Agent inspection is not human validation.

Initial AFTER_178_RESULTS.json lost SEM net-income and two multi-metric source cases. Raw-only aliases discarded an existing spatial label; query normalization overwrote multi-operand intent. The compatibility repair restores the existing spatial path and only fills absent intent. The failed run and PAIRED_REGRESSION_COMPARISON.json are preserved. Final same-scope comparison has no source Recall@5 loss; only the three targeted ACB source cases improve.

Residual regression: wrong classified metric at Top-1 rises from 1/117 to 4/120 (different classified denominators). PNJ net income, CEO net sales and REE investment-property now rank related chunks with another metric; specialized SEM continuing-operations pretax is deliberately not classified as total profit. These remain RELATED_PASSAGE, numeric_answer_eligible=false; no wrong verified claim. This is a documented ranking limitation, not an accuracy PASS. No claim of financial-answer certification.

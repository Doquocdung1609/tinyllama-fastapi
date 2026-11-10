# FIS V8.1 — root cause and repair

Baseline: Draft PR #35 at `0259fba44e8eb54daba775ee35194d7dd663e8c4`.

| Failure | Observed cause | Repair | Verification |
| --- | --- | --- | --- |
| F01 asks which issuer despite explicit HD focus | Entity mentions were treated alike; contextual COST/PG leaked into ambiguity | Source-bound task plan separates focus, comparison, context, exclusion and unselected names | React/API: HD only, 1/1, two verified cells |
| F02 loses operating income | Vietnamese metric recognizer omitted `lợi nhuận hoạt động`; orchestrator truncated metrics and `riêng từng chỉ tiêu` falsely requested parent-only scope | Added terminology, removed truncation, corrected scope parser, one task per metric | React/API: 3/3, six verified cells |
| F03 returns one English competition excerpt | Narrative path lacked independent topic obligations | Competition and cybersecurity tasks; separate authenticated excerpts and concise Vietnamese disclosure/interpretation distinction | React/API: 2/2, two source excerpts |
| F04/F05 source boundary | Requested AMZN/PEP filings absent from UI selection | Planner rejects focused unselected issuer before retrieval/calculation | Both 0 citations, 0 calculations |
| F06 returns administrative text | Margin had no per-issuer operand binding; generic fallback could answer with unrelated excerpts | Independent issuer-local margin tasks, matching CIK/filing/period/scope/unit and Decimal division | React/API: 3/3, six verified cells |
| Short affirmative/followup | Missing clarification slot was lost; issuer followup lacked prior SEC plan | Preserve pending slot and inherit previous numeric task only for a recognized short issuer followup | Unit tests plus live H07/T07; incompatible 13-week PG/COST abstains |
| Unseen Vietnamese paraphrases | Synonyms such as `thu nhập ròng`, `lãi hoạt động`, `biên hoạt động`, `nguy cơ` were not recognized | Added limited financial/risk aliases | Preserved first sealed results as failures; new round T01–T07 evaluated separately |
| Future-year margin | Margin generated a request using the selected filing date, ignoring an explicit year | Reject an unavailable requested year before cell lookup | H05/S05/T05 abstain, zero citations |

This is a bounded deterministic repair. It does not assert general financial question accuracy or change frozen research labels, gold, rankings, or source bytes. Source-cell verification is described in `source_cell_audit.json`.

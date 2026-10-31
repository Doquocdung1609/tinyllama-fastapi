# P5 — Independent evaluation status

**Status: BLOCKED for independent efficacy claims.** The six SEC questions in `../01_REPRODUCTION/PROVISIONAL_SOURCE_QRELS.jsonl` were prepared and inspected during development. Four positive row targets were then used for the structure intervention and ablation; all six are exposed. There is no independently human-reviewed gold set, no untouched issuer/document split, and no defended 200-question sample. Counts for the proposed 40/100/60 development/held-out/unseen partitions are **0/0/0 completed**, not zeros for system performance.

The original author's repository provides 25 queries with `relevant_terms` but no source-document IDs or independent relevance judgments. Its returned-result-based recall cannot substitute for gold. The two modern SEC filings used here do not equal the original 47-filing set. Earlier HPG, ACB, Apple, SEM and V3R3 owner examples are also exposed regression cases.

`ANNOTATION_TEMPLATE.jsonl` defines the fields required for a source-grounded human review. Before independent evaluation, a reviewer must inspect immutable source pages/rows, record period, scope, currency, scale and answerability, then freeze a new corpus/question manifest with issuer/document split and hashes. No held-out item should be used to tune a later run. If one is used to repair code, that item becomes exposed for the next generalization claim.

**Reportable now:** controlled, exposed known-target lookup on four machine-prepared SEC rows and conservative negative guards on two queries. **Not reportable:** independent Recall@k, nDCG, financial answer accuracy, OCR digit accuracy, confidence intervals, generalization to Vietnamese PDFs, or superiority over the original paper.

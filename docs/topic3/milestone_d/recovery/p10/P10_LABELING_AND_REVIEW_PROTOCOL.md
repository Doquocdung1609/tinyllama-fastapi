# P10 source-grounded labeling and review protocol

Status: **PROPOSED; no independent judgments yet**. There are zero human annotators. Automatically matching a row label is a development aid, not independently judged financial relevance.

For each frozen question, annotators inspect authenticated SEC bytes and canonical parent chunks without seeing arm rankings. They record every relevant parent and the precise SEC locator, issuer, accession, form, statement/table, row, column header, reporting-period kind and end, unit, scale, sign and any footnote or extraction warning. For a numerical question, record source cell IDs and the intended formula using Decimal. A parent is relevant only when it contains enough grounded evidence for the question; a related term or different comparative column alone is insufficient. Multiple parents may form one evidence group. Label `UNANSWERABLE` only after the defined corpus scope has been inspected and a reason recorded.

Two independent human reviewers and adjudication are preferred. If unavailable, record the actual number and identities/roles without inventing consensus; limit generalization claims. Store initial labels, disagreement, adjudicated labels and audit trail separately. Validate CIK, accession, raw hash and parent membership mechanically. Do not use LLM answers as ground truth.

Freeze qrels and all rationale/locator records by content hash before any final held-out run. Reviewers of held-out labels must not view held-out retrieval outputs until labels and the final strategy are frozen. The P10 development handshake has no qrels and is not scored as a quality evaluation.

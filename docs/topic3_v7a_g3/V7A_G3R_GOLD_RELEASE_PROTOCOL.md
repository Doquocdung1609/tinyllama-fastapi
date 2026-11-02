# G3R human gold release protocol

AI agreement is a review candidate, never human-certified gold. A human adjudicator opens the original SEC source and checks the frozen question, accession, statement scope, table, row, period and duration, exact column, original value, currency, multiplier, and locator. Multiple required cells must all be annotated; extra comparative periods must be labeled supplemental.

The coordinator queue starts with blank `human_decision`, `human_explanation`, `human_reviewer`, and `human_reviewed_utc` fields. A release script may include a row only when all four are provided by an authorized actual reviewer and the source URL is present. A second reviewer should check disputed terminology, negative findings and question errata. Preserve the completed queue as a new version with its own SHA-256; never edit the frozen AI submissions.

Allowed negative-question labels: `POSITIVE_SUPPORTED`, `NEGATIVE_SUPPORTED`, `UNSUPPORTED_REQUEST`, `AMBIGUOUS`, `SOURCE_INSUFFICIENT`. `NEGATIVE_SUPPORTED` requires inspection of the bounded relevant statement or disclosure and explicit scope. A keyword miss is insufficient. Missing evidence remains `SOURCE_INSUFFICIENT`. Ambiguous wording remains `AMBIGUOUS` until the benchmark policy resolves it.

If only a subset is approved, release its exact question IDs and approval records, report approved/94 coverage and how the subset was selected, and do not describe it as an unbiased full benchmark. Unjudged retrieval candidates remain unjudged, never automatic negatives. F10 Policy B still scores only original single-chunk retrieval; supplemental multi-chunk evidence can verify an answer but does not earn retrieval credit. No benchmark run or qrels expansion precedes the required review gates.

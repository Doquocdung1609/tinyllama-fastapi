# P11 owner decision memo

## Decision boundary

P11 supplies a new, issuer-disjoint SEC research acquisition and a development-only comparison protocol. It does **not** supply an independent final test of Hybrid superiority. P&G, Home Depot and Costco remain consumed development examples from earlier work; the historical C/D5 held-outs are excluded and unchanged.

The fixed nine-issuer plan acquired seven official primary filings. ORCL and DE exceeded the preregistered 6 MiB file limit, and no replacement was selected after seeing that outcome. The realized partitions are development MCD/CAT, validation SBUX/UPS/TXN and held-out raw-only AMGN/BKNG. The planned 3/3/3 corpus is incomplete. The held-out has no question bank, qrels, parsing, index or scoring, so a final evaluation is not authorized.

Ten positive development questions have provisional parent labels based on source inspection before ranking. Four adversarial scope questions have no qrel and must not be counted as retrieval negatives. No independent human relevance reviewer participated, and completeness of alternative relevant parents is unknown. Both indexed development filings have partial table extraction. A parent hit does not prove correct period, value or unit.

The isolated index and provisional B/D/F/A results are engineering evidence only. BM25 remains the accepted recommendation for the previously evaluated corpus. No production default or historical scientific result changes under P11. The next owner decision is whether to authorize a **new versioned source-selection protocol** for the over-budget filings and obtain source-grounded human label review before any validation finalist or held-out run. Do not retroactively alter this P11 selection or freeze.

The isolated MCD/CAT development generation is READY at 2,887 matching BM25/vector parents. On ten provisional labels, Recall@5 was B 0.30, D 0.10, fixed F 0.50 and exploratory A 0.40; details and per-query failures are in `P11_DEVELOPMENT_COMPARISON.md`. The result is label-dependent and too small for a scientific superiority claim. A was not selected. Source tampering in a cloned MCD file was refused, and the local full regression passed 587 tests with three expected skips.

P11's new Draft PR is for review only. No merge or activation is authorized here.

# P10 new evaluation source eligibility

Status: **PLANNED, not frozen or evaluated**. The C and D5 held-outs are consumed. PG, HD and COST in `p10_dataset_registry.json` are previously inspected development sources; their P10 handshake cannot establish out-of-sample retrieval quality.

Before acquisition, enumerate issuers used in C, D5 and D2–P9; exclude them from the new validation and held-out partitions. Select distinct issuers for development, validation and held-out before reading candidate financial rows. Record the selection rule, accession, form, full raw SEC SHA256, filing URL, reporting period and issuer fiscal calendar. Pin parser/chunker versions, source manifest, parent membership and one compatible vector generation. Do not substitute filings after viewing outcomes. No new SEC source was downloaded in P10.

For every source/question record the issuer CIK, accession, raw hash, form, exact question, eligible authenticated parent IDs, supporting structural locator, relevant column period and unit, judgment rationale, labeling method and review status. Empty fields mean **not yet sourced**, never a negative relevance judgment. Current validation and held-out arrays are empty. The final held-out remains uncreated and unexamined.

Target categories: exact metric, paraphrase, income statement, balance sheet, cash flow, EPS, segment, notes, comparative period, instant versus duration, ambiguous and unanswerable questions. Include wrong-issuer, wrong-period and cross-filing contradictions with source-grounded expected refusal. A feasible study needs verified source coverage for these categories; the current three 10-Q development filings are insufficient.

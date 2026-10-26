# P2 targeted defect ledger

| Issue | Reproduction | Expected / disposition |
|---|---|---|
| Weak real net-sales ranking | PG quarter-ended question; target parent `fin_d411...` ranked 28 of first 40 BM25 hits. D1 returned `NEEDS_CLARIFICATION` because column metadata incomplete. | Do not tune BM25 on the consumed D5 held-out. The source-bound P0/P3 probe names the parent explicitly; automatic QA remains blocked. |
| Contradictory CIK filter | Query CIK `0000080424`, explicit filter CIK `0000909832` returned `NEEDS_CLARIFICATION` / `ISSUER_CONFLICT`. Matching CIK returned `RESOLVED`. | Current PG scenario refuses conflict. Earlier D5 status discrepancy needs exact original reproducer before a code repair. |
| Segment row confusion | No new source-grounded adversarial case verified in this checkpoint. | NOT_TESTED; no ranking-policy change. |
| Column period uncertainty | D1 scope for PG quarter-ended 2026 returns `COLUMN_PERIOD_METADATA_INCOMPLETE`; source iXBRL context separately verifies two actual cells. | Preserve D1 uncertainty until a reviewed typed catalog adapter exists; do not mark the entire filing period-verified. |
| SEC link navigation | The SEC HTML was independently opened and its statement row read; URL and structural locator are recorded. Live browser navigation to the exact cell has not been verified. | PARTIAL. |
| Concurrent read/publication | No live publication test against owner data. | NOT_TESTED; isolated concurrency fixture required. |

No rank weights, defaults or D5 metrics were changed. The only implementation repair here is a new, opt-in authenticated cell derivation and explicitly scoped arithmetic path, with regression tests.

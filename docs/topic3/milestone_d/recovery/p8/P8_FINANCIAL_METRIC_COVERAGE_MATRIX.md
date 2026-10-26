# P8 metric coverage matrix

| Category | Current real automatic outcome | Boundary |
|---|---|---|
| Income statement, PG net sales | SUPPORTED | Exact `us-gaap:Revenues`, three-month duration, one verified parent |
| Income statement, HD net sales | UNSUPPORTED | Source uses `us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax`; fiscal quarter end is not a calendar month end, and repeated rows require additional context |
| Income statement, COST revenue | UNSUPPORTED | 12-week/36-week periods and ambiguous physical cells; no automatic substitution |
| Balance sheet, PG and HD total assets | SUPPORTED | Exact `us-gaap:Assets`, USD million scale, INSTANT dates, no segment context |
| Cash / operating cash flow | UNSUPPORTED | No source-backed P8 concept/period contract |
| Basic / diluted EPS | UNSUPPORTED | No per-share unit and distinct basic/diluted mapping contract |
| Segment values | UNSUPPORTED | P0 rejects XBRL segment contexts for this path |
| Carrying versus fair value | UNSUPPORTED | P7 valuation guard refuses it; no measurement-basis bridge |

`SUPPORTED` means a narrow source-authenticated operand/answer for listed real examples, not general company coverage. All other categories retain typed refusal.

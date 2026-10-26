# P8 multi-issuer real SEC evidence

Read-only source diagnostics inspected 41 indexed candidate rows from the three retained filing groups under manifest `86ad36365fbfb813e78e14246a48ae5735d7a8a1218f73daa4289caa98b215d0` and generation `8f0a7ba5ed851313a9948ddb465753c54012d94f9c36942239f7b2ec15b5e2fb`. Before P8, one parent produced authenticated cells; afterward three parents did. Exact cell records, XBRL concepts, periods, values, coordinates and locators are in `p8_source_cases_after.json`.

| Issuer / accession | Raw SHA256 | Supported real evidence |
|---|---|---|
| PG / `0000080424-26-000256` | `30904fac63dc81fec0a524c812bea5109521b9b8063f34adf13f3f50bd2a4b53` | NET SALES duration quarters 2026/2025: 23,276/22,386 USD millions; TOTAL ASSETS instants 2026-09-30/2026-06-30: 133,132/126,521 USD millions |
| HD / `0001628280-26-058715` | `3d638bc025ef9643317d539f63c3891c8db9b47e35a8edd8040928704d0703f1` | TOTAL ASSETS instants 2026-08-02/2026-02-01: 109,384/105,095 USD millions |
| COST / `0000909832-26-000051` | `8375d1545d28bee4225bb88cb490116ef8aab8de44c4ab8ad99f243c00d6d3c2` | No supported automatic numerical cell: ambiguous physical cells, extraction warnings and 12-week fiscal duration remain unresolved |

PG assets parent `fin_d672c7165a5bb6a66c21bc904d480810`, columns 16/22; HD assets parent `fin_9fadb8b8f3b78592782f972a63a9e7ed`, columns 4/10. Their source `us-gaap:Assets` facts are INSTANT values and are never substituted for duration revenue. This is development verification, not a new held-out accuracy study.

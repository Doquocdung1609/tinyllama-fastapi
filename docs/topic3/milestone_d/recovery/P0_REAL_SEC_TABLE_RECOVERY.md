# P0 real SEC table recovery

## Source and chain

The selected official P&G 10-Q is CIK `0000080424`, accession `0000080424-26-000256`, [SEC source](https://www.sec.gov/Archives/edgar/data/80424/000008042426000256/pg-20260930.htm), raw SHA256 `30904fac63dc81fec0a524c812bea5109521b9b8063f34adf13f3f50bd2a4b53` (1,066,740 bytes). Parent `fin_d411518414b61a2eb637d96721c5aaed` has payload hash `64425237b815fbed03bf90f756774f202479c8937a69d0b940b38ccabd184c34`; table `table_24f0cc566ca5c5871edfcdb7`. All identities are checked against the committed D3 registry and pinned lexical generation, then C `verified_source` rehashes/reparses/rechunks the complete source. A second accepted parse supplies the original physical cell coordinates. No accepted byte, chunk ID, parser output or parent hash is changed.

| Period | Physical cell | Header | Display | iXBRL | Effective value | Source locator |
|---|---|---|---:|---|---:|---|
| 2026-07-01–2026-09-30 | row 3, col 4 | Three Months Ended September 30 / 2026 | 23,276 | `us-gaap:Revenues`, context c-1, USD, scale 6 | 23,276,000,000 USD | `/document[1]/html[1]/body[1]/div[46]/table[1]/tr[4]/td[3]` |
| 2025-07-01–2025-09-30 | row 3, col 10 | Three Months Ended September 30 / 2025 | 22,386 | `us-gaap:Revenues`, context c-20, USD, scale 6 | 22,386,000,000 USD | `/document[1]/html[1]/body[1]/div[46]/table[1]/tr[4]/td[7]` |

Expected: accept only the physical `NET SALES` cells when header, context duration, CIK, fact concept, USD measure, sign and scale agree. Observed: two `VERIFIED_SOURCE_CELL` observations, with `FILING_PARTIAL_EXTRACTION_OUTSIDE_SELECTED_TABLE`. Global filing status is partial; selected table itself is `OK`. The warning remains visible. Unsupported mappings return no verified observation, not a guessed number. `tests/test_real_sec_recovery.py` covers unit/period derivation, entity/header mismatch and tampered fact attributes on synthetic input; the real probe records the actual SEC observations.

The adapter's 4 MB complete-source budget is separate from the unchanged D2 v1 250 KiB context cap. It builds a bounded iXBRL resource map and selects one parent/table row; it still incurs a full canonical parse plus one second parse. P&G/COST/HD research sources fit this new bound; the six retained WMT/NVDA D2 examples have not been recovered here. Coverage is **one income-statement family**, not six. Large sources, segment contexts, non-USD values, ambiguous fact mappings, incomplete headers and unsupported dates fail closed.

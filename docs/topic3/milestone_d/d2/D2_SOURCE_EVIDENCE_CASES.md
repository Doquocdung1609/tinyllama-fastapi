# D2 worked source evidence cases

All values, filing identities and HTML here are **synthetic development fixtures**, not NVIDIA/Walmart or actual SEC financial observations. No retained owner corpus was opened. Blueprint examples motivated the failure shapes only. Source URL is `https://example.invalid/synthetic`. Parent filing is synthetic `sec:0000000202:0000000202-25-000001`, filing date2026-03-01, report date2025-01-31; neither date supplies a missing cell period.

Ground truth is authored in `tests/fixtures/table_evidence/cases.json` before transformer implementation. Source construction is the literal HTML generated from each fixture by `scripts/benchmark_table_evidence.fixture`, using the unchanged accepted parser/chunker. Same construction is exercised by test helper `source` in `tests/test_table_evidence.py`. Row/column coordinates below are zero-based **physical cell origins in the accepted grid**; all six primary data rows are row1. Locators are exact `/document[1]/html[1]/body[1]/table[1]/tr[2]/td[N]` for these fixtures. Headers are source row0; parent locators identify the table plus row1.

| Family / fixture | Exact parent chunk | Source cells and raw values | Grounded header/period | Unit and basis | Expected |
|---|---|---|---|---|---|
| A Income | `fin_cc0b1639b3fbeff730b0da3b94afc090` | Net sales; (r1,c1)`100`, (r1,c2)`90` | Year ended Jan31 2025 /2024, each duration12 months | USD ×1000000; AMOUNT, consolidated label retained | VERIFIED_CONTEXT |
| B Balance | `fin_06ef382f80a1b4ea62a0a7adbf93f146` | Current liabilities; c1`(125.50)`, c2`90` | As of Jan31 2025 /2024, INSTANT | USD ×1000; AMOUNT; first Decimal−125.50 | VERIFIED_CONTEXT |
| C Cash flow | `fin_1a4e6e41955a29d37418e4e899d4e55d` | Consolidated net income; c1`25`, c2`20` | Year ended Jan31 2025 /2024 | USD ×1000000; raw reconciliation row remains net income, not operating-cash-flow subtotal | VERIFIED_CONTEXT |
| D EPS | `fin_5bd9b2eb226e7353ecd39e3ce393c3a1` | Basic EPS; c1`2.74`, c2`2.42` | Year ended Jan31 2025 /2024 | Explicit USD millions **except per-share** context plus EPS row → USD_PER_SHARE ×1, BASIC_EPS | VERIFIED_CONTEXT |
| E Segment | `fin_234251c704b85fed372daf3798145101` | Segment A operating income; c1`139`, c2`51`, c3`58%` | c1 FY2025; c2 USD change; c3 Percent change | c1/c2 USD ×1000000; c2 AMOUNT_CHANGE; c3 PERCENT ×1, PERCENT_CHANGE | PARTIAL_CONTEXT: c2/c3 have no typed observation period; never assigned FY2025 automatically |
| F Notes | `fin_ab360843df359dc7b6e21a3ccdcb7200` | Long-term debt; c1`38,166`, c2`36,777` | Both as of Jan31 2025; carrying/fair headers distinct | USD ×1000000; c1 CARRYING_VALUE, c2 FAIR_VALUE | VERIFIED_CONTEXT |

Every primary cell's exact parent payload hash is recorded in [measurements JSON](D2_REPRESENTATION_MEASUREMENTS.json). Raw cells and parent JSON remain intact. Header lists do not get sorted independently from values. These13 value cells comprise the primary representation denominator, including both unresolved change-column periods.

## Permanent counterexamples and structural cases

The dedicated suite also verifies:

- Reversed year order, three fiscal columns and repeated same-year labels retain distinct coordinates/IDs. `test_wrong_column_sorted_period_hazard` rejects100→2024/90→2025.
- A two-level merged header has source(r0,c1,colspan2) covering carrying/fair children(r1,c1)/(r1,c2); values remain at(r2,c1)/(r2,c2). No header-origin coordinate is synthesized from display order.
- A body value spanning two columns remains one physical cell with colspan2 and PARTIAL status; it is not duplicated into two period observations.
- FY versus calendar year, Q1-Q4, instant versus duration and January year-end remain distinct. Bare2025, invalid dates, FY1800 and Q5 syntax remain unresolved.
- Negative, Unicode minus, parentheses and exact long Decimal values retain signs/precision; inline minus and parentheses apply once. Opposing inline plus/display minus conflicts.
- USD-percent mixed text, conflicting USD/EUR context and incompatible dimension context conflict. Percent, percentage points, shares and EPS units retain their distinct multipliers.
- Inline scale/header mismatch, basic/diluted mismatch and carrying/fair tag/header mismatch flag conflicts; contextRef/unitRef resource definitions are not guessed.
- Blank, dash and N/A remain missing; scientific notation/malformed grouping/footnote-adjacent text are not partial numeric matches.
- Table footnote text/locations are retained, but a cell association is not invented. `100 *` stays unresolved rather than stripping a potentially meaningful reference.
- An immediate authenticated same-table row-group can expand one parent; budget1 suppresses it. Similar text in a different table/filing is not a relationship.

One accepted-parser limitation was exposed during fixture development: an all-text N/A/NaN row before any data may be treated as another header and produce no row chunk. Supplemental numeric-parser fixtures therefore include an explicit preceding numeric control row, keeping the original test cell unchanged and making its source row membership unambiguous. Accepted parser behavior was not changed or claimed complete. No assertions were weakened to force the target row into source evidence.

Three temporary runtime mutants were rejected by existing oracles: swapped header columns, EPS multiplied by one million, and removed parenthetical negative sign. These were monkeypatches in the test process, not production feature flags or committed mutations.

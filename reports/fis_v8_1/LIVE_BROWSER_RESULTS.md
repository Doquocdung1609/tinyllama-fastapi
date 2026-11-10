# Live React acceptance

Automated Chromium at 1440×900 used the real React frontend at `http://127.0.0.1:18110/app/`, authenticated through the local runtime, selected the four actual COST/HD/PG/MSFT filings in the source picker, entered the six exact disclosed questions, and inspected both request scope and rendered answers. Script: `frontend/fis_v8_1_live_smoke.cjs`; machine-readable results: `react_acceptance.json`. Page errors: zero.

| Case | HTTP | API status | Completed/required | Citations | Browser assessment |
| --- | ---: | --- | ---: | ---: | --- |
| F01 | 200 | SUPPORTED | 1/1 | 2 | PASS; HD only |
| F02 | 200 | SUPPORTED | 3/3 | 6 | PASS; three metric comparisons |
| F03 | 200 | SOURCE_EXCERPTS | 2/2 | 2 | PASS with source extraction warning |
| F04 | 200 | NEEDS_CLARIFICATION | 0/1 | 0 | PASS safe refusal |
| F05 | 200 | NEEDS_CLARIFICATION | 0/1 | 0 | PASS safe refusal |
| F06 | 200 | SUPPORTED | 3/3 | 6 | PASS; separate COST/HD/PG margins |

Actual screenshots: `F01-react.png`, `F03-react.png`, `F06-react.png`. Screenshots show the selected source chips and rendered chat response; they are not mockups. The browser script is repeatable against the documented runtime. Each browser request was asserted to carry exactly the four selected filing IDs.

The separate SEC source-view audit reopened 16 citations. It validated raw hashes, filing IDs, precise locators and every numeric source cell against the response; six Decimal calculations were recomputed. See `source_cell_audit.json`.

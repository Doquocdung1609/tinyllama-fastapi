# V8.1 paraphrase evaluation

The six disclosed F01–F06 prompts were development acceptance, not holdout. Eight H cases then exposed genuine failures: H02 missed `thu nhập ròng`, H03 missed `sức ép đối thủ`/`tấn công mạng`, H05 incorrectly answered a 2037 request from a 2026 filing, and H07b fell through to unrelated excerpts. The exact initial responses are preserved in `holdout_round1_initial.json`. Repairs were made; the H cases became regression probes.

A separately sealed S set (script SHA-256 `6203ebaf9b5e0a3728b7404a1449bf9b83924ac90aa327066b8a4fea1bc79f65`) exposed additional phrasing failures: S01 omitted the ratio, S02 omitted operating income, S03 and S06 fell to generic excerpts. The exact first responses remain in `holdout_round2_initial.json`. The same set was not claimed independent after terminology repairs.

The subsequent T set was written and SHA-256 locked (`d2c69f3258fbdc240ae6352f443f908c3d8667b0635acf692dd82072e0ef3a50`) before execution. No application code was changed after its run. Actual T results are in `holdout_round3_results.json`:

| Case | Scope tested | Status | Completeness | Citations | Assessment |
| --- | --- | --- | --- | ---: | --- |
| T01 | Microsoft focus and prior-quarter net income | SUPPORTED | 1/1 | 2 | PASS |
| T02 | Costco operating margin | SUPPORTED | 1/1 | 2 | PASS |
| T03 | Microsoft competition and cyber risk | SOURCE_EXCERPTS | 2/2 | 2 | PASS with partial-table warning |
| T04 | Excluded/unselected Amazon | NEEDS_CLARIFICATION | 0/1 | 0 | PASS abstention |
| T05 | Absent HD year 2039 | NEEDS_CLARIFICATION | 0/1 | 0 | PASS abstention |
| T06 | COST/PG independent margins | SUPPORTED | 2/2 | 4 | PASS |
| T07a | HD 13-week margin | SUPPORTED | 1/1 | 2 | PASS |
| T07b | Followup PG inherits unavailable 13-week duration | NEEDS_CLARIFICATION | 0/1 | 0 | PASS safe limitation |

This small independent set is a bounded product smoke, not statistical proof of broad Vietnamese financial-language accuracy. It uses the four available issuers; AMZN/PEP were deliberately absent. It does not grade unseen gold answers from the frozen research benchmark.

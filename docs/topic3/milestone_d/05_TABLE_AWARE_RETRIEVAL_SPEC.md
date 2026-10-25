# Table-aware evidence representation

**Design only.** This does not authorize re-ingestion, re-embedding or replacing C's index. Examples were read with Python SQLite `file:C:/msch/index/lexical.sqlite3?mode=ro`, URI mode, selecting existing `documents.payload,payload_hash`; no index engine/model was opened. Values describe retained snapshots, not a fresh SEC verification or new benchmark. These consumed issuers are suitable for development illustrations only.

## Existing versus proposed

C's `app/financial_ingestion/chunker.py` already emits one row per table chunk with expanded column/header context, caption/section, row group, units, source URL/structural row locator, footnotes and numeric cell attributes. Expanded colspan creates repeated header text. Some rows have inline numeric facts; others have only raw numeric strings. Filing status and per-table status differ. A D contribution cannot be “we introduced row chunks.”

Proposed `table-evidence-v1` preserves immutable raw chunk and a compact derivative: issuer/accession; section/caption; row label and ancestor group; distinct column header paths mapped to original cell coordinates; raw cell text; period/duration; value-role (amount/fair/carrying/change/percent/EPS); unit and multiplier; sign/parentheses; numeric attributes; footnote references; original continuation and source locations; extraction warnings. Repeated **identical semantic headers** may be displayed once, but coordinates remain lossless. Never deduplicate different periods merely because labels or values coincide.

Every view records parent chunk ID/payload SHA, parser/chunker identities, representation version and canonical view SHA. Raw values and normalized values coexist. No numeric value is inferred from a neighboring row. If table text conflicts with inline facts, flag the cell for review and block numerical answering rather than choose whichever produces a plausible answer.

## Worked source-grounded examples

Coordinates below are stored zero-based source row/column coordinates, not claims about visual spreadsheet numbering. `N` filing = `sec:0001045810:0001045810-26-000021`; `W` = `sec:0000104169:0000104169-26-000055`. Their document versions bind raw snapshot hashes `887d559e6180462ecfe36d4c7bba0d8f04a1f63deaaa743ab945edefd9d074bf` and `1c34c37ec615ea572ced3dd5e202b084057d262d55a779951cbfca9c3c25ed82`, parser `sec-html-v5`, chunker `financial-structure-v5`.

| Family / actual parent | Raw evidence retained | Proposed semantic view / caution |
|---|---|---|
| Income/operations, W `fin_19d2cfc014d0fa3de5de7388f8fc10a4` | “Consolidated Results of Operations”, Net sales, table `table_17ba60f65450c7dd97840b18`, row 3; fiscal years ended January 31, 2026/2025/2024: `706,413` / `674,538` / `642,637`; dollar amounts in millions | `{Net sales, consolidated, FY end Jan31, raw value, USD million}` per column. This available operations-summary row is not falsely relabeled the primary audited statement. Footnotes remain attached |
| Balance-sheet family, N `fin_5bfa952d62635c58a11a200e85a0e38e` | Note 9 — Balance Sheet Components, Finished goods, table `table_2f117e6fde9da94f4f08d2e4`, row 5; c3 `8,774` at Jan25 2026, c9 `3,273` at Jan26 2025; inline `scale=6,unitref=usd` | Instant balances, not annual revenue; preserve note context, USD ×10^6 and `InventoryFinishedGoodsNetOfReserves`. This is a balance-sheet component note, not a full balance-sheet coverage claim |
| Cash flow, W `fin_109254de42ad309951696ba81ea6dc04` | Consolidated Statements of Cash Flows, Consolidated net income, table `table_b8421643d1b99fd27e851778`, row 4; c7 `22,270`, c13 `20,157`, c19 `16,270`, FY2026/2025/2024; inline USD scale6 | Preserve statement role: net income reconciled in cash-flow statement, **not** “net cash from operations.” Same-looking net-income evidence elsewhere can support a different question |
| EPS, W `fin_cb5fd1b6ac172b0d600dd27213b06cfa` | Note 2 — Net Income Per Common Share, Basic, table `table_0289774539af35ad15d75d4b`, row14; c7 `2.74`, c13 `2.42`, c19 `1.92`, FY2026/2025/2024; `usdPerShare`, scale0 | Display “Basic EPS — USD/share”; do not multiply by a million because the table says amounts in millions **except per-share data**. Sorted reporting-period list is not a value-column mapping |
| Segment reporting, N `fin_16dad97ca625b02269e2de09fbd6b28c` | Operating Income by Reportable Segments, Total, table `table_5faec752188bf4656bec8e6f`, row7: c4 `139,297`, c10 `87,960`, c16 `51,337`, c21 `58`, c23 `%`; year-end Jan25 2026 / Jan26 2025, $ change / % change; no inline numeric facts | Keep Total + section, not a fabricated individual segment. Dollar-change and percentage columns are distinct. `58` is a displayed percentage, not another period amount. Empty numeric-facts array is not zero |
| Notes / measurement basis, W `fin_5effdf056e993e8bf68080bb9742de49` | Note 7 — Fair Value Measurements, long-term debt including current portion, table `table_afed7f5249ecc9f5ebb7526d`, row3: Jan31 2026 Carrying `38,166` c7 / Fair `36,777` c13; Jan31 2025 Carrying `35,999` c19 / Fair `33,790` c25 | Headers distinguish measurement basis. Existing inline attributes label all four `LongTermDebtFairValue`; do not let that repeated tag override carrying/fair headers. Flag semantic conflict for numerical verification |

Source URLs present in metadata/text:

- [NVIDIA retained filing](https://www.sec.gov/Archives/edgar/data/1045810/000104581026000021/nvda-20260125.htm).
- [Walmart retained filing](https://www.sec.gov/Archives/edgar/data/104169/000010416926000055/wmt-20260131.htm).

Example source paths: EPS table `/document[1]/html[1]/body[1]/ix:continuation[9]/ix:nonnumeric[1]/div[2]/table[1]`, source row14, value cell structural suffix `/tr[15]/td[4]`; segment table `/document[1]/html[1]/body[1]/div[625]/table[1]`, source row7. A URL without its row/header context is insufficient. No new browser claim about these pages is made here.

Read payload SHA256 cross-checks (SQLite canonical payload hashes):

| Parent suffix | SHA256 |
|---|---|
| `19d2cfc014d0fa3de5de7388f8fc10a4` | `06c7f7ef3d1b8cf35042a237e10f42d946865d6a21767facc649499c19254696` |
| `5bfa952d62635c58a11a200e85a0e38e` | `7b9a6347ba6182161b0f7fc29617541138d033e950838ac3fa6568772a574f5f` |
| `109254de42ad309951696ba81ea6dc04` | `b6871c9af11e9aa462343bb5297bfdf4e3ac85ef73909442b71eadb73bf4b097` |
| `cb5fd1b6ac172b0d600dd27213b06cfa` | `c56e55da6e20dfbd546507f08d0f9e7364b2523a6bb252788c2438866067a05d` |
| `16dad97ca625b02269e2de09fbd6b28c` | `c23086d18ff36c84112a785395cdb6b552cd9935c29facac9169bf2a056423d4` |
| `5effdf056e993e8bf68080bb9742de49` | `0f7607a13fd240d6fe241bdf010ca628af0feba8cbdd376800b02a5064b0826a` |

## Placement experiment and invariants

Initial D2: candidate-time compact views on existing C chunks, used for header/row-role matching and evidence display. This requires no new embeddings. A separate later experiment compares full C row embeddings versus compact row embeddings with the same model, query prefix, truncation budget, source membership and qrels; new representation generation mandatory. Table summaries or cell-level indexes are deferred because they multiply candidates/storage and complicate fair deduplication.

Expansion budget: at most one immediate preceding row-group label and one directly referenced footnote/continuation per selected row, at most 20 parent chunks in a 5-result bundle; unresolved cross-reference is a warning, not fabricated text. Expansion cannot cross issuer, accession, generation, period scope or unverified source boundary. Rank/count canonical parents, not each repeated view; separately report cell/operand coverage for multi-row questions.

Regression designs: lossless raw text/sign/parentheses; rowspan/colspan maps; percent cell separate from absolute change; basic vs diluted EPS unit exception; blank/dash not zero; negative inline sign vs display parentheses applied once; same label across tables; fiscal headers not paired by sorted year list; footnote and continuation; incomplete extraction; inline/header disagreement; incompatible view rejects vector reuse; source tamper invalidates derivative. Measure tokens/characters and required-cell position before/after truncation. Compactness alone is not evidence of better retrieval or correctness.

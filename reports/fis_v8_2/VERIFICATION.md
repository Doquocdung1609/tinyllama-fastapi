# V8.2 verification and runtime provenance

## Acceptance

| Case | Real 18110 result |
| --- | --- |
| A01 | PASS. 2,815 ÷ 70,527 = 3.99%; 2,815 ÷ 69,154 = 4.07%. All figures are in million USD. The second denominator is the separately tagged product-sales row, which excludes membership fees. |
| A02 | PASS. September 2025 uses 37,961 and 77,673. September 2024 uses 30,552 and 65,585. Both columns belong to 10-Q accession 0001193125-25-256321. The margins are 48.87% and 46.58%, a +2.29 percentage-point change. |
| A03 | PASS. The HD question returned 14.29% for 13 weeks. The P&G turn retained the same session and requested margin, overrode the duration to the shortest reported period, and returned 25.51% using 5,937 and 23,276 for the three months ending 2026-09-30. |
| A04 | PASS. All three topics were tracked. Three authenticated Microsoft passages cover security impact, competitive pressure and legal exposure. |

React carried all five filing IDs in A01–A04. The two A03 turns were in one session. F01–F06 were replayed with their original four-filing selection and passed, including the safe unselected-issuer cases. The prior F06 unit-language regression was fixed before the final browser run. [React log](browser.json) · [screenshots](screenshots)

The SEC viewer reopened 14 references from the four user scenarios and matched the filing ID, source SHA and generation. It reproduced 11 exact cell locators and three narrative passages. All seven Decimal calculation steps matched the independently recomputed results. Apple and BIDV numeric citations, multi-PDF retrieval and the existing two-generation PG comparison passed the browser controls. HPG inventory retained 24 pages, five passing reconciliation tasks and the existing partial income-reconciliation task. [Cell audit](source-cell-audit.json) · [PDF and SEC controls](pdf-controls.json) · [HPG control](hpg-control.json)

## Snapshot reconciliation

The primary API `http://127.0.0.1:18110` is served from `C:\Users\Admin\.codex\worktrees\topic3-v7p\tinyllama-fastapi\studio_workspace\react-product-20261028`. Its Microsoft raw SHA starts `1143bfbc`, byte length 5,597,567, generation `bfec66ac…`, status LEXICAL_READY. BM25 returned the source row Total revenue from this copy.

The alternate 18112 workspace has a separate acquisition with SHA `26f4b439…`, byte length 5,597,580, generation `6e153e6f…`, status READY. Each copy matched its own acquisition receipt. The four A02 operands used the primary copy only. The reason the downloaded bytes differ was not established by this audit. [Full provenance](provenance.json)

## Replay and limits

Use the existing studio launcher with workspace `studio_workspace/react-product-20261028` and port 18110. Run `node scripts/fis_v8_2_browser.cjs` with the local browser dependency and existing local API token. Use `FIS_V8_2_OUTPUT` to choose an output directory. To roll back, revert the V8.2 commit and restart this runtime.

Ratio support requires an authenticated source row and compatible denominators. A year-earlier comparison with missing columns can return a partial answer. Cross-filing ratio stitching, arbitrary formula inference and unstructured narrative coverage beyond supported or explicit topic lists remain limited. No unverified amount counts as a correct numeric answer.

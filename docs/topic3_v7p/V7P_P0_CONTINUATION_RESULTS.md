# Real application execution — P0 still NOT_PASSED

Source: `NASDAQ_AAPL_2025.pdf`, SHA256 `3eb270b22acb7d8d8e9c32a43dc221dec3345f8e4bca02755fdbc1ee16c823de`. Uploaded via the actual PdfWorkspace API into a new isolated research directory; processed with live Nomic embedding, no fake vector provider and no manually seeded facts. **READY, 80 pages, 451 chunks; ingestion 79.63 seconds**. No accepted SEC index was opened for mutation.

Actual backend requests/responses: `V7P_P0_REAL_BACKEND_RESPONSES.json`. Actual authenticated Uvicorn HTTP requests/responses: `V7P_P0_REAL_HTTP_RESPONSES.json` when present. The three acceptance requests still return SOURCE_EXCERPTS with empty numerical values and `TABLE_CONTEXT_INCOMPLETE`, reason `NATIVE_CELLS_REQUIRE_CURRENCY_FISCAL_AND_METRIC_BINDING`. FY2037 refuses with INSUFFICIENT_EVIDENCE; a Microsoft question with the Apple document returns QUERY_CONTEXT_CONFLICT before retrieval. Neither HTTP200 nor recovered table candidates are counted as a financial answer.

## Remaining blocking component

Geometry now recovers source rows/columns, but the automatic verifier still needs a trustworthy currency and fiscal-period binder, exact metric/qualifier selection, complete segment-set verification and a shared typed operand contract feeding Decimal calculation. The current PDF presents dollar signs and a millions scale; the adapter deliberately does not treat a dollar symbol alone as an authoritative USD identity. The full five-way explicit-setting matrix and normalized year/end-date compatibility are not implemented. Frontend auto/advanced serialization remains unchanged. P1 must wait for genuine P0 completion.

## Executed checks

- Focused adapter/context/assistant: 16 passed (before final company-conflict test).
- Intermediate full suite: 747 passed, one existing Starlette warning, 46.90 seconds.
- Final full suite after period/company safety repairs: **748 passed, 1 existing warning, 40.10 seconds**. Compileall and diff check passed.
- Real HTTP: all five requests HTTP200; three SOURCE_EXCERPTS, one INSUFFICIENT_EVIDENCE, one QUERY_CONTEXT_CONFLICT. None are counted as a supported numerical answer.
- React `npm run build`: passed.
- Frontend test on system Node22.13.1: worker startup failure in undici; no tests executed. Re-run with installed Node24.22.1: **1 file, 10 tests passed**, 3.76 seconds. No dependency assertions were weakened.
- Browser UI: NOT_TESTED. No new screenshots claimed.

This is an incomplete continuation on existing Draft PR35, not P0 acceptance. G2 was not scored; frozen scientific files and research algorithms remain outside the commit diff.

# Final A7 product revalidation

Extended result **V7P_LOCAL_SOURCE_VERIFICATION_COMPLETE_EXTERNAL_SEC_ACCESS_BLOCKED**. Original strict result **V7P_NOT_ACCEPTED**. Draft PR35 remains unmerged; only its existing branch changed.

Real HD source: issuer HOME DEPOT, INC.; form10-Q; accession0001628280-26-058715; Total assets109,384 million USD; INSTANT2026-08-02. Parent `fin_9fadb8b8f3b78592782f972a63a9e7ed`; table `table_483d3ac2b60916e1e4c8d837`; zero-based row14/column4; structural location `/document[1]/html[1]/body[1]/div[65]/table[1]/tr[15]/td[3]`. Logical grid column4 differs from physical td3 because source colspans are preserved, not invented.

Source hash `3d638bc025ef9643317d539f63c3891c8db9b47e35a8edd8040928704d0703f1`. Source includes comparison105,095 at February1,2026, shown with original adjacent rows/headers. Selected-cell evidence is verified by iXBRL Assets/c-3/USD/scale6 in the accepted adapter. The source has documented partial extraction outside the selected table, displayed as a warning; byte verification does not certify all tables.

Executed commands:

- `python -m compileall -q app scripts`.
- `python -m pytest -q tests/test_v7p_sec_viewer.py`:22 passed,1 existing Starlette warning.
- `python -m pytest -q`: 818 passed,0 failed/skipped,1 existing warning,43.43s.
- `python -m pytest -q -m "not integration"`:818 passed,1 same warning,58.80s.
- Installed Node24.22.1: `tsc -b`, `vite build`, `vitest run --config vitest.config.ts`:PASS;15 tests/3 files.
- Windows Prebuilt launcher18110 restart:2 existing PDFs and configured SEC remain READY; no rebuild.
- `python -m scripts.v7p_sec_viewer_http --sec-root <isolated SEC root> --vector-root <matching vectors>`:13 actual source/control/fault cases PASS, original source unchanged.
- `python -m scripts.v7p_sec_navigation_checks`:4 actual HTTP checks PASS: old reference after restart, baseline and V3 Search source resolution, additional PG source-cell view. PG NET SALES23,276 million USD for quarter ended2026-09-30 is additional development verification, not held-out evidence.
- `node frontend/v7p_sec_viewer_acceptance.cjs`: real Chromium147 local table, exact displayed cell/header/date, copy, back and mobile PASS; external URL correct but SEC content blocked.
- `python -m scripts.v7p_sec_html_safety`: real browser with controlled hostile source and actual endpoint;PASS, no active content/resources, tampered source hidden.
- `node frontend/v7p_pdf_post_a7.cjs`: all3 real Apple questions and actual PDF p32 highlights PASS; HPG unsupported numeric query safely refused.
- `git diff --check`:PASS.

Existing reports/fixtures supply full requests/responses; no response mocking in real HD/PG/Apple browser/HTTP controls. Synthetic safety fixtures are labeled separately. API uses local source bytes only, existing dependencies, no models/embeddings/index rebuild. Clone HTTP run copies62.65MB bounded by free-space guard; test data remains in isolated ignored tmp/topic3 namespaces. No peak-memory or retrieval quality result is invented.

Frozen audit:843 historical Git blobs unchanged; original A7 ledger remains unchanged; no PR36 source substitution, F10/PolicyB/G2/V6/author-result edits or sealed question execution. Runtime owner HD bytes still hash to the same registered source. Main and accepted base branches are not modified.

Inspect `V7P_REAL_SEC_VIEWER_HTTP_RESULTS.json`, `V7P_REAL_SEC_VIEWER_BROWSER_RESULTS.json`, `V7P_A7_ADDITIONAL_HTTP.json`, `V7P_SEC_HTML_SAFETY_BROWSER.json`, `V7P_A7_PDF_REGRESSION.json`, `V7P_A7_FREEZE_AUDIT.json` and `V7P_A7_ACCEPTANCE_LEDGER.json`. New screenshots: a7-local-hd-source-desktop/mobile, a7-official-sec-navigation, a7-synthetic-html-safety, a7-synthetic-tamper-refusal and a7-apple-pdf-regression.

Remaining limits: selected source must exist within pinned authenticated membership and size caps; derived context is bounded rather than a full original DOM; unsupported financial concepts/layouts refuse; HPG scan numerical mapping remains unsupported; new/rotated workspace keys require fresh references. Upstream acquisition/registry trust and local-machine protection remain dependencies. No external SEC access fix or original V7P_PRODUCT_ACCEPTED is asserted.


Review scope: existing Draft PR35, branch `codex/topic3-v7p-verified-financial-chatbot`; A7 start `9047888178ec67929b59f4577b832dd9ca6a5767`; implementation HEAD `dd6e1d08d8d2f225f16761347d551f3854c54ac9`. Same-system Codex review/test, not independent human adjudication. No merge, PR36 import, benchmark scoring, model downloads, source replacement or index rebuild. Final evidence commit/CI identity is recorded in PR35 checks and handoff.

Implementation-head CI: [core41482798805](https://github.com/Doquocdung1609/tinyllama-fastapi/actions/runs/41482798805), completed success on exact `dd6e1d08d8d2f225f16761347d551f3854c54ac9`. Final evidence-head CI is checked separately before handoff.

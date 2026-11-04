# Search & Chat V3 — real acceptance and handoff

## Result

71 real API cases:45 Search and26 Chat. Final outcomes:65 PASS,5 PARTIAL,0 FAIL,1 BLOCKED. Partial cases are unavailable FY2026 results, partial BIDV adjustment coverage, HPG OCR amount, unsupported FX, and an intentionally context-cleared source switch. SEC is BLOCKED. All16 supplied regression prompts are exercised, including the three-turn Services sequence and BIDV follow-ups.

These are source-checked development acceptance cases, not human gold or a locked holdout score. Expected financial cells were reopened from the unchanged PDFs and checked by independent source/Decimal validation. SHA evidence: SOURCE_INTEGRITY.json. No original PDF, research manifest/index, frozen benchmark or PR36 changed.

Python:880 full tests PASS (pytest-final.txt), with a dependency deprecation warning. React:36 tests PASS; production build PASS. Source/semantic targeted tests also pass. Build/unit tests are supporting evidence, not the acceptance basis.

## Actual browser evidence

`frontend/e2e/v3-product.mjs` uses real localhost API and installed Chromium through Playwright, without response mocking.56 checks PASS:27 Search submissions across all three PDFs and all four methods; Top5/10 plus FAITH-R Top20; unique input, no empty table/no missing-rank placeholder; source jump/return; BIDV handoff and1114; Apple regional correction, Services three-turn growth and tax explanation; HPG honest OCR warning; collapsible history, rename/reload, source-dialog Escape/focus, Enter/Shift+Enter, real offline/retry, cancelled waiting and durable server completion.

`v3-layout-check.mjs`:12 additional checks PASS on the final build. Desktop1366×768,1440×900,1920×1080, tablet768×1024 and mobile390×844; no page-level horizontal overflow. The125% check uses a rendering-equivalent1093×614 CSS viewport at DPR1.25, not a claim of changing native browser-chrome zoom. Legacy stored method preferences are migrated and then execute an actual FAITH-R query.

Screenshots:
- before-search-1366.png / after-search-1366.png; corresponding1440,1920,768,390 pairs.
- before-chat-1366.png / after-chat-1366.png; corresponding five-size pairs.
- after-chat-125pct-equivalent.png.
- search-bidv-page4.png, chat-bidv-page7.png, apple-greater-china-page25.png, apple-tax-explanation.png, hpg-ocr-limit.png.

Native PDF source highlights are real measured rectangles. HPG5 shows the OCR coordinate warning. No synthetic diagram or mockup is used as product evidence.

## Raw files and failures retained

- api-before.json / api-after.json: identical four requests, same source SHA, before/after.
- browser-before.json, browser-e2e.json, browser-final.log, layout-final.json.
- acceptance.json + frozen-smoke.json + COVERAGE_FINAL_PROBES.json + SEMANTIC_FINAL_CASES.json aggregate into FINAL_ACCEPTANCE.json, SEARCH_TOPK_MATRIX.csv and CHAT_SEMANTIC_COVERAGE.csv.
- attempt1.json/log and release.json/log retain genuine failures. They are not counted as final passes: region names mistaken for issuers; list period-type mismatch; source-scope phrasing; internal scope candidate limit; source-only native citation verification after an FX refusal.
- browser-attempt1: correct row but missing inherited year. browser-attempt2: offline mutation paused instead of producing an error. Both were repaired and rerun. The final browser run passes.
- EDGE_PROBES.json confirms authenticated native-cell handoff and rejects complete status for incomplete multi-year geography. COVERAGE_FINAL_PROBES.json confirms pure source explanation and honestly partial adjustment coverage through actual Chat.
- SESSION_RESTART_RESULT.json proves the final browser session payload stayed identical across an owned API restart.

## Top5 on the same BIDV PDF/question

Question: “Tìm dòng lợi nhuận sau thuế chưa phân phối năm 2024.” The actual request uses the natural spaced year in TOP5_BIDV_EXAMPLE.json/raw traces.

| Requested product mode | Executed retrieval/profile | Returned | Pages in order |
|---|---|---:|---|
| BM25 | bm25 / baseline |5 of5|7,4,8,5,5|
| Hybrid RRF | hybrid / baseline |5 of5|8,8,5,5,7|
| FAITH-R | hybrid / faith_r_product_v1 |2 of5|4,7|

FAITH-R considered29 candidates and filtered by metric/scope/table evidence. It did not add unrelated chunks. The two hits are source rows, not two automatically certified amounts. Exact metadata JSON is in TOP5_BIDV_EXAMPLE.json. Raw rank scores are not confidence probabilities. This is a small product-flow comparison, not a retrieval superiority or Recall/MRR/nDCG claim.

## Timing and resources

METRICS.json records actual sequential wall time; source/model caches are mixed and mostly warm.69 timed non-blocked rows are included; the untimed coverage-only repair and unavailable SEC are excluded. Median is about0.52s and p95 about4.51s for this mixed Search/Chat workload; max about4.78s. Do not compare this overall median with a different previous workload. api-before/api-after contain four genuinely identical paired requests and their measured times, with differing process/cache age; these are descriptive, not controlled speed claims. Native source checks and local embeddings use the existing8GB machine; no larger or paid model was added.

## Largest remaining limits

- HPG numeric OCR/quarter columns are not certified; source review remains required.
- SEC source/index is unavailable. No SEC functionality is presented as READY or PASS.

Other bounded-layout/semantic limits and the partial multi-year geography probe are documented in ROOT_CAUSE.md. There is no remaining FAIL among the71 main acceptance cases. Partial source capability is not hidden by the PASS count.

## Windows launch and three short demos

From PowerShell:

```powershell
Set-Location -LiteralPath 'C:\Users\Admin\.codex\worktrees\topic3-v7p\tinyllama-fastapi'
$env:PATH='C:\Users\Admin\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin;'+$env:PATH
npm run build --prefix frontend
.\scripts\run_financial_studio.ps1 -Mode Prebuilt -ApiPort 18110 -Workspace 'C:\Users\Admin\.codex\worktrees\topic3-v7p\tinyllama-fastapi\studio_workspace\react-product-20261028'
```

Open http://127.0.0.1:18110/app/ and refresh an already-open tab. Use the local startup key; it is not included in the repository or report.

1. Search→PDF: choose BIDV; ask the retained-earnings row question. Toggle BM25/Hybrid/FAITH-R and Top5/10/20. FAITH-R shows2 relevant rows; open page4, then return to the same results.
2. BIDV→calculation: choose “Hỏi về bằng chứng”; ask “Mức điều chỉnh của riêng ngân hàng và hợp nhất khác nhau bao nhiêu? Giải thích cách tính.” Result72012−70898=1114 triệu đồng, with native citations7/4 and expandable steps.
3. Apple→semantic: select Apple and ask the full Greater China question in DEMO_ANSWERS.md. Read the decline, both period values, absolute/percentage change, total-growth contrast and source explanation. Open the regional source at25 and total-sales source at32. Then test the false69377 proposal or the three-turn Services growth question.

Reproduce:

```powershell
$env:PYTHONIOENCODING='utf-8'
.venv\Scripts\python.exe -m pytest -q
npm run test --prefix frontend
.venv\Scripts\python.exe scripts/fis_search_chat_v3_e2e.py --name rerun
node frontend/e2e/v3-product.mjs
node frontend/e2e/v3-layout-check.mjs
.venv\Scripts\python.exe scripts/report_fis_search_chat_v3.py
```

The aggregator preserves the named acceptance/repair artifacts. Review a new rerun separately rather than silently replacing historical gold/results. E2E creates ordinary local demo sessions; it never deletes user history.

## Commit / rollback / CI

Exact pushed HEAD and PR35 CI status are reported in the handoff after push; PR35 remains Draft and unmerged. To identify locally: `git log -1 --format=%H`. Rollback by reviewing and reverting the V3 code commit, rebuilding React, and restarting only the startup script-owned API. Do not reset the worktree or replace source/research data. Session migration is additive and existing chats remain stored.

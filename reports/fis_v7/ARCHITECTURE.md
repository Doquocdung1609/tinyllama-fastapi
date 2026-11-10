# V7 architecture and replay

## Source-backed execution

1. Chat and FAITH-R Search receive the actual selected document IDs. The existing source digest and session fingerprint keep citations and conversation state within those sources.
2. A read-only native parser opens the original PDF and checks its digest. The parser groups positioned words, locates supported restatement labels and binds each numerical cell to a semantic header and independently reopened source rectangle. The result carries a local metric label, table and row IDs, basis, scope, date/year, currency, magnitude, raw marker and citation.
3. The question path binds source labels by exact normalized phrase, bounded word reordering and a small set of generic accounting aliases. It handles direct restatement amounts, changes, scope differences, source-defined ratios, correction of a proposed amount and page inventory. Rows and columns that cannot be bound are disclosed.
4. The two-issuer comparison path uses independently selected files and column metadata. Existing V3 geometrically bound candidates and existing human reviews retain their respective status. Monetary operands use Decimal. Unreviewed OCR participates only in separately labeled preliminary reconciliation and is excluded from certified values.
5. The React answer shows original and normalized amounts, dates, scopes and cell citations. The PDF viewer reuses its existing coordinate display.

The parser currently supports one native restatement table per upright page with supported scope, unit and time context. It handles reordered columns, some split headings, simple row wraps and strongly evidenced continuation. It does not replace the legacy comparative native table parser, recognize arbitrary scanned tables, or implement a model-based general task planner. Source identities outside supported aliases and unambiguous legal headings can require confirmation. The implementation is deliberately scoped to the observed faults and is not an independent proof of general financial QA.

## Replay

Use the repository virtual environment and the existing local API token. The BIDV/HPG demo used a distinct product workspace with both real PDFs and the preserved HPG V3 extraction. A copy of the existing human review remained human provenance. No automated run created or updated a review.

```powershell
.\scripts\run_financial_studio.ps1 -Mode Prebuilt -ApiPort 18114 -Workspace studio_workspace/fis-v7-acceptance -RuntimeName fis-v7-runtime
node scripts/fis_v7_browser.cjs
$env:SCORE_THRESHOLD='0.55'
$env:RUN_REAL_MEDIA_TESTS='0'
.venv\Scripts\python.exe -m pytest -q -m 'not integration'
Set-Location frontend
npx --yes --package=node@24 node node_modules/vitest/vitest.mjs run --config vitest.config.ts
npm run build
```

Set `FIS_V7_URL` and `FIS_V7_OUTPUT` to change browser target and artifact directory. The browser log is a subset of the request/response fields. It excludes the API token and full extracted PDF text. For rollback on the draft branch, revert the V7 code commit with Git and rebuild/restart against the original workspace. The source PDFs and extraction checkpoints require no rollback.

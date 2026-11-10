# FAITH-R Product — local execution evidence (2026-11-04, UTC+7)

This is a usable local PDF-chat increment on the existing PR35 worktree/branch. It does not certify universal financial accuracy or the PR36 research scorecard.

## Executed product behavior

- Shared `FINANCIAL_QUERY_UNDERSTANDING_V1` and `FAITH_R_PRODUCT_V1` serve Search AUTO and Chat. Baseline BM25, Dense, Hybrid RRF k=60 and legacy V3 remain independently runnable. The PDF adapter unions original retrieval with immutable page/table-row evidence, ranks metric/period/scope/basis, preserves distinct rows and traces the actual algorithm. No runtime BIDV page/value shortcuts.
- Q2/Q2b return retained-earnings rows on PDF pages 4 (SEPARATE) and 7 (CONSOLIDATED); no issuer/currency false refusal. Search and Chat citation IDs match.
- Original native PDF cells, their rectangles, ordered semantic headers, source date/unit/scope and arithmetic identity qualify the narrow adjustment-table verifier. Verified source values: page4 `34,164,156 + 70,898 = 34,235,054`; page7 `36,192,494 + 72,012 = 36,264,506`, million VND. Q3 follow-up computes `72,012 - 70,898 = 1,114 million VND` with both citations. Search returns the same numeric result on the resolved question.
- Q1 is explicitly a partial adjustment list, with per-row certification status. No claim of exhaustive enumeration.
- HPG scanned parent-company PDF stays source/OCR-qualified; numeric refusal keeps citations. Requesting consolidated scope produces clarification. Apple English/Vietnamese queries use real page32 source cells for supported values; summaries select actual source passages.
- Durable SQLite sessions have additive migration, stable IDs, message roles, timestamps, evidence IDs, owner scoping, list/search/pagination/reopen/rename/delete. Existing turn payloads are retained; source/metadata scope changes fork the session instead of erasing prior history. Conversation context is session/source-bound.
- React renders escaped text, safe headings/lists/tables and inline citation buttons; copy/retry/Enter/Shift+Enter/loading/cancel-wait are implemented. Stop cancels waiting, not the already running server job. Source requests run one at a time on this constrained machine.
- Browser clicked citations to pages4/7. Native highlights were checked at75/100/125/150% and rotation90; raw DOM coordinates are in browser-geometry.json. OCR geometry and missing coordinates are explicitly disclosed. Desktop1366x768 and mobile390px were inspected; mobile evidence is an open/close drawer, without a focus trap.

## Validation

- Full Python suite: 837 PASS, one existing Starlette deprecation warning (185.19s in the final run).
- Frontend: 32 PASS / 3 files; TypeScript and Vite production build PASS. Uses pre-existing bundled Node24.22.1 because system Node22 lacks the zstd API required by the installed jsdom/undici dependency. No dependency or model installation.
- `after.json`: 22 distinct real Chat requests, 25 paired retrieval requests over five identical question/source pairs (BM25/Dense/Hybrid/V3/FAITH-R). Observed Chat request median2184.255ms, range37.58–10142.65ms; this is this local run, not a population benchmark.
- On BIDV Q2/Q2b: V3 top pages8/5, FAITH-R top pages4/7. Page correctness is source-verified for these rows; no fabricated aggregate accuracy score for other queries.
- Seven independent source-safety probes rejected changed digits, wrong row/scope/period, unrelated inherited heading, OCR certification and unsupported currency.
- `final-smoke.json` and `restart-check.json`: real API restart preserved the saved two-turn/four-message session; final Q2 source rows and shared numeric parity passed. Final Q2 API RSS snapshot157,765,632bytes for the server, plus843,776bytes launcher; this is not peak memory.
- SHA256 of all three original PDFs unchanged. No upload/reindex/re-embedding/research-data changes. The two pre-existing modified research files remain outside this commit.

## Explicit limits

- SEC is UNAVAILABLE in this demo workspace: no compatible configured snapshot/vector roots. A read-only port of PR36 A5 ontology/features ranks the separate product SEC candidate pool when configured; the existing source-first HTML/iXBRL answerer remains the numeric verifier. Full A5 CLI/index equivalence and live SEC numerical operation are not claimed. No research indexes were transplanted.
- Optional `FIS_NARRATIVE_MODEL` enables local Ollama exact-quote selection only. Unknown citations, altered numbers/text, invalid output or model failure fall back to deterministic source excerpts. The demo used extractive mode; unrestricted generative financial prose is not enabled or claimed.
- Native adjustment certification supports the documented three-column layout; ambiguous layouts and OCR values remain unverified. The initial before-UI screenshot was not captured; before-fix HTTP responses are retained in before.json.
- Local bearer authentication represents a single authorized workspace; it is not a multi-user account system. Thread ownership is scoped within that workspace.

## Restart / reproduce

From `C:/Users/Admin/.codex/worktrees/topic3-v7p/tinyllama-fastapi`:

```powershell
.\scripts\run_financial_studio.ps1 -Mode Prebuilt -ApiPort 18110 -Workspace 'C:\Users\Admin\.codex\worktrees\topic3-v7p\tinyllama-fastapi\studio_workspace\react-product-20261028'
.venv\Scripts\python.exe scripts/faith_r_product_acceptance.py --paired
```

Open http://127.0.0.1:18110/app/. Use the existing local token file (never publish it). Select BIDV, start a new chat, ask Q2b, click [1]/[2], return and ask Q3. The named browser-demo session `BIDV · Điều chỉnh FY2024` also remains available in the session search.

To stop the script-managed API, run `.\scripts\run_financial_studio.ps1 -Stop`. Rebuild frontend from source before Prebuilt startup when transferring the commit to a different checkout. Keep PR35 Draft/open/unmerged; no force push.

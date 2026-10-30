# V3R3 release candidate

**Decision: `SEARCH_V3R3_PARTIAL`.** The isolated owner clone and Prebuilt application work when the resource gate admits queries. The minimum observed free RAM of 16.59 MiB and repeat browser deferral after restart prevent an unconditional demo-ready recommendation on this laptop. The owner review workbook remains `HUMAN_AUDIT_PENDING`; no `SEARCH_LOCKED` claim is made.

Launch from repository root:

```powershell
.\scripts\run_financial_studio.ps1 -Mode Prebuilt -Workspace 'C:\Users\Admin\Documents\GitHub\tinyllama-fastapi\studio_workspace\search-v3r3-owner-20261030'
.\.venv\Scripts\python.exe scripts/preflight_search_v3r3.py --workspace studio_workspace/search-v3r3-owner-20261030
```

Open `http://127.0.0.1:8110/app/` when preflight reports READY. The local access token stays in `tmp/studio-runtime/access-token.txt` and is never included in reports. Stop only this managed session with `.\scripts\run_financial_studio.ps1 -Stop`. The original V3R2 workspace, nine PDF source bytes, model files and old results remain rollback points.

The candidate contains one scanned SEM PDF and native/mixed PDFs, verified CEO source row/highlight, PNJ and ACB source examples, an unreviewed SEM raw OCR candidate, a negative query that abstains, and a same-document BM25/Dense/Hybrid comparison. `LIVE_BASELINE_COMPARISON.json` records five hits in each arm with the identical CEO document/query; the candidate result is reported separately. The 13 browser screenshots are in `screenshots/`. A direct post-restart query still returned the reviewed assets row on page 2. The workbook's 26 decisions and seven SEM exact values need independent owner review.

Local regression: backend **709 PASS, one existing Starlette/httpx deprecation warning**; frontend **10 PASS**; Vite build **PASS**; targeted precision tests **38 PASS**. Live browser first batch **4 PASS, 1 resource FAIL**; replay of the failed scenario **PASS**; post-restart browser replay **resource FAIL**. All 178 exposed benchmark queries executed, but second prewarm **LOW_MEMORY_DEFERRED**. No independent new heldout was available. Remote CI must be read from the Draft PR check status; local PASS does not imply CI PASS.

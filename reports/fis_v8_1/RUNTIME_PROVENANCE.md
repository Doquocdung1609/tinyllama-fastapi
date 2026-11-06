# Runtime and regression provenance

- Branch: `codex/topic3-v7p-verified-financial-chatbot`, Draft PR #35, based on `0259fba44e8eb54daba775ee35194d7dd663e8c4`. Final commit is recorded in the PR and final handoff.
- Code worktree: `C:\Users\Admin\.codex\worktrees\topic3-v7p\tinyllama-fastapi`.
- User's primary workspace: `C:\Users\Admin\Documents\GitHub\tinyllama-fastapi\studio_workspace\react-product-20261028`.
- Runtime: Prebuilt FastAPI/React, API port 18110, `/app/`; launched from the PR #35 worktree after the final application changes. The runtime uses the existing SEC source and vector roots under the main checkout's `tmp/studio-runtime/sec` and preserves all owner documents and index generations.
- Existing primary PDF documents observed READY: BIDV 2024 correction, 8 pages/23 chunks; HPG Q4/2025, 24 pages/64 chunks. Apple PDF was not present in this primary workspace and was not reimported. Its existing fixture/regression coverage passed, but a fresh Apple browser run on this workspace is not claimed.
- COST and MSFT official SEC HTML were newly acquired with a contactable User-Agent and imported as separate lexical-ready user-library generations. HD and PG existing generations were reused. No frozen research corpus, F10, G2, PR #34/#35 history or model ranking was changed.

Verification on the final source tree:

- Python: `python -m pytest tests -q` → **948 passed, 2 warnings** in 35.56 s. Warnings: Starlette `httpx` TestClient deprecation and FastAPI `on_event` deprecation. No failed/skipped tests in this run.
- Frontend: `npm test -- --run` → **4 files, 37 tests passed**.
- Frontend: `npm run build` → **PASS**, TypeScript and Vite production build.
- React six-case smoke → **6/6 browser flows PASS**, zero page errors.
- Live SEC evidence endpoint → **16/16 references resolved**, 14 numeric source views fully verified; two narrative views carried explicit `PARTIAL_TABLE_EXTRACTION` warning. Six calculations passed independent Decimal recomputation.

Launch after setting the documented SEC source/vector environment variables to their existing local directories:

```powershell
& .\scripts\run_financial_studio.ps1 -Mode Prebuilt -Workspace 'C:\Users\Admin\Documents\GitHub\tinyllama-fastapi\studio_workspace\react-product-20261028' -ApiPort 18110
```

To stop only this script-owned runtime: `& .\scripts\run_financial_studio.ps1 -Stop`. The local access token is deliberately omitted from reports.

Limits: live PDF Apple/BIDV/HPG business-answer regression was not repeated here; the full automated suite and READY state are the evidence reported. The two narrative excerpts do not erase whole-filing partial-extraction status. The T-set holdout is small, and an unrecognized new paraphrase may still require clarification.

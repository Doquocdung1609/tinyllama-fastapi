# Regression, resources and security

Commands on Windows/Python3.13.2:

- `.venv/Scripts/python -m compileall -q app scripts`: PASS.
- `.venv/Scripts/python -m pytest -q`: 796 passed, 0 failed/skipped, 1 existing StarletteDeprecationWarning; latest full run41.66s on final repair code.
- `.venv/Scripts/python -m pytest -q -m "not integration"`: 796 passed, 1 same warning;63.99s on final repair code.
- Focused source/metadata/company/math tests48 cases (29 native operand tests); full suite includes all permanent regressions.
- Installed Node24.22.1: TypeScript `tsc -b`, Vite build PASS; Vitest12 passed/2 files. System Node22 worker incompatibility is documented, not counted as a test skip.
- `git diff --check`: PASS (LF/CRLF informational warnings only).
- Authenticated HTTP27 + source-derived negatives3; Chromium real E2E PASS except external SEC content denied, accurately separate.

Initial implementation CI: GitHub core run41451182240, success, exact f86e2daf415689120f4fbf32c63c83eddce4ad21. Final report/evidence commit CI must separately be checked; see PR checks/final response.

Performance `V7P_RESTART_PERFORMANCE_HTTP.json`: first after API restart14689.16ms; subsequent n4 median2353.525ms/p95 nearest-rank4269.36ms for same real Apple exact question. Not a research benchmark and n4 cannot characterize population tails. Model/OS caches retained. Full source hashing only n10 median4.331ms/max4.571ms, excludes parsing/complete provenance. API Python RSS snapshot307666944bytes (~293MiB), not measured peak. RAM total8419053568bytes; available1247772672; free disk8526274560 at sample. No peak-memory/stage parsing timing claim. HPG OCR+embedding138.51s measured separately.

Security: protected documents/chat/upload/search/files use existing bearer dependency. Missing token rejected401, empty doc list422, bad PDF422, source-byte tamper409 with no claim, mismatched issuer/context refuses. Query/document/session IDs bounded; no token in bundle/screenshots/artifacts. Per-request full source rehash precedes immutable source-keyed context cache. Parser/table/source size budgets retained. Tesseract standard installed path reused, no model/package downloads. Old manually reviewed facts require non-destructive table-scope re-review. Actual PDF bytes/current database/index consistency remain mandatory.


Code reviewed/tested: `3e85fdba74737f5a94f555424d283126fe84dc0e`. Starting work-order HEAD: `f3c3fc320d957a4be418054e179e18800f49e5cf`; PR34 base: `cd8deb96cb8c147ca5c090e9c0a323de511c65bd`. Existing Draft [PR35](https://github.com/Doquocdung1609/tinyllama-fastapi/pull/35), branch `codex/topic3-v7p-verified-financial-chatbot`. Same-system Codex adversarial pass, not independent human review. No merge or new PR. Final documentation commit identity is available from Git/PR; this report does not invent a self-referential SHA.

## Final adversarial semantic closure

On the initial implementation, tests reproduced a requested EUR currency being ignored and bare revenue being treated as net sales. The repair refuses unsupported conversion/scale/percentage-point requests and non-equivalent generic metric labels. Segment extrema now require the net-sales metric rather than silently substituting it for segment net income. Explicit restatement basis conflicts are blocked. Permanent tests and real HTTP negatives pass. These fixes narrow claims; they do not introduce FX conversion, restatement synthesis or ranking tuning. Latest focused48/full796/non-integration796 all pass.

Repair code CI41452440427 completed success on `3e85fdba74737f5a94f555424d283126fe84dc0e`. Supplemental actual drag/drop/remove/filechooser PASS in `V7P_UPLOAD_INTERACTIONS.json`.

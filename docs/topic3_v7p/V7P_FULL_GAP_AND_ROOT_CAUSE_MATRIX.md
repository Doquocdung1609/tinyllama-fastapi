# Gap and root-cause closure

| Milestone | Previous gap | Implementation and evidence |
|---|---|---|
| M0 | Partial checkpoint, owner work and frozen data | Fast-forwarded documentation-only owner commit; isolated existing V7P worktree; 843 historical Git blobs unchanged, `V7P_FREEZE_BLOB_AUDIT.json` |
| M1 | Native cells ineligible; raw dollar sign/FY insufficient | `verified_financial.py`: exact rows, same-source currency proof, explicit fiscal declarations, annual headers/end dates, local heading scope, complete segment set; shared `financial_math.py`; real Apple 3/3 |
| M2 | Required metadata busywork; selected file/status unclear | `document_metadata.py`, `DocumentMetadataPanel.tsx`, zero-metadata upload, immutable bytes, timestamped corrections, duplicate SHA feedback, READY/restart evidence |
| M3 | Search and assistant disagree; misleading AUTO | Shared `unified_search`, `automatic_answer`, postcondition validator, actual effective profile/mode/reason; Search financial_evidence equals Chat contract |
| M4 | Separate workflows, stale issuer/period | `FinancialChat.tsx`, `/studio/chat`, source/revision fingerprint, bounded sessions/history, 2024 follow-up and comparison; original SEC/manual/research tools remain advanced |
| M5 | Competing controls; unreadable evidence | Basic chat default; advanced filters opt-in; viewer row/cell/header boxes and correct p32; Research Lab comparison; real screenshots |
| M6 | Windows invalid PDF file lock, untyped source tamper error | Byte-backed metadata parsing and 422 cleanup; 409 hash mismatch on chat/metadata; per-request source check; installed Tesseract autodetection; offline transport/restart tests |
| M7 | Unit-only claims | 23 real HTTP cases + 3 source-derived HTTP negatives; actual Chromium, HPG OCR/indexing, frontend/full regressions; external SEC browser content remains BLOCKED |

Additional adversarial corrections: malformed explicit period is rejected, reversed comparison is not silently reordered, current filing year cannot exclude prior-year verified columns, display metadata does not authenticate issuer, incomplete segment set/duplicate conflicting values refuse. No numeric answer is chosen by matching an expected financial value. Numerical expected values appear in tests and evidence only.

Two previous mocks claimed SUPPORTED without hash/locator/citations. Their assertions now require fail-closed rejection while preserving plan-routing assertions. This strengthens the contract; tests were not disabled. Original checkpoint report preserved verbatim in `V7P_PRE_COMPLETION_ACCEPTANCE_CHECKPOINT.md`.


Code reviewed/tested: `3e85fdba74737f5a94f555424d283126fe84dc0e`. Starting work-order HEAD: `f3c3fc320d957a4be418054e179e18800f49e5cf`; PR34 base: `cd8deb96cb8c147ca5c090e9c0a323de511c65bd`. Existing Draft [PR35](https://github.com/Doquocdung1609/tinyllama-fastapi/pull/35), branch `codex/topic3-v7p-verified-financial-chatbot`. Same-system Codex adversarial pass, not independent human review. No merge or new PR. Final documentation commit identity is available from Git/PR; this report does not invent a self-referential SHA.

## Final adversarial semantic closure

On the initial implementation, tests reproduced a requested EUR currency being ignored and bare revenue being treated as net sales. The repair refuses unsupported conversion/scale/percentage-point requests and non-equivalent generic metric labels. Segment extrema now require the net-sales metric rather than silently substituting it for segment net income. Explicit restatement basis conflicts are blocked. Permanent tests and real HTTP negatives pass. These fixes narrow claims; they do not introduce FX conversion, restatement synthesis or ranking tuning. Latest focused48/full796/non-integration796 all pass.

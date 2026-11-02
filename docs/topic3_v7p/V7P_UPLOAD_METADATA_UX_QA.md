# Upload and metadata QA

Real Apple PDF: 80 pages/451 chunks READY, no entered metadata and zero manual financial facts. HPG scanned PDF: 24 pages/64 chunks READY in 138.51s with installed Tesseract vie+eng and live Nomic; `V7P_NONAPPLE_HTTP.json` records actual upload/extract/embed transitions. READY means indexes complete, not verified financial values. HPG automatic issuer/period remains UNKNOWN instead of guessing from filename; numerical query safely refuses.

Browser checks selected filename before upload, optional metadata section, duplicate SHA handling, READY after reload, source snippets/status and an explicit Apple Inc. display correction persisted after reload. Repeat browser runs encounter an already indexed duplicate; screenshots accurately show that state. They do not represent a second full indexing run. HPG first ingestion is separately measured over actual HTTP.

Metadata fields AUTO_CONFIRMED/NEEDS_REVIEW/UNKNOWN/CONFLICTING_METADATA have source page/snippet/method. Corrections have timestamp/revision and remain distinct from original fields. A corrected display issuer never authorizes a different company's answer. Source hash and bytes unchanged. Source/revision changes invalidate backend conversational context; browser source-switch discards stale turns/responses. Manual metadata and old advanced tools remain available.

Malformed PDF -> 422 and no new database record/file; repeated regression protects Windows file-handle cleanup. 20MiB upload limit preserved; no automatic model downloads. Restart retained two READY PDFs, corrections, source IDs and indexes without full rebuild. Only newly generated negative test documents were deleted through exact-ID-confirmed API removal.


Code reviewed/tested: `3e85fdba74737f5a94f555424d283126fe84dc0e`. Starting work-order HEAD: `f3c3fc320d957a4be418054e179e18800f49e5cf`; PR34 base: `cd8deb96cb8c147ca5c090e9c0a323de511c65bd`. Existing Draft [PR35](https://github.com/Doquocdung1609/tinyllama-fastapi/pull/35), branch `codex/topic3-v7p-verified-financial-chatbot`. Same-system Codex adversarial pass, not independent human review. No merge or new PR. Final documentation commit identity is available from Git/PR; this report does not invent a self-referential SHA.

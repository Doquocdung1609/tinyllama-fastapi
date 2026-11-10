# Windows local run

```powershell
git fetch origin
git checkout codex/topic3-v7p-verified-financial-chatbot
# Use the documented installed Python dependencies and Node24 for this checkout.
# First build if no prebuilt frontend exists:
cd frontend
npm ci
npm run build
cd ..
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_financial_studio.ps1 -Mode Prebuilt
```

Open the printed `/app/` URL. The launcher stores a local key at tmp/studio-runtime/access-token.txt; enter it in the login form, never commit/share it. Default API port8110 (acceptance used18110). Existing Nomic digest/768 dimensions is required for new Dense indexing; no automatic model download. Installed Tesseract vie+eng is needed for scanned PDFs; launcher reuses its standard Windows location. Use a separate workspace with `-Workspace` if needed. Stop only launcher-owned processes with the same script `-Stop`.

Upload the owner's Apple annual report in Kho tài liệu without filling metadata; wait READY, then select it in Trợ lý tài chính. Ask the three questions recorded in V7P_REAL_APPLE_3_CASES_E2E.json. Follow with `Còn năm 2024?`, inspect formulas and click source. Uploaded PDFs are local user-owned sources, not assumed official SEC snapshots. HPG scanned data can be searched; unsupported numeric extraction remains refused.

SEC requires the separately verified existing research roots (`STUDIO_SEC_RESEARCH_ROOT`, `STUDIO_SEC_VECTOR_ROOT`, `TOPIC3_RESEARCH_ROOT`); no new SEC download is implied. Without those snapshots SEC is unavailable while uploaded-PDF workflow remains separate. Official SEC website may deny automated browser access. Do not share local token or source files with private content.


Code reviewed/tested: `3e85fdba74737f5a94f555424d283126fe84dc0e`. Starting work-order HEAD: `f3c3fc320d957a4be418054e179e18800f49e5cf`; PR34 base: `cd8deb96cb8c147ca5c090e9c0a323de511c65bd`. Existing Draft [PR35](https://github.com/Doquocdung1609/tinyllama-fastapi/pull/35), branch `codex/topic3-v7p-verified-financial-chatbot`. Same-system Codex adversarial pass, not independent human review. No merge or new PR. Final documentation commit identity is available from Git/PR; this report does not invent a self-referential SHA.

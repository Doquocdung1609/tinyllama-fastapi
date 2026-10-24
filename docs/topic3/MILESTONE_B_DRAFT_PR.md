Financial row chunks now retain statement titles, multi-row period headers, units/scale, source-backed continuation context and footnote locators. Inline text order and redirects are handled safely; derived snapshots are versioned and provenance verifies complete chunk context. The final gap audit adds a read-only quality diagnostic while preserving conservative document status. This audit does not change parser/chunker output or manifest schema and introduces no retrieval architecture.

**Recommendation: VERIFIED_WITH_DOCUMENTED_LIMITATIONS, subject to owner acceptance.** Whole Apple filing remains PARTIAL_EXTRACTION; financial completeness is not inferred automatically.

| Apple table (zero-based) | Classification | Effect |
|---|---|---|
| 5 | LEGAL_OR_ADMINISTRATIVE | State/tax ID/address; no financial amount lost; typed fields not normalized |
| 9 | LEGAL_OR_ADMINISTRATIVE | Filer checkbox declarations; raw/cell labels preserved |
| 11 | DOCUMENT_LAYOUT | Contents/navigation page references, not monetary values |
| 38 | LEGAL_OR_ADMINISTRATIVE | Exhibit/certification index; headers recoverable in source |

Manual decisions are pinned to exact raw hash and locators; no automatic reclassification or READY override. Existing Apple evidence remains: 40 tables / 4,762 cells, 28 financial-context cases, 566 stable chunks and 12 VERIFIED provenance samples.

Real Tesla 10-K/A `0001104659-26-053166` is linked to original 10-K `0001628280-26-003952`. SEC explanatory note explicitly confirms the original. Separate raw snapshots/filings, original manifest preservation, two-document manifest and repeated ingestion checks pass. 10-Q/A remains fixture-only.

Historical files and manifest paths persist; active registry/evidence API does not resolve arbitrary old derived chunk IDs. This is documented interface scope, with a controlled preservation/404 test. General-chat financial confusion is reproducible only with the application wrapper in the two-prompt comparison; no retrieval/source context is involved. No advisory-accuracy claim or prompt expansion.

Regression: **147 passed, 0 failed, 0 skipped, 2 warnings**, with real OCR/Tiny-SD/SAPI/FFmpeg. Targeted: 31 passed / 1 warning. Live legacy Chat/RAG: 5 checks pass. Quality API, health/docs and Streamlit health return 200.

See docs/topic3/MILESTONE_B_FINAL_GAP_AUDIT.md for exact source locators, hashes, failure analysis, commands and limits. Existing commits/evidence preserved. Target remains unmerged Milestone B branch to avoid mixing A/B into main. **Draft; do not merge. No Milestone C.**

## Updated verification gates

| Gate | Audit finding | Evidence / limitation |
|---|---|---|
| B1 Baseline/PR | VERIFIED | 058b33e verified before work; same contributor branch and Draft PR #7 |
| B2 Environment | VERIFIED | Existing working environment, pip check clean; versions remain documented |
| B3 LLM function | VERIFIED_WITH_DOCUMENTED_LIMITATIONS | Real generation works; ungrounded financial Chat error reproduced |
| B4 Embeddings | VERIFIED | Real 768-dimensional embedding / isolated Qdrant compatibility retained |
| B5 API/Streamlit | VERIFIED | HTTP 200 health/docs/UI; new read-only quality endpoint tested |
| B6 Legacy RAG | VERIFIED | Real PDF→embedding→Qdrant→answer with correct file/page, 5 checks pass |
| B7 SEC | VERIFIED | Fresh Apple HTTP 200/hash match; Tesla original+amendment HTTP 200 |
| B8 Financial table context | VERIFIED_WITH_DOCUMENTED_LIMITATIONS | 28 source value/period/unit cases pass; 4 unresolved tables manually shown outside quantitative financial-table scope; whole filing remains PARTIAL |
| B9 Provenance | VERIFIED | 12 Apple samples rechecked; raw/normalized/context tamper regression passes |
| B10 Idempotency | VERIFIED | Apple 566 IDs/manifest unchanged; both Tesla filings reused without duplicates |
| B11 Recovery | VERIFIED | Controlled checkpoint/retry/restart fixtures; not an OS power-loss test |
| B12 Amendments | VERIFIED_WITH_DOCUMENTED_LIMITATIONS | Real Tesla 10-K/A pair with explanatory-note proof; 10-Q/A remains fixture-only |
| B13 Regression | VERIFIED | 147 PASS / 0 FAIL / 0 SKIP / 2 warnings, real media/OCR enabled |
| B14 Git delivery | VERIFIED | Existing Draft PR #7 updated on the same branch; no merge |

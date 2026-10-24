SEC row chunks lost statement titles, multi-row reporting periods and units; reprocessing could reuse stale derived versions. Preserve source-backed table/row context, iXBRL sign/scale, footnote locators, nested/continuation links and versioned artifacts. Verify complete chunk context and keep final status consistent.

Evidence: real Apple 10-Q HTTP 200, raw hash matches handoff; 40 tables / 4,762 cells match independent DOM; 28 value/period/unit cases PASS; 566 chunks with stable IDs/manifest; 12 provenance samples VERIFIED. Real Ollama Chat, 768-dimensional embeddings and isolated Qdrant/RAG citations pass. Full regression with real OCR, Tiny-SD, SAPI and FFmpeg: **142 passed, 0 failed, 0 skipped, 2 warnings**.

Acceptance **PARTIAL**: four layout tables retain ambiguous headers, amendments are fixture-only and historical lookup remains limited to active registry revision. Prior OCR failure with tessdata_fast resolved by choosing official tessdata_best and rerunning full regression; no failing tests removed or skipped. Environment differences documented.

Depends on unmerged A/B work in codex/topic3-milestone-b-sec-corpus; target that branch to isolate collaborator fixes. Previous commits preserved. No Milestone C, no production data/collection deletion, no secrets/models/local data included. **Draft for owner review; do not merge automatically.**

See docs/topic3/MILESTONE_B_INDEPENDENT_VERIFICATION.md for B1–B14 matrix and reproduction commands; COLLABORATOR_ENVIRONMENT_REPORT.md for environment differences.

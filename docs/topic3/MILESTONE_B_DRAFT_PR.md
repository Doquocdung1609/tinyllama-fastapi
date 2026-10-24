SEC row chunks lost statement titles, multi-row reporting periods and units; reprocessing could reuse stale derived versions. Preserve source-backed table/row context, iXBRL sign/scale, footnote locators, nested/continuation links and versioned artifacts. Verify complete chunk context and keep final status consistent.

Evidence: real Apple 10-Q HTTP 200, raw hash matches handoff; 40 tables / 4,762 cells match independent DOM; 28 value/period/unit cases PASS; 566 chunks with stable IDs/manifest; 12 provenance samples VERIFIED. Real Ollama Chat, 768-dimensional embeddings and isolated Qdrant/RAG citations pass. Full regression with real OCR, Tiny-SD, SAPI and FFmpeg: **142 passed, 0 failed, 0 skipped, 2 warnings**.

Acceptance **PARTIAL**: four layout tables retain ambiguous headers, amendments are fixture-only and historical lookup remains limited to active registry revision. Prior OCR failure with tessdata_fast resolved by choosing official tessdata_best and rerunning full regression; no failing tests removed or skipped. Environment differences documented.

Depends on unmerged A/B work in codex/topic3-milestone-b-sec-corpus; target that branch to isolate collaborator fixes. Previous commits preserved. No Milestone C, no production data/collection deletion, no secrets/models/local data included. **Draft for owner review; do not merge automatically.**

See docs/topic3/MILESTONE_B_INDEPENDENT_VERIFICATION.md for B1–B14 matrix and reproduction commands; COLLABORATOR_ENVIRONMENT_REPORT.md for environment differences.

## Verification gates

| Gate | Status | Bằng chứng / giới hạn |
|---|---|---|
| B1 Correct Git baseline | VERIFIED | Auth/fetch thành công; remote B de01cbd; hai commit cũ giữ nguyên, không divergence |
| B2 Environment | VERIFIED | pip check, CUDA/OCR/FFmpeg, 3 model digest đúng; phiên bản khác owner được ghi rõ |
| B3 Ollama LLM | VERIFIED | Direct generate có nghĩa, /chat sinh thật; không phải kiểm chứng mọi câu tài chính |
| B4 Embedding | VERIFIED | Vector số 768 chiều, Qdrant dimension 768 |
| B5 API/UI | VERIFIED | Health/docs/Streamlit health HTTP 200, startup READY; chưa kiểm mọi tương tác trình duyệt |
| B6 Qdrant/RAG | VERIFIED | PDF fixture qua upload/embedding/Qdrant riêng, RAG đúng ý và file/trang 1 |
| B7 Real SEC | VERIFIED | HTTP 200, hash gốc trùng owner; 10 checks metadata từ submissions/iXBRL |
| B8 Financial tables | PARTIAL | 28 giá trị/kỳ/scale PASS; 4 layout tables thiếu header; cả filing PARTIAL_EXTRACTION |
| B9 Provenance | VERIFIED | 12 mẫu + API VERIFIED; test raw/normalized/context tamper |
| B10 Idempotency | VERIFIED | 1 filing, 1 raw, 566 IDs và manifest giữ nguyên |
| B11 Recovery | VERIFIED | Checkpoint/retry/new registry instances; fixture kiểm soát, không kill production |
| B12 Amendments | PARTIAL | Cả 10-K/A và 10-Q/A fixture đạt; live amendment NOT_TESTED |
| B13 Regression | VERIFIED | 142 PASS, 0 FAIL, 0 SKIP, 2 warnings, bật real media và OCR |
| B14 Draft PR | VERIFIED | Draft PR #7 OPEN, target nhánh B; đã push, không merge |

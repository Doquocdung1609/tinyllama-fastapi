# P7 — Actual isolated Prebuilt smoke, 31 October 2026

Launcher: `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_financial_studio.ps1 -Mode Prebuilt -Workspace .\tmp\topic3\demo-workspace -ApiPort 18110`. Local URL `http://127.0.0.1:18110/app/`. This new workspace did not replace any owner PDF source, vector collection or model. The launcher reported OCR `READY`, SEC `READY`, 2 configured SEC filings and, after uploads, 2 PDF `READY`. Token values are intentionally absent from artifacts.

| Scenario | Observed | Status |
|---|---|---|
| Prebuilt/health/authenticated UI | `/health` and `/app/` HTTP 200; logged into React; navigation worked | PASS |
| Hòa Phát real scanned PDF upload | Original 4,897,389-byte file SHA-256 `4a92af827aaf1e73e017544d0ff20d0d14ae4d368bd9c90d5d6d60a28af8b447`; 24/24 pages extracted with OCR; 64 chunks; READY | PASS for ingestion/search readiness |
| Hòa Phát financial search | Production V3 BM25, Dense and Hybrid each returned PDF page 3 as top page for same question/document. UI showed `TONG CONG TAI SAN` row, 2025-Q4, source VND and scanned PDF page with OCR highlight. All were `RELATED_UNVERIFIED_EVIDENCE` | PASS for source location; numeric verification pending |
| Hòa Phát assistant after repair | Fresh restart, `/studio/analysis` with `search_profile=production_v3` returned `SOURCE_EXCERPTS`, five citations, top page 3, `values=[]` | PASS for automatic retrieval and safe excerpt; full generated QA partial |
| Hòa Phát unsupported numeric | Numeric mode without locally reviewed cells returned `INSUFFICIENT_EVIDENCE`, no values | PASS abstention |
| BIDV real revised PDF | Original 1,760,974-byte file SHA-256 `2bed2b3c312c8149e6a2ff6ab80c694a4c710e82f65b1c35a1a943eae4fa32a6`; 8 pages (6 native, 2 OCR), 23 chunks, READY | PASS ingestion |
| BIDV revised consolidated search | Hybrid Top-1 page 8 consolidated income statement, page 1 announcement also in Top-5. Source text visibly distinguishes original, State Audit adjustment and restated 2024 columns, `triệu đồng`. No cell value certified | PASS source retrieval; numeric comparison pending |
| BIDV same-scope comparison | UI ran BM25, Dense, Hybrid against BIDV-only scope. BM25 Top-1 page 1; Dense and Hybrid Top-1 page 8. UI correctly stated no qrels for this new question | PASS comparison, no efficacy metric |
| SEC sourced value | HD total assets Aug 2 2026: `/studio/sec/analysis` HTTP 200, `SUPPORTED`, one source-cell citation, normalized value `109384000000 USD`; UI displayed it | PASS for this one cell, no general accuracy claim |
| SEC negative | HD total assets Aug 2 2037: HTTP 200 `INSUFFICIENT_EVIDENCE`, zero values/citations; UI displayed refusal | PASS abstention |
| Bounded research | Hòa Phát asynchronous job completed eight stages with `use_llm=false`; no error. External market/news stage has no official live source | PASS bounded workflow, source scope limited |

The screenshots in `screenshots/` are actual React views: overview, empty search, SEC row, supported/refused SEC analysis, Hòa Phát READY, Hòa Phát result/viewer/highlight, BIDV result/comparison and system readiness. They were captured in the isolated browser on this run. A pixel-by-pixel comparison to old reference images was not performed; visual structure matches the existing six-page navigation and source-viewer layout by inspection.

**Remaining:** Hòa Phát OCR digits and BIDV restatement cells have not received independent image review; no PDF Decimal calculation was authorized. There is no new independent qrel set for either PDF. The SEC and PDF paths use different verifiers. Browser E2E automation was not rerun against this isolated workspace; manual browser evidence and unit/frontend tests are separate. Do not present the excerpt search as a verified numeric answer.

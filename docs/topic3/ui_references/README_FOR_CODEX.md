# Financial Intelligence Studio — UI Reference Pack

These are **seven separate, desktop 1600×1000 concept images**, not screenshots of implemented functionality. Mock figures, badges, citations, PDF pages, response times and document records are **illustrative only**. Codex must use actual backend evidence and runtime status, never copy mock numbers as facts.

| Image | Screen | Expected interaction |
|---|---|---|
| `01_trang_chu_tong_quan.png` | Overview | Two primary CTAs, corpus stats from live backend, service health, document pipeline |
| `02_tim_kiem_tai_chinh.png` | Hybrid Search | Search input, BM25/Dense/RRF mode, issuer/date filters, ranked evidence, selected preview |
| `03_xem_tai_lieu_highlight.png` | Source/PDF Viewer | Left full document page, right verified source evidence, page/row/highlight navigation |
| `04_phan_tich_tai_chinh_ai.png` | Financial AI | Source-backed answers, period comparison, Decimal formulas, citations, abstention |
| `05_tai_lieu_len_pipeline.png` | PDF Upload | File validation, extraction, chunking, BM25, Dense, Qdrant stages, progress/failed/retry |
| `06_kho_tai_lieu_he_thong.png` | Documents & System | Library table and live service health, optional advanced diagnostics |
| `07_danh_gia_so_sanh_bm25_dense_hybrid.png` | Method Comparison | Three methods side-by-side, source overlap, measured latency, provisional metric labels |

## Product IA (recommended 6 top-level navigation destinations)
- Overview
- Financial Search (include Comparison as tab/secondary view)
- AI Financial Analysis
- Document Library (include PDF Upload and processing)
- Evidence Viewer (can be contextual screen opened from Search/Analysis)
- System & Settings

## Mandatory acceptance conditions
1. **Only two core capabilities:** Hybrid Financial Search and source-backed Financial AI Analysis; the other pages support them.
2. Uploading an owner-owned PDF must process and index into isolated BM25 and Dense collections, with accurate status (not READY until both verified).
3. Searching must return **real retrieved chunks**, scores/ranks and current generation; compare runs must use the same corpus membership and filters.
4. Clicking a search result opens a real document. For PDF, page and highlight must be derived from extracted text boxes or reliable page spans. If coordinates are missing, highlight only the verified extracted excerpt and explicitly label page position as unknown. For SEC HTML, do not fabricate deep anchors/row landing.
5. Numerical answers must use a deterministic verified cell/Decimal pipeline. Unsupported values must abstain.
6. Only show evaluation quality metrics for a selected labeled dataset; P11 development qrels are provisional and must be labeled as such.
7. Remove unrelated audio/image/video/general-chat UI and genuinely unused feature-specific dependencies **only after** proving no impact on shared Ollama, FastAPI, Qdrant, PDF, RAG and historical data.
8. Use Vietnamese-first terminology, consistent navy/blue design, keyboard focus, real loading/empty/error states, practical 1366px responsive layout.
9. Product is a class-demo research prototype, not production-certified or a universally accurate financial QA system.

## Visual design tokens
- Sidebar background: `#081A35` to `#0B2850`
- Primary action: `#176CFF`
- Content background: `#F3F7FC`
- Card: `#FFFFFF`, border `#E2EAF4`, radius 13px
- Success: `#09BD86`; warning: `#D99318`; secondary/purple: `#6550EA`
- Heading: `#142B54`; body: `#142646`; muted: `#72839D`
- Desktop reference: 1600×1000; retain meaningful scroll on smaller screens

The PNG files are visually detailed *implementation references*, not sources of numerical ground truth. Match layout hierarchy, spacing, section structures and interactions, rather than pixel-perfect replication of example content.

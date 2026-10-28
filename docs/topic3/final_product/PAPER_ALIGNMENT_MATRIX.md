# Paper-to-product gap audit — 2026-10-28 (before implementation)

Integration base inspected: `39cc2ed203671ca3007db859eefe7155595a16b6`, latest product branch/PR #22, descendant of P11 `ecd8162`. New work preserves that ancestry; no PR/main merge authorized. Frozen local baseline: `.venv/Scripts/python -m pytest -q -m "not integration"`: **590 passed, 1 warning, 33.43 s**. Existing reports describe another machine; their runtime/CI/source availability is not assumed here.

References inspected read-only from public Git repositories (local copies under ignored tmp; no implementation copied):

- A: [financial-hybrid-search-qdrant](https://github.com/satyam671/financial-hybrid-search-qdrant), README §§1–2, `src/hybrid_search/`.
- B: [ai-agent-moat](https://github.com/eriktaylor/ai-agent-moat), README, `research_agent.py`, `tools.py`.

| Reference capability / exact location | Current Python / API / UI evidence | Audit status | Difference / priority / minimal repair | Course relevance |
|---|---|---|---|---|
| A ingestion `ingestion/pipeline.py`, edgar_client | `app/financial_ingestion`, frozen SEC tests; `/financial-corpus`, `/studio/sec/catalog`; Streamlit only | IMPLEMENTED backend; PARTIAL product | Preserve source identity, no new acquisition; P0 surface catalog in React | End-to-end source lineage |
| A context chunking `chunking/chunker.py` | B table-aware chunks, hashes/context, regression | IMPLEMENTED backend | Preserve; uploads add native/OCR page evidence before existing chunk/index path | Traceable retrieval |
| A BM25 `retrieval/bm25_retriever.py` | SEC persisted explicit BM25; user PDFs SQLite FTS5 `/studio/search`; existing workspace tests | IMPLEMENTED backend/API; PARTIAL React | P0 React request adapter; do not equate FTS5 raw scores with SEC BM25 | Lexical retrieval |
| A dense `dense_retriever.py`, embeddings/dense.py | Accepted Nomic 768 digest; isolated Qdrant; tested fake embeddings and earlier live report | PARTIAL live on this machine | P0 preserve model/digest, test installed live model; don't import reference BGE model | Semantic retrieval |
| A fusion `bm25_dense_retriever.py` | Fixed rank RRF k=60; same eligible PDF membership; backend tests | IMPLEMENTED backend/API; PARTIAL React | P0 side-by-side UI + identical-scope comparison guard | Hybrid comparison |
| A filters `filtering/metadata_filter.py` | SEC ticker/period, PDF document IDs; issuer/market via metadata | PARTIAL | P0 human-readable company/document/period/source controls | Scope fidelity |
| A SPLADE `sparse_retriever.py`, `sparse_dense_retriever.py` | No deployed approved sparse model | NOT_REQUIRED | Optional under owner's work order; avoid large model download/three-vector migration | BM25+dense demonstrate fusion |
| A stage2 `reranker.py`, `extractor.py` | Optional local reranker; authenticated SEC table numeric adapter in research QA | PARTIAL / optional reranker | Keep optional; P0 PDF row/column evidence & Decimal safety, no learned scores claimed | Source-grounded numbers |
| A evaluation `evaluation/{metrics,latency,benchmark}.py` | Frozen C/P11 development evidence; no labels for new owner PDFs | IMPLEMENTED artifacts; PARTIAL UI | P0 show real request latency/overlap; no invented Recall/MRR for unlabeled queries | Honest evaluation |
| B context `_get_context`, `_create_rag_chain` | RAG/PDF search and SEC QA separate APIs; no React | PARTIAL | P0 bounded document-only orchestration API, source citations; local LLM optional and labeled | Multi-tool RAG |
| B live stock/news `tools.py`, `_get_context` | No configured supported financial/news connector | NOT_REQUIRED live source | P1 explicit unavailable tool result with timestamp; continue document-only | Tool failure handling |
| B `generate_market_outlook` | No bounded product workflow | MISSING | P0 cited business-context stage over selected documents | Research context |
| B `generate_value_analysis` | SEC exact values/Decimal, no company workflow | PARTIAL | P0 eligible PDF facts + context, no valuation without market inputs | Fundamentals |
| B `generate_devils_advocate_view` | Source abstention guards, no persona stage | PARTIAL | P0 explicit risks, contrary/missing evidence; no fabricated contradictions | Critical evaluation |
| B `generate_final_summary` | No consolidated product report | MISSING | P0 four sequential bounded stages, visible real events, cited Vietnamese synthesis | Research report |
| Owner Vietnamese OCR/rotated tables | Old PDF `_extract` native only; signature-only pages can produce chunks; no OCR evidence in studio | MISSING product | P0 page classifier, bounded Tesseract vie+eng, persisted checkpoints, real coordinates, uncertain numeric abstention | Primary Vietnamese demo |
| Owner PDF highlighting | `/studio/.../highlight` PNG with real native line boxes; Streamlit | PARTIAL | P0 PDF.js text-selection/zoom/page viewer, source geometry overlay; SEC structural excerpt only | Inspect evidence |
| Owner React six pages | `product_ui.py` Streamlit; seven supplied references inspected | MISSING | P0 React/TS/Vite/Tailwind/shadcn/PDF.js/Recharts; preserve legacy rollback until parity | Product delivery |

## Compatibility inventory frozen before changes

| Visible old workflow | Existing service/API | Migration contract |
|---|---|---|
| Overview/status | `/health`, `/system/status`, `/studio/health`, SEC catalog | Actual counts/readiness, no illustrative badges |
| SEC search | `SecResearchIndex.search`, `/studio/sec/search` | Read-only approved snapshot, same B/D/F scope |
| Uploaded PDF search | `PdfWorkspace.search`, `/studio/search` | Source hashes, READY only after both memberships |
| Financial SEC AI | `app.research_api`, `ResearchBackend.query`, automatic_real workflow | Safe same-process wrapper; preserve existing API/tests |
| Library/upload/retry | PdfWorkspace + `/studio/documents` | Isolated owner workspace; persisted state; no frozen data mutation |
| PDF source image | PdfWorkspace.page_image | Preserve old contract; new authenticated bytes/geometry API for PDF.js |
| Comparison | Streamlit orchestrates independent backend searches | Move orchestration to Python wrapper; verify same generation; metrics only with labels |
| General chat/media | Already removed from product at base; shared legacy code remains | No new product navigation; audit before removal |

Business logic in Streamlit is request orchestration, Decimal display, citation formatting and evidence selection, not the retrieval algorithm. Move missing orchestration into Python; presentation/state into React. Native/OCR numeric source verification is distinct from SEC iXBRL authentication. All final status upgrades require actual tests, not this design matrix.

## Final observed closure (28/10/2026)

P0 React, API orchestration, native/OCR source viewing, Vietnamese lexical cache, local Nomic retrieval, reviewed-cell Decimal and bounded multi-tool research are implemented and exercised on both owner PDFs. Detailed PASS/PARTIAL/NOT_TESTED evidence is in FINAL_PRODUCT_ACCEPTANCE.md and RUNTIME_EVIDENCE.json. This closure does not overwrite the initial audit statuses above.

Owner subsequently explicitly authorized new SEC downloads (“tải sec mới cũng được”). The initial no-acquisition constraint above is superseded only for this bounded PG/HD product setup. Two fresh files were isolated under a new product identity; old PG raw hash was not reproduced and historical freeze was not changed. SPLADE/three-vector, autonomous framework, new holdout/qrels and live market connectors remain omitted with reasons described above. Reference papers are architectural comparisons, not claims of full reproduction.

# Milestone C product smoke test — 2026-10-25

Candidate combines target `b7fd390` and source `a6c3d6f`. FastAPI runs at `http://127.0.0.1:8000`; Streamlit at `http://127.0.0.1:8518/`. Isolated financial corpus/index: `C:\msch\corpus` and `C:\msch\index`. Legacy upload/Qdrant paths are under the temporary integration worktree, never owner historical paths.

## Commands

```powershell
# Owner Python 3.13.2 venv, qdrant-client 1.20.0
python -m uvicorn main:app --host 127.0.0.1 --port 8000
python -m streamlit run streamlit_app.py --server.address 127.0.0.1 --server.port 8518 --server.headless true --browser.gatherUsageStats false
```

Process environment selects explicit IPv4 Ollama, Nomic model, isolated financial paths and a temporary local mutation token; local bypass is false. The token is not retained as a credential in this report.

## Live browser recovery

The stopped Windows session was not reused. A newly authorized in-app browser tab opened the explicit Streamlit URL and reported its URL/title on every observation. AX observations and a screenshot verify the rendered page. Screenshot: `reports/milestone_c_acceptance/financial_search_live.png`.

| Scenario | Actual result | Evidence class |
|---|---|---|
| Financial Search page | Page heading, dataset selector, 320 chunks, query/filter controls rendered | LIVE_VERIFIED |
| Methods | Dropdown exposes Từ khóa/BM25, Ngữ nghĩa/Dense, Kết hợp/Hybrid; all submitted | LIVE_VERIFIED |
| BM25 | `Walmart basic earnings per share 2026 2025 2024`, ticker WMT; first result Note 2 with Basic 2.74/2.42/1.92 and fiscal-year column labels | LIVE_VERIFIED |
| Dense | Paraphrase about interest rates, long-term debt and fair value; first result Market Risk; no semantic-unavailable warning | LIVE_VERIFIED |
| Hybrid | Same paraphrase; first Market Risk, then Note 7 Fair Value, Note 5 debt; corresponding API ranks/RRF contributions recorded | LIVE_VERIFIED |
| Result context | Walmart Inc., 10-K, report date 2026-01-31, filed 2026-03-13, source section/content rendered | LIVE_VERIFIED |
| Provenance | “Nguồn đã đối chiếu”; expander exposes chunk ID, filing ID, full generation, section, structural path and row/table locator | LIVE_VERIFIED |
| Partial extraction | Visible yellow warning: “Có tờ khai được trích xuất một phần. Hãy kiểm tra nguồn trước khi sử dụng số liệu.” | LIVE_VERIFIED |
| SEC navigation | Click opened actual Walmart 10-K in a second tab, correct issuer/form/year. Note 2 row and Market Risk text independently matched filing source | LIVE_VERIFIED |
| Invalid generation | API 409 `INDEX_GENERATION_NOT_FOUND`; no results or fallback. UI only selects READY generations, no manual invalid-generation field | LIVE_VERIFIED at API |
| Mutations | Missing-token activation 401; authorized same-generation activation 200, no active pointer change | LIVE_VERIFIED |
| Legacy Chat | UI loads model qwen2.5:3b and Online status; API returns requested short response | LIVE_VERIFIED |
| Legacy RAG | UI accessible; isolated PDF upload reaches READY with 2 chunks; retrieval API returns two scoped sources, page/bbox/table provenance | LIVE_VERIFIED with local fixture PDF |

## Snapshot and API evidence

- Dataset `issuer-heldout-index-v1`, generation `afe00aa93e6957a92e0292f6ae54d258dc1c1f5a84e3f83c275931476875d691`, 320 points, READY.
- Model `nomic-embed-text:latest`, digest `0a109f422b47e3a30ba2b10eca18548e944e8a23073ee3f3e947efcf3c45e59f`, 768 dimensions; separate `search_document: ` / `search_query: ` prefixes.
- API smoke applies ticker WMT, 10-K, fiscal year 2026 and exact filing ID before ranking; every returned hit matches and has VERIFIED provenance, with unique logical chunk IDs.
- API invalid-generation and missing-token rejection were rechecked in the recovered session.
- SEC URL: https://www.sec.gov/Archives/edgar/data/104169/000010416926000055/wmt-20260131.htm
- UI locator is inspectable JSON; the SEC link opens the document, not an automatic highlighted row. This remains a navigation limitation.

## Limits

Legacy RAG answer generation was not scored; retrieval returned correct fixture-scoped evidence with `generate_answer=false`. Chat success and source correspondence do not certify financial-answer accuracy. First cold provenance request and subsequent warm requests are not directly comparable latency measurements. Raw API summaries are retained separately; the original failed 1.19 compatibility attempt is documented in the security review.

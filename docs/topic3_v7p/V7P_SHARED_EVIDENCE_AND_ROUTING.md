# Shared evidence and actual routing

Uploaded PDF Search and Chat use `unified_search` -> source-authenticated native table adapter -> `automatic_answer` -> claim postcondition. Search exposes `financial_evidence`; no separately fabricated answer branch. Original BM25/Dense/Hybrid implementations and baseline configurations are retained.

| Situation | Effective behavior |
|---|---|
| Generic uploaded PDF, AUTO | `production_v3`, hybrid, actual generation/reason returned |
| Matching READY owned V3R3 derived workspace | `production_v3r3` only after readiness check |
| AUTO hybrid, model transport/digest unavailable | Explicit BM25 fallback with actual mode and routing reason |
| Explicit Dense unavailable | Fails; never relabeled Hybrid |
| Explicit filters contradict question | QUERY_CONTEXT_CONFLICT, empty values |
| Unknown unit/scope/column | Insufficient evidence, no numeric claim |

Live Apple workspace used `GENERIC_PDF_V3_NO_COMPATIBLE_READY_DERIVED_INDEX`; no false V3R3 badge. Actual offline transport injection returned `DENSE_UNAVAILABLE_BM25_FALLBACK`, mode bm25, correct source operands. Owner Ollama process was never stopped.

SEC uses retained pinned ResearchBackend/D1/D3/D2/D4 integration and source-cell locators. It is distinct from generic PDF V3, not silently called FAITH-R validation on uploaded PDFs. Browser HD total assets returned 109384000000 USD as of 2026-08-02 with exact official URL, raw hash and cell locator. No new retrieval-quality claim follows from this product test.

Research Lab preserves available author methods/improvements, unavailable methods and independent evaluation state. Executed B/D/F comparison shows real latency/overlap. No qrels for the interactive query -> no invented Recall/MRR/nDCG.


Code reviewed/tested: `3e85fdba74737f5a94f555424d283126fe84dc0e`. Starting work-order HEAD: `f3c3fc320d957a4be418054e179e18800f49e5cf`; PR34 base: `cd8deb96cb8c147ca5c090e9c0a323de511c65bd`. Existing Draft [PR35](https://github.com/Doquocdung1609/tinyllama-fastapi/pull/35), branch `codex/topic3-v7p-verified-financial-chatbot`. Same-system Codex adversarial pass, not independent human review. No merge or new PR. Final documentation commit identity is available from Git/PR; this report does not invent a self-referential SHA.

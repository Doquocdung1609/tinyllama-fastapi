# V4 release review — owner decision pending

| Gate | Result | Evidence / remaining limit |
|---|---|---|
| A Product core | PASS | Browser login, real PDF reupload, direct BIDV answer, PDF page 1 viewer, safe numeric restraint. |
| B Financial evidence | PARTIAL | SEC Home Depot verified cell and absent-year refusal pass; Hòa Phát/BIDV OCR table cells have no reviewed row/column/period/unit chain. Apple FY2025 PDF not retested. |
| C Research Lab | PASS with limits | Three live product methods and eight explicitly saved historical arms, source links and timings. SPLADE/Stage-2 not live. |
| D Scientific integrity | PARTIAL | Existing 4/4 versus 0/4 exposed target results and structure ablations retained; chunk-count/IDF confound and zero independent human-reviewed items remain. |
| E Live demo | PASS with limits | Fresh launch, login, PDF source, comparison, SEC verified cell, refusal, upload, managed restart and screenshots. One process-memory/free-disk snapshot recorded; no cold OCR timing or whole-system peak. |

**Recommendation: `PRODUCT_DEMO_READY / RESEARCH_PARTIAL` for the bounded presentation script.** This does not assert complete PDF numerical QA or research reproduction of the original 47 SEC filings. The repository owner retains final acceptance authority. Do not merge PR #29 or this V4 Draft PR on the basis of this memo alone.

Local checks: 722 Python PASS (one Starlette `httpx` deprecation warning); 10 frontend PASS; Vite build PASS. Remote GitHub Actions require a separate check; PR #29 jobs previously did not start due to account billing, which is not a test PASS.

Remaining work for a stronger claim: human-reviewed independent qrels, equal-count chunking control, exact PDF table-cell review, Apple PDF unit case, cold OCR timing and resource peaks. No model weights, source PDFs, local token or Qdrant index are part of the commit.

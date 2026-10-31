# Topic 3 final gate assessment — owner review

**Recommendation: `RESEARCH_PARTIAL`.** This branch is a Draft PR candidate for review, not a merge or scientific-completion claim. Owner retains final acceptance authority. No token, owner workspace, model weight or local Qdrant index is committed. Research intervention and product smoke are evidence-backed; independent efficacy is not established.

| Gate | Result | Evidence and reason |
|---|---|---|
| G1 Paper traceability | PARTIAL | PDF, pinned author code and discrepancy audit mapped in `../00_AUDIT/`; three supplementary work-order files inaccessible. |
| G2 Reproduction | PARTIAL | Genuine R0–R6 code paths and 31 author unit tests on two SEC filings; original 47 filings, original qrels and historic model snapshots absent. |
| G3 Failure evidence | PASS | Five measured, source-located cases across wrong row/metric, candidate depth and unsupported issuer/period; negative cases are retrieval risks only. |
| G4 Controlled improvement | PARTIAL | Full structure BM25 4/4 known target @1 vs author BM25 0/4 on exposed development set; three structure ablations. No broad I0–I6 or independent significance claim. |
| G5 Independent evaluation | BLOCKED | Zero human-reviewed untouched held-out items. Six exposed machine-prepared questions cannot establish generalization. |
| G6 Operational QA | PARTIAL | Fresh isolated Prebuilt launch, 2 real PDFs, 3-mode comparisons, 12 UI captures, resource snapshots and 714 Python/10 frontend tests; peak API RAM, OCR-only time and complete automated browser/recovery matrix missing. |
| G7 Unified product | PARTIAL | React PDF document QA now uses the same explicit production V3 retrieval service as Search and abstains from unchecked numbers. SEC verified-cell path is separate; generated PDF answer and research-index deployment unproved. |
| G8 Demonstrable release | PARTIAL | Isolated live demo and guide work; scientific G5 block prevents `RESEARCH_COMPLETE`. |

## Regression and smoke

- Original author tests: **31 PASS**, two warnings in isolated original environment.
- Project Python after code repair: **714 PASS**, one Starlette deprecation warning.
- Frontend: **10 PASS**, TypeScript/Vite production build PASS.
- Manual browser: 12 actual screenshots across overview, Search, Analysis, Library, Viewer, Compare and System; HD 2026 source cell supported; 2037 request abstained; Hòa Phát and BIDV PDFs READY.
- A fresh-process start after the assistant-routing repair returned Hòa Phát page 3 with five citations and zero values; legacy API default retained by unit test.

## Remaining review decision

Human reviewers must inspect a new, untouched source-grounded test set and PDF financial cells before claiming retrieval efficacy or verified PDF calculations. Any paper result, score or UI screenshot should be cited with its exact artifact and provisional status. The safe presentation sentence is: **“We reproduced the original search methods on two alternative SEC filings, measured concrete row-location failures and a promising structure-aware improvement on four exposed questions, and demonstrated a source-linked local product; independent financial accuracy remains unverified.”**

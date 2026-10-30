# Final V3R3 acceptance memorandum

**Recommendation: `SEARCH_V3R3_PARTIAL` — owner acceptance remains open.** This is a precision repair and review packet stacked on Draft PR #27 at exact parent `006d056d47ce1e417befd965937e38536045850a`. No PR is merged and no V4 work is included.

| Gate | Result | Evidence |
|---|---|---|
| Exact baseline, source/model/checkpoint integrity | PASS | `V3R3_BASELINE_REVIEW.md`, `OWNER_CLONE_INTEGRITY.json`, `BASELINE_AUDIT.json` |
| Top-1 metric precision on exposed 178 queries | PASS with limits | Correct 124/130 → 128/130; known wrong 3/130 → 0/130; source Top-5 128/142 → 129/142 with zero paired loss; `V3R3_PRECISION_EVALUATION.md` |
| SEM exact numeric certification | PENDING | Seven source/digit locators retained, 0/7 newly reviewed, 0/7 numeric eligible; `V3R3_SEM_NUMERIC_INTEGRITY.md` |
| Human source audit | PENDING | 26/26 decision rows blank; owner workbook unedited; `V3R3_OWNER_REVIEW_GUIDE.md` |
| Local backend/frontend/build | PASS | 709 backend, 10 frontend, 38 targeted; build PASS; one dependency warning |
| Prebuilt browser and source viewer | PARTIAL | 4/5 first batch, failing case PASS on replay, all 13 actual screenshots; resource guard blocked a later post-restart browser replay |
| Index/source restart integrity | PASS with startup limit | 11/11 stable hashes; unchanged generation; API query 200 with correct page-2 row; ~114-second in-memory preparation |
| Windows demo memory | PARTIAL | Minimum available RAM 16.59 MiB; preflight alternated WAIT/READY; `V3R3_DEMO_STABILITY_REPORT.md` |
| Independent heldout and owner signoff | NOT AVAILABLE | `NEW_INDEPENDENT_EVAL_NOT_AVAILABLE`; `HUMAN_AUDIT_PENDING` |

The product preserves raw OCR, source boxes, unit/period guards and numeric eligibility. The ranking change alone does not certify a value. Wrong period/basis/unit rates were not measured independently in the exposed set. The prior SEC data and original owner workspaces were retained. The complete 178-query harness did not write its normal final artifact because its repeat prewarm was deferred by low RAM; the per-query records and reconstructed summary explicitly retain that limitation.

For a live presentation, run the preflight in `V3R3_RELEASE_CANDIDATE.md` and proceed only when it reports READY with adequate memory. The repository owner makes the final acceptance decision after checking the 26-case packet. `SEARCH_LOCKED` is not asserted.

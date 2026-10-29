# V3R2 final acceptance — PARTIAL

Authorization: SEARCH_V3R2_TARGETED_REPAIR_ONLY. Base Draft PR26 exact SHA `3ba5e5e0f138fd2c1fd41c34c8b1262d74c308a9`; contributor branch `codex/financial-search-v3r2-hardening`. No merge. No model/service/agent roadmap change.

Published as [Draft PR27](https://github.com/Doquocdung1609/tinyllama-fastapi/pull/27), stacked directly on PR26's contributor branch. Code-bearing commit `b35b8028c4d239b1abe9c25277e4b94a827cb1b3`; exact-head CI was blocked before any job steps by the account restriction. Later documentation bookkeeping does not change tested code.

**Decision: SEARCH_V3R2_PARTIAL.** Targeted ACB repairs and bounded regression/source/persistence checks pass, and a usable 26-case human review packet is prepared. Overall financial answer quality and Windows memory stability remain limited. Do not mark SEARCH_LOCKED or independently reviewed. Owner retains acceptance authority. SEARCH_V3R2_OWNER_REVIEW_READY is not issued as an unqualified final gate.

| Gate/workflow | Actual status | Evidence/limit |
|---|---|---|
| Exact baseline / preservation | PASS with process-lease change | 591/592 exact hashes unchanged; only owned SEC Qdrant PID lease renewed. Source/vector/checkpoint/review/report bytes unchanged. |
| ACB equity, pretax, net income | PASS targeted source retrieval | 0/3→3/3 Recall@5; equity rank3, profit rank1. No invented source text/header/value. |
| SEM seven raw cells | PASS preservation / PARTIAL numeric quality | 88 checkpoint hashes identical; malformed OCR remains visible and unreviewed. |
| Unit/signed/blank safeguards | PASS bounded tests/live display | VND million and KRW/USD source-header candidates; unknown scale/context abstains. |
| 178-query source regression | PASS no Recall@5 losses | 88.03%→90.14%; only three ACB gains. All exposed, not held-out. |
| Top-1 metric quality | PARTIAL | Wrong-classified rate 1/117→4/120; related chunks not numeric evidence. |
| Numeric negative abstention | PASS bounded | 36/36; two explicit numeric-eligible positives retain eligibility. |
| Wrong period/basis aggregate metrics | NOT_MEASURED | Qrels lack complete labels; null is not zero error. |
| New scan OCR/upload/index/three modes | PASS technical lifecycle | SEM page7 raster derivative; 10.62s region extraction, 11.49s upload→READY. Only newly created test document removed. |
| Real Chrome | PASS 4 bounded scenarios | 12 actual screenshots; reviewed highlight, pending raw units, source PDF, stale response, comparison, 20 page transitions. |
| Restart / historical local snapshots | PASS | 9 READY PDFs, 8 prior reviewed facts, 5 index files and mtimes unchanged; old immutable generations retained. |
| Resource admission/cache/reuse | PASS bounded behavior | One heavy task, max2 waiters; repeated prepare buildcount unchanged; new-doc rebuild invalidates old memory. |
| Owner-machine RAM stability | PARTIAL | API peak1091.59MiB; Chrome aggregate4235.83MiB; minimum available708.15MiB, 6 samples below1536MiB. No observed OOM; no leak claim. |
| Human source review | PENDING | 26 cases with images/sourcehash/locator/results; 104 human input cells blank. |
| Local backend/frontend/build | PASS | 706 backend, 10 frontend, 4 Chrome; compileall, pipcheck and build. Existing Starlette/httpx warning; Node color-env warning. |
| Remote CI | REMOTE_CI_BLOCKED_BY_ACCOUNT | Exact PR26 head cannot start jobs due payment/spending restriction; not CI PASS. |
| New independent generalization | SKIP | No new unseen sources/labels; 24 PNJ/ACB are regression only. |

## Owner review and launch

Use [V3R2_HUMAN_AUDIT_CHECKLIST.md](V3R2_HUMAN_AUDIT_CHECKLIST.md), `V3R2_HUMAN_AUDIT_RESULTS.xlsx` and adjacent `source_images/`. Agent transcriptions/retrieval candidates are provisional; all human decisions remain blank. Native Excel execution was not tested; Artifact Tool recalculation and saved XML/validation/blank-input checks passed. Source paths in column M are plain relative paths to avoid unsupported hyperlink rendering.

Launch from repository PowerShell:

```powershell
.\scripts\run_financial_studio.ps1 -Mode Prebuilt -Workspace 'C:\Users\Admin\Documents\GitHub\tinyllama-fastapi\studio_workspace\search-v3r2-owner-r2-20261029'
```

Open http://127.0.0.1:8110/app/ . Choose PDF uploads, appropriate document, and Search V3R2 profile. Wait for prepared index. Use READY documents for a presentation; avoid concurrent OCR/benchmarks. Owner may free RAM by closing unnecessary work voluntarily. No unrelated application was stopped by this task.

Rollback: stop only launcher-owned processes using `.\scripts\run_financial_studio.ps1 -Stop`; the committed base branch and original workspaces remain available. Do not delete workspaces/models. Active new owner root is `search-v3r2-owner-r2-20261029`; the earlier failed partial clone `search-v3r2-owner-20261029` is retained and must not be used.

## Reports

- [Baseline](V3R2_BASELINE_REVIEW.md)
- [ACB diagnosis / Top-10 evidence](V3R2_ACB_ROOT_CAUSE_AND_REPAIR.md)
- [Numeric / unit validation](V3R2_NUMERIC_AND_UNIT_VALIDATION.md)
- [Windows resources and memory limits](V3R2_RESOURCE_STABILITY_REPORT.md)
- [Independent human review packet](V3R2_HUMAN_AUDIT_CHECKLIST.md)
- [Regression and denominators](V3R2_REGRESSION_AND_EVALUATION.md)
- [CI disposition](V3R2_CI_DISPOSITION.md)

Full failed-development and final raw runs are retained separately. Related evidence can appear despite numeric abstention; source Recall@5 is not financial accuracy. Correction of one old ACB reference window is additive and does not rewrite earlier scores. No new human-reviewed numbers were created.

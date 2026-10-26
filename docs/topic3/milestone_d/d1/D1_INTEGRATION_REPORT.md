# D1 controlled integration evidence

Date: 2026-10-26 (Asia/Bangkok). Authorization: `TOPIC3_MILESTONE_D1_CONDITIONAL_OWNER_ACCEPTANCE_AND_CONTROLLED_INTEGRATION`.

Final status: **MILESTONE_D1_ACCEPTED_WITH_DOCUMENTED_LIMITATIONS**. Scope and exclusions are in [owner acceptance](D1_OWNER_ACCEPTANCE.md).

## Preflight and exact objects

- PR #10 was independently re-read as Draft/open/unmerged, source `fae5f070973d86b187425e5959a62560bbb354b1`, base `codex/topic3-milestone-b-sec-corpus` at `d1d5195b26f77d8fb25c830229c4c3693d4b638f`. Source/target matched expectations at initial fetch and immediately before integration. Discussion timeline returned no comments. No conflicting concurrent tracked edits were present.
- PR #9 remains separate, Draft/open/unmerged, source `bcd5728afda4207e79ebf789edd73594aab60bbe`.
- `git merge-base` returned the exact accepted target. Recomputed `git merge-tree --write-tree <target> <source>` returned tree `1c0657d27a55a104bebe513f31d996e43de8af08`, without conflicts.
- Isolated detached candidate `a527b9fa8a0bf0ec0e35c8010879cae3f78928db` has first parent target and second parent source. Its tree equals source. Candidate regression below was freshly reproduced, not copied from the review report.
- [Core CI run 40189308404](https://github.com/Doquocdung1609/tinyllama-fastapi/actions/runs/40189308404) completed SUCCESS. Job `121156698734` ran compilation and intended deterministic-core tests. Logs explicitly show checkout of `a527b9f` merging exact source into exact target. Result: **364 passed, 1 skipped, 3 deselected, 1 warning, 8.10s**, Linux/Python 3.13.16. The extra skip relative to Windows is unavailable Tesseract; media tests are deselected. This is candidate CI, not a newly claimed post-merge CI run.

## Review revalidation

Read all three existing review reports, all 56 adversarial tests and their fixture, plus relevant repaired source bodies. No new patch or test weakening was needed. Permanent passing regression coverage:

| Finding | Verified control |
|---|---|
| F01 HIGH | CIK decimal/path suffixes rejected as INVALID_INPUT; verified padded aliases retained |
| F02 HIGH | Unsupported/malformed forms and embedded accessions clarify; no prefix identity inference |
| F03 HIGH | Invalid/compact/fractional fiscal-period syntax clarifies; typed comparative-quarter controls pass |
| F04 HIGH | Long Decimal retains every digit under context precision 6/28/50 |
| F05 MEDIUM | Signed/grouped amounts, scale, percent and percentage-point constraints retained or clarified |
| F06 MEDIUM | Explicit form/filter conflict retains clarification despite fiscal filter |
| F07 MEDIUM | Inconsistent shared-accession metadata rejected; consistent joint registrants allowed |
| F08 MEDIUM | Text/tree/cycle limits and bounded adversarial intake pass |
| F09 MEDIUM | Attributable income stays distinct; units use whole-token semantics |

No demonstrated unresolved HIGH/CRITICAL finding remains. This is a same-system evidence revalidation, not independent human review or a proof of all possible English inputs.

## Commands and local results

Used existing configured venv without installation or dependency mutation. Windows 11 build 10.0.26300; Python 3.13.2; Pydantic 2.13.5, pytest 8.4.2, FastAPI 0.142.2, Starlette 1.7.0, httpx 0.28.1, qdrant-client 1.20.0. `SCORE_THRESHOLD=0.55`, `RUN_REAL_MEDIA_TESTS=0`. Commands below use that interpreter as `python`. All tests use isolated fixtures; existing real-media opt-in behavior is preserved.

| Command | Exact candidate, pre-merge | Exact accepted merge, post-merge |
|---|---|---|
| `python -m compileall -q app scripts` | Exit 0 | Exit 0 |
| `python -m pytest -q tests/test_financial_query.py` | 114 PASS, 0 FAIL, 0 SKIP, 1.84s | Combined focused command below |
| `python -m pytest -q tests/test_financial_query_review.py` | 56 PASS, 0 FAIL, 0 SKIP, 0.59s | Combined focused command below |
| `python -m pytest -q tests/test_financial_query.py tests/test_financial_query_review.py` | Separate focused commands above | 170 PASS, 0 FAIL, 0 SKIP, 1.54s |
| `python -m pytest -q` | 365 PASS, 0 FAIL, 3 SKIP, 1 warning, 37.83s | 365 PASS, 0 FAIL, 3 SKIP, 1 warning, 33.72s |
| `python -m pytest -q -m "not integration"` | 365 PASS, 0 FAIL, 0 SKIP, 3 deselected, 1 warning, 44.28s | 365 PASS, 0 FAIL, 0 SKIP, 3 deselected, 1 warning, 40.70s |
| `git diff --check` | Exit 0 | Exit 0 |

All three full-suite skips are existing opt-in real-media tests. The warning is existing Starlette/httpx TestClient deprecation. Temporary-fixture accepted C financial index/API/provenance/security and legacy Chat/RAG regressions are included; this is not a fresh live owner UI verification.

## Controlled merge and ancestry

After candidate tests and latest source/target confirmation, PR #10 was marked ready and merged via the standard GitHub merge API, method `merge`, with expected source SHA enforcement. No bypass, squash, force push, branch deletion or auto-merge was used. GitHub returned success and confirmed PR merged/closed at 2026-10-26T02:37:14Z.

Accepted merge: **`182771470841b805d2f8d78f11b7dfa70c2dfc99`**.

Exact parents: `d1d5195b26f77d8fb25c830229c4c3693d4b638f` then `fae5f070973d86b187425e5959a62560bbb354b1`. Tree: `1c0657d27a55a104bebe513f31d996e43de8af08`. Fetched remote target and checked out this exact merge detached in the isolated worktree. `git diff --exit-code <candidate> HEAD` passed. Source ancestry check passed. The post-merge commands above ran on this actual merge, not just an equal-tree assumption.

## Post-merge integrity and boundaries

Batched `git ls-tree -r --format` comparison verifies all **524 existing accepted C blobs identical**, no missing/modified baseline file. All changes relative to accepted target are 24 D1 additions. No production route/module outside `app/financial_query` references D1; scanning all other app Python files returned an empty match list. Financial Search, API/UI, legacy code, dependencies, workflow, production defaults and migrations remain unchanged.

Remote main remains `ceaa8acfcfaea8056e45b859a0fc44d6381fb22a`. PR #9 stays open/unmerged and its source is unchanged. No D2-D5 code was created. Existing owner checkout remains clean. Tests used temporary synthetic data; no owner snapshot/manifest/Qdrant collection was rebuilt, activated or deleted.

Frozen C queries/qrels/metrics and consumed held-out files are unchanged Git blobs. Historical Recall@5 remains BM25/Dense/Hybrid 0.911/0.321/0.714, and held-out 0.9375/0.8125/0.9375. BM25 remains recommended. No D1 resolver performance figure is presented as retrieval-quality improvement.

Structural schema validation and metadata lineage checks do not authenticate source bytes. Upstream verified catalog/source provenance remains mandatory. `RESOLVED` means metadata scope only; it does not verify metrics, amounts, units, citations or financial answers. Live UI/Ollama and fresh physical-disk hashes of untracked owner history: **NOT_TESTED**. These limits do not block integration of an isolated opt-in D1 library.

## Acceptance conditions

Current-head CI, no open HIGH/CRITICAL finding, all repaired regressions, exact isolated candidate full regression, unchanged scientific artifacts, no unapproved production changes, non-destructive owner-data boundary, and correct target confirmation all passed before merge. Post-merge compilation, focused/full/core suites and diff check all passed. Publication adds only these two documents in a controlled follow-up commit; accepted code and historical reports are not changed. This workflow runs on PRs and main pushes, so a target-branch documentation push does not imply a new CI run.

D2 is ready for separate planning around source-bound typed table columns and downstream status gating. No D2 implementation is authorized or started.

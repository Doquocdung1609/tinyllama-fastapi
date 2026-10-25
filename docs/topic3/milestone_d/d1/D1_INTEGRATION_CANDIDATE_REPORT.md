# D1 integration-candidate verification (no merge authorization)

## Exact candidate identity

| Object | Identity |
|---|---|
| Original reviewed PR source | `4506e3e0346ce1107fefe90d2cc2e57e8bdfa3f5` |
| Current target at construction | `d1d5195b26f77d8fb25c830229c4c3693d4b638f` |
| Repaired implementation source | `901a4d389aedbdc69d0d744d437c95cdc113097e` |
| Merge base | `d1d5195b26f77d8fb25c830229c4c3693d4b638f` |
| Local candidate commit | `9c212968cb08416fe49817f1ade0a845a502a5e0` |
| Candidate tree | `c7ccfe8bce9f2d92f5dc446ca81c75581ca252f0` |
| First parent | Target `d1d5195b26f77d8fb25c830229c4c3693d4b638f` |
| Second parent | Repaired source `901a4d389aedbdc69d0d744d437c95cdc113097e` |

Created with `git merge-tree --write-tree <target> <repaired-source>` and `git commit-tree <tree> -p <target> -p <repaired-source> -m "Review-only D1 integration candidate; not published"`. No conflict was reported. The target is an ancestor; candidate/source trees are equal. This is a **local review-only object**, checked out detached in a second managed worktree; no target ref or PR was merged. The candidate is retained locally for audit, not pushed onto the accepted branch.

After these tests, review documentation is committed separately. That delivery changes only reports, not tested Python/fixtures. Final delivery-head GitHub CI must still be verified; its test-merge ref/source/target are recorded in PR #10/final delivery. A later final documentation-tree candidate can be checked without pretending the original candidate SHA changes retroactively.

## Actual candidate tests

Python is the existing configured venv interpreter. Environment: Windows11/Python3.13.2, `SCORE_THRESHOLD=0.55`, `RUN_REAL_MEDIA_TESTS=0`, dependency versions in the adversarial report. No dependencies were installed or changed.

| Exact command on candidate | Result |
|---|---|
| `python -m compileall -q app scripts` | Exit0 |
| `python -m pytest -q` | **361 PASS,3 SKIP,1 warning**,41.03s |
| `python -m pytest -q -m "not integration"` | **361 PASS,3 deselected,1 warning**,22.19s |
| `git diff --check` | Exit0 (repair/source diff also checked) |

Three full-suite skips are existing opt-in real-media tests. Core deselects these; local Tesseract is available, so no additional local skip. The warning is existing Starlette/httpx TestClient deprecation. CI/Linux may lack Tesseract, making its count differ by one; report actual CI output rather than treating361 as a universal fixed count.

Before the candidate, the repaired review tree passed114 original D1 tests,52 new adversarial tests, full361/3SKIP and core361/3deselected. Original source passed114 existing tests but failed18 of the52 new tests. These are fixture-based correctness/compatibility checks, not a controlled retrieval-quality evaluation.

## What integration actually verifies

The full suite exercises actual accepted C classes with temporary synthetic corpora/indexes: persistent BM25/filter parity, restart/rollback, incremental reuse, generation/model mismatch, source tampering, authentication, retention/stale cleanup, cache/TOCTOU and Qdrant owner safeguards. Existing financial API/schema and legacy Chat/RAG prompt/source/hybrid regressions pass. D1 remains opt-in; no production module imports it and no API/UI/default was changed.

Live owner Financial Search UI, live Ollama/Dense ranking, generated financial answers and production deployment are **NOT_TESTED** here. Passing temporary-fixture production-code paths is not represented as new live product acceptance. No new model, SEC source, embedding or vector generation was created.

## Historical integrity and owner data

A batched `git ls-tree -r` blob-map comparison checked **all524 existing tracked baseline files** against repaired source/candidate ancestry: every original blob is identical. Repaired implementation adds21 D1 files relative to the accepted target (original19 plus review test/fixture); later review documentation adds three reports and append-only qualifications. No accepted app/API/UI/dependency/workflow/report/query-set blob changed. Original D1 benchmark JSON and original40-case fixtures remain byte-identical to the reviewed PR HEAD.

This proves tracked source/evidence preservation, not a fresh hash audit of every untracked physical owner snapshot/collection. The review opens no owner corpus/index. Existing tests use isolated temporary fixtures; no destructive experiment, owner-data cleanup, SQLite/Qdrant mutation against owner history, generation activation or network inference was performed. The configured Python environment was reused read-only.

## Merge readiness interpretation

The implementation candidate passes compilation, complete regression and deterministic-core selection with documented environment limits. Nine reproduced D1 findings have targeted repairs; none remains open at HIGH/CRITICAL severity. Final-head CI is a separate delivery gate and must pass before a final owner-acceptance recommendation. Neither this report nor a green CI run authorizes merging PR #10/#9, changing main, enabling auto-merge or starting D2–D5. All final refs/statuses are rechecked at delivery.

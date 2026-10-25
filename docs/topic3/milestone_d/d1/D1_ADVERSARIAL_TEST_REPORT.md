# D1 adversarial test evidence

This is deterministic, synthetic review evidence. No source-grounded held-out dataset, new SEC filing, vector generation, ranking experiment or financial answer was produced. The reviewer is the same Codex system doing a fresh pass, not an independent human.

## Before/after method

Original source: `4506e3e0346ce1107fefe90d2cc2e57e8bdfa3f5`. Tests were authored in a separate review worktree; the original source was exercised before any production edit. The complete52-test review file was also executed from the clean original checkout with explicit `--rootdir=.` and the review test path, confirming `app.financial_query.__file__` referred to the original checkout. That avoids accidentally testing repaired modules while claiming original failures.

| Run | Result | Meaning |
|---|---|---|
| Original existing `tests/test_financial_query.py` |114 PASS,1.53s |Original suite alone misses the counterexamples |
| First36 new tests, original source |17 FAIL,19 PASS,0.77s |Minimal failures saved before repairs |
| Complete52 new tests, original source |18 FAIL,34 PASS,0.97s |Additional unsigned-number example fails too; unrelated controls pass |
| Repaired combined original+new D1 suite |166 PASS,1.76s |No original test removed or rewritten |
| Repaired original focused command |114 PASS,1.69s |Explicit original-suite reproduction |
| Repaired review-focused command |52 PASS,0.94s |All new counterexamples/controls pass |
| Repaired full suite |361 PASS,3 SKIP,1 warning,56.83s |All available regression; expected media skips |
| Repaired core (`not integration`) |361 PASS,3 deselected,1 warning,86.23s |Windows has Tesseract; no test skip in this selection |

Tested implementation commit: `901a4d389aedbdc69d0d744d437c95cdc113097e`. The full-suite run immediately before that commit used identical Python/fixture bytes. Separate merge-candidate outcomes are in [integration report](D1_INTEGRATION_CANDIDATE_REPORT.md).

## New inventory:52 cases/tests

All tests are in `tests/test_financial_query_review.py`; the11 named query oracles are stored in `tests/fixtures/financial_query/review_counterexamples.json`. This file was added rather than mutating the original40-case fixture or historical measurement JSON.

| Inventory / count | Attempt to falsify | Original observation → repaired behavior |
|---|---|---|
| F01 CIK decimal/path,2 |Never use a valid prefix of an invalid explicit identifier |Both falsely resolve CIK202 → INVALID_INPUT |
| F02 unsupported/malformed forms,3 |Never ignore20-F or truncate10-k/ab |Two falsely resolve10-K → clarification;10-q2 already blocked and remains control |
| F03 invalid/compact/bare periods,3 |Never silently drop q5, fy2025q2 or2200 |Three falsely resolve → clarification |
| F05 unit order/conflict,2 |No multiplier/currency loss |USD-million order loses scale, USD-percent loses currency → clarification |
| F06 explicit conflict plus fiscal filter,1 |Conflict must not become corpus absence |NO_ELIGIBLE_EVIDENCE → NEEDS_CLARIFICATION |
| F04 long parenthetical Decimal,1 |Numeric precision independent of decimal context |Rounded at6/28 precision → exact at6/28/50 |
| F05 unsigned formatted amount,1 |No removal of numeric predicate |Empty numeric list → Decimal1250.75, unit UNKNOWN |
| F07 contradictory shared accession,1 |Catalog lineage rejects inconsistent submission metadata |Accepted → INVALID_INPUT |
| Consistent co-registrants,1 |Do not outlaw repeated accessions or derive subject CIK from prefix |Allowed with explicit issuer; accession alone ambiguous, before and after |
| F08 overlong catalog text,1 |Question bound must not be mistaken for catalog bound |100k label accepted → INVALID_INPUT |
| F09 attribution qualifier,1 |Do not collapse parent-attributable income into net income |Unqualified exact metric → qualified exact metric, related only to net income |
| F09 unit-token boundaries,2 |Percent points ≠ percent; steps ≠ EPS |Incorrect extra units → correct token-based units |
| Equivalent verified aliases,6 |CIK padding/ticker/name/alias should preserve membership |Same expected Beta filing, before and after |
| Catalog permutation/addition,1 |Order or unrelated catalog item must not change result |20 seeded permutations and unrelated addition stable; genuine ticker collision appropriately changes to ambiguity |
| Added restrictions,5 |Explicit constraints never broaden RESOLVED membership |Never broadens; conflicts/absence remain typed |
| No I/O/execution/mutation,1 |Queries cannot open files/sockets/SQL or execute text |Monkeypatched `open/eval/exec/socket/sqlite.connect` remain unused; catalog unchanged |
| Invalid/cyclic catalog+generation,1 |Typed validation failure rather than no evidence or crash |Malformed JSON string, unknown field, cycle and generation mismatch rejected |
| Forged valid-looking hash/alias,1 |Distinguish authentication from structure |Accepted as trusted supplied metadata, **not authenticated**; explicit upstream dependency, not a repaired defect |
| Mutated empty resolved scope,1 |Empty membership cannot be revalidated as RESOLVED |Pydantic correctly rejects before and after; initial review hypothesis disproved |
| January fiscal/comparative/free-text-only,1 |No calendar/filing-year substitution or promoted free-text label |Typed comparative FY2024 survives2025 filing; calendar/filed2024 not inferred; missing typed columns clarify |
| Bounded pathological queries,1 |No hang on near-limit literals/parentheses/path-like data |Four bounded requests complete inside generous5s guard, before and after; no throughput claim |
| Four fiscal quarters,4 |Only verified requested quarter refs qualify |Q1–Q4 match their synthetic typed refs, not a ticker calendar |
| Required numeric examples,6 |Signs/precision/scales/percent/points remain distinct |Unsigned grouped decimal was dropped; all six now exact |
| Distinct multiple metrics,4 |No plain revenue/net-sales, income, liability or EPS collapse |All remain separate concepts |
| Adapter mismatch controls,1 |Manifest/content/hash/version mismatch must fail without source reads |Raw/normalized/version/hash mismatch rejected; byte authenticity still upstream |

## Commands and environment

`python` below denotes the existing configured venv interpreter, explicitly selected when running from the worktrees. No package installation or dependency update occurred. Test environment matched the repository core workflow: `SCORE_THRESHOLD=0.55`, `RUN_REAL_MEDIA_TESTS=0`. Real-media opt-in conditions were preserved.

```text
python -m pytest -q tests/test_financial_query.py
python -m pytest -q tests/test_financial_query_review.py --tb=no
python -m pytest --rootdir=. -q <review-worktree>/tests/test_financial_query_review.py --tb=no
python -m pytest -q tests/test_financial_query_review.py tests/test_financial_query.py
python -m compileall -q app scripts
python -m pytest -q
python -m pytest -q -m "not integration"
git diff --check
```

Windows11 build10.0.26300; Python3.13.2; Pydantic2.13.5; pytest8.4.2; FastAPI0.142.2; Starlette1.7.0; httpx0.28.1; qdrant-client1.20.0. The sole local warning is the pre-existing Starlette/httpx TestClient deprecation. Full-suite skips are the three existing real-media tests gated by `RUN_REAL_MEDIA_TESTS`; core deselects those three. No source test was disabled to obtain green results.

One intermediate repair guard accidentally recognized the Q in10-Q followed by an accession as a period. The unchanged original explicit-filing test caught this (1 FAIL/149 PASS); the guard was narrowed to exclude a preceding hyphen. All final results above include that correction. This is disclosed as repair-development evidence, not an open finding.

## Qualifications and unverified assumptions

- Metamorphic checks cover a finite seeded space, not all English questions/catalogs. Adding a genuinely colliding alias may legitimately make an old query ambiguous.
- Restriction monotonicity applies to **RESOLVED** results. Unresolved scope may retain uncertain candidate membership, e.g. missing filing-date metadata; consumers must gate on status.
- Caller inputs are not mutated. Frozen Pydantic objects do not promise deeply immutable Python lists; external data must be revalidated before trust.
- Structural catalog checks cannot authenticate a forged-but-well-formed hash, alias or column source ref. Tests deliberately demonstrate that dependency rather than invent a provenance guarantee.
- New input budgets bound accepted data, not worst-case execution time for every allowed large catalog. No distributed/service DoS certification or scale claim is made.
- Original D1 benchmark JSON is unchanged. It is not evidence of repaired-code latency; no new retrieval quality/end-to-end speed claim was tested.
- Live UI, Ollama output, owner historical physical-disk hashes and arbitrary real-world issuer/filing language are NOT_TESTED in this review. Temporary-fixture C search/security/provenance/legacy regressions are exercised in the full suite.

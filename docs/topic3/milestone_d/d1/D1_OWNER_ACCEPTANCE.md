# Milestone D1 owner acceptance

Date: 2026-10-26 (Asia/Bangkok). Authorization: `TOPIC3_MILESTONE_D1_CONDITIONAL_OWNER_ACCEPTANCE_AND_CONTROLLED_INTEGRATION`.

Status: **MILESTONE_D1_ACCEPTED_WITH_DOCUMENTED_LIMITATIONS**.

This owner-authorized acceptance follows the earlier independent-style review by the same Codex system, not independent human review. Earlier reports and PR review statements prohibiting integration describe their historical authorization boundary; this later authorization permits the controlled D1 merge after its mandatory gates pass. Original reports and measurements remain unchanged.

## Exact accepted identities

| Object | Identity |
|---|---|
| PR | [#10](https://github.com/Doquocdung1609/tinyllama-fastapi/pull/10), merged/closed |
| Source branch | `codex/topic3-milestone-d1-query-understanding` |
| Reviewed source | `fae5f070973d86b187425e5959a62560bbb354b1` |
| Target branch | `codex/topic3-milestone-b-sec-corpus` |
| Target before integration | `d1d5195b26f77d8fb25c830229c4c3693d4b638f` |
| Tested two-parent candidate | `a527b9fa8a0bf0ec0e35c8010879cae3f78928db` |
| Accepted merge | `182771470841b805d2f8d78f11b7dfa70c2dfc99` |
| Candidate/source/merge tree | `1c0657d27a55a104bebe513f31d996e43de8af08` |

GitHub's standard merge API used method `merge` and expected source SHA enforcement. No squash, force push, auto-merge or branch-protection bypass was used. The merge has target then source as its two parents. PR #9 remains Draft/open/unmerged at `bcd5728afda4207e79ebf789edd73594aab60bbe`. Remote main remains `ceaa8acfcfaea8056e45b859a0fc44d6381fb22a`.

## Acceptance scope and evidence

Accepted capability: deterministic, versioned Python query-intent and SEC metadata-scope resolution, isolated and opt-in. No route imports D1; Financial Search retains accepted C retrieval. There are no API/UI/dependency/workflow/migration changes. D1 is not activated in production search.

All nine demonstrated findings were re-inspected. Four HIGH findings have permanent passing regressions: whole invalid CIK tokens (F01), malformed form/accession tokens (F02), malformed fiscal periods (F03), and exact context-independent parenthetical Decimal values (F04). Five MEDIUM repairs cover numeric/unit preservation, conflict precedence, shared-accession consistency, catalog bounds, and qualified metric/unit semantics. All 56 adversarial tests and 114 original D1 tests passed again; no demonstrated HIGH/CRITICAL issue remains open. See [review](D1_INDEPENDENT_REVIEW_REPORT.md) and [adversarial evidence](D1_ADVERSARIAL_TEST_REPORT.md).

Current-head [CI run 40189308404](https://github.com/Doquocdung1609/tinyllama-fastapi/actions/runs/40189308404), job `121156698734`, succeeded. Logs identify the exact candidate/source/target above: Linux/Python 3.13.16, 364 PASS/1 SKIP/3 deselected/1 warning. Local candidate and actual merge both passed complete regression, detailed in [integration report](D1_INTEGRATION_REPORT.md). Three local full-suite media skips remain opt-in; the existing Starlette/httpx warning is disclosed. No test was weakened or disabled.

## Scientific and owner-data integrity

All **524 existing accepted-baseline tracked blobs** are byte-identical on the source, candidate and accepted merge. The PR adds only 24 D1 files. Frozen 14-query Recall@5 BM25/Dense/Hybrid remains 0.911/0.321/0.714. Consumed held-out evidence remains untouched; no query/judgment/measurement is rerun, tuned or rewritten. BM25 remains the recommended default on the accepted evaluated corpus; Hybrid superiority is not established. D1 fixture latency is not retrieval-quality evidence.

Tests used isolated synthetic fixtures and temporary indexes. No owner SEC corpus/Qdrant generation was opened for an experiment, activated, cleaned up or overwritten. No SEC acquisition, model download, real embedding, ranking experiment or migration occurred. Owner primary checkout was clean before and after tests. This is non-destructive tracked-state/operation evidence; a fresh physical-disk hash audit of untracked owner history is **NOT_TESTED**.

## Limits and upstream dependencies

- `RESOLVED` means corpus metadata scope resolved. It does not establish retrieved evidence, metric presence, correct financial amount/unit, citation validity or answer accuracy.
- Structural Pydantic validation and catalog lineage/membership checks are distinct from cryptographic source-byte authentication. D1 trusts the caller's verified aliases/typed column metadata. Authentic source-byte verification remains an upstream C provenance responsibility; a syntactically valid forged catalog is not authenticated by D1.
- Supported English grammar and terminology are finite. Missing fiscal calendars, incomplete typed columns, uncertain amendment links, ticker collisions and partial extraction remain explicit clarification/warning cases. Amendments do not synthesize merged statements.
- Complexity budgets and bounded tests do not certify worst-case service performance or production security. No fresh live UI/Ollama smoke test occurred during this acceptance (**NOT_TESTED**).

This acceptance makes no claim of financial-answer correctness, production certification, retrieval improvement or Hybrid superiority. It authorizes no D2-D5 implementation. D2 planning can use the accepted contracts and explicit provenance/column dependencies, but implementation requires separate authorization. PR #9 is not merged.

The two acceptance documents are published by a subsequent documentation-only commit on the accepted target; that commit does not change the code accepted at the merge identity above.

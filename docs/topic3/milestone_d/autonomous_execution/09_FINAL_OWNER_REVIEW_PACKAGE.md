# Owner review package — final evidence snapshot v2

Status: **TOPIC3_D2_D5_PARTIALLY_COMPLETE_WITH_BLOCKERS**. This v2 summary supersedes the historical progress notes retained at the end of this file. Authorization `TOPIC3_AUTONOMOUS_D2_TO_D5_GATED_EXECUTION_AUTHORIZED` permitted sequential research stages, isolated SEC acquisition and Draft PRs; it did not authorize merging any stage, changing main or accepted retrieval defaults. Accepted integration baseline remains `32c4a4834c5f8a0b34ac28c42f960c862dd8077d`.

```mermaid
flowchart LR
 D1[Accepted D1 scope] --> D3[Research D3 retrieval]
 D3 --> D2[D2 evidence]
 D2 --> D4[Bounded D4 verifier]
 D4 --> UI[Opt-in API/UI]
 UI --> D5[Frozen D5 evaluation]
```

## Reviewable delivery

| Stage | Draft PR and exact stacked base | Delivered result | Checkpoint |
|---|---|---|---|
| D2 | [#11](https://github.com/Doquocdung1609/tinyllama-fastapi/pull/11), based on accepted C `32c4a483`, final source `470bf86a` | Three source-correspondence repairs and 14 adversarial tests; 6/6 retained real examples exceed unchanged 250 KiB cap | COMPLETE_WITH_LIMITATIONS |
| D3 | [#12](https://github.com/Doquocdung1609/tinyllama-fastapi/pull/12), based on D2 `470bf86a`, final source `e8230ddd` | Seven fixed research arms and frozen lexical-only official SEC diagnostic; no Dense or adaptive quality winner | IMPLEMENTATION_COMPLETE_SCIENTIFIC_COMPARISON_BLOCKED |
| D4 | [#13](https://github.com/Doquocdung1609/tinyllama-fastapi/pull/13), based on D3 `e8230ddd`, final source `1e0b9e04` | Typed Decimal claim verifier, separate opt-in ASGI/Streamlit paths, synthetic positive QA, real SEC numeric abstention | D4_DETERMINISTIC_ONLY |
| D5 | [#14](https://github.com/Doquocdung1609/tinyllama-fastapi/pull/14), based on D4 `1e0b9e04`; exact final head in PR | One preregistered held-out diagnostic, live local API/UI checks, 24-scenario ledger and open limitations | PARTIALLY_COMPLETE_WITH_BLOCKERS |

All four PRs are intended to remain **Draft, open and unmerged**. PR #9 research blueprint remains separate. This package does not request integration.

## What works and what has not been shown

Actual official SEC files PG, COST and HD were acquired under the fixed bounded plan into an owner-marked research namespace, with raw SHA-256 and manifest identity recorded in [D3 dataset freeze](../d3/D3_DATASET_FREEZE_MANIFEST.md). A persistent SQLite BM25 research index serves C-verified parent chunks, with D1 issuer/filing scope and pinned generation. The opt-in real FastAPI endpoint and Streamlit page displayed PG evidence, form, report date, partial-extraction warning, official SEC Archive URL and structural locator. It returned **no numeric claim** because D2 cannot form verified cell contexts from these >250 KiB sources. The source link was visible; the browser did not confirm landing on the SEC page after clicking it.

The synthetic demo, explicitly marked as invented and sourced to `example.invalid`, exercised D1→D3→D2→D4 and displayed a source-derived 100,000,000 USD claim with a cell locator. Dense/fixed RRF visibly failed safely. No real financial-answer accuracy or LLM behavior was established. Legacy Chat/RAG source paths were unchanged and passed regression; a live legacy UI was not rechecked. Financial Search production defaults were unchanged.

## Scientific evidence

The original accepted C 14-query Recall@5 remains BM25 `0.911`, Dense `0.321`, Hybrid `0.714`; on its evaluated corpus BM25 remains the recommended default. These historical metrics are not compared directly with new partitions. New source manifest `86ad36365fbfb813e78e14246a48ae5735d7a8a1218f73daa4289caa98b215d0`, generation `8f0a7ba5ed851313a9948ddb465753c54012d94f9c36942239f7b2ec15b5e2fb`. Development/validation: 11 literal-row queries, BM25 Recall@5 `0.701515`; Dense/fusion channels unavailable, no adaptive finalist ([D3 comparison](../d3/D3_BASELINE_COMPARISON.md)). The frozen HD held-out was opened **once** after preregistration `ce2c362b9cf894b523ec47b1cd6bae87b8f377e5cdc8cc9275247b7a369e71c7`: 5 auto-labeled exact-row queries, BM25 Recall@5 `0.685714`, MRR@5 `0.700000`, nDCG@5 `0.670731`; Dense/fixed RRF had 0 valid runs. One issuer and zero human adjudicators preclude issuer-cluster confidence intervals and broad quality claims. First exact net-sales parent ranked seventh, a recorded negative result ([raw ranks](D5_FROZEN_HELDOUT_RESULT_v1.json), [interpretation](D5_SCIENTIFIC_EVALUATION_REPORT.md)).

D4 synthetic QA fixture: 4/4 answerable cases correct, 4/4 unanswerable cases abstained; correctness across all eight under the answer-only definition 4/8 ([frozen case labels](D4_SYNTHETIC_QA_CASES_v1.json), [results](D4_SYNTHETIC_QA_EVALUATION_v1.json)). Offline same-bundle verifier ablation rejected 5/5 deliberate forged claims; an unchecked draft path would accept them ([ablation](D5_VERIFIER_ABLATION_v1.json)). This measures a deterministic guardrail on one invented bundle, not LLM hallucination or SEC QA accuracy. No held-out tuning or historical evidence rewrite occurred.

## Tests, security and operations

D2 local: 112 focused PASS, 477 full PASS/3 SKIP; final-head GitHub Actions run `40266090006` success. D3: 40 focused PASS, 517 full PASS/3 SKIP; run `40280668811` success. D4: 35 focused PASS, 552 full PASS/3 SKIP; run `40284075689` success on `1e0b9e04`. D5 current local: `python -m compileall -q app scripts`; `python -m pytest -q` → 552 PASS/3 SKIP/1 warning; non-integration suite 552 PASS/3 deselected/1 warning. D5 final-head CI must be verified from PR #14 after this documentation commit; no CI success is claimed here before that run. The warning is a Starlette/httpx TestClient deprecation, not a failed test.

Twenty-one actual localhost HTTP requests returned 20 HTTP 200 typed responses and one unauthorized 401; the HTTP 200 cases include explicit abstentions. Two live Streamlit modes were observed in a fresh browser session. The 24 E2E scenarios and exact inputs/results are in [E2E report](D5_E2E_VALIDATION_REPORT.md) and [HTTP log](D5_LIVE_HTTP_MATRIX_v1.json). Scenario 21, concurrent reads during generation publication, remains NOT_TESTED live. Synthetic restart reused the same generation without rebuilding SQLite. The opt-in API defaults to 503 without configuration, rejects bad authorization and oversized input, and exposes no mutation route. A non-ASCII Authorization 500 was reproduced and repaired before D4 delivery; regression asserts 401. All 550 accepted baseline Git blobs remain byte-identical at Git level; all three new official SEC raw hashes revalidated. No historical owner Qdrant/SEC directory was used for destructive tests.

Hardware was Windows 11/Python 3.13.2 with ~8 GiB visible RAM and <1 GiB free at preflight. Ollama at `127.0.0.1:11434` refused connections; no large model, vector index or paid service was used. D3 and D5 timing values have different scopes from accepted C HTTP/cold-warm benchmarks. See [resource and limitations report](D5_REPRODUCIBILITY_AND_LIMITATIONS.md).

## Decision and next actions

Do **not** merge this stack on the current evidence. Blocking research dependencies: bounded real D2 source context, compatible vector availability, human-adjudicated cross-issuer/period labels, and demonstrated real numeric QA. Product gaps include conflict-status explanation for contradictory CIK filters, a weak top-ranked PG `net sales` chunk, unconfirmed SEC browser navigation, and untested live publication/read concurrency. Preserve the D5 held-out as consumed; any future evaluation requires a new independently frozen dataset. Review all Draft PRs and authorize any integration or new research separately. No investment decision or production certification is supported.

## Archived v1 progress note (historical, superseded by v2 above)

The initial checkpoint stated D2 review complete and D3/D4/D5 not yet tested. That was a contemporaneous status, not the final state.

## D3 checkpoint addition

D3 checkpoint appended: research implementation and real-source BM25 diagnostics exist, full scientific comparison blocked. D4/D5 still NOT_TESTED at this point. See d3 reports and machine checkpoint events; continue automatically after final D3 CI, no stage merge.

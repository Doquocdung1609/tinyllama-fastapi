# C4R/V8 technical acceptance — 2026-11-04

**Decision: MEASURED_EXPLORATORY_RECOVERY_WITH_LIMITATIONS.** On the new 12-fact source-first English set, opt-in A5_BASE reached **12/12 filing Top-5 and 12/12 source-enriched financial answers** versus faithful author Stage-2 heuristic **11/12 and 11/12**. This is operational parity and a one-case improvement on this small, query-new set. It is **not** a human-certified gold result, a proof of general superiority, or original-chunk cell accuracy. The [K0–K12 gate matrix](C4R_RECOVERY_GATE_MATRIX.json) records all partial gates.

## Actual changes

- `app/financial_query/ontology_v8.py` adds typed English/Vietnamese accounting terms, preserving the original question and separating metrics that should not collapse (e.g. net sales vs cost, gross profit vs gross margin %, parent vs consolidated). Forty contrastive examples are checked.
- `app/research_retrieval/faith_r_a5.py` is opt-in. It filters explicit issuer/form, **does not hard-filter FY metadata**, ranks fiscal end/section/metric evidence, caps original candidates at 60, and records every search attempt and empty/error status. A post-holdout sidecar bug was fixed by reserving slots within 60; only the four dev questions were rerun to measure that correction.
- `app/research_retrieval/financial_answer_v8.py` gives the author and A5 arms the **same** answerer. `ORIGINAL_CHUNK_ONLY` abstains when column context is not verified. `SOURCE_ENRICHED_V1` takes only a filing already retrieved in original Top-5, then checks its byte-verified SEC iXBRL concept/context/period/scale before outputting Decimal value, unit and source locator. Vietnamese queries return a Vietnamese literal in the second paired-language pass. No evaluation answer key is loaded by the runner or answerer.
- Source-first reference freeze and one-run executor/evaluator live in `scripts/topic3_c4r_*`. Private question/answer fields never enter Git; frozen G2, A/B payloads, PR #35 and old G3U/C4 outputs remain unchanged.

## Reproduced failures and measured repair

The old A4 FY-only filter was incompatible with **46/93** target filing payloads, including 10-Q `Q-YYYY-MM` and two TSM 20-F fiscal drift cases. A5's inference filter is compatible with all 46 without knowing the target accession. After the versioned repair, the **exposed** G2 diagnostic ran 94/94 questions with explicit outcomes and found the target filing at Top-5 for **93/93 eligible**. Its previous A4 26 missing-hit-row executions remain provenance-unknown; they were not rewritten as proven misses. This is a post-exposure regression check, not a fresh benchmark. The private per-question register and [public failure taxonomy](R0_FAILURE_REGISTER.md) retain other causes.

The new 16 source-derived facts were frozen before any C4R method output: **4 dev / 12 holdout**, distinct SEC filings, 8 10-K and 8 10-Q. Raw SEC package hashes match the frozen source manifest; 16/16 chosen iXBRL element IDs also had the expected displayed row label and literal in a separate row-text QA pass (private SHA `91195af539cfd3ac817d6811b71f6a1d3074867aefa9da2a0967edf07a9c2c28`). The reference remains **machine/AI verified, not human signed**. The generator and answerer share the iXBRL extraction rules, so answer exactness is an *exploratory source-derived check*, with method differences chiefly from retrieving the right filing. No original-chunk EXACT qrels were fabricated.

The [answer-level scorecard](C4R_ANSWER_LEVEL_SCORECARD_VI.md) shows all six author methods, A5 ablations, numerator/denominator, refusals, bilingual paired results, p50/p95 and uncertainty. The single English A5 gain over Stage-2 is AMD 10-Q `0000002488-25-000108`; the other 11 are ties, with no A5 loss on this 12-fact set. Wilson 95% intervals for 12/12 and 11/12 overlap. `ORIGINAL_CHUNK_ONLY` correctly abstained 12/12 for both methods because the original flattened chunks lack a verified column/context relation. For Vietnamese, 12 paired paraphrases of the **same** facts gave A5 12/12 versus Stage-2 10/12; they are not 12 extra independent facts. A second, explicitly post-exposure language pass confirmed 12/12 Vietnamese answer literals.

The three AMD source-present facts missing from original Part-I chunks remain a corpus limitation. Source enrichment is a distinct track and does not implement those segment-specific answers yet. Comparative, policy narrative, bounded negative, parent-only and OCR-ambiguous answers still require further evidence work. Hòa Phát/BIDV PDF product evidence remains on separate PR #35; C4R added a real [paired Vietnamese/English retrieval smoke](C4R_HPG_BIDV_PAIRED_PDF_SMOKE.json) with 12/12 HTTP 200 and five candidates, but no new trustworthy numeric PDF gold. Its Top-1 page changes by language/mode; no PDF answer-accuracy score is claimed. No new embeddings, paid model, index mutation, final G2 qrel benchmark or model tuning on the 12-fact holdout occurred.

## Tests, resources and handoff

Local **47 targeted tests PASS; 815 full Python tests PASS**, 0 failures, one existing Starlette/httpx deprecation warning. All 108 English holdout method executions, 108 Vietnamese paired method executions and every refusal/error have private question-level rows. The [wrong/refused casebook](C4R_WRONG_ANSWER_CASEBOOK.md) indexes 121 English holdout refusal/wrong rows; **zero wrong emitted numeric values** were seen in the 12-fact sample. Three real negative controls abstained. The owner laptop used CPU ONNX cache: English holdout peak process RSS **1,328.19 MB**, 98.35 seconds wall time, with about 1.53 GiB available RAM immediately after that run. No OOM occurred; Colab was not required or run. Fixed method order and warmed source cache make the measured method latencies unsuitable for a speed-superiority claim. [Resource report](C4R_LATENCY_RESOURCE_REPORT.json).

Final private handoff: `C:\Users\Admin\Downloads\C4R_PRIVATE_HANDOFF_20261104_V4.zip`, SHA-256 `82350fd486a6b0617c6169ecb5f3aea90395d17d0180ad37a0cdad7fe8f1ab28`, **28 members**, ZIP CRC and every member SHA/size PASS. [Public SHA manifest](C4R_PRIVATE_HANDOFF_MANIFEST_V4.json). Earlier V1–V3 packages remain unchanged as history. The public [evaluation lock](C4R_NEW_EVALUATION_MANIFEST.json) pins private reference SHA `fe192c60300282dd7b55b0e14c2c51db9ba92fca1804b2b12b614b96e938c140`; [protocol V1](C4R_BENCHMARK_PROTOCOL_V1.json) SHA `cafcb6a57766e537f5dbadd2f6e2264b616df787fa5e06c406bed9de0e4c0343` was written before the new run.

## Reproduce safely

From `C:\Users\Admin\Documents\GitHub\tinyllama-fastapi`, inspect the immutable scorecards and run the unit/regression suite:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_topic3_c4r_a5.py
.\.venv\Scripts\python.exe -m pytest -q
```

For a **live non-benchmark** Vietnamese query on index B (the command reads no gold):

```powershell
.\.venv\Scripts\python.exe -m scripts.topic3_c4r_demo --question 'Tesla báo cáo tiền và các khoản tương đương tiền tại ngày 2023-12-31 trong hồ sơ 10-K là bao nhiêu triệu USD?' --index-b tmp/topic3_v5r/restored/B --source-manifest docs/topic3_v7a_g3/V7A_G3S_SEC47_RAW_SOURCE_MANIFEST.json --author-root tmp/topic3/original-author --cache tmp/topic3/model-cache
```

The live command was run and returned `COMPLETED_WITH_HITS`, `VERIFIED_SOURCE_CELL`, Vietnamese output and a `https://www.sec.gov/...#f-...` locator. Its private JSON SHA is `3b4f4680a3623825ca5ad861063131aac4cbac4d58db0c741c99548919fad483`. The demo reads source HTML **after** finding a filing. Do not present the number as recovered from a single original chunk. Do not rerun the locked 12 English holdout as a new independent test; use new versioned facts for future tuning.

**Presentation status:** the C4R CLI financial-source demonstration and the existing PR #35 Hòa Phát/BIDV React demo are usable with the above limits. A broad, independently human-checked financial-answer benchmark and original-chunk qrels remain pending. No merge is authorized or performed.

GitHub CI for C4R commit `3611f7f`: [Python core PASS](https://github.com/Doquocdung1609/tinyllama-fastapi/actions/runs/41682526102/job/126079616854) and [frontend test/build PASS](https://github.com/Doquocdung1609/tinyllama-fastapi/actions/runs/41682526102/job/126079616223). The runner warned about future Node/Ubuntu action migrations; neither job failed.

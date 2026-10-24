# Milestone B — Final gap audit, 24/10/2026

**Recommendation: VERIFIED_WITH_DOCUMENTED_LIMITATIONS**, limited to the agreed pilot financial-corpus ingestion/provenance scope. The repository owner retains final acceptance authority. This is an audit recommendation; the filing's conservative `PARTIAL_EXTRACTION` state is unchanged.

Baseline reviewed: `058b33ef279c2cd10b3c5e65dfcb7828a90d6c69`. Minimal repair/evidence commit: `ed7ec575d9a38d258b54f673c29b9fd5c2160dab`. Same branch `codex/topic3-milestone-b-independent-verification-20261024`, same [Draft PR #7](https://github.com/Doquocdung1609/tinyllama-fastapi/pull/7), target `codex/topic3-milestone-b-sec-corpus`. No merge, force-push or Milestone C implementation.

## 1. Classification of the four unresolved tables

Indices are **zero-based** and bound to this exact primary SEC source and raw bytes:

https://www.sec.gov/Archives/edgar/data/320193/000032019326000020/aapl-20260627.htm

Raw SHA256: `d2fa42061d517dc6fd528f32a09197553f0d70214405f6fc09497829c95e8b8c`.

These are manual source-review findings in MILESTONE_B_TABLE_GAP_CLASSIFICATION.json, not an automatic classifier or parser status override. FINANCIAL_DISCLOSURE includes substantive accounting/financial explanatory notes, even without amounts. Regulatory cover declarations and the exhibit index are classified by their actual purpose, not by the presence/absence of numeric iXBRL facts alone.

| Index | Purpose and classification | Financial values / information loss | Recovery from source |
|---|---|---|---|
| 5 | Cover-page legal identity/address; LEGAL_OR_ADMINISTRATIVE | 94-2404110 is an employer tax identifier, 95014 is a postal code; neither is a financial amount. Source labels below the values survive in raw/cells; typed administrative-field interpretation is incomplete. | Labels for state, employer ID, executive-office address and ZIP are explicit. Recoverable without invented headers. |
| 9 | Filer-category checkboxes; LEGAL_OR_ADMINISTRATIVE | Large accelerated filer is checked; the other category boxes are unchecked. Regulatory relevance exists, but this is not a financial balance/performance measure. Text/checkbox relationships remain in source/grid. | Source paragraph explicitly explains the category checkboxes; typed flags are not normalized. |
| 11 | Contents/navigation; DOCUMENT_LAYOUT | Numbers 1/13/19/20/21/24/25 are printed filing-page references, not amounts or HTML-to-PDF page metadata. A Page label exists in source but is not normalized into columns. | TABLE OF CONTENTS, section labels and internal anchors make the purpose unambiguous. Navigation normalization remains limited. |
| 38 | Item 6 exhibit index; LEGAL_OR_ADMINISTRATIVE | 31.1/31.2/32.1/101/104 are exhibit IDs, not financial amounts. The actual header row remains in raw/grid. References to financial statements are not the statement values themselves. | Exhibit Number/Description/Form/Exhibit/Filing Date-Period End Date are explicit after a merged Incorporated by Reference row. Typed exhibit/link normalization is incomplete. |

Exact locators:

- Index 5: `table_e8223f402df1d87c223d961e` → `/document[1]/html[1]/body[1]/div[23]/table[1]`.
- Index 9: `table_9ec38cac80a4844632a4b4b1` → `/document[1]/html[1]/body[1]/div[35]/table[1]`.
- Index 11: `table_21ab125fbc4b00c23e96d980` → `/document[1]/html[1]/body[1]/div[50]/table[1]`.
- Index 38: `table_5054ebe830bcaf8c37685853` → `/document[1]/html[1]/body[1]/div[338]/table[1]`.

No identified financial statement amount is lost from these four tables. This does not mean their generic extraction is complete: administrative fields, checkbox forms, navigation and exhibit relationships remain semantically under-normalized. The raw/cell content remains recoverable. We retain PARTIAL for all four and for the whole filing; no source table was reclassified in production to obtain acceptance.

The financial-context acceptance evidence remains the independently checked balance sheet, income statement, cash-flow statement, EPS note and 28 value/period/unit cases. This is representative pilot evidence, not a claim of exhaustive correctness for all issuer disclosures or all footnotes.

## 2. Status semantics and minimal backward-compatible repair

`READY` means the configured parsing/chunking/staging steps finished without parser warnings. It does not prove financial completeness, numerical correctness, semantic indexing or advisory-answer accuracy. `PARTIAL_EXTRACTION` means the artifacts exist but at least one parsing/context warning remains. Jobs may be COMPLETED while a filing is PARTIAL; registry and immutable manifest partial-document lists continue to report that fact.

The current enum cannot distinguish administrative ambiguity from missing financial context or recoverability. For these four source tables the issue is recoverable by source-aware interpretation. Missing/corrupt source or unsupported association needs separate investigation; PARTIAL does not imply either permanent data loss or safety to infer missing values.

Minimal change: add **GET /financial-corpus/quality/{filing_id}**, backed by a read-only pipeline diagnostic. It reports the registered document status, per-table warnings, context-present flags, numeric-fact counts and unresolved-table count. It separately reports **financial_completeness=NOT_ASSESSED** and explicitly says that purpose/completeness requires independent source review. Zero numeric facts is not used as an automatic nonfinancial classification.

Live endpoint result for Apple: document_status=PARTIAL_EXTRACTION, table_count=40, unresolved_table_count=4, financial_completeness=NOT_ASSESSED. The endpoint does not verify provenance by itself and says so. Missing filing/snapshot returns 404/410; invalid structured payload returns 409.

No parser/chunker version, raw/structured/chunk bytes, filing status, registry schema or manifest schema/hash was changed. This avoids silently invalidating historical manifest hashes by adding serialized defaults. Regression checks assert no mutation and no financial-completeness claim for either READY or PARTIAL.

## 3. Real SEC amendment validation

Chosen company: Tesla, Inc., CIK 0001318605. One amendment was selected from recent SEC submissions and its original found in a bounded set of 20 originals. The shared client uses the configured private contact User-Agent, 1 request/second, timeout 25 seconds and at most one retry. Only the two selected primary documents were downloaded; repeat audits reused them.

| Field | Original | Amendment |
|---|---|---|
| Form | 10-K | 10-K/A |
| Accession | 0001628280-26-003952 | 0001104659-26-053166 |
| Filing date | 2026-01-29 | 2026-04-30 |
| Report date | 2025-12-31 | 2025-12-31 |
| HTTP | 200 | 200 |
| Raw SHA256 | `78bd6ce48d15320a703cedfd0b4603999b69746d63abd013ed83923b59069ed4` | `04085826be0cf868dab0db23a6529a62c089e1ad1b0b95188ccaa7acf8fa0888` |
| Chunks | 1,609 | 597 |

[Original source](https://www.sec.gov/Archives/edgar/data/1318605/000162828026003952/tsla-20251231.htm) · [Amendment source](https://www.sec.gov/Archives/edgar/data/1318605/000110465926053166/tm2611837d1_10ka.htm).

The amendment's EXPLANATORY NOTE explicitly identifies the original Form 10-K filed January 29, 2026 for the year ended December 31, 2025. It explains that the amendment adds Part III information and certifications, rather than generally updating all original disclosures. This independently supports the relationship beyond a same-period registry heuristic.

`amendment_of=sec:0001318605:0001628280-26-003952`. Two separate filing IDs, raw directories and registry records remain. Original raw bytes and the original-only manifest are unchanged after amendment ingestion. Original-only snapshot `v1-5e37c84f1ae26a32` (1 document) becomes a new two-document snapshot `v1-ee6129b054db1ebb`; the earlier manifest is retained. Final manifest hash `fad83b03abafefe126fb01c7147961544f91baa5ae1db7ff4ca7a5031f38e2a4`.

Repeated ingestion reuses both filings, preserves their counts and the final manifest. Real **10-K/A lineage/immutability** is verified. 10-Q/A remains fixture-tested. Tesla whole-document extraction is PARTIAL; this test does not certify every Tesla financial table. Automatic linkage requires the original to be present; amendment-first backfill is not asserted.

## 4. Historical revision retrieval and acceptance scope

Supported today: registry/API distinguish original and amendment by separate CIK/accession filing IDs. Manifest inventory retains previous snapshots and paths. Raw, structured JSON, chunks JSONL and manifests remain on disk in versioned paths. Reprocessing tests confirm old bytes persist.

Unsupported today: `registry.get_chunk(old_id)` and GET /evidence/old_id do not resolve a prior derived revision after the active chunk records have been replaced; the endpoint returns 404. A controlled fixture test verifies both the preservation and this interface limit. Historical original/amendment filings are distinct from parser revisions of one filing.

The pre-existing FINANCIAL_CORPUS_ARCHITECTURE.md explicitly describes one active membership/revision and defers multi-snapshot membership schema to a later milestone. DATASET_AND_PROVENANCE.md commits to immutable artifacts/manifests; it does not promise an archive-query API. Therefore amendment/original identity and immutable preservation are Milestone B requirements and are verified here. Arbitrary old-derived-chunk lookup is a previously documented interface limitation, not an unfulfilled pilot API promise. If the owner requires archive querying as a new acceptance condition, that condition remains open; this audit does not redefine it silently or introduce a new retrieval architecture.

Historical audit measured **8 valid manifest content hashes** and recomputed hashes of **8 raw files** across the retained local roots. Derived files remain present, version/normalized-hash metadata and row counts match manifests. Old parser code was not replayed, so this does not re-certify every historical chunk. Apple v5 raw/normalized hashes and its 12 representative chunks were independently checked again.

## 5. Financial Chat failure analysis

Original question: “Explain the purpose of a balance sheet in one sentence.” Empty history, qwen2.5:3b, temperature 0, num_predict 80, num_ctx 4096. Digest remains the owner-matching model.

The two-prompt reproduction uses the same /api/generate endpoint and options; only the prompt string differs:

| Case | Observation |
|---|---|
| Plain question | Correctly describes assets, liabilities and equity at a specific point in time. |
| `_chat_prompt(question, [])` | Reproduces the mixed-language answer using “损益表” and a period-based generic description. This is the same failure archived in integration-v3.json and integration-final.json. |

The wrapper prepends language-following instructions, including a Vietnamese-language conditional, and literal User:/Assistant: markers. It preserves “balance sheet”; it does not substitute “income statement”. No retrieval function is called and no document/source context is provided by this general-chat route. Therefore retrieval and SEC table context are not causes of this failure. The evidence supports **ungrounded model generation interacting with prompt framing**; it does not isolate one particular instruction or prove that changing a sentence will fix financial accuracy.

Ground truth for assessing the distinction: [SEC Beginners' Guide to Financial Statements](https://www.sec.gov/about/reports-publications/beginners-guide-financial-statements) describes a balance sheet as a point-in-time view of assets, liabilities and equity; income statements cover activity during a period. The reproduction is a narrow failure analysis, not a benchmark or financial-advice certification.

No general-chat prompt/model repair was made: grounded financial QA is outside this ingestion/provenance gap audit. Correct RAG behavior on the known financial fixture was checked separately. A correct plain answer does not cancel the wrong wrapped answer or establish general accuracy.

## 6. Regression and evidence

- Targeted: **31 PASS / 0 FAIL / 0 SKIP / 1 warning**.
- Full suite with RUN_REAL_MEDIA_TESTS=1: **147 PASS / 0 FAIL / 0 SKIP / 2 warnings in 27.61s**.
- Two warnings remain Starlette/httpx TestClient and Diffusers/NumPy array-copy deprecations; no failing tests removed or converted to skips.
- Real legacy integration: all 5 checks pass (Chat nonempty, expected RAG answer, correct filename/page, Qdrant dimension 768, expected error responses).
- Apple fresh source request: HTTP 200, 1,018,317 bytes, same raw SHA256; preserved snapshot untouched. Existing ingestion reuses 566 IDs and manifest. Financial audit: 40 tables, 4,762 cells, zero mismatches, 28 value/period/unit cases PASS, 12 provenance samples VERIFIED.
- Controlled tests cover checkpoint/retry/new-instance recovery, both amendment forms, migration preservation, tampered raw/context detection and the documented historical API limit.
- compileall, pip check and git diff --check pass. Updated live API quality endpoint, health/docs and Streamlit health return 200.

All measured JSON/stdout evidence is retained under tmp/milestone_b_verification, excluded from Git. Raw source and SQLite/Qdrant data remain local. The first replay wrote both responses successfully but hit a Windows console encoding error when printing; stdout was made ASCII-safe and the exact reproduction was rerun successfully without changing model requests.

## 7. Updated acceptance matrix

| Gate | Audit finding | Evidence / limitation |
|---|---|---|
| B1 Baseline/PR | VERIFIED | 058b33e verified before work; same contributor branch and Draft PR #7 |
| B2 Environment | VERIFIED | Existing working environment, pip check clean; versions remain documented |
| B3 LLM function | VERIFIED_WITH_DOCUMENTED_LIMITATIONS | Real generation works; ungrounded financial Chat error reproduced |
| B4 Embeddings | VERIFIED | Real 768-dimensional embedding / isolated Qdrant compatibility retained |
| B5 API/Streamlit | VERIFIED | HTTP 200 health/docs/UI; new read-only quality endpoint tested |
| B6 Legacy RAG | VERIFIED | Real PDF→embedding→Qdrant→answer with correct file/page, 5 checks pass |
| B7 SEC | VERIFIED | Fresh Apple HTTP 200/hash match; Tesla original+amendment HTTP 200 |
| B8 Financial table context | VERIFIED_WITH_DOCUMENTED_LIMITATIONS | 28 source value/period/unit cases pass; 4 unresolved tables manually shown outside quantitative financial-table scope; whole filing remains PARTIAL |
| B9 Provenance | VERIFIED | 12 Apple samples rechecked; raw/normalized/context tamper regression passes |
| B10 Idempotency | VERIFIED | Apple 566 IDs/manifest unchanged; both Tesla filings reused without duplicates |
| B11 Recovery | VERIFIED | Controlled checkpoint/retry/restart fixtures; not an OS power-loss test |
| B12 Amendments | VERIFIED_WITH_DOCUMENTED_LIMITATIONS | Real Tesla 10-K/A pair with explanatory-note proof; 10-Q/A remains fixture-only |
| B13 Regression | VERIFIED | 147 PASS / 0 FAIL / 0 SKIP / 2 warnings, real media/OCR enabled |
| B14 Git delivery | VERIFIED | Existing Draft PR #7 updated on the same branch; no merge |

## 8. Remaining limitations and decision

Recommendation **VERIFIED_WITH_DOCUMENTED_LIMITATIONS** applies to this pilot's source identity, representative financial context, immutable snapshots, provenance, idempotency, controlled recovery, real amendment handling and regression compatibility. The four genuine generic-extraction ambiguities are nonfinancial administrative/navigation issues in this exact source. They do not block the scoped financial corpus evidence, while their status and missing normalization remain visible.

Limitations retained: whole filing PARTIAL; financial completeness is not automatically assessed; arbitrary old-derived-revision API lookup absent; real 10-Q/A not run; only one real amendment pair and representative issuer evidence; no OS power-loss/vector corruption test; general Chat can give wrong financial explanations; no production/advisory accuracy claim; financial SEC staging is not a dense-search index. Owner decides whether these limits are acceptable. No Milestone C implementation or PR merge.

## Reproduction commands

```powershell
.\.venv\Scripts\python.exe scripts/audit_preserved_corpus.py --root financial_corpus/collaborator-v5-final --output tmp/milestone_b_verification/gap-preserved-corpus.json
.\.venv\Scripts\python.exe scripts/verify_milestone_b.py --root financial_corpus/collaborator-v5-final --dataset-id collaborator-v5-final --output tmp/milestone_b_verification/gap-apple-audit.json
.\.venv\Scripts\python.exe scripts/audit_live_amendment.py --root financial_corpus/gap-audit-amendment --output tmp/milestone_b_verification/gap-amendment-final.json
.\.venv\Scripts\python.exe scripts/reproduce_financial_chat.py --output tmp/milestone_b_verification/gap-chat-confirmed.json
.\.venv\Scripts\python.exe -m pytest tests/test_final_gap_audit.py tests/test_financial_ingestion.py tests/test_sec_table_context.py tests/test_financial_corpus_api.py -q
$env:Path += ';' + [Environment]::GetEnvironmentVariable('Path', 'User')
$env:RUN_REAL_MEDIA_TESTS='1'
$env:TTS_OUTPUT_DIR='./audio/milestone-b-verification'
$env:IMAGE_OUTPUT_DIR='./images/milestone-b-verification'
$env:VIDEO_OUTPUT_DIR='./videos/milestone-b-verification'
.\.venv\Scripts\python.exe -m pytest -q -rs
.\.venv\Scripts\python.exe scripts/verify_local_integration.py --collection independent_verification --output tmp/milestone_b_verification/gap-integration.json
.\.venv\Scripts\python.exe -m compileall -q app scripts main.py
.\.venv\Scripts\python.exe -m pip check
```

These commands assume the already documented private SEC identity, OCR best-data configuration, local models and isolated API profile. The Tesla script discovers a bounded recent amendment and requires its explanatory note to support the original relationship; future source changes must be reported rather than silently substituted.

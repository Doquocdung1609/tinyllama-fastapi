# Milestone C completion and acceptance

Date: 2026-10-24. Scope: local persistent SEC evidence retrieval pilot, not production or certified financial advice.

## Integration and implementation identity

- B source repaired/reviewed: `bdd12d895a7942ca7763bda7f81e3e735153aa6a` over target `de01cbd4157fcbfdcac3201aed7e2f89ba3b3044`.
- Tested candidate: `22563b6cbdb5e1adeefbb72613118056c4fd8e04`.
- PR [#7](https://github.com/Doquocdung1609/tinyllama-fastapi/pull/7) integrated by ordinary merge into the B target at `bde80f6d672f1744b54ec669300a86844139c54f`; main was not merged.
- Candidate/merged B regressions: 169 PASS each, no failures/skips, two dependency warnings. B pilot accepted with documented limitations.
- C branch: `codex/topic3-milestone-c-persistent-hybrid`, based on acceptance commit `c84c060d1bbf507b01badb8073f22cbf53b9b7ec` (same application code as tested B merge).
- Feature commit: `bb60a82`; lifecycle/retained-source validation and reproducible experiment scripts: `fafe60263ece3807608af1f830197543d94b0bc1`.

## Acceptance gates

| Gate | Status | Evidence and scope |
|---|---|---|
| C1 persistent restart | VERIFIED | Fixture launches a new interpreter; live 822-chunk index built by CLI then served by a new API process without rebuilding |
| C2 no corpus rebuild per query | VERIFIED | Stored postings/DF and query-term SQL; no-retokenization test and formula-matched ranking comparison |
| C3 incremental/idempotent | VERIFIED | Original/amendment/new derived revision fixtures; real unchanged build embeds zero; live 694→822 cached membership update |
| C4 snapshot integrity | VERIFIED | Manifest/source hashes, membership, implementation/model identity, mismatch and tamper rejection tests |
| C5 financial lexical behavior | VERIFIED | Signed values, percentage aliases, fiscal periods/forms/accessions and deterministic ranking/filter fixtures |
| C6 dense synchronization | VERIFIED | Real 768-dimension nomic vectors, generation-specific Qdrant collections, complete prepublish membership and model/dimension mismatch rejection |
| C7 hybrid evidence | VERIFIED | RRF correctness/dedup/ties; live returned evidence source-validated; no raw-score mixing |
| C8 metadata filters | VERIFIED | API/fixtures and source-grounded queries scoped by ticker/form/filing; filter-local lexical statistics |
| C9 legacy compatibility | VERIFIED | Full legacy regression plus five live Chat/RAG checks; available isolated collection unchanged at three vectors; owner's unavailable knowledgebase is NOT_TESTED |
| C10 real performance | VERIFIED | Apple/Tesla pilot benchmark, cold build, idempotent/update, restart, disk/RSS; dense scaling above 822 NOT_MEASURED |
| C11 retrieval quality | VERIFIED | Fourteen frozen source-row development queries, macro Recall/MRR/nDCG@5, exact source locators; no held-out or answer-accuracy claim |
| C12 recovery | VERIFIED | Controlled interrupted build, close/new engine/resume, previous-active preservation, Qdrant failure and retained-generation rollback tests; power-loss NOT_TESTED |
| C13 regression | VERIFIED | Final 182 PASS / 0 FAIL / 0 SKIP / 2 warnings, 32.07 s with real OCR/media enabled (earlier 47.40 s); final targeted 25 PASS |
| C14 reproducibility | VERIFIED | Architecture, implementation, measured benchmark/quality, limitations, source/query manifests, CLI/API/UI verification commands |
| C15 Draft PR | NOT_TESTED | Delivery pending; do not merge C |

Final recommendation is pending Draft PR delivery. The repository owner retains final acceptance authority. All limitations in MILESTONE_C_LIMITATIONS.md remain applicable; successful retrieval/source verification does not establish financial-answer correctness.

## Reproduction

Use the accepted B artifacts with exact manifest hashes in `MILESTONE_C_SOURCES.json`. Paths resolve relative to repository root; local raw files, databases, models and credentials are intentionally not in Git. C uses existing snapshots and makes no SEC fetch requests.

```powershell
# Run from repository root. Ollama with the recorded nomic model must already be installed/running.
# Close the API owning financial_search_data before CLI build; use a separate root for a cold experiment.
.\.venv\Scripts\python.exe scripts/financial_index.py build --dataset sec-pilot-c --sources docs/topic3/MILESTONE_C_SOURCES.json
.\.venv\Scripts\python.exe scripts/financial_index.py status
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
# In another terminal, against that API:
.\.venv\Scripts\python.exe scripts/benchmark_persistent_financial.py --output tmp/milestone_c_verification/reproduction --repeats 3
.\.venv\Scripts\python.exe scripts/verify_financial_search_ui.py
.\.venv\Scripts\python.exe -m scripts.topic3_bm25_scaling --sizes 100 1000 5000 --repeats 5 --output tmp/milestone_c_verification/legacy-scaling-repeat.csv
$env:RUN_REAL_MEDIA_TESTS='1'
$env:TTS_OUTPUT_DIR='./audio/milestone-b-verification'
$env:IMAGE_OUTPUT_DIR='./images/milestone-b-verification'
$env:VIDEO_OUTPUT_DIR='./videos/milestone-b-verification'
.\.venv\Scripts\python.exe -m pytest -q -rs
.\.venv\Scripts\python.exe -m compileall -q app scripts main.py client.py
.\.venv\Scripts\python.exe -m pip check
git diff --check
```

Real OCR/media also requires the configured existing Tesseract best packs, FFmpeg and local Tiny-SD model. Default pytest may skip opt-in media tests; the reported full run explicitly enabled them. Live legacy smoke uses an isolated PDF/RAG collection and configured B root, not a new production knowledgebase.

To query retained indexed generations, pass `generation` on `/financial-index/search`. To roll back, POST `/financial-index/activate` with dataset ID and a retained READY generation; activation validates source integrity and dense membership. CLI supports the same operation when it owns the local Qdrant directory. Do not delete previous generations as a migration shortcut.

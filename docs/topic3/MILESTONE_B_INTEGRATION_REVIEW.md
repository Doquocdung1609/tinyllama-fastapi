# Milestone B integration review — 24/10/2026

Review target: PR #7, target `codex/topic3-milestone-b-sec-corpus`. Initial base `de01cbd4157fcbfdcac3201aed7e2f89ba3b3044`, initial source `bf7be205a03292eac8b08bd2ee8f8df7fb8161c6`. Owner authorizes integration only after gates; `main` is outside this authorization.

## Actual review and findings

Reviewed the complete source diff and current implementations of `html_parser.py`, `chunker.py`, `schemas.py`, `sec_client.py`, `pipeline.py`, `registry.py`, `app/api/financial_corpus.py`, their tests and immutable artifact contracts. Also inspected legacy financial search, Qdrant, embedding, Chat/RAG integration and API mounting. This review uses source and executed evidence rather than accepting earlier completion reports as proof.

| Severity | Finding | Disposition |
|---|---|---|
| P1 / required before integration | Ingestion metadata accepted noncanonical CIK/accession path components; primary filenames were normalized for URLs but used unnormalized in filesystem paths. A crafted API filing could escape intended snapshot directories. | Fixed before integration: require canonical ASCII metadata identifiers, reject rooted/drive/stream/URL-control/reserved filenames, validate dataset IDs at direct ingestion/job/manifest entry points. Rejected before network requests and registry mutation. |
| Documented limit | Large SEC HTML is parsed in RAM and the rate limiter is per client rather than aggregate across processes. | Keep bounded sequential pilot operations. No scale/readiness claim. |
| Documented limit | Whole-document PARTIAL includes four administrative/navigation tables. | Preserve status; read-only quality diagnostic keeps financial completeness NOT_ASSESSED. |
| Documented limit | Historical derived-file storage outlives active chunk lookup; general Chat can misstate financial concepts. | Retain explicit limits; no architecture/prompt expansion during B integration. |

Security-specific checks: HTTPS SEC host allowlist remains enforced before requests and each redirect; redirects are bounded; source identity is checked before writes; filenames/dataset path components now reject traversal and Windows ambiguities; JSON/Pydantic and parameterized SQLite are used, not unsafe deserialization. Atomic file writes and versioned derived paths preserve old artifacts. No credentials are added to logs/remotes and no production Qdrant delete/upsert is introduced by ingestion. Filesystem input tests include the API job path. There is no bypass of branch protection.

Financial-specific checks: multi-row headers retain original grid/cell spans, periods, row-axis group labels, explicit units/sign/scale and original display text. Context inheritance requires supporting source text; nested tables and ambiguous contexts remain visible. Source locators identify physical source rows. Chunk IDs incorporate filing/raw/parser/chunker versions. Provenance rechecks raw/normalized hashes and the complete chunk context. Manifest schemas/hashes and the conservative state transitions are retained. Original/amendment filing identities remain distinct.

## Executed pre-candidate evidence

- Security/connector/ingestion targeted suite: 45 passed before adding the API-specific regression case.
- Full suite at the security repair tree: 168 passed, 0 failed, 0 skipped, 2 existing library warnings; real OCR/Tiny-SD/SAPI/FFmpeg enabled. The final candidate adds one API validation test and is tested separately below/in the pilot-acceptance record.
- Apple pilot audit repeated: 40 tables, 4,762 cells, zero mismatches, 566 stable chunks, 28 financial-context cases and 12 provenance samples. No original corpus cleanup or status promotion.
- Preserved corpus audit: eight immutable manifests and eight raw files retain their expected hashes; derived files/version metadata/counts remain available.
- Real Tesla original/amendment audit repeated with SEC contact and bounded requests: separate identities, explanatory-note relationship, immutable originals/manifests and idempotency pass.
- Real legacy Chat/RAG/Qdrant integration is rerun for the integration gate. Financial SEC staging remains isolated from `knowledgebase`.

Preflight found PR mergeable/CLEAN and no configured CI checks. `gh pr diff 7 --stat` is unsupported by this gh version; equivalent local `git diff --stat origin/codex/topic3-milestone-b-sec-corpus...HEAD` and the actual source diff were inspected. Missing CI is not counted as a passing check. The repository permits merge commits; a regular merge commit preserves all contributor commits. Draft-to-ready transition and merge occur only after the candidate test gate, without admin override or changes to `main`.

## Recommendation

The identified P1 input-validation defect is repaired on the existing PR branch. Integrate only after the final GitHub candidate tree, real source/provenance and compatibility gates pass. Accept only the agreed financial-corpus pilot with documented limitations. Exact tested candidate SHA, merge result and post-merge regression are recorded in `MILESTONE_B_PILOT_ACCEPTANCE.md`; Milestone C remains blocked until that record is complete.

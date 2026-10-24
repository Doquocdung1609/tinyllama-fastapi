# Milestone C implementation

Base: accepted Milestone B commit `c84c060d1bbf507b01badb8073f22cbf53b9b7ec`, following merge `bde80f6d672f1744b54ec669300a86844139c54f`. The owner-authorized B gate passed before C implementation.

## Delivered path

`app/financial_index/corpus.py` resolves registered immutable B manifests, validates raw/structured/chunk hashes, reparses financial context and selects a deterministic, query-independent subset. A partial source requires explicit opt-in. B filing extraction status is never rewritten.

`lexical.py` stores immutable chunk payloads, inverted postings, lengths, per-generation membership/document frequencies, vector cache and the active-generation pointer in SQLite WAL. BM25 retains positive IDF, k1=1.5 and b=0.75. Metadata-filtered scoring uses filter-local statistics, matching the previous formula. Financial aliases add signed amounts, percentages, fiscal/quarter periods, forms and accessions without changing source display or converting units. The legacy tokenizer and `/financial/search` route remain available unchanged.

`service.py` coordinates manifest/tokenizer/scorer/model-bound generations. Batches default to eight, capped at 32. Unchanged chunks reuse postings; identical embedding inputs reuse vectors keyed by installed model digest, dimension and input policy. New generation publication still materializes all membership/frequencies and upserts its full selected Qdrant collection. This is incremental reuse, not O(new-documents) publication.

Dedicated local Qdrant collections use UUID5(chunk ID), with the original ID and payload hash stored reversibly. Collections are isolated from legacy Qdrant. Source/model/dimension/generation/membership validation precedes publication. Failed and interrupted generations preserve the previous active READY generation; resuming reuses persisted work. Explicit rebuild creates a new generation. Retained READY generations support scoped lookup and checked rollback. No historical collection is deleted.

Search supports BM25, dense and rank fusion (RRF k=60, default 40 candidates/channel, maximum 100). Dense retrieval requests up to four times the candidate limit before deterministic score/ID sorting. IDs are deduplicated by the existing RRF implementation. Model or generation failures fail closed; hybrid degradation to BM25 requires `allow_degraded=true` and returns the reason. Selected evidence is hash-checked and reparsed against frozen artifacts before returning VERIFIED provenance. Provenance describes source correspondence, not financial truth or answer accuracy.

## Application integration

`app/api/financial_index.py` exposes dataset inventory, bounded background builds, scoped search and retained-generation activation. API builds accept registered source dataset/manifest IDs under configured B storage, not caller-provided filesystem paths. The CLI supports explicit multiple source roots for local experiments. A locked singleton shares the local Qdrant owner across build/search, and application shutdown closes it.

`client.py` adds **Tìm kiếm tài chính**: indexed dataset selection, three search modes, ticker/form filters, readable table/narrative evidence, periods, SEC links and provenance details. Partial extraction and unfinished index states are visible. It returns evidence rather than an LLM financial answer. `FINANCIAL_INDEX_PATH` is configurable and separate from the legacy store.

Keyword mode is the initial UI choice. The frozen pilot evaluation did not show a hybrid relevance improvement; dense/hybrid remain selectable for inspection. This UI choice does not alter the frozen queries, rankings or relevance judgments.

## Reliability evidence

`tests/test_persistent_financial_index.py` has 13 test groups: new-process lexical persistence; deterministic ranking/formula parity; no query-time corpus tokenization; financial tokens/filters; idempotent and incremental original/amendment/derived revisions; interrupted build and restart; retained generations/rollback; Qdrant failure; model/dimension/generation mismatch; duplicates; source corruption; unsupported implementation versions; and API dataset scoping. These use fixture SEC sources, deterministic fake embeddings and real local Qdrant. They do not claim live-model failure injection.

Full regression with real OCR/media enabled: initial **182 PASS, 0 FAIL, 0 SKIP, 2 dependency deprecation warnings, 47.40 seconds**; final run after the UI default/measurement-reporting changes: **182 PASS, 0 FAIL, 0 SKIP, 2 warnings, 32.07 seconds**. Earlier targeted persistent/legacy retrieval: **22 PASS**, one dependency warning; the final broader targeted run is recorded below. Warnings concern Starlette/httpx test-client compatibility and a NumPy copy keyword in Diffusers, not failed retrieval tests. `compileall`, `pip check` and `git diff --check` passed.

Live local evidence is separate: nomic-embed-text produced 768-dimensional embeddings for 822 real SEC chunks; the index was reused by a restarted API process. Legacy Chat/RAG passed all five checks, including source filename/page, answer content, 768-dimensional Qdrant and error responses. The isolated legacy collection remained at three vectors. Historical B audit rechecked eight raw snapshots and eight manifests; whole-document PARTIAL_EXTRACTION remained unchanged. Streamlit AppTest against the live API passed seven workflow checks, including five results, tables, SEC links and partial-source/provenance labels; browser pixel layout is NOT_TESTED. Benchmark and quality results are reported in companion documents.

Final targeted persistent/legacy financial-search regression: **25 PASS, 0 FAIL, 0 SKIP, one dependency warning, 6.82 seconds**. A diagnostic audit invocation initially supplied the aggregate corpus directory instead of the Apple isolated root and correctly rejected the missing filing; it was rerun successfully with `--root financial_corpus/collaborator-v5-final`. A separate one-line count reader used Windows' default text encoding and failed; UTF-8 reading confirmed eight manifests/eight raw files. These invocation/reporting errors are recorded separately from product regression results; no failing test was disabled or relabeled.

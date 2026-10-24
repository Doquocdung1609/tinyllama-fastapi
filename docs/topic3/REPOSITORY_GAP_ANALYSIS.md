# Topic 3 — Repository gap analysis

## Executive gap

The repository has a credible local PDF/RAG foundation and now has an auditable
retrieval research endpoint. It does **not** yet have the corpus, metadata,
index lifecycle, authorization model, or independent evaluation required by the
Topic 3 definition of done.

## Capability matrix

| Capability | Evidence | Status |
|---|---|---:|
| FastAPI/Streamlit/PDF ingestion | Existing production app and regression suite | VERIFIED |
| Persistent dense vectors | Local Qdrant, 1,947 production vectors | VERIFIED |
| Explicit document-scoped financial search | `/financial/search` rejects missing scope | VERIFIED |
| Okapi BM25 formula | Inspected implementation and hand-checkable tests | VERIFIED |
| Dense retrieval | Real Ollama embedding plus Qdrant smoke | VERIFIED |
| RRF | Correct `sum(1/(60+rank))`, channel dedup added | VERIFIED |
| Optional Cross-Encoder | Local-only loader and fail-closed HTTP 503 | PARTIAL |
| Query normalization | Unicode casefold and locale-number aliases | PARTIAL |
| Table-aware retrieval | Existing table chunks participate as text; no dedicated table ranker | PARTIAL |
| Search provenance | Ranks, scores, source fields, timings, corpus hash | PARTIAL |
| Stable result IDs | Deterministic document-hash/chunk-index IDs | PARTIAL |
| Metadata ANN prefilter | Implemented when metadata is present | VERIFIED in tests; PARTIAL in production |
| Filing metadata ingestion | No SEC issuer/CIK/accession/form/period pipeline | NOT IMPLEMENTED |
| Persistent lexical index | BM25 rebuilt from all eligible chunks per query | NOT IMPLEMENTED |
| Lexical/vector version handshake | No shared committed index generation | NOT IMPLEMENTED |
| Real development/holdout retrieval qrels | Only one development smoke label | NOT IMPLEMENTED |
| User workflow for company/period/form filters | No finance-specific Streamlit screen | NOT IMPLEMENTED |
| Document-level ACL | Document IDs are caller supplied, not authorized principals | NOT IMPLEMENTED |
| Rate limiting/audit trail | No endpoint-level control/audit log | NOT IMPLEMENTED |

## Index lifecycle findings

### Add and duplicate upload

Uploads are streamed, size/signature/disk checked, content-hashed, and use the
first 32 hash characters as document ID. New exact duplicate uploads reuse the
existing record. This is VERIFIED for the current ingestion route.

There are two legacy production records with the same full content hash and 971
chunks each. This predates current deduplication and was not deleted or merged.

### Reprocess/update

Qdrant point IDs are deterministic UUIDs derived from chunk IDs. Reprocessing
upserts current points and prunes stale trailing points for the document. The
query-time BM25 view always reads current in-memory chunks, so it cannot become
stale as a separate index; the tradeoff is O(N) rebuild cost on every query.

There is no transaction spanning processed JSON, the in-memory registry, and
Qdrant. A crash between stages can produce an INTERRUPTED record and is
recoverable, but no shared generation ID proves that lexical and vector state
were committed atomically.

### Delete

The delete path removes the in-memory chunks, Qdrant points, uploaded PDF,
processed text, and processed JSON. Conversation references may then return a
deleted-document error. No persistent lexical index currently exists to clean.

### Stable identity limitation

Chunk IDs are stable only while chunking inputs and ordering remain unchanged.
A new chunking/index version can shift subsequent indices. There is no
`filing_version + source_location + content_hash` identity suitable for SEC
amendments, restatements, or reproducible qrels.

## Retrieval and scaling gaps

The synthetic scaling probe used 72-token finance-like chunks and seven runs per
size. It measures algorithm cost only:

| Chunks | Warm P50 | Warm P95 | P50 throughput | Peak traced allocation |
|---:|---:|---:|---:|---:|
| 100 | 30.498 ms | 35.621 ms | 32.789 q/s | 0.170 MB |
| 1,000 | 261.552 ms | 312.418 ms | 3.823 q/s | 1.579 MB |
| 5,000 | 1,079.902 ms | 1,208.678 ms | 0.926 q/s | 7.845 MB |

The trend is approximately linear because tokenization, document frequencies,
and length statistics are recomputed per request. This is acceptable as a small
research baseline, not as the required big-finance lexical index.

## Metadata and provenance gaps

- Legacy chunks carry document, filename, page, and chunk index.
- Newly extracted multimodal chunks can carry source IDs, modality, bbox, table
  structure, extraction method, and confidence.
- Existing production chunks used in the live smoke have `source_id`, modality,
  and bbox as null, so the endpoint can open page 155 but not an exact PDF region.
- Ticker, CIK, fiscal year/period, form type, filed date, accession number, source
  URL, amendment flag, and filing version are absent from the generic PDF path.
- A response-level corpus SHA-256 now detects unfair method comparisons, but it
  is not a replacement for a committed multi-index generation manifest.

## Security and operations

Existing upload validation, local-only default services, restart recovery, and
health checks are useful. The financial endpoint still has no authentication,
tenant ownership, ACL prefilter, rate limiting, query audit log, retention policy,
or backup/restore proof. Explicit `document_ids` prevent accidental global
search but are not an authorization boundary.

The target machine has about 8 GB RAM and 4 GB VRAM. The design correctly keeps
Cross-Encoder optional and CPU-only, and no model was automatically downloaded.
Observed dense latency is dominated by the local embedding call; adding more LLM
review passes would be inappropriate before retrieval quality is established.

## AI_agent_Demo reuse decision

| Candidate | Decision | Reason |
|---|---|---|
| English intent rules | Defer/evaluate | Potential baseline; unmeasured and not bilingual |
| Markdown table-preserving chunking | Do not copy directly | Loses page/bbox lineage; current app already has structured table chunks |
| 0.4 BM25 + 0.6 semantic score blend | Reject for benchmark core | Incomparable normalized scores and fixed prior |
| Analyst/Critic loop | Defer to optional QA | Same model generates and critiques; added latency; no citation contract |
| AST arithmetic evaluator | Reuse concept only | Current repository already has broader deterministic finance calculations |
| TAT-QA dev loader | Adapt later, not as retrieval holdout | It injects full context and tests QA, not retrieval; public test labels absent |

## Production blockers ordered by dependency

1. Reproducible SEC corpus and filing metadata.
2. Immutable corpus snapshots and source-location lineage.
3. Persistent/versioned lexical index synchronized with Qdrant.
4. Independent development and sealed holdout qrels.
5. Finance search UI with evidence opening and comparison.
6. Principal-aware ACL, rate limiting, audit, recovery and load tests.
7. Optional grounded QA only after retrieval gates pass.

# D1 compatibility and risk report

## Preservation boundary

D1 starts at accepted target `d1d5195b26f77d8fb25c830229c4c3693d4b638f`. Changes are additions under `app/financial_query/`, isolated fixture/tests, one fixture-only benchmark script and D1 documentation. No existing production module, dependency file, workflow, frozen C report/query set, API route, Streamlit screen or retrieval default is changed. Research PR #9 remains Draft/unmerged and is not an ancestor dependency of this branch.

The resolver takes in-memory objects and has no file, network, SQL, registry, Qdrant, Ollama or mutation interface. `catalog.py` deliberately does not instantiate `FinancialRegistry`, whose constructor initializes SQLite. It checks the supplied manifest content hash, exact filing membership, raw/normalized metadata hashes, parser/chunker identity and typed catalog lineage. It does **not** read/hash source bytes: upstream provenance verification remains the caller's responsibility. A caller-created catalog is trusted input, not cryptographically authenticated merely by passing Pydantic validation.

Existing C indexes/corpora were not opened or rebuilt by D1. Full regression uses the existing suite's isolated temporary fixtures and its configured integration/skip rules. No new SEC downloads, embeddings, generations or owner-data cleanup were performed. Git comparison against the exact base ensures historical tracked evidence is byte-identical. Production modules have no new import of D1; the interface does not influence B/D/F ranking.

## Compatibility evidence

Full regression includes persistent BM25/filter parity, restart/rollback, incremental reuse, mutation authentication, Qdrant ownership, retention/cache/source-tamper tests, SEC corpus/parser/path tests, financial API schemas and legacy Chat/RAG source/prompt/hybrid tests. Counts and skips are recorded in the benchmark report. Passing fixture regressions does not establish a new live UI or live financial-answer acceptance. No such claim is made.

New tests additionally prohibit socket creation during all40 resolver cases, assert no mutation of catalog/manifest/structured input, check input-order invariance and serialized repeatability, reject invalid generation identity, unknown filters, fabricated filing identity, blank aliases and wrong amendment parents. Adversarial text is treated as strings; no execution/evaluation tool exists. No numeric expression is calculated, and Decimal parsing never calls binary floating-point arithmetic.

## Remaining limitations and future dependencies

| Area | Limitation / safe behavior | Future boundary |
|---|---|---|
| Language/phrasing | Small English grammar; unknown/relative dates, negation, range operators, unsupported currencies/form phrases and confusable numbers need clarification or unsupported status. Not multilingual NER | More aliases/grammar need source-authored tests, not an LLM fallback |
| Issuer recognition | Whole-token catalog names/tickers/aliases and limited unknown-name cues; cannot reliably identify every unrecognized natural-language company mention | Caller must surface scope for confirmation; broader entity model requires separate review |
| Ticker history | Aliases are observed within snapshot; no independent temporal ticker registry | No global uniqueness or historical ownership claims |
| Periods | Adapter cannot verify comparative column periods from free-text labels alone; missing fiscal metadata remains unresolved | D2 may later supply verified column evidence; no such implementation now |
| Amendment | Linkage must exist in supplied catalog; only supported original/form relationships; no table-level restatement merge | Future evidence consumer must verify affected sections separately |
| Metric/units | Terms and Decimal predicates preserved; metric presence, accounting equivalence and source units are not verified | D2/D3 evidence validation and D4 arithmetic remain unauthorised |
| Extraction | `PARTIAL_EXTRACTION` propagated; metadata scope does not certify complete table extraction | No stronger completeness claim |
| Multiple filings | Returns explicit known membership without selecting latest; version ambiguity is blocked | Ranking/selection belongs to later authorized work |
| Metadata trust | Caller verifies source bytes and supplies snapshot; adapter validates correspondence of metadata/hashes only | C provenance remains authoritative |
| Scale/cost | Per-call catalog validation and exact alias scanning; fixture timings do not establish large-corpus scalability | A cached immutable catalog would need separate identity/invalidation design |

## Acceptance gates

| Gate | Status | Concrete evidence |
|---|---|---|
| D1-01 baseline | VERIFIED |Git base/ancestor inspection recorded in implementation report |
| D1-02 blueprint | VERIFIED |PR #9 HEAD checked;13 docs available, six required references reviewed |
| D1-03 contracts | VERIFIED |`contracts.py`; contract validation/roundtrip/version and catalog-lineage tests |
| D1-04 normalization | VERIFIED |`normalizer.py`; raw Unicode/sign/whitespace, bounds and malformed-input tests |
| D1-05 issuer | VERIFIED_WITH_LIMITATIONS |C03–09 plus collision/contradiction/unknown-name/blank-alias/confusable tests; bounded English recognition |
| D1-06 filing/amendment | VERIFIED_WITH_LIMITATIONS |C10–16,C36–39; explicit accession/form conflict and missing-link tests; snapshot linkage only |
| D1-07 periods | VERIFIED_WITH_LIMITATIONS |C02,C14–27,C34; explicit quarter-filter and no invented-calendar/column tests; adapter metadata gaps unresolved |
| D1-08 terminology | VERIFIED_WITH_LIMITATIONS |Decimal/sign/unit/synonym/related-concept tests; no source metric verification claim |
| D1-09 ambiguity/conflict | VERIFIED |Status oracles and negation/relative/explicit-filter conflict tests |
| D1-10 fixtures | VERIFIED |Synthetic catalog:3 issuers, duplicate ticker,6 filings, linked/unlinked amendments, different fiscal period ends, comparative metadata, partial extraction;40 case oracles |
| D1-11 focused tests | VERIFIED |114 passed in final focused run; test report lists command/runtime |
| D1-12 full regression | VERIFIED_WITH_LIMITATIONS |309 passed,3 pre-existing media skips,1 pre-existing warning; no new live UI/model claim |
| D1-13 performance | VERIFIED_WITH_LIMITATIONS |1,000 warm fixture requests and10 fresh-process C01 trials; benchmark JSON/report, no large-corpus claim |
| D1-14 historical evidence | VERIFIED |Only new allowed paths; exact-base diff check; no existing artifacts modified |
| D1-15 production retrieval | VERIFIED |No route/UI/search edits or imports; existing compatibility tests |
| D1-16 Draft PR | VERIFIED |[Draft PR #10](https://github.com/Doquocdung1609/tinyllama-fastapi/pull/10), open/unmerged, correct accepted target; implementation commit `8c49d041228ab18ca131af753f2c0b0446447cdc` |

GitHub delivery:19 added files, no modifications/deletions to accepted files; normal push only. PR #9 remains a separate Draft, not merged into D1. The delivery-record commit changes documentation only; final HEAD/CI are independently visible in PR #10 and the final report. No merge is authorized or performed. No unsupported gate is upgraded merely because code is complete.

## Later review qualification

The gate ledger above is the original implementation checkpoint, not proof for a repaired HEAD. A new adversarial pass reproduced18 failing tests in a52-test independent-style inventory, repaired nine findings and retained all original tests/fixtures. Current evidence and IR01–IR18 are in [review report](D1_INDEPENDENT_REVIEW_REPORT.md) and [candidate report](D1_INTEGRATION_CANDIDATE_REPORT.md). D1 now rejects unsupported/malformed explicit identity/period tokens, unsupported numeric unit order and conflicting amount/percent modifiers instead of silently narrowing intent. Catalog intake additionally limits string/tree complexity; this is not a large-corpus performance guarantee. Consistent joint-registrant accessions are allowed, while conflicting form/date metadata is invalid.

No accepted C production module, default, dependency or historical scientific blob was changed. Source-byte authentication, authentic alias/column evidence and any later integration consumer remain explicit dependencies. No live financial-answer or production certification is added by this review.

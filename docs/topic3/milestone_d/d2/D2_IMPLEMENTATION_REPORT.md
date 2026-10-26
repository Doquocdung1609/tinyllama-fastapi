# D2 source-bound table evidence implementation

Authorization: `TOPIC3_MILESTONE_D2_SCOPED_IMPLEMENTATION_AND_EVIDENCE_VALIDATION_AUTHORIZED`. Date: 2026-10-26. Implementation only; no integration authorization.

Base: `32c4a4834c5f8a0b34ac28c42f960c862dd8077d`, accepted integration branch `codex/topic3-milestone-b-sec-corpus`; D1 merge `182771470841b805d2f8d78f11b7dfa70c2dfc99` is an ancestor. Work branch: `codex/topic3-milestone-d2-table-evidence`. Exact final source/CI/PR identities are recorded in the Draft PR delivery record, avoiding self-referential hashes in this commit.

## Schema-gap audit and design reference

Read the actual accepted ingestion schemas, HTML parser, row chunker, manifest identity, C `verified_source` and D1 contracts/resolvers. Read blueprint PR #9's architecture, query, table, grounded-QA, evaluation, implementation and claim/evidence documents directly from its remote ref, without merging/copying the research branch. PR #9 stays Draft/unmerged.

| Required field | Existing accepted representation | D2 treatment |
|---|---|---|
| Canonical issuer/accession/form/document version, URL | Parent chunk metadata and filing identity | Preserve; bind complete canonical parent payload, including metadata |
| Row/column origin and locator | `TableCell.row/column/source_location`, zero-based expanded grid origin | Preserve physical origins; never enumerate displayed strings into fabricated coordinates |
| Rowspan/colspan | Accepted `TableCell` retains source spans | Header coverage uses actual origin/span; merged body cells stay one unresolved observation |
| Header hierarchy | Full `FinancialTable.cells` has header origins; row chunk only has its own row cells and flattened header text | Need separately authenticated full source table; never zip flattened/sorted periods with values |
| Fiscal/comparative periods | Free text `reporting_periods` is sorted, not column identity; contextRef is an opaque resource ID | Parse only explicit supported header labels at grounded coordinates; unknown labels remain unresolved |
| Raw numeric display and inline attributes | Normalized cell text plus numeric facts/sign/scale/name/unitRef/contextRef/format | Preserve exactly as accepted; Decimal whole-cell grammar, no neighbor-value inference |
| Footnotes/continuations | Table-level text and locations/linkage | Preserve associations at table level; no invented per-cell link or recursive expansion |
| XBRL context/unit resource definitions | Not retained by accepted cell metadata | Do not resolve contextRef/unitRef by their spelling; flag missing resources |
| Row group / entity dimension | Some text context, no complete XBRL dimension graph | Preserve row group/raw labels; finite explicit consolidated/segment label classification, otherwise UNKNOWN |
| Source authenticity | C verifies hashes and reconstructs accepted chunks from source bytes | Reuse accepted parse/rechunk correspondence in memory against a separately trusted pinned binding |

Existing B/C already provides row-aware chunking. D2 contributes a versioned derivative and validation layer, not a new row chunker. No accepted parser/chunker or corpus is changed. Source reconstruction is CPU-only and ephemeral, analogous to C provenance validation, not an ingestion job.

## Modules and contracts

New package `app/table_evidence`:

- `contracts.py`: frozen Pydantic contracts, tuple containers, explicit versions/statuses, finite Decimal and completeness invariants.
- `source.py`: bounded in-memory source reconstruction; byte hash, metadata hash, normalized correspondence and exact parent membership against a trusted `SourceBindingV1`; immutable serialized process-local context.
- `bounds.py`: iterative cycle/depth/node/text preflight before model serialization.
- `identity.py`: same sorted/compact UTF-8 JSON convention as C canonical payload hashing.
- `interpretation.py`: conservative header-period, unit, sign and measurement rules; no fiscal calendar inference.
- `builder.py`: exact physical-cell/header mapping and conflict propagation.
- `bundle.py`: one-context, one-filing bundle, selected order retained; optional single immediate same-table row-group expansion.
- `compact.py`: presentation projection with parent/hash references, no ranking consumer.
- `__init__.py`: exports only; no service initialization.

Contracts: `financial-table-evidence/v1`, `table-evidence-result/v1`, `table-evidence-bundle/v1`, `table-source-binding/v1`; representation/derivation identity `table-evidence-v1`. `TableEvidenceV1` keeps the complete canonical original parent JSON and text, coordinates/locators, parser/chunker identities and source generation/manifest. Cell and table hashes cover derived semantics, source identity and representation version. Cells are not new ranked documents.

Interfaces:

```python
context_from_snapshot(raw_bytes, filing_metadata, trusted_binding)
build_table_evidence(parent_chunk, verification_context=None,
                     representation_version="table-evidence-v1")
build_evidence_bundle(verified_candidates, verification_context,
                      scope=None, expansion_budget=20, expand=False)
```

The builder/bundle do no I/O, network, database/vector work or model calls. Source construction consumes caller-supplied bytes only. A context-free derivative is explicitly UNAUTHENTICATED/PARTIAL; a mismatched context fails INVALID_SOURCE. Bundle input errors raise bounded `ValueError` rather than fabricate evidence.

Deviations from proposed logical schemas: header interpretation lives alongside original coordinates/text, with final unit/measurement interpretation on the cell; footnotes remain table associations because exact cell references are not retained; there is no claim that contextRef provides a typed period. Expansion is stricter than the maximum20: at most5 selected plus one immediate row-group per selection, hence at most10 actual parents. Header/footnote text already retained in the table does not fetch extra parents. Cross-table continuation remains unresolved. The source context is a per-filing trusted process object, not a new authenticated token or persistent cache.

## Bounds and uncertainty

Pilot source context is limited to250KB UTF-8 source,5000 tags,2000 physical cells,depth64 and spans1..32. Parent intake permits250KB JSON/total supplied text,20000 visited nodes,depth20,5000 items/container; row view permits256 physical cells. Source-binding parent membership is limited to2000. These conservative bounds are acceptance limits, not whole-SEC scalability claims.

Supported headers include explicit FY, calendar year, fiscal quarter, `as of` and `year/quarter ended` dates through the accepted D1 period grammar. Bare years, ambiguous compound periods, missing resource definitions, malformed dates and unsupported numeric formats remain unresolved. No filing date/report end supplies a missing cell period. Basis rules distinguish explicit carrying/fair value, basic/diluted EPS, amount/percent changes and labelled segment/consolidated context. This finite registry does not understand arbitrary accounting concepts.

`VERIFIED_CONTEXT` means exact structural/source correspondence **relative to the trusted upstream anchor** with supported cell interpretation; it is not financial-answer correctness. PARTIAL/CONFLICTED cells have no `effective_value`. Missing blank/dash/N/A cells never become zero. Body spans do not duplicate observations. Nested tables are UNSUPPORTED. General XBRL resource/dimension resolution and arbitrary SEC formatting are not implemented.

## Tests and delivery

The dedicated `tests/test_table_evidence.py` covers98 synthetic cases; original D1 tests remain unchanged. Six fixture families and overhead measurements are in the companion [cases](D2_SOURCE_EVIDENCE_CASES.md), [provenance](D2_PROVENANCE_AND_CONFLICT_REPORT.md) and [test report](D2_TEST_AND_BENCHMARK_REPORT.md). All pre-existing tracked baseline blobs must remain identical at delivery. No production API/UI/default, D1 resolver, ranking, dependency, index or accepted scientific artifact is modified. D3-D5 are not implemented; PR #9 and the D2 PR remain unmerged.

# D2 interface readiness for a separately authorized D3

D2 is an opt-in Python view builder. It does not rank, retrieve, generate answers or change BM25/Dense/RRF. No existing route imports `app.table_evidence`. BM25 remains the accepted default recommendation. D1 `RESOLVED` still means metadata scope only.

## Future caller contract (not implemented)

1. Pin an existing accepted C generation and its verified manifest; retain the original canonical ranked parent IDs and source payload hashes. Authenticate every source through C provenance before supplying a D2 source binding. Do not derive an anchor from client-provided fields.
2. Supply caller-owned immutable source bytes and metadata to `context_from_snapshot`. No additional SEC download, index generation, persistence or embeddings are implied. Context preparation is separately costed; fail closed on budget/version/hash errors.
3. Call `build_table_evidence` for each selected row. Preserve the original parent and every raw cell/coordinate. Reject INVALID/UNSUPPORTED for numerical use; keep PARTIAL/CONFLICTED with their reasons visible. VERIFIED_CONTEXT is relative structural correspondence, not financial truth.
4. Optionally assemble a single-filing bundle with at most5 selected parents, total budget≤20. Actual supported expansion is at most one immediate verified same-table row-group per selection, no recursion. Source table headers/footnotes are already embedded and do not fetch another document. Cross-table continuations are unresolved. A broader multi-filing assembler needs a separate reviewed design.
5. If D1 scope is supplied, require RESOLVED status and exact dataset/manifest/generation/CIK/filing membership. Every numeric cell must match an explicitly requested period exactly; the current adapter refuses mixed/out-of-scope rows rather than silently dropping raw columns. Empty requested-period lists do not certify periods. A future cell-selection adapter may separately preserve excluded raw context, with distinct identity and review.
6. Any future D3 scoring must operate on canonical parent candidates, not duplicate each derived cell as a new ranked document. The current compact presentation projection is not a ranking feature or vector representation and cannot authorize old-vector reuse for a changed representation.

## Cell-period adapter proposal only

An eventual reviewed adapter may project authenticated `CellEvidenceV1.period` plus its exact `locator`, parent hash and evidence ID into D1 typed column references. Never use filing date/report end or C's sorted `reporting_periods` list as a substitute. Only source-supported typed period kinds are eligible; unresolved XBRL resource contexts and conflicting periods remain blocked. Do not infer that an amended row replaces an original or that identical numeric values share a measurement basis.

No accepted D1 resolver is modified to consume D2. No adaptive fusion, query routing, reranking, financial arithmetic/answer generation or D5 held-out evaluation is included. Those need separate authorization, source-grounded truth and a fresh experiment freeze. The consumed C holdout is unchanged and cannot be recycled as fresh validation.

## Readiness limits

The98-case synthetic suite and13-cell primary audit establish bounded structural behavior, not broad SEC coverage. Full XBRL contexts/units/dimensions, arbitrary header grammar, cell-specific footnote links, nested tables, cross-table continuation and mixed-scope selection remain limitations. Compact views reduce the bytes of these particular full parent JSON objects, but exceed their parent display-text bytes and do not establish retrieval-quality gain. Large-fixture reconstruction/build cost must be budgeted; no hidden persistent cache is introduced.

Proceed only with D2 owner review. The D2 PR and blueprint PR #9 remain Draft/unmerged; D3-D5 implementation is not authorized by this note.

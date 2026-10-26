# D2 provenance and conflict boundary

## Four distinct checks

1. **Schema:** strict versions, types, finite Decimals, immutable tuple containers and status invariants. This does not authenticate anything.
2. **Lineage:** pinned dataset/manifest/generation, exact filing identity, parser/chunker version and metadata digest. A valid-looking hash in client metadata is not trusted.
3. **Parent payload:** canonical full-parent SHA256, including text, source locator and all metadata, must match a reconstructed member of the source binding. `source_text_hash` alone covers only C row text and is insufficient.
4. **Source bytes:** `context_from_snapshot` hashes the exact supplied raw bytes against a **separately trusted upstream binding**, parses/rechunks with accepted C functions, checks normalized source hash and complete expected parent membership. It does not read files or fetch SEC data.

The trust anchor MUST originate in trusted application code from C's pinned generation and authenticated source/manifests. Existing `app/financial_index/corpus.py::verified_source` establishes read-time byte verification/reconstruction; it and generation manifest checks remain the upstream integration dependencies. D2 does not wire a new live adapter into that service. Caller must supply accepted filing metadata plus raw bytes that match its frozen source and canonical parent digests from that authenticated generation. D2's metadata hash binds all supplied metadata, including URLs and filing dates. No source file, registry or database is opened by D2 itself.

`SourceBindingV1` is trusted INPUT, not cryptographic authentication issued by Pydantic. A Python caller able to create an arbitrary new anchor can describe a completely synthetic source, as all fixtures do. It is unsafe to accept this object from an HTTP client as a self-attestation. `SourceVerificationContext` is a process-local immutable snapshot, not a serializable bearer token or a new cryptographic system. Shape checks cannot turn a forged self-issued binding into SEC truth. `MATCHED_UPSTREAM_BINDING` states this exact relative trust, rather than unqualified authenticity.

Without context the builder emits only PARTIAL_CONTEXT with UNAUTHENTICATED parent provenance; cell effective values are withheld. A dictionary such as `{verified:true}` is rejected. Tampered parent text/IDs/metadata, raw bytes, normalized source hash, parent hashes or supplied metadata fail closed. Mismatched scope generation/manifest/dataset, filing membership or cell period causes bundle refusal. All parents in a bundle must match its single pinned context; parent expansion cannot introduce another issuer/accession/manifest/generation.

## Conflict and uncertainty policy

| Condition | Output |
|---|---|
| Parent/source mismatch or malformed parent | INVALID_SOURCE; no evidence |
| Non-table row or nested table | UNSUPPORTED_STRUCTURE; no claimed mapped observation |
| Missing explicit column period/unit, partial extraction, opaque XBRL resources, unparsed numeric text | PARTIAL_CONTEXT; raw evidence preserved; no effective value |
| Conflicting header periods, display/inline sign or scale, carrying/fair or basic/diluted indicators, currency/unit dimensions | CONFLICTED_CONTEXT with typed coordinate-specific records; no effective value |
| Fully supported exact cell/header relationship matched to trusted binding | VERIFIED_CONTEXT relative to that binding; no answer-correctness claim |

Text labels are preserved but are not numeric observations. Table completeness considers all value/missing columns; blank/dash columns remain partial. Contradictory labels cannot be rescued by financial plausibility. Raw amounts, displayed Decimal, unit multiplier and effective source value are separate. Opposing signs conflict; two encodings of the same negative sign apply once. Unknown XBRL units/contexts never derive semantics merely from resource IDs such as `usd` or `c2024`.

Cryptographic derived hashes bind complete semantics and representation version to the parent, generation and manifest. Consumers of detached JSON must rebuild/revalidate against the trusted source; a hash copied into forged JSON is not authentication. Frozen contracts prevent ordinary in-place mutation, and returned context filing/parent objects are fresh copies. Python privileged callers and `model_copy` are not a security boundary; future consumers cannot skip source revalidation because an object has a type name.

## Actual adversarial evidence

`tests/test_table_evidence.py` includes byte/metadata/hash tampering, foreign filing/manifest metadata, wrong generation/explicit D1 scope, forged self-declared dictionary context, invalid locator, cyclic/overlong metadata, bounded malformed HTML, SQL/path/prompt-like cell strings, unknown versions/fields, sign/scale/EPS/measurement conflicts, no-I/O guards, immutable snapshot copies, and deterministic identities. It invokes no owner storage. Newly added D2 currency conflict tests first reproduced2 FAIL/1 PASS, then all3 passed after conservative unit guards; this development defect and permanent regressions are retained.

No network, LLM, SQL execution, arbitrary expression evaluation, vector calls or source writes occur. Budgets are finite pilot limits, not worst-case performance or security certification. The physical contents of untracked owner history were not freshly hashed; source/evidence preservation is supported by unchanged Git blobs and non-destructive operations, not a new disk audit.

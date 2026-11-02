# Output contract and navigation consistency

1. **Stale warning reproduced/fixed:** automatic financial responses inherited a generic unverified-excerpt warning from document QA even after CELL_VERIFIED. Supported cell claims now carry their own warnings; original retrieved text is explicitly SOURCE_TEXT_UNREVIEWED in a distinct field. No warning claims the selected financial cell is unverified.
2. **HTML locator removal reproduced/fixed:** the old public SEC serializer removed every *_path key, including structural_path. The source DOM locator is retained while raw/structured/chunk filesystem paths and secrets remain filtered. Real original-source resolution validates that locator, not a synthetic URL anchor.
3. **Evidence identities:** original retrieved chunk IDs are deduplicated and kept distinct from new stable PDF cell evidence IDs. Supplementary statement lookup remains explicitly marked, never counted as new retrieval success or a quality improvement. Cell citations retain actual source page/header/row/value boxes.
4. **Period metadata:** SUPPORTED automatic answers use selected-cell source periods, not generic filing/report metadata inherited from the first search hit. Comparative answers enumerate source_periods; prior-year scalar answers expose their actual source end. answer_source_chunk_id is null for cell claims, with explicit answer_evidence_ids instead.
5. **SEC filing identity:** public citation metadata matches exact filing_id, not merely CIK. Signed references bind the actual immutable source and target; Search baseline/V3 and numerical QA all use the same resolver.
6. **Back navigation:** real browser found the advanced SEC answer was lost on unmount. Scoped session answer/filter persistence now restores it; changed scopes/errors do not display a prior successful response. Current source bytes are revalidated when opening the viewer.
7. **Metadata context:** the Library now initializes to the active selected document and names the metadata document explicitly. User-corrected display metadata is still not an authenticated financial issuer identity; original source proof remains mandatory.
8. **Research boundary:** product PDF V3 and the retained pinned SEC development adapters are not relabeled as a fresh frozen FAITH-R experiment. No held-out scoring or qrel/benchmark edit occurred.

No Apple values changed:112010 million USD; Americas178353 million USD;6.43% from416161/391035. HPG remains searchable READY24pages64chunks with safe refusal for unsupported scanned numeric mapping. No universal coverage or semantic paraphrase guarantee follows from these examples.


Review scope: existing Draft PR35, branch `codex/topic3-v7p-verified-financial-chatbot`; A7 start `9047888178ec67929b59f4577b832dd9ca6a5767`; implementation HEAD `dd6e1d08d8d2f225f16761347d551f3854c54ac9`. Same-system Codex review/test, not independent human adjudication. No merge, PR36 import, benchmark scoring, model downloads, source replacement or index rebuild. Final evidence commit/CI identity is recorded in PR35 checks and handoff.

Pre-fix browser evidence `screenshots/a7-before-fix-back-navigation.png` records the lost advanced answer. It is historical failure evidence, not a passing final screenshot. The final desktop/mobile captures demonstrate the repaired path.

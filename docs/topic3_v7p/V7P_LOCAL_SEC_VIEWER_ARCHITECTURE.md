# Local SEC source viewer

Citation → server-signed source reference → authenticated POST /studio/sec/evidence → server-owned source lookup → current generation/membership verification → full-source hash/reconstruction → accepted parser → bounded table/context → ordinary React text/table rendering.

Backend `app/product/sec_viewer.py` uses registered canonical parent IDs and frozen source mappings. It rehashes all three artifacts per request, verifies current lexical row against initialized trusted membership, reconstructs canonical chunks via verified_source, then parses the already authenticated raw bytes for physical table cells. Selected numeric cells also pass the existing derive_cell/iXBRL period, unit, scale, concept and header verifier. No new ranking/financial arithmetic is introduced.

Frontend `SecSourceViewer.tsx` shows identity, form/accession/report date, source hash, exact cell/period/unit, physical source table with original colspans, adjacent rows, headers and provenance. Text is rendered as React children; no raw HTML, iframe, remote image, script, style or arbitrary link attributes are emitted. The view is explicitly derived, not a claim that a full original DOM is displayed. Boundaries: max4MB raw source,32MB each structured/chunk artifact,2000 selected-table cells,32 columns, at most10 header rows plus11 neighboring rows,250KB response, single concurrent source view. Exceeding these caps refuses rather than weakening verification.

A numeric citation selects the exact source row/column; a Search citation displays its verified parent/table without pretending a numeric column was selected. Text-only parents return SOURCE_EVIDENCE_PARTIAL with an explicit locator limitation. Missing old source references require a fresh query. Source bytes remain immutable and separate from the derived view.

The signature key is a separate random64-hex server file in the isolated product workspace, not the browser bearer token. It is persistent across launcher restart, excluded with workspace data and never returned. References bind workspace signing identity plus dataset/generation/manifest/parent/raw hash and optional exact financial-cell target. They are not authorization credentials; the endpoint still requires the bearer token.

Source view failure hides cached verified content. Back navigation preserves the SEC question/filter and scoped answer in the browser session; changed requests/errors do not reuse a prior successful answer. The official action remains “Mở bản công bố trên SEC.gov”, with safe link handling and no fabricated anchor.


Review scope: existing Draft PR35, branch `codex/topic3-v7p-verified-financial-chatbot`; A7 start `9047888178ec67929b59f4577b832dd9ca6a5767`; implementation HEAD `dd6e1d08d8d2f225f16761347d551f3854c54ac9`. Same-system Codex review/test, not independent human adjudication. No merge, PR36 import, benchmark scoring, model downloads, source replacement or index rebuild. Final evidence commit/CI identity is recorded in PR35 checks and handoff.

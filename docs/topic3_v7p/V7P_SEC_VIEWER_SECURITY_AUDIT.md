# SEC viewer security audit

No unresolved demonstrated HIGH/CRITICAL defect remains in this bounded pass. This is not production security certification.

| Boundary | Actual verification |
|---|---|
| Source trust | Committed upstream anchors; actual full bytes hashed; canonical C reconstruction; table cell checked with existing iXBRL verifier |
| Request input | Opaque reference only; token auth before effects; arbitrary paths/URLs/extra fields/oversize rejected |
| Workspace | Independent persistent signing key; cross-workspace and client-bearer-signed references rejected |
| Current state | READY vector/lexical identity and pinned manifest/generation required; live lexical source/payload must match trusted index |
| Tamper/cache | Prewarmed source tamper returns409, no old numeric claim; missing file explicit; restored clone control passes |
| HTML | Original scripts/events/resources never inserted into DOM; encoded markup stays text; official URL is server validated |
| Bounds | Raw/parser/selected table/response caps and one source-view slot; no remote proxy or model invocation |

Permanent Python tests: `tests/test_v7p_sec_viewer.py`,22 passed. Includes signed locator/period/value faults, unknown key, self-declared tampered hash, missing bytes, generation and identity mismatch, source-only/network-free resolution, separate persistent key, cross-workspace rejection, auth/validation, stale-warning removal, locator preservation, unique cell IDs and final V3 reference retention. Three added frontend tests cover escaped source text/precise cell, unsafe URL rejection and removal of cached verified content after failed revalidation; total frontend15 passed.

Real HTTP faults use a new clone of the existing registered snapshot and an isolated Uvicorn18112. Copied62,651,474 bytes per run, no Qdrant vector data or re-embedding. The owner source is never tampered with; original HD hash is rechecked after tests. Clone-only faults cover modified raw bytes, wrong filing/period/locator, missing file and failed generation; malformed requests/auth are also checked. These are 13 recorded endpoint controls, not 13 numerical accuracy claims.

SEC-07 actual browser safety uses a clearly labeled SYNTHETIC_HTML_SECURITY_FIXTURE_NOT_REAL_SEC_EVIDENCE on its own ephemeral server18113. Input contains script tags, event handlers, javascript links, external images, encoded markup and an adjacent malformed table. Recorded: zero active unsafe DOM nodes, zero unsafe network requests, zero dialogs, no script executed; encoded payload remains readable literal text. After fixture tamper and reload, no verified cell remains. The fixture-only routes are not imported or registered by main/app.

The JSON text representation is not claimed safe for direct insertion into innerHTML by a different client. The supplied React renderer intentionally uses ordinary text nodes. Local workstation file access/ACLs and upstream source acquisition remain deployment trust dependencies.


Review scope: existing Draft PR35, branch `codex/topic3-v7p-verified-financial-chatbot`; A7 start `9047888178ec67929b59f4577b832dd9ca6a5767`; implementation HEAD `dd6e1d08d8d2f225f16761347d551f3854c54ac9`. Same-system Codex review/test, not independent human adjudication. No merge, PR36 import, benchmark scoring, model downloads, source replacement or index rebuild. Final evidence commit/CI identity is recorded in PR35 checks and handoff.

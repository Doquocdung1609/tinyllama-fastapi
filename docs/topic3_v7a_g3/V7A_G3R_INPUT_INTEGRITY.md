# V7A G3R input integrity (2026-11-02)

The two post-source submissions are additive. Their original ZIP bytes are preserved in `C:\Users\Admin\Downloads\code` and all detailed AI answers remain outside Git.

| Input | SHA-256 | Result |
|---|---|---|
| Agent 1 post-source ZIP | `f7d53e1b32cbadc1ac1d85a732898e7044b1831de5b608164f5952d876c0c275` | CRC and all declared file hashes pass |
| Agent 2 post-source ZIP | `5a749bbe8f9002bf24ac98f2518ce82859dd74bf4c7b77950d2c3e07c3419a73` | CRC and data-file hashes pass; two self-reference warnings below |
| Shared nine-source SEC ZIP | `9ab979c7156b99b1f0ca25747b0ff1ca24771812253f2d1e0cae3deec95c3afb` | CRC and every `SHA256SUMS.txt` entry pass |
| G2 question-only CSV | `a92cdfb6a00744c3ea8bdae93b337d60919be52e65019b4f541b40235f4aa4ef` | 94 unique frozen IDs |
| Agent 1 reviewer input ZIP | `e8ef439f232717e26fc0b5c47cc8afa0f15605f239ddb273e6cfed1fc04aaf3c` | Nested source and G2 input CRC pass |
| Agent 2 reviewer input ZIP | `b4390d9ca5f355084b5f211aeabfc65f2654742dfc8122d0be082caad2fcdd9b` | Nested source and G2 input CRC pass |

Both post-source outputs contain exactly the same 18 expected G2 IDs and nine accession mappings. Every reviewer-declared source URL and SHA matches the acquired raw HTML. The source bytes are the SEC-served representation; each of the nine responses carries a 109-byte trailing script relative to the index-listed size. No earlier pristine archive-byte equivalence is claimed. HTML parsing did not execute scripts.

**Agent 2 manifest inconsistency:** `AGENT2_G3_POST_SOURCE_FREEZE_MANIFEST.json` declares its own SHA as `f70c6af8…` but its actual SHA is `44c1c852…`; it declares `SHA256SUMS.txt` as `a95d7c71…` but its actual SHA is `68a5e618…`. The `SHA256SUMS.txt` entries for data files match actual bytes, including the actual manifest SHA. Preserve the received ZIP and ask its author to explain the self-reference mismatch; do not rewrite it. This prevents a clean manifest-integrity PASS, although the data files were independently validated.

Agent 1 output states no Agent 2 or coordinator answers were read. Agent 2 output states no Agent 1 answers, coordinator disputes or model predictions were read. Separate input packages and frozen ZIP hashes support the chain of custody; this is not proof of a reviewer's unseen internal process.

Private generated artifacts: `C:\Users\Admin\Downloads\V7A_G3R_PRIVATE_AUDIT_20261102_V5`. The prior 94-row comparison remains locked by SHA-256 `94`-question manifest and its own immutable file hash in `V7A_G3R_PRE_RECOVERY_COMPARISON_LOCK.json`.

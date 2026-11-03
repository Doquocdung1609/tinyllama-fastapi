# Owner guide: twelve source cases and blind original chunks

Start with the twelve source-policy questions from the private G3T casebook: `05_01`, `09_02`, `12_01`, `12_02`, `14_02`, `15_01`, `21_01`, `24_01`, `25_02`, `30_01`, `32_01`, `38_01`. The three AMD questions `09_01`, `10_01`, `10_02` follow; their source financial cells are absent from the frozen original chunks. The reviewer can then use the prospectively stratified queue and continue through all 94 questions. These groups overlap by question only where explicitly listed; do not double-count a source cell or independent observation.

| Priority IDs | AI source proposal | Human source decisions |
| --- | --- | --- |
| `05_01`, `14_02`, `21_01`, `24_01` | Ambiguous | 0 |
| `09_02`, `30_01`, `32_01` | Partial | 0 |
| `12_01` | Bounded negative support | 0 |
| `12_02`, `15_01` | Provisional exact under minimum-answer rule; strict hold | 0 |
| `25_02`, `38_01` | Question validity concern | 0 |

The local blind-chunk tool has two separate queues: `http://127.0.0.1:18748/` serves the **static target-filing source audit** (17,340 pairs), while `http://127.0.0.1:18749/` serves the **approved mixed-arm ranked blind union** (5,792 pairs, including off-target candidates). The static queue cannot assess off-target retrieval. Both display one frozen question and one original chunk with text/hash, source accession and URL. Neither displays method, rank, score, prior gold or AI qrel suggestion. Choose `EXACT` only if that one chunk itself supplies every mandatory answer element; choose `PARTIAL` for meaningful but insufficient evidence; choose `NONE` only after actually inspecting an irrelevant/insufficient chunk. Use `DISPUTED` or `SOURCE_INSUFFICIENT` when appropriate. Cite the exact original chunk and source, give a reason, and explicitly attest that the decision is yours. Each event is append-only and SHA chained; the owner must independently verify self-declared reviewer identity. Both queues currently have zero human decisions.

The AI qrel overlay is separate and deliberately conservative: mechanical row/value evidence can become only `PARTIAL`; all other pairs remain `UNJUDGED`. No automated `EXACT`, `NONE` or human event is created. HTML source can validate answer truth but cannot earn an original-chunk retrieval hit. The 17,153 static G3T `UNJUDGED` pairs are preserved as their own earlier version and are not treated as negatives.

# G3S checkpoint audit

Base is G2 PR #34 (`cd8deb96cb8c147ca5c090e9c0a323de511c65bd`); work continues on Draft PR #36. The frozen design is 47 filings, 10 issuers, 94 question IDs, 8,670 corpus chunks, V6 holdout and F10 Policy B. No question, index, embedding, ledger or algorithm was edited.

| Frozen input | SHA-256 | Result |
|---|---|---|
| Agent 1 post-source ZIP | `f7d53e1b32cbadc1ac1d85a732898e7044b1831de5b608164f5952d876c0c275` | ZIP CRC and data checks passed |
| Agent 2 post-source ZIP | `5a749bbe8f9002bf24ac98f2518ce82859dd74bf4c7b77950d2c3e07c3419a73` | ZIP CRC/data passed; two self-reference warnings documented separately |
| Nine-source ZIP | `9ab979c7156b99b1f0ca25747b0ff1ca24771812253f2d1e0cae3deec95c3afb` | Preserved |
| Eight-dispute ZIP | `3ed0e945d6dbef95c92e9909080921fd2475c427087d53cd898692961eabb0e2` | Preserved |
| G2 47-filing source manifest | `46c0d0a0fed423ba373afab075b1952a6a0d3da85041c0f5b0f626585bbebaa6` | Unchanged |
| G3R private nine-case book | `cf60baaee6a2719a49ebd0aa94a3a6ca627f3b442a7c815ba9a56ab5529025f2` | Unchanged |

The 94 IDs in the G3R human queue and new source audit match exactly. Existing G3R comparison and AI ledgers were read, not rewritten. The detached [attestation](V7A_G3S_EXTERNAL_HASH_ATTESTATION.json) records the actual Agent 2 self-hashes and preserves the original ZIP.

The public audit files omit proposed answer values. Full source-cell proposals and review input are held outside Git under `C:\Users\Admin\Downloads\V7A_G3S_PRIVATE_EVIDENCE_AUDIT_20261102_V6` and `C:\Users\Admin\Downloads\V7A_G3S_PRIVATE_REVIEW_DATASET_20261102_V2.json` (SHA-256 `211336358375445568f168ffa687459a455fa73f1c3349d05af998427e57a44d`).

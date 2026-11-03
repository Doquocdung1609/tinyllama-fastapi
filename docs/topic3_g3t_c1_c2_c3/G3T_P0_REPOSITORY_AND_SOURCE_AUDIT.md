# G3T P0 repository and source audit

- Before this work: Draft PR #36, `codex/topic3-v7a-g3-sec-source-snapshots`, HEAD `8c619753fef9895811504a5f8b2b5ce78f497594`, base PR #34. The fetched remote head matched. PR #35 and its product code are outside this change.
- Existing untracked `output/`, `tmp/search-v3r3/`, and `tmp/topic3/` were preserved. No reset, clean, rebase, or force push was used.
- The G3S verifier checked all 47 frozen accession/form/URL identities and 47/47 raw primary HTML byte sizes and SHA-256 values. No source was synthesized. The nine-document source handoff and the eight-dispute source handoff were found and checked as inputs; see the immutable private evidence manifest for derivative file hashes.
- Original frozen corpus: 8,670 chunks, SHA-256 `7c6852a8c68ed1c64194c2da9339fbb4719482949e5705596499db53114abb1f`. Recovered index A SHA-256 `1e8e3c6393e7e59786575ed0228254079639016c7b986d1e9702fa5a3ce32540`; index B SHA-256 `fef99bfa5cde1ec358f460efacd3db4ca540673213491c569d64e313070df663`. Both contain the same 8,670 original chunk IDs and text hashes. Index payloads were inspected statically without executing pickles.
- The source and review ZIPs remain outside Git. The private answer/evidence ledgers and value-bearing qrels remain outside Git. This branch adds no raw SEC HTML or frozen research mutation.

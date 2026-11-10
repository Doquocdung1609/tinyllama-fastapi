# Research freeze preservation

`V7P_FREEZE_BLOB_AUDIT.json`: 843 tracked historical files under docs/topic3*, data, reports, financial_corpus and checkpoints, excluding this new V7P checkpoint area. Git blob manifest SHA256 `739a81d0f54aef534a0744f3709756703ff4c1563a4466bfdd023b712f06ce28`; base PR34 cd8deb96cb8c147ca5c090e9c0a323de511c65bd. Changed historical files: zero. G2/F10/SEC47 and earlier metrics not scored, tuned or edited.

Two Windows working-tree status entries can appear modified from stat/line-ending handling while normalized Git diff is empty: PROVISIONAL_SOURCE_QRELS.jsonl and V6_FRESH_HOLDOUT_30_UNJUDGED.csv. Neither staged nor rewritten. Canonical Git blobs preserved. Owner V6 and older portable-data worktrees were not reset/stashed/cleaned.

No production retrieval parameter changes, new model weights, source snapshots or vector files committed. Existing isolated portable SEC sources were opened read-only. Only local product workspace and newly generated test fixtures were written. This is non-destructive scope/evidence, not a byte inventory of all unrelated owner disks. Independent human adjudication remains whatever the frozen protocols require; product acceptance does not mark research complete or establish Hybrid superiority.


Code reviewed/tested: `3e85fdba74737f5a94f555424d283126fe84dc0e`. Starting work-order HEAD: `f3c3fc320d957a4be418054e179e18800f49e5cf`; PR34 base: `cd8deb96cb8c147ca5c090e9c0a323de511c65bd`. Existing Draft [PR35](https://github.com/Doquocdung1609/tinyllama-fastapi/pull/35), branch `codex/topic3-v7p-verified-financial-chatbot`. Same-system Codex adversarial pass, not independent human review. No merge or new PR. Final documentation commit identity is available from Git/PR; this report does not invent a self-referential SHA.

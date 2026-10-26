# P9 historical integrity audit

Read-only Git comparison from accepted target `32c4a4834c5f8a0b34ac28c42f960c862dd8077d` to P8 HEAD found no changed tracked Milestone C scientific files under `docs/topic3/MILESTONE_C*` or D1 records under `docs/topic3/milestone_d/d1`; no changed accepted `app/main.py`, `app/financial_index` or legacy `app/services/rag_service.py`. P9 branch changes are new verification scripts/reports only. The local two-parent candidate tree equals the P8 tree exactly. No migration or tracked SQLite/vector artifact was introduced to the candidate.

Fault injection used only `t3-p7-isolated-review-20261026-v1` and a further disposable concurrency clone, never accepted SEC/Qdrant storage. The PG raw SEC byte SHA256 after tamper restoration remained `30904fac63dc81fec0a524c812bea5109521b9b8063f34adf13f3f50bd2a4b53`; cloned lexical generation state was READY after the invalid-generation probe. The P7 12-case clone test confirmed restored control after each mutation. No new SEC filing was downloaded. The consumed D5 held-out was neither opened for tuning nor rewritten.

Remote preflight kept main `ceaa8acfcfaea8056e45b859a0fc44d6381fb22a` and accepted branch `32c4a4834c5f8a0b34ac28c42f960c862dd8077d`; recheck immediately before any future integration. This audit checks tracked Git blobs and designated local clones, not every untracked owner file on the host.

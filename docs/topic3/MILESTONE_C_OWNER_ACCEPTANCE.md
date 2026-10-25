# Milestone C owner acceptance

**MILESTONE_C_ACCEPTED_WITH_DOCUMENTED_LIMITATIONS**

Accepted implementation: merge commit `69e6866552d15571858b44707d59a453443fae9c`, PR #8, integrated into `codex/topic3-milestone-b-sec-corpus` under the owner's conditional authorization after mandatory gates were verified. Target before merge: `b7fd390`; final source: `4dfe514`. Main remains `ceaa8ac`.

Scope: **Controlled local Financial Intelligence pilot.**

Accepted capabilities: persistent lexical financial retrieval, snapshot-bound semantic retrieval, RRF fusion, financial metadata prefilters, SEC evidence provenance, restart/resume/rollback, bounded generation lifecycle, mutation auth, single-owner embedded safeguards, bounded parse cache retaining per-request cryptographic verification, evaluation artifacts and CI.

Evidence: final CI run `40168878980` passes on a merge candidate with the same tree as the accepted commit. Post-merge full suite: **195 passed, 3 skipped, 1 warning**; deterministic core: **195 passed, 3 deselected, 1 warning**. Live Financial Search UI and API workflows, SEC navigation, mutation rejection, authorized isolated activation, invalid-generation failure and legacy Chat/RAG retrieval were verified. All six available owner historical corpus/Qdrant file checksums remained unchanged.

Accepted scientific conclusion: **BM25 is the recommended default for the current evaluated financial corpus.** Held-out Recall@5 BM25/Dense/Hybrid = 0.9375/0.8125/0.9375. Hybrid does not demonstrate consistent superiority. Exact frozen queries/results and independent audit are documented in `MILESTONE_C_SCIENTIFIC_EVIDENCE_FREEZE.md`.

Exclusions remain: production security certification, multi-node scalability, distributed Qdrant coordination, general financial-answer accuracy, universal SEC completeness, enterprise disaster recovery, automated financial decision-making and universal Hybrid superiority. Three optional real-media tests were not rerun; CI lacked Tesseract for one additional core test. SEC source navigation exposes locators but does not auto-highlight rows. Read API/auth and server mode remain limited to trusted local deployment. Milestone B PARTIAL_EXTRACTION and administrative-table limitations remain valid.

Acceptance provenance: `MILESTONE_C_INTEGRATION_REPORT.md`, `MILESTONE_C_FINAL_SECURITY_REVIEW.md`, `MILESTONE_C_PRODUCT_SMOKE_TEST.md`, and raw evidence under `reports/milestone_c_acceptance/`. This record does not authorize or implement Milestone D.

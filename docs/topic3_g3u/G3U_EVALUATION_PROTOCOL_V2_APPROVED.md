# Approved G3U v2 pool acquisition

The owner explicitly approved one complete 94-question candidate-pool run after reviewing the RRF discrepancy and partial-run disclosure in this Codex conversation. The machine-readable v2 lock has SHA-256 `1bfbcad876e123d975a2475a0d2c2516c98677e3eb4e81296d1195cc5ed15f32`; its arm registry has SHA-256 `eddef050ac78b1184d4fa311ffbf1758ae7f458940483a412f8d69271aad1f76`. Both are new derived files; the G3T v1 protocol and G3U v1 registry remain unchanged.

The approved native-author RRF is Qdrant local's actual default `k=2`, because the pinned author calls `FusionQuery(RRF)` without an explicit k. Each arm contributes at most 20 outputs. Native Stage-2 has 60 internal SPLADE+BGE candidates for output k=20. The controlled explicit `k=60` variant is not part of this approval. A4R remains exposed post-hoc development. The new run records FastEmbed 0.9.1, Qdrant client 1.20.0 and the prior incomplete execution. The earlier partial log is preserved, not used to select or tune candidates. A complete blind pool from v2 remains an **exposed continuation**, not a pristine never-before-executed sealed set.

This authorization covers pool acquisition and blind relevance preparation only. It does **not** approve final G2 metrics, human qrels, model tuning, merging or any human-certified benchmark.

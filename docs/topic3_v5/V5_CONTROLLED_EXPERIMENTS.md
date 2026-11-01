# Controlled experiments and budget

Policy fixed in [preregistration](V5_EXPERIMENT_PREREGISTRATION.md) before rerank outcomes, but development labels and one case had been inspected. [`replay_results.json`](replay_results.json) retains input hashes, all 15 paired case IDs, exact candidate IDs, ranks, features, labels and aggregates. A1 and A4 use identical `B_CORRECTED bm25_dense` Top-10 ID sets, text hashes and candidate count; no new embedding, index, method fusion or source was added.

| Arm | Executed status | Result / limit |
|---|---|---|
| A0 original | RECORDED | 0/90 target filing Top-10 across six methods |
| A1 fiscal overlay | RECORDED | 90/90 target filing Top-10; `bm25_dense` known-positive financial chunk top1 3/15, top3 7/15, top10 14/15 |
| A2 query slots | EXECUTED in replay | 15 explicit issuer/year/metric slots; no separate retrieval change, so no gain attribution |
| A3 provisional row representation | EXECUTED on same Top-10 | Candidate metadata only; no new index or coverage gain |
| A4 rerank | EXECUTED on same Top-10 | Known-positive top1 11/15, top3 13/15, top10 14/15; top1 labels YES 11, NO 2, PARTIAL 1, UNJUDGED 1 |
| A5 safe verification | EXECUTED as gate | 0 newly verified numeric cells; all `UNVERIFIED`; existing V4 verifier unchanged |

Top1 known-positive bounds: A1 3–3/15, A4 11–12/15 (`PARTIAL_NOT_GOLD` is excluded from the possible-positive upper bound). Pairing is by question, not by 90 method rows. These are exposed development cases; no significance or independent superiority claim. Runtime p50/p95 and memory overhead of a live 47-filing run cannot be estimated from saved top10 replay. The new Python rerank itself is lightweight; see QA for measured execution time.

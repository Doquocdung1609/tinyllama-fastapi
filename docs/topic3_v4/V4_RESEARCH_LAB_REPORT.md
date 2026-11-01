# Research Lab

The Compare screen has two deliberately separate datasets:

| Mode | Executed now? | Corpus and methods |
|---|---|---|
| Live product comparison | Yes | Same selected product document scope and question; BM25, Dense, Hybrid fixed RRF. Per-request timings, top-k snippets and page links. |
| Topic 3 saved experiment | No | Two 2026 SEC 10-Q snapshots; 121 author chunks versus 1,241 structure chunks. Seven original/project-extension arms plus structure BM25. Frozen six questions, per-arm target rank and local Qdrant query time. |

The saved API validates the qrels SHA-256 before serving results and returns `RECORDED_EXPERIMENT_NOT_LIVE`. Stage-2 is labeled deterministic author code, never a neural reranker. SPLADE, Stage-2 and the structure research index are marked unavailable for live product search.

Live BIDV question “BIDV điều chỉnh báo cáo tài chính năm 2024 theo kết quả nào?” returned page 1 at BM25 rank 1 and Hybrid rank 1; Dense rank 1 was page 8. Measured screenshot run timings: BM25 20.58 ms, Dense 294.09 ms, Hybrid 119.60 ms. A preceding run measured 15.46/94.05/104.16 ms respectively, illustrating cache/runtime variation. These runs carry no qrels, so no Recall/MRR is claimed. The live product scope included both prepared PDFs; the historical SEC corpus is not directly comparable.

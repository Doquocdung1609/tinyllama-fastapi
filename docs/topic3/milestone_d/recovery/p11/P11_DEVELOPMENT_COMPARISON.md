# P11 provisional development comparison

Run: `python -m scripts.p11_evaluate_dev --root <owned P11 research root> --output docs/topic3/milestone_d/recovery/p11/p11_development_metrics.json`. The B/D/F/A implementation and qrels were committed before this first scoring run. Generation `d37a5139aa1817d4564238e7c1e03abc818991c6035991ce5b6d9435bac33f28` contains exactly 2,887 authenticated MCD/CAT parents in both SQLite BM25 and isolated Qdrant. Nomic digest `0a109f422b47e3a30ba2b10eca18548e944e8a23073ee3f3e947efcf3c45e59f`; 768-dimensional COSINE vectors; 40 candidates per channel; fixed RRF k=60. No channel failed. Every returned parent was checked against the pinned source and generation.

| Arm | Recall@5 | Recall@10 | MRR@5 | nDCG@5 |
|---|---:|---:|---:|---:|
| B: BM25 | 0.30 | 0.60 | 0.073 | 0.127 |
| D: Dense | 0.10 | 0.20 | 0.100 | 0.100 |
| F: fixed 1:1 RRF | 0.50 | 0.60 | 0.212 | 0.282 |
| A: preregistered development heuristic | 0.40 | 0.70 | 0.107 | 0.177 |

The one proposed parent qrel per question makes Recall@5 identical to provisional evidence-group hit rate. These are **10 automatically proposed, unreviewed development labels**, with no claim that all relevant parents have been found. MCD asset proposals come from a `Segment Information` table, and MCD revenue proposals from a management discussion table. Those financial relevance judgments require human review. No label was selected from these rankings. These figures cannot overturn the accepted BM25 recommendation or establish Hybrid superiority.

| Query | B rank | D rank | F rank | A rank |
|---|---:|---:|---:|---:|
| MCD assets exact | 9 | 10 | 1 | 9 |
| MCD assets paraphrase | >10 | 1 | 3 | 3 |
| MCD revenue current | >10 | >10 | >10 | >10 |
| MCD revenue prior | 7 | >10 | >10 | 7 |
| CAT sales quarter | 6 | >10 | 4 | 6 |
| CAT sales paraphrase | >10 | >10 | >10 | >10 |
| CAT sales six months | 5 | >10 | 5 | 5 |
| CAT cash instant | 5 | >10 | 6 | 5 |
| CAT basic EPS | >10 | >10 | >10 | >10 |
| CAT diluted EPS | 3 | >10 | 3 | 3 |

`>10` means the proposed parent was absent from top 10, not necessarily absent from the 40-candidate pool. Full canonical IDs, RRF contributions, candidate counts and stage latencies are in the machine-readable JSON. The four scope/refusal controls had no qrels; all returned no eligible filing: wrong issuer `NEEDS_CLARIFICATION`, wrong period `UNSUPPORTED`, relative-date ambiguity `NEEDS_CLARIFICATION`, and unsupported annual duration `NEEDS_CLARIFICATION`. They are not counted as retrieval successes or negatives.

Per-question wall time p50 1,020 ms and p95 4,159 ms on this laptop, including source authentication/reparse, BM25, live Ollama embedding, Qdrant, fusion and post-query rehash. These are development runs without cold/warm randomization; they are not accepted production latency figures. Wrong-issuer top-5 rate was zero under explicit CIK/filing filters. Column-level wrong-period rate and numerical correctness were not measured. The isolated index occupied 94,622,119 bytes at run end. No validation or held-out ranking was accessed.

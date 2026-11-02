# V6 checkpoint and author code audit

Checkpoint is Draft PR #32 HEAD `571750b116dde37c9a1b39dcc95ec075c02f9950`; V6 branches from it without resetting or merging. The pinned author checkout is `16682dd42ca9cd4887ae74935cb3526dce580c49`. The V6 algorithm freeze was committed separately before examining any new holdout outcome. The existing user `output/` and `tmp/` workspaces were left intact.

## Verified checkpoint

The V5R handoff archive and frozen 8,670-chunk corpus checksums agree with `docs/topic3_v5/recovery_live/restore_manifest.json`. The full-point audit shows 8,670 unique IDs in both A and B, 384-dimensional finite dense vectors, and nonempty BM25 and SPLADE sparse vectors. Point IDs, text hashes and vector hashes agree; only `fiscal_period` differs on 3,516 points spanning 15 accessions. A is recovered P3D, not proven exact P3C. The tracked 480 compact Top-10 results and four raw-result manifests agree with the historical reconciliation: P5 A 150/150 exact order; P7L B 90/90; P7L A 88/90, with the same Top-10 sets in the two mismatches. The exposed A0–A5 and post-hoc A4R results are retained unchanged. The 30 V5R questions were all UNJUDGED. V5R local regression 732 passed and the React build passed; V6 reruns regression after its additions.

## Author claims compared with actual code

| Claim or impression | Pinned source and evidence | Finding |
|---|---|---|
| Six retrieval modes include BM25, BGE dense, SPLADE and two RRF hybrids | `retrieval/engine.py`, original embedding and retriever modules; 480 V5R live queries | Supported as executable methods on the restored corpus. Scores across methods are not on a common scale. |
| Stage-2 is neural/ColBERT | `retrieval/reranker.py` declares a ColBERT model name but `rerank()` computes regex/extractor features and a fixed weighted score; no ColBERT inference call | The executed Stage-2 is a deterministic heuristic. Its class name is misleading. |
| Table boundaries preserve answer cells | `chunking/chunker.py` and `retrieval/extractor.py` carry text, but no verified row × column × period × unit cell relation | Chunk relevance cannot certify a financial value. |
| Evaluation guarantees high precision | `evaluation/benchmark.py` uses self-retrieved terms; `evaluation/report.py` contains a precision guarantee | The benchmark design and V5R counterexamples do not support a universal guarantee or independent financial-cell accuracy. |
| Fiscal-year filtering is reliable | Original payload periods and corrected B metadata; all-point diff | Fifteen accessions had 3,516 wrong fiscal labels in A; B corrects metadata without changing vectors or text. |

The author's original `config/default.yaml` sets 384 dense dimensions, BGE-small, Qdrant BM25, SPLADE, default prefetch 50 and RRF constant 60. Its Stage-2 retrieves at least 20 candidates and uses fixed weights `[0.15, 0.25, 0.10, 0.15, 0.10, 0.15, 0.10]`. V5R A2 adds safe metadata filters; A3 scans the same corpus for row-like candidates; A4 applies six lexicographic features; A4R was developed **after** exposed errors; A5 only marks `UNVERIFIED`. Neither A4 nor A4R verifies a financial cell. The feature and code hashes are in `V6_ALGORITHM_FREEZE_MANIFEST.json`.

## Reproducibility boundaries

The original P3C snapshot and historical query vectors are absent, so full bitwise equivalence of A to P3C is unproved. Full SEC HTML, local Qdrant snapshots, model caches and full-text raw runs remain ignored locally; compact IDs, source URLs, score lists and SHA-256 signatures are tracked. Original project files and already-running independent services were not overwritten.

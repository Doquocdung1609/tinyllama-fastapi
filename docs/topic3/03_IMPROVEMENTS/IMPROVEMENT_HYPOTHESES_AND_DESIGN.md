# P3 — Source-structure intervention

## Failure → hypothesis → intervention → control → measurement → result → limits

F01/F02 showed that generic 500-character chunks can put segment discussion or goodwill ahead of the requested consolidated statement row. The hypothesis was that preserving issuer, statement, period, column and row context within each retrievable unit would raise the known source row. The intervention indexes the already preserved `financial-structure-v5` SEC chunks with the **same FastEmbed `Qdrant/bm25` generator**, frozen six query vectors, two raw SEC filings and Qdrant sparse IDF scoring. The control is R0, the pinned author's parser/chunker and BM25 on the same raw filings. No V3R3 owner index is changed.

The measured outcome is the rank of **one machine-prepared known target** for each of four source-positive questions, plus query-only local Qdrant latency. Full structure found all four at Rank 1; R0 found none at Rank 1 and three within Top 10. The intervention has 1,241 chunks versus R0's 121, so chunk cardinality, term distribution and IDF also change. This is an exposed development comparison, not a causal estimate of one metadata field, independent retrieval accuracy, or a claim against the author's 47-filing result.

F04/F05 showed 2037 and Apple questions returning unrelated hits. The separate conservative candidate policy checks issuer presence and explicit period before presenting a source row; its six-query outcomes are in `CONSERVATIVE_EVIDENCE_ASSESSMENT.json`. It certifies **zero** numeric answers. The P&G net-sales duration table remains `AMBIGUOUS` because its reporting-period metadata is a duration label, not an exact instant-date token. Three other positive candidates are `SOURCE_SUPPORTED_UNREVIEWED`; both negative questions abstain. This policy is isolated in `app/topic3/evidence_policy.py` pending broader integration and review.

## Frozen inputs and scope

- Raw SEC HTML hashes and source URLs: `../00_AUDIT/REPOSITORY_INVENTORY.json` and `../01_REPRODUCTION/CORPUS_MANIFEST.json`.
- Machine-prepared questions: `../01_REPRODUCTION/PROVISIONAL_SOURCE_QRELS.jsonl`, SHA-256 `daeb3bc5ba9425aa4ed729e6967bff73177b3c6f12beae52d8a8ba56043ea601`.
- Structure chunk hashes and row locators: `STRUCTURE_BM25_RESULTS.json` and `STRUCTURE_TARGETS.json`.
- Rebuild: `python -m scripts.topic3_structure_bm25 --variant full` in the isolated author environment, after its saved BM25 query vectors are available; each variant requires a fresh index path. `python -m scripts.topic3_assess_structure` creates the conservative assessment.

Region OCR and unit/column verification were **not** experimentally changed. The locked HTML inputs require no OCR, and the original iXBRL/source tables remain `PARTIAL_EXTRACTION`; a retrieved row alone cannot authorize a numeric answer.

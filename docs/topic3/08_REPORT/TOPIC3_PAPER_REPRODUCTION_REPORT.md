# Topic 3 paper-to-product reproduction report

## What was examined

The supplied 23-page image-only Topic 3 PDF was OCR-read and visually checked. The referenced public author project is pinned at Git SHA `16682dd42ca9cd4887ae74935cb3526dce580c49`; code and configuration mapping are in `../00_AUDIT/PAPER_TO_CODE_TRACEABILITY.md`. The repository's committed data contains a summary benchmark report but not its 47 SEC filings, 8,609 chunks, per-query runs or independent relevance judgments. Three supplementary files named in the work order were not present at the accessible paths. Consequently **exact reproduction is not established**.

## What was actually rerun

The pinned author parser, 500/100 chunker, FastEmbed BM25/BGE-small/SPLADE models, Qdrant sparse/dense collection, fixed RRF and deterministic second stage were executed on **two locked 2026 SEC 10-Q HTML filings**. The author chunker produced 121 chunks. Six machine-prepared questions (four known source-row targets, two unsupported) were frozen before the retrieval runs. Original author unit suite: 31 PASS, two warnings. R0–R6 results, per-query ranks and timings are in `../01_REPRODUCTION/BASELINE_BENCHMARK_REPORT.md` and `../01_REPRODUCTION/RETRIEVAL_RESULTS.json`.

The author benchmark's apparent Recall@10 derives its denominator from each method's own returned hits. The executable counterexample in `../00_AUDIT/AUTHOR_METRIC_COUNTEREXAMPLE.json` shows why this cannot be treated as independent recall. Its “neural” reranker is deterministic term-overlap code with an unused model name. PDF, README and committed summary timings/metrics also disagree; the discrepancies are traced in `../00_AUDIT/AUTHOR_EVALUATION_AUDIT.md`. No result here claims to exceed the author's report.

## Improvement result and meaning

On this exposed four-question development set, structure-aware SEC chunks indexed with the same BM25 model put 4/4 selected row targets at Rank 1, versus 0/4 for the author-style 121-chunk BM25 control. The structure index has 1,241 points, so BM25 statistics and evidence unit both differ. Ablations suggest issuer and period context matter on these questions, while row-only retrieval falls to 0/4 at Rank 1. See `../03_IMPROVEMENTS/CONTROLLED_EXPERIMENT_RESULTS.md` and `../04_ABLATION/ABLATION_STUDY.md`. The source targets are not human gold, and numeric accuracy is unmeasured.

The isolated product smoke loaded a real Hòa Phát scanned PDF and BIDV revised PDF, found source pages, ran three search modes and showed conservative answer states. React document QA now explicitly routes to the same production V3 retrieval service as Search, while legacy callers retain their prior default. It returns excerpts, never a guessed numeric value. A separate SEC verifier supported one HD source cell and refused a 2037 request. See `../06_PRODUCT_QA/PRODUCT_END_TO_END_QA.md`.

## Scientific conclusion

The work **reproduced methods on an alternative two-filing corpus**, demonstrated concrete source-location failures and measured a source-structure intervention on an exposed development set. It did **not** independently reproduce the original 47-filing benchmark or establish generalizable financial answer accuracy. Release classification: `RESEARCH_PARTIAL` until independent human-reviewed, untouched evidence and end-to-end verifier coverage exist.

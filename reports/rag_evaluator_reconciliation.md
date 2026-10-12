# RAG evaluator reconciliation

Historical holdout grading is now treated as development evidence because the questions were inspected. The current production regression run scored 5/5 answers correct and 100% evidence-in-prompt recall. Its page-range citation heuristic scores 4/5: R01 contains a correct partial answer and citations, but one citation falls outside the narrow expected-page window. This is recorded as an evaluator disagreement, not rewritten as PASS.

The final P0 run scored 4/4 answers, 100% Recall@8, 100% evidence-in-prompt coverage, 100% supported citation accuracy and 100% refusal recall. T15 was reclassified PASS because a grounded refusal is the intended outcome.

No independently sealed holdout was supplied. A Codex-authored set would not be independently blind, so `fresh_holdout_results.csv` records this acceptance item as BLOCKED rather than inventing a score.

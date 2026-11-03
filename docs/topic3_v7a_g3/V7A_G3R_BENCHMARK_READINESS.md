# G3R benchmark interface and gate

The 94-question G2 manifest, 47-filing source manifest, frozen corpus and F10 Policy B remain unchanged. The private 94-row additive reconciliation has a human-review queue but **zero approved human decisions**. Therefore final benchmark scoring is blocked.

An evaluation-ready record should contain `question_id`, frozen question hash, accession, answerability and negative-question category, source-cell annotations, source HTML hash/locator, original corpus chunk IDs with qrel review status, unjudged-candidate policy, method/version/index identity, evaluation split ID, and reviewer decision/provenance. A source cell and a relevant original retrieval chunk are distinct annotations.

Future author-method baselines: BM25, BGE Dense, SPLADE, BM25+Dense RRF, SPLADE+Dense RRF and the original Stage-2 heuristic. Frozen FAITH-R configurations must retain their original settings. Evaluation should separately report target-filing retrieval, source-passage retrieval, exact-cell retrieval, verified numerical answer, correct abstention, latency and compute cost. Incomplete qrels cannot be treated as fully negative. The sealed 94 questions are not to be used for method tuning or final scoring until human gold and protocol gates pass.

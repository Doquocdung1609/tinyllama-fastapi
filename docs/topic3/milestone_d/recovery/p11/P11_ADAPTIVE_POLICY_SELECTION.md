# P11 adaptive-policy decision

Before any P11 ranking, `p11_adaptive_policy_v1.json` fixed one exploratory D3-A-like candidate: exact/table categories use BM25 when five positive-scored BM25 hits exist; otherwise use RRF with 2:1 BM25:Dense weights, while paraphrases use equal 1:1 weights. Candidate budget is 40 per channel and RRF k=60. This heuristic counts positive scores, **not relevance**. P11's manually authored category tags feed this development script; this is not a production D1/D3 deployment or a new production default.

No adaptive finalist has been selected. Validation has no reviewed qrels and remains unscored. A development metric alone cannot select a finalist or justify Hybrid superiority. If the candidate is evaluated, preserve all negative results and record its route for every query. A future validation decision needs a preregistered criterion and source-reviewed labels; at most one finalist may proceed to a frozen held-out.

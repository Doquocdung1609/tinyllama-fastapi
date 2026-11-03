# G3T C3 research readiness

The evaluation design is versioned and locked: pre-registration SHA-256 `2a8372f17d0a421879bbca858ae09224b8b91d948e80ff2d239e771ebacc4b59`; C3 protocol SHA-256 `153873bb84a87c72c700c349253e46ddaff15e4536478fa98fdf400d2e2347cc`. Any substantive change requires v2 and a score-exposure statement.

**Tier A AI provisional: BLOCKED.** There are 94 source reviews but no EXACT original-single-chunk relevance judgments. The static original-corpus audit yielded 17,340 question/chunk pairs: 187 PARTIAL co-occurrences and 17,153 UNJUDGED. The depth-20 ranked union for six author arms and FAITH-R arms has not been run or judged. The 72-row AI-only release candidate is an answer-evidence subset, not permission to score retrieval.

**Tier H human certified: HUMAN_ADJUDICATION_PENDING and BLOCKED.** There are zero genuine human decisions and zero human-certified qrels. No final sealed benchmark was run. The deterministic four-filing bootstrap dry run validates calculation wiring only; it is synthetic and has no G2 scores.

The next technical step is a prospective, fixed-depth pooled candidate generation followed by original-chunk review, keeping UNJUDGED explicit and avoiding post-score expansion. The next human step is independent source and qrel adjudication, with owner signoff for a sealed final benchmark. Neither a source HTML match nor a row/value co-occurrence in a chunk is automatically an EXACT qrel.

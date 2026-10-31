# Research and product limitations

1. Original 47-filing/8,609-chunk corpus, historical model revisions and per-query author benchmark outputs are absent. The local 2-filing/121-author-chunk run is methodological replication only.
2. Original benchmark relevance is constructed from returned hits; its reported Recall@10 is not an independently judged recall. Original second-stage reranker is deterministic, despite “neural” naming.
3. Four SEC row targets and six questions were machine-prepared and exposed during tuning. No independent human gold or untouched held-out/unseen issuer set exists. No confidence interval or generalization claim is valid.
4. Structure intervention changes chunk granularity and BM25 IDF. Its 4/4 Rank-1 result cannot be attributed to a single metadata field or extended to other filings without testing.
5. Both locked SEC source documents are `PARTIAL_EXTRACTION`; the research evidence policy certifies zero financial values. Duration label in P&G net-sales question remains ambiguous without exact column validation.
6. Hòa Phát OCR row and BIDV revised columns were retrieved, but their digits, period, unit and original/adjusted/restated cells were not independently image-reviewed. No PDF numeric QA or Decimal calculation is claimed from them.
7. Product SEC source-cell verifier and PDF reviewed-cell verifier are separate. The new structure research index is not in production; React PDF document QA now shares production V3 retrieval but still returns excerpts rather than generated fact answers.
8. SPLADE document embedding peaked at 5,516.5 MiB process RSS and left only 0.8 MiB system available during the bounded run. Its use alongside OCR on this laptop is unsafe without a resource redesign.
9. Local Qdrant query microbenchmarks exclude embedding, server transport and browser time. Single end-to-end smoke latencies are not p50/p95. API peak RAM and OCR-only time were not instrumented.
10. Browser manual checks cover the isolated workspace and shown screens. Full automated browser, restart/recovery, adverse file and source-integrity matrix was not rerun here. Existing regression suite passed, but it does not replace scientific gold.

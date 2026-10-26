# P8 retrieval discovery

The existing P6 budget of 64 remains unchanged. Automatic original BM25 ranks from `p8_real_qa_results.json`: PG total assets 2026 rank 8 and prior comparative rank 3; HD total assets 2026 rank 4 and prior rank 2; PG net sales rank 47. Two-date HD/PG asset comparisons selected parents at ranks 4/3. A parent below budget is not promoted by expected numeric value; unsupported HD net sales and COST assets returned no numeric claim.

Before P8, `p8_source_cases.json` recorded 41 candidate rows and only one compatible parent. After adding the exact `us-gaap:Assets` concept pairing, `p8_source_cases_after.json` recorded three compatible parents. The decisive HD revenue blocker is not merely candidate rank: its fiscal duration and repeated rows need an independently reviewed contract. This is development engineering coverage, not Recall@5 or proof that increasing top-k improves ranking quality. Frozen D3/D5 rankings and the consumed held-out were untouched.

# Independent evaluation status and exploratory pilot

**Independent human judgments: 0. Sealed final evaluation runs: 0. Financial cells independently verified: 0.** A scientifically valid baseline-versus-FAITH-R improvement score is therefore pending. The frozen final 30-question design was not queried. The 30 old V5R questions were used only as an explicitly **unjudged exploratory pilot** after the candidate algorithms were frozen.

## What actually ran

On corrected Index B (8,670 points), the six pinned author methods and A2/A3/A4/A4R each ran on all 30 pilot questions: **300 live searches**. Full-text raw results remain ignored locally at `tmp/topic3_v6/pilot_raw.jsonl` (owner-machine byte SHA-256 `f4ee52ff41f354d2aea575fcc418c26a86ed9ebabd581fdcaf531fccd860fb78`). Tracked `V6_PILOT_RANKS_COMPACT.jsonl` preserves per-question Top-10 IDs, ranks, scores, source locators, fiscal labels and text hashes (LF-normalized SHA-256 `569c02a5467f62ec40f3724b8d8a1f34454956da08a880c349916c78eaa041e6`). `V6_PILOT_SUMMARY.json` records times and process memory. The unsupported FY2037 question is excluded from the accession denominator and yields zero hits under A2/A3/A4/A4R.

The only numerical retrieval proxy available before human review is whether the **preselected source accession appears**. It does not test the correct financial row, column, period, unit or value. On the other 29 pilot questions:

| Method | Source accession at Top-1 | At Top-10 | Search p50 ms |
|---|---:|---:|---:|
| Original BM25 | 16/29 | 23/29 | 254.5 |
| Original BGE dense | 11/29 | 29/29 | 41.2 |
| Original SPLADE | 14/29 | 28/29 | 610.6 |
| Original BM25+Dense | 16/29 | 28/29 | 301.5 |
| Original SPLADE+Dense | 14/29 | 29/29 | 671.0 |
| Original Stage-2 heuristic | 18/29 | 29/29 | 691.1 |
| FAITH-R A2 | 25/29 | 29/29 | 425.3 |
| FAITH-R A3 | 25/29 | 29/29 | 433.7 |
| FAITH-R A4 | 25/29 | 29/29 | 430.4 |
| FAITH-R A4R post hoc | 29/29 | 29/29 | 428.7 |

These counts are **not** Recall, MRR, nDCG, relevance accuracy or proof of superiority. A2 hard-filters the issuer and usually a single fiscal year, making source-accession occurrence easier by construction. A4R can favor a filing while selecting the wrong cell. No ordinary retrieval relevance metric or confidence interval is appropriate without independently established source-span qrels and coverage. The compact file permits future paired per-question comparison once reviewers finish; it must not be scored as gold now. The 30 questions span 13 filings, so future intervals must also account for within-filing dependence.

In pilot raw pools, A3 adds at least one ID beyond A2 in 7/30 questions, A4 changes Top-1 relative to A3 in 9/30, and A4R changes Top-1 relative to A4 in 10/30. Whether any such movement is *toward the right cell* remains unknown. The result is a check that the methods really execute and differ, not a quality measurement.

## Final protocol after human adjudication

Use the frozen fresh split and original SEC source-review packets. Reviewers resolve answerability, exact source span, row, fiscal column, unit and value first. Freeze qrels/answer cells by checksum. Then run the ten locked methods once on the same corrected B index and compare paired accession hit, candidate entry, correct evidence Top-1/3/10, exact cell, answer correctness and abstention. Report judged coverage, incomplete-qrel bounds, uncertainty interval and per-filing failures. If any algorithm is repaired after viewing these results, that split becomes development and a new untouched split is required. Current final status is **EVALUATION_PENDING_HUMAN_REVIEW**.

# V3R3 precision evaluation — exposed regression only

The 178 queries are the prior V3 (84), V2 (70) and V3R (24) exposed sets, with unchanged qrel hashes. The final 178 query records are in `AFTER_178_CEO_FINAL.json.progress.jsonl` and `AFTER_178_CEO_RECONSTRUCTED.json`; the second prewarm gate returned `LOW_MEMORY_DEFERRED`, so this is **query-complete, harness-partial** evidence. `NEW_INDEPENDENT_EVAL_NOT_AVAILABLE`. No owner workbook verdict was used.

| Metric | PR #27 | V3R3 |
|---|---:|---:|
| Correct classified metric Top-1 | 124/130 | 128/130 |
| Known wrong classified metric Top-1 | 3/130 | 0/130 |
| Unclassified metric Top-1 | 3/130 | 2/130 |
| Exact source evidence Top-1 | 102/142 | 106/142 |
| Source locator Recall@5 | 128/142 | 129/142 |
| Source locator MRR@5 | 0.8124 (142) | 0.8300 (142) |
| nDCG@5 | 0.8013 (142) | 0.8161 (142) |
| Exact cell Top-5 | 13/16 | 14/16 |
| Numeric no-answer abstention | 36/36 | 36/36 |
| Eligible positive numeric evidence | 2/2 | 2/2 |

Paired source Recall@5 has one gain (`v3f007`) and zero losses. Six Top-1 or source changes are listed in `PAIRED_PRECISION_FINAL.json`; `v3d013`, `v3d014`, `v3f007` and `v3r-pnj-08` improve metric or exact source, `v3f018` improves exact source but stays unclassified, and `q048` is a negative query with a classification change. Unclassified outcomes remain separate from correct and known-wrong. Wrong period, basis and unit rates remain **NOT_MEASURED**; neither a zero numerator nor source retrieval proves those properties.

## Strata

Strata below are old/new exact evidence Top-1 counts among source-positive queries; `UNSPECIFIED` rows retain the older qrels whose stratum was not annotated. Missing denominators are shown as —.

| Dimension | Stratum | PR #27 | V3R3 |
|---|---|---:|---:|
| pdf_type | UNSPECIFIED | 50/56 | 50/56 |
| pdf_type | mixed_native_header_image_table | 2/9 | 3/9 |
| pdf_type | native | 13/16 | 13/16 |
| pdf_type | scan | 19/36 | 20/36 |
| pdf_type | scan_existing_ocr_layer | 6/9 | 7/9 |
| pdf_type | scanned | 7/8 | 8/8 |
| pdf_type | text-native | 5/8 | 5/8 |
| content | UNSPECIFIED | 62/72 | 63/72 |
| content | narrative | 0/4 | 0/4 |
| content | tabular | 40/66 | 43/66 |
| language | UNSPECIFIED | 50/56 | 50/56 |
| language | en | 15/31 | 17/31 |
| language | vi | 37/55 | 39/55 |
| form | UNSPECIFIED | 62/72 | 63/72 |
| form | exact | 23/37 | 24/37 |
| form | paraphrase | 17/33 | 19/33 |
| pages | UNSPECIFIED | 62/72 | 63/72 |
| pages | multi | 4/6 | 4/6 |
| pages | single | 36/64 | 39/64 |
| answerability | UNSPECIFIED | 50/56 | 50/56 |
| answerability | negative_numeric_context | — | — |
| answerability | no_answer | — | — |
| answerability | positive | 40/70 | 43/70 |
| answerability | source_positive_unreviewed | 12/16 | 13/16 |

Other per-stratum metrics and all denominators are preserved in `PAIRED_PRECISION_FINAL.json`. The 12 source-positive queries with no metric inferred from intent are unjudged for Correct Metric@1; 36 numeric-negative queries all abstained. No new independent document or human labels were available, so the result is a regression check only.

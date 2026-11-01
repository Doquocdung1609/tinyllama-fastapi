# Verified failure catalog

| ID | Observed evidence | Category / qualification |
|---|---|
| F01 | Author `evaluation/benchmark.py` derives relevant IDs from results just retrieved | Evaluation circularity; genuine code defect for independent Recall |
| F02–F03 | P7G 15/47 fiscal mismatches, 3,516/8,670 chunks; P7L recorded A/B target-filing hits 0/90 versus 90/90 | Metadata/filtering; target filing is not financial cell |
| F04 | Saved questions explicitly identify company, fiscal year and metric; author reranker relies on heuristic text regex | Query constraint risk; not an independently measured parser comparison |
| F05–F07 | F10 `bm25_dense` corrected Top-10 known-positive top1 3/15 and top10 14/15 | Evidence localization/ranking on exposed development labels; one target absent or unjudged in Top-10 |
| F08 | Author `reranker.py` uses arithmetic features, no neural inference | Implementation/report mismatch |
| F09 | Corrected P7L payload period can say FY2022 while frozen header says FY2023 | Metadata/text inconsistency; V5 excludes header from phrase matching |
| F10 | F10 checkpoint: 900 rank rows, 192 unique `UNJUDGED` case/chunk pairs; eight sealed-design rows pending | Incomplete qrels; no ordinary Recall or final holdout evaluation |

Source rows and case IDs are in [replay_results.json](replay_results.json), input hashes alongside them. Meta FY2024 CAPEX remains `PARTIAL_NOT_GOLD` top1 after rerank; AMZN FY2022/FY2024 remain `NO`. These are explicit failures of the current rule. A correct chunk label does not validate a value, unit, statement scope or comparative column.

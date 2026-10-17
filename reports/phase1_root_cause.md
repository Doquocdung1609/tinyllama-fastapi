# Phase 1 root causes and repairs

Tested implementation lock: `32d250955900dc81c54db959f6ec7135333d338a`  
Final benchmark tooling commit: `fe0462bbd777740138dd50488572dde2950d090a`

## REAL03 table caption and false figure

On page 3 of `CO2_FDI_FINAL_PUBLICATION_READY.pdf`, the true caption bbox is `[49.05, 583.93, 213.79, 593.89]`, the table bbox is `[49.0, 596.73, 562.97, 681.35]`, and the vertical gap is 2.84 pt. All 19 drawing primitives belong to the table fill/grid.

The old logic searched caption words globally. The word `mô hình` in narrative text satisfied the figure-label heuristic, while any page drawing satisfied the graphical-region heuristic. Downstream table rendering then preferred the first column header `Nhóm` over the real caption.

The repair in `app/services/pdf_service.py` now anchors caption patterns to coordinate-aware lines near the table, joins compatible multi-line captions, records bbox/distance/provenance, returns `UNKNOWN_CAPTION` when unverified, excludes table-contained drawing primitives from figure detection, and requires an independent graphical region for a figure. `app/services/rag_service.py` uses the verified caption for inventory and explanation.

Before: caption `Nhóm`; a narrative region appeared as a figure.  
After: `Bảng 1. Cấu trúc mẫu theo nhóm thu nhập`; one table, zero charts, zero figures. The real API answer is stored in `reports/phase1_real03_queries.json`.

## Financial calculation and verification

The original number parser and dispatcher had incomplete unit coverage, a limited formula set, and could route any mention of ROA/ROE to ratio calculation. This caused statistical questions such as “ROA có bao nhiêu quan sát?” to return an average-balance warning.

The repair in `app/services/calculation_service.py` adds bilingual units and scales, parenthesized negatives, period-aware formulas, average-balance requirements for ROA/ROE, table-slice grouping, company qualification, and explicit refusal of uncertain OCR cells. Statistical ROA/ROE lookups are no longer treated as formula requests. A conservative OCR text-row fallback preserves year order and sign and always labels the result for source-image review.

## Cross-language grounding and locale numbers

The deterministic grounder compared surface tokens. A Vietnamese answer grounded in an English table could be deleted even when its metric and number were correct. Locale-equivalent values such as `0,00` and `0.00` were also treated as different anchors.

The repair in `app/services/rag_service.py` adds language-neutral finance concepts for evidence validation, Vietnamese-to-English retrieval aliases, and locale-neutral numeric anchors. Numbers still have to occur in the included evidence; concept matching cannot introduce a value.

Development regression before repair: 2/9 PASS.  
After repair: 9/9 PASS in `reports/phase1_development_holdout1_after.csv`.

## OCR diagnosis

The hard Vietnamese table errors are mainly accents, financial-term spelling, header recognition, and row/column segmentation. Critical clean numeric cells remained more reliable than prose. Repeating deskew, contrast, adaptive threshold, row and cell crops did not improve the same hard fixture overall.

The adopted change is a conservative exact dictionary normalization for financial labels only. Raw OCR, word boxes, confidence, normalized value and normalization events are all retained. Numeric values are never plausibility-corrected. Difficult OCR evidence is marked `NEEDS_REVIEW`; exact calculation from such table cells is blocked.

## Remaining root causes revealed by sealed holdout

The final holdout was not used to change application code. It found:

- Multi-column scientific tables do not preserve hierarchical column associations reliably; FH04 returned 90.2% instead of 75.7%.
- Grounding can discard the correct Table 1 value (FH03).
- Retrieval can cite a later summary page rather than the requested classification page and omit the explicit count (FH01).
- A list-style slide can still be extracted as an uncaptioned table (FH08).
- Follow-up resolution remains weak for “loại thứ hai” and cross-reference phrases such as “Câu 4 ngay phía trên” (FH09-FH11).
- A refusal can retain an irrelevant citation (FH07).

These are critical correctness defects and keep Phase 1 unaccepted.

## Reproduce

```powershell
$env:PYTHONPATH='.'
.\.venv\Scripts\python.exe scripts\phase1_structure_benchmark.py
.\.venv\Scripts\python.exe scripts\phase1_financial_benchmark.py
.\.venv\Scripts\python.exe scripts\phase1_fresh_holdout.py
```


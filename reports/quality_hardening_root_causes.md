# Quality hardening root causes

## Baseline and checkpoint

Baseline commit: `1124fba1304c4b8a8f7e610d69043160164ab6bb`. A recoverable checkpoint is stored under `checkpoints/quality-hardening-20261012-102242`; it includes the Git diff, production document/Qdrant snapshots and a consistent SQLite backup. Production held 1,947 vectors and was not mutated.

## C05: structural navigation was treated as semantic QA

**Reproduction.** “Trang 1 có các bảng và biểu đồ nào?” returned an unsupported-information message. The next question resolved to `table:p1:t2`, yet the generated answer described values 100/125 and cited `table:p1:t1`.

**Root cause.** The resolver correctly created the ordinal source ID, but the answer path still depended on hybrid retrieval and model generation. The old evaluator at `scripts/conversation_api_benchmark.py` only checked whether `table:p1:t2` appeared anywhere in selected evidence. It did not check the table actually entered the prompt, the answer content, or the supporting citation.

**Repair.** `app/services/rag_service.py:945` now routes page inventories and ordinal-table explanations through indexed page/table/chart metadata. It loads the exact table structure and builds the subject, headers, periods, rows, units/confidence and source citation deterministically. The evaluator at `scripts/conversation_api_benchmark.py:107` enforces all required facets and exact source IDs.

**Before:** unsupported inventory; follow-up described the wrong table and cited table 1.

**After:** “Bảng 2 trình bày Dòng tiền… Kinh doanh — 2023: 20, 2024: 28. Đơn vị: bảng không ghi rõ đơn vị.” with only `table:p1:t2`. The absent-table case reports that page 1 has only two tables.

## C09: claimed numbers contaminated retrieval and disappeared on correction

**Reproduction.** “Lợi nhuận năm 2024 là 15 triệu đồng đúng không?” returned insufficient information even though the table contains 16. The old C09 evaluator passed a correction if the rewritten question and any citation existed.

**Root causes.** A false value was used as a retrieval anchor even though it need not occur in the source. The correction resolver then sanitized 15 into “bao nhiêu”, removing the hypothesis required for comparison. The first verifier handled only tables with metrics in rows and years in columns; the production fixture uses years in rows and metrics in columns.

**Repair.** `app/services/rag_service.py:1103` uses a retrieval-only query with untrusted non-year numbers removed. The original question remains intact. `app/services/conversation_service.py:275` carries the full prior hypothesis into a correction turn. `app/services/calculation_service.py:138` performs deterministic four-way verification and `:166-203` supports both table orientations. The answer is rendered from the exact source cell and cites its included E-ID.

**Before:** refusal without citation.

**After:** “Không đúng. Khẳng định 15 triệu đồng khác giá trị với nguồn. Theo bảng, lợi nhuận … năm 2024 là 16 triệu đồng.” with `table:p1:t1`. The same result is returned when the user asks to recheck the prior answer.

## Evaluator false PASS

C05 equated retrieval with correctness. C09 equated reference rewriting plus citation presence with correction. Both could pass while the user-facing answer was wrong. `scripts/conversation_api_benchmark.py:44` now records independent context resolution, extraction, prompt evidence, answer correctness/completeness, numeric correctness, claim-supporting citation and refusal behavior. A strict PASS requires every mandatory dimension. Qwen does not grade its own output.

## OCR

The 15.85% Vietnamese scanned-table CER is mostly missing diacritics in Tesseract output. Controlled deskew, contrast, adaptive threshold, table-line removal, region/row OCR, PSM 4/6/11 and language-order tests did not improve CER; some damaged numeric cells. The production route therefore remains the measured baseline. It preserves 6/6 critical numeric cells and 4/4 header tokens under accent-insensitive matching. This is a documented unresolved quality limit rather than a claimed improvement.

## Charts

The earlier chart path treated every extracted label/value pair as directly comparable. It did not explicitly prevent dual-axis or cross-unit comparisons and could fall through to free generation when exact labels were absent. `app/services/calculation_service.py:441` now returns deterministic limitations for diagrams, unreadable exact labels, missing requested series and incompatible axes/units. Exact values remain supported only when labels are machine-readable.

## Duplicate production documents

The two 971-point lecture documents have the same byte SHA-256 and the same normalized extracted-text hash. They are genuine exact duplicates, not merely equal chunk counts. They predate the current stable content-hash upload identity. Current isolated uploads reuse the document ID and do not add vectors. Cleanup remains a dry run because deleting one legacy ID could invalidate external citations.

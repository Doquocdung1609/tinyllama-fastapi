# V3R development extraction coverage

**Gate B/D: PASS_BOUNDED for checked source-location recovery;not certified numeric answers.** EXTRACTION_COVERAGE_RAW.json retains actual measurements for14sampled pages across HPG,BIDV,CEO,FOX,REE,Samsung Electronics and SEM. All14have in-page source-coordinate bounds;411candidate rows were found in the first complete audit. Three original-source negative crops (company logo,corporate stamp,signature) did not become financial tables. Synthetic native/mixed/duplicate/rotation/failed-region regressions are separate from these source measurements.

All seven previously missing SEM values were recovered as **digit-equivalent raw OCR candidates in the correct labelled row,current2025KRW column and manually checked original-image cell window**. Year and currency candidates carry actual header words/coordinates. No number was inserted from the gold labels. Only3/7raw strings reproduce original punctuation exactly;the other4have missing/different separators. Confidence is sometimes low and competing readings are retained. Such strings are not silently normalized into financial facts and no SEM cell becomes REVIEWED or automatically answer-eligible.

The first audit incorrectly estimated the equity row's coordinate window;the source crop proved it selected the following total-funding row. The failed first output and explicit development annotation correction are preserved. No financial value,label,query,period or unit was changed to raise a retrieval score. This is an agent source audit,not independent human review.

Source-coordinate checks and source-cell matches are bounded. Financial-value coverage here means signed digit equivalence *within the matched source cell*,not an arbitrary number anywhere on the page. Row-label,period-column and KRW-currency checks pass7/7for these cells. Complete column/scale interpretation of every table is not established. Negative values and currency/current-prior counterexamples are tested;blank cells are never treated as zero.

Runtime coverage uses raster/text geometry as well as OCR outcomes. Old complete checkpoint tokens can be reused with raw hash ancestry;missing SEM regions receive new regional OCR. The new generation retains all old PDFs/checkpoints separately. READY only means technical indexing completion. Remaining image/text-coverage warnings stay visible and document-level financial review stays pending even if a specific cell has an audited review.

Actual sampled resource observations are in the raw JSON (including elapsed page times,parent/combined OCR RSS,parent CPU and sampled child CPU lower bounds). The extractor uses CPU Tesseract,not GPU;no large model or paid OCR was installed. An isolated15.4MBofficial English tessdata_best trial did not fix the key failure enough to justify changing the deployment;it is not used by the selected pipeline. Existing eng/vie/osd and locked Nomic remain the active resources. Probe outputs and resource hash record this unsuccessful experiment rather than claiming it improved coverage.

Source crops,raw before/after results and exact denominators will accompany the final owner packet. Future new-source evaluation must be reported separately after the full extraction/index/search/performance policy is frozen. No independent review or SEARCH_V3R_LOCKED claim follows from this bounded gate.


## Checked SEM cells

All locators refer to the current 2025 KRW column, not the neighboring USD or prior-year columns. The confidence below is engine confidence, not correctness probability. Source images and checkpoint ancestry are linked in the owner packet.

|Metric|PDF page|Column index|Original display|Unmodified OCR candidate|Confidence|Financial review|
|---|---:|---:|---|---|---:|---|
|assets|7|1|14,595,895,255,468|14,595895.255468|64.0|PENDING|
|liabilities|8|1|4,798,551,372,605|4798551372605|56.0|PENDING|
|equity|8|1|9,797,343,882,863|9,797,343,882,863|29.0|PENDING|
|cash_equivalents|7|1|2,701,205,916,236|2,701,205,916,236|18.0|PENDING|
|inventory|7|1|2,412,996,843,057|2,412,996843,057|57.0|PENDING|
|pretax_income|9|1|895,831,372,804|895,831,372,804|79.0|PENDING|
|net_income|9|1|730,989,517,218|730.989.517.218|50.0|PENDING|

Final sampled extraction audit: 14 pages, 411 candidate rows, 14/14 coordinate-bound checks, 7/7 bounded SEM row/year/currency/window matches, 3/7 exact raw punctuation, and 3/3 actual decorative negative regions passing. Native/OCR duplicate-fusion and four quarter-turn coordinate regressions pass separately. An actual illustration-only negative corpus was not assembled (SKIP); the decorative source sample is not exhaustive.

The first generation ingested 309 pages / 7 PDFs in 300.05 seconds using verified prior checkpoints where appropriate. This is not fresh OCR throughput. Fresh PNJ scanned ingestion took 206.92 seconds for 28 pages, including indexing/embedding; ACB took 41.26 seconds for 78 mostly native pages. NEW_SOURCE_EXTRACTION_TIMINGS.json separates per-page regional extraction wall time from total ingest time. It does not claim isolated Tesseract CPU time.

CEO and Samsung Electronics retain EXTRACTION_COVERAGE_WARNING; fresh ACB also retains TEXT_LIKE_REGION_OCR_EMPTY. Those warnings are visible, not reclassified to obtain a pass. PNJ's eight checked source cells, including the rotated income statement, have exact source-cell locator hits at top five. All 16 newly annotated values were found in checkpoint cells, but global document/currency-scale completeness is unproven. No new cell is REVIEWED.

Gate B and the development portion of Gate D are PASS_BOUNDED. Financial accuracy of every cell, full-table column interpretation and post-freeze ACB label/scale correctness remain limitations.

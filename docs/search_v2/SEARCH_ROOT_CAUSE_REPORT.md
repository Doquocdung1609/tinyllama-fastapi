# Search V2 root-cause audit — 2026-10-28

Baseline `6aa3ccd97cb0f59a0b338e5d6233f04897a992ce` (PR23). Reproduced before implementation on a stopped, byte-copied isolated workspace, using installed locked Nomic. Original owner workspace is not used for experiments. Query: “Tổng tài sản của Công ty mẹ Hòa Phát tại ngày 31/12/2025 là bao nhiêu?”, scoped to that PDF.

Observed top5 PDF pages: B0 `[10,3,2,17,4]`; B1 `[8,16,17,19,4]`; B2 `[17,16,8,3,4]`. The first two RRF ranks differ from the owner observation, but the reported failure is reproduced: the correct row on page3 is rank4. Exact scores and IDs will be retained in audit evidence.

Confirmed causes:

1. Every folded word is OR'ed into FTS5, including company/date/question boilerplate. No phrase or label field weighting. Vietnamese folding correctly handles accents/đ, but does not express financial intent.
2. Fixed RRF k60 merges ranks without checking metric/basis/period. A page high in both noisy lists outranks the exact total row; RRF score is not probability.
3. PDF chunks are sequential ~700-character line groups, no overlap, no inherited table headers. Source row at end of page3 is in a different chunk from its date/scope header. Preview truncation1400 does not fix missing context. Footer/watermark noise remains searchable.
4. Baseline vectors embed raw chunk text with Nomic document prefix,768d/COSINE and first6000 policy. These chunks are normally shorter than6000, so this regression is **not** proven to arise from truncation. Query is full natural Vietnamese; company/date boilerplate and OCR fragmentation differ from row text. Semantic model limitations are a hypothesis, not measured multilingual accuracy.
5. Real page evidence has words/confidence/geometry and candidate rows, but search does not index rows or use reviewed facts. OCR income-statement labels are visibly fragmented (e.g. a net-revenue row's label is incomplete). High OCR confidence does not verify financial content. Some native pages also contain multiple original/adjusted/restated columns.
6. Baseline Qdrant provenance/digest/filter guards work. Dense pool40 and lexical pool40 are fixed; no evidence of an identity/distance defect. SEC has an independent verified snapshot and remains unchanged.
7. UI describes extracted text but does not distinguish a related paragraph from evidence satisfying the full question. PDF page numbers are1-based; exact row/cell boxes already exist and can be used without invented coordinates.

Plan frozen before improvements: B0/B1/B2 remain unchanged; C1 controlled lexical phrases/fields; C2 additive versioned row index; C3 deterministic evidence compatibility reranking; C4 bounded candidate combination. No new mandatory model. Benchmarks must distinguish source annotations from independent human review. No SEARCH_V2_LOCKED unless all gates pass.

Original run bytes (including superseded diagnostics and first test) are retained in MEASURED_RUN_SNAPSHOTS.zip; per-entry hashes are in its manifest. Final result JSON files use one record per line without changing any measured values.

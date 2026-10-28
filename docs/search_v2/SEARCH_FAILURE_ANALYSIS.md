# Search failure analysis

Initial HPG full-question failure is reproduced: B0 pages10/3/2…, B1 page8 first, B2 pages17/16/8/3…. Correct source row is page3. C4 does not change RRF to force an answer: it adds a source-bound row index and compatibility rules, independently preserving the old baselines.

Development review caught a real unsafe promotion: a narrative risk question was labelled as answered by an unrelated reviewed liabilities cell. The repaired policy requires an explicit matching metric before numeric eligibility. Generic multiple source periods and original/restated columns now require clarification. Initial diagnostic files remain evidence of that failure, not acceptance results.

## Remaining heldout misses / incomplete locator coverage

- q015 (hpg_pretax): Lợi nhuận kế toán trước thuế Hòa Phát báo cáo riêng quý IV năm 2025 → Recall@5=0.000, first locator=[].
- q021 (hpg_financial_revenue): Tìm doanh thu tài chính trong kết quả kinh doanh Hòa Phát → Recall@5=0.000, first locator=[].
- q022 (hpg_financial_revenue): Doanh thu hoạt động tài chính quý IV 2025 của công ty mẹ Hòa Phát → Recall@5=0.000, first locator=[].
- q059 (sec_PG): What were PG net sales for the three months ended September 30, 2026? → Recall@5=0.000, first locator=[(None, None, 'fin_646a74814dc203212d54b1a94ab6d8ff')].
- q060 (sec_PG): P&G net sales September 2026 quarter → Recall@5=0.000, first locator=[(None, None, 'fin_5f7cf498be431b5f61d6c2915be69868')].
- q061 (sec_PG): Show PG net sales in the income statement → Recall@5=0.000, first locator=[(None, None, 'fin_600c3d68b67287564f599173bd302228')].
- q062 (sec_PG): Net sales Procter and Gamble quarter ended September 30 2026 → Recall@5=0.000, first locator=[(None, None, 'fin_0f40b123dda534e08723949e2e0ae8db')].
- q066 (cross_page_identity): Tìm bằng chứng các trang để kiểm tra phương trình kế toán công ty mẹ Hòa Phát năm 2025 → Recall@5=0.333, first locator=[(4, None, 'pdf_4a92af827aaf1e73e017544d0ff20d0d_4_00007')].

No weights were optimized against test labels. A critical unknown-proper-name guard repair after the original test invalidates any untouched-heldout certification; v2.6 reuses those test queries as regression cases. SEC misses remain a passthrough baseline limitation; multi-page source coverage is not the same as finding one relevant row. Uncertain OCR labels/date/basis can still prevent retrieval. No manually fabricated headers/numbers were added to make a case pass.

The original all-token OR, source header separation and broad dense rankings remain visible in B0/B1/B2. False-negative source matching is possible because annotations are provisional/non-exhaustive. A further human audit is required before interpreting a top1 outside these labels as wrong evidence. No claim of full ontology coverage, automatic table verification, general market QA or multilingual model superiority.

Original run bytes (including superseded diagnostics and first test) are retained in MEASURED_RUN_SNAPSHOTS.zip; per-entry hashes are in its manifest. Final result JSON files use one record per line without changing any measured values.

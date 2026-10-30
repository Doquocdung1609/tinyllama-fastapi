# V3R3 baseline audit

Draft PR #27 was checked at exact `006d056d47ce1e417befd965937e38536045850a`. V3R3 starts from that commit. The prior `SEARCH_V3R2_PARTIAL` decision is retained as the before state.

Confirmed: the V3R2 retrieval candidate layer preserves raw OCR/source boxes, seven SEM cells stay pending, and the existing eight reviewed facts are retained. The owner clone contains nine READY PDFs; its raw source and 88 SEM checkpoint hashes were compared with the stopped V3R root. The Nomic digest remains `0a109f422b47e3a30ba2b10eca18548e944e8a23073ee3f3e947efcf3c45e59f`, 768-dimensional COSINE. Existing SEC generations, source PDFs, old qrels/results, models and user `output/` are outside this repair. The old contributor branch/workspaces remain rollback points.

Workbook check: all 26 cases, 30 image references and their local PDF SHA256 values match; all human decision/reviewer/date/note cells are blank and all 26 completion formulas are present. See `BASELINE_AUDIT.json`. The prior workbook has not been edited.

Confirmed ranking defect: V3R2 combines capped lexical FTS score with a fixed metric boost. When OCR damages a financial row, a different classified metric or generic chunk can rank first. The previous 178-query results contain PNJ net-income, CEO net-sales, REE investment-property and SEM continuing-operations examples. Some have the right source page in Top-5 but the top result has a different or unclassified metric. An unclassified result is not evidence of correct metric, even if the aggregate wrong-classified numerator falls.

Hypothesis under test: penalizing a known conflicting metric and cautiously recovering a source-anchored VAS income-statement row can improve precision without changing numeric eligibility. Regression will decide whether this causes source losses. The old V3R2 full result is the immutable comparator.

Evidence limits: the 178 questions and 26 owner packet cases have already been viewed by Codex. They are regression only. No independent human verdict or new held-out source is available. Whole-machine memory and Chrome RSS do not alone prove a leak. Remote Actions on PR #27 failed before steps due GitHub account spending/payment status, not a test result.

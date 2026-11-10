# Native source recovery checkpoint — 2026-11-02

`app/product/native_financial_tables.py` is a bounded native PDF geometry adapter. It reads authenticated PDF bytes, groups words by baseline, recognizes an aligned multi-year header, reconstructs right-aligned value columns and excludes adjacent percentage tokens. A nearby statement/segment heading supplies **candidate** scope; page-wide unrelated scope words are not used by this adapter. Parentheses remain negative Decimal values. Every recovered cell retains raw display, row label, year header box, value box, page, source SHA256 and original retrieved chunk references when invoked through the product service.

Limits: at most 12 retrieved pages, 12,000 words per page, 20 MiB PDF, unrotated native text only. Fiscal-year headers are not silently converted to exact fiscal start/end dates. A bare dollar symbol is not silently converted to USD. OCR and layouts without an aligned year header remain unsupported. Cells are explicitly `CANDIDATES_NOT_ELIGIBLE_FACTS`; this checkpoint does not insert them into reviewed_facts or return numerical SUPPORTED answers.

The response field `source_verification_evidence` is separate from original retrieval hits. Source-side table recovery does not grant additional retrieval credit. The existing reviewed-fact path remains available. Its older page-wide scope check has NOT yet been replaced with a fully table-bound manual-review policy; that remains an open verification issue.

## Real Apple source observations

`V7P_RECOVERED_SOURCE_CELLS.json` records actual recovery on pages25/32 of the authenticated 80-page PDF. It recovers Net income 112,010, Americas 178,353, total net sales 416,161 and 391,035 with source boxes. The five non-total geographic rows sum to the total. Diagnostic Decimal arithmetic is 6.43%. These are geometry/diagnostic observations, **not** end-to-end verified answers.

A non-Apple HPG PDF was inspected read-only on pages1–12 (source hash in JSON); zero supported tables were recovered. No generalization success is claimed. Generic native PDF tests verify negative values, unknown unit/scope, incomplete header and tamper rejection.

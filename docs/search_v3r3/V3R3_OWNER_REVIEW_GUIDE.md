# Owner source review guide — HUMAN_AUDIT_PENDING

The original [26-case checklist](../search_v3r2/V3R2_HUMAN_AUDIT_CHECKLIST.md), [fillable workbook](../search_v3r2/V3R2_HUMAN_AUDIT_RESULTS.xlsx), source images and SHA-linked API results remain the review packet. V3R3 does not fill any owner decision.

1. Open the image named in column M beside the workbook and confirm the PDF SHA256 in column N. Compare the row label, current/prior period, statement scope, source currency/unit and exact cell. Rotate the original page if needed. A region box is only a locator, not an exact-cell certification.
2. Check signs, parentheses, decimal/group separators and whether a blank or dash really means no value. Compare OCR characters with the image; record a corrected reading separately in notes if needed. Do not overwrite raw OCR.
3. In the yellow fields B–E, select ĐÚNG / SAI / CHƯA RÕ, record reviewer and date, then describe any mismatch. A formula indicates whether required human fields were entered; it never certifies the financial value.
4. After independent review, the owner may submit a decision through the existing fact-review workflow with source row/column, period, unit, basis, raw display and box. That step must verify current PDF/checkpoint hashes and preserve review history. V3R3 does not submit decisions on the owner's behalf.

Review first: seven SEM scanned cells (malformed separator and KRW/USD/current/prior risks), three ACB rows (including the corrected but not independently approved net-income locator), PNJ net-income OCR row, then negative issuer/period/unit cases and the HPG/BIDV multi-page examples. The remaining cases can follow in sheet order.

All 30 image references and associated original source hashes were checked in `BASELINE_AUDIT.json`. Source-located and raw-digit matched are weaker claims than reviewer-confirmed exact value; numeric answer eligibility is a separate guard. Until signed human results exist, status stays `HUMAN_AUDIT_PENDING` and `SEARCH_LOCKED` is unavailable.

# Financial Assistant QA

| Case | Actual result | Assessment |
|---|---|---|
| BIDV: “BIDV công bố điều chỉnh báo cáo tài chính 2024 vì lý do gì?” | Source quotation on PDF page 1 states changes followed State Audit results; five page citations; `SOURCE_TEXT_UNREVIEWED`. | PASS for source-linked narrative answer; OCR text still needs visual review. |
| Hòa Phát: unit of Q4 2025 report | Page 24 OCR shows “Quý IV năm 2025 Quý IV năm 2024 / VND VND”. Answer selects the unit-bearing line; `SOURCE_TEXT_UNREVIEWED`. | PARTIAL: cited unit, no certified numeric cell. |
| BIDV consolidated assets in 2037 | `INSUFFICIENT_EVIDENCE`, no numeric citations or values after repair. | PASS safe refusal. |
| Home Depot total assets on 2026-08-02 | SEC path returned 109,384 million USD, displayed as 109,384,000,000 USD, with a source cell citation. | PASS verified SEC extract; separate from PDF/OCR path. |
| BIDV numeric OCR question in 2024 | `NUMERIC_UNVERIFIED`, `values=[]`, source pages offered for review. | PASS safe abstention; PDF numerical QA incomplete. |

The excerpt answer is a source quotation, not an LLM-generated verified financial conclusion. A corrected single response is not a general accuracy benchmark. See browser screenshots and the explicit limits in `V4_FINAL_ACCEPTANCE.md`.

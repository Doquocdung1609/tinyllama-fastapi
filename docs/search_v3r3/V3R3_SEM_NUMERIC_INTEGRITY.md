# SEM numeric integrity — source found, value unreviewed

The preserved SEM PDF SHA256 is `0991f170e8d358d9b09f851c49894d22f1a5184a9dab6191bc528bb46ec3a6a7`. All 88 original page checkpoint hashes match the previous V3R workspace. The seven original-source image locators are pages 7–9 in the owner packet. No OCR text, confidence, box, source PDF or reviewed fact was rewritten.

The table below compares the provisional image transcription with raw OCR returned by the prior live API in `HUMAN_AUDIT_CASES.json`. Removing separators yields the same digit sequence in all seven; this **does not prove decimal/grouping, sign, column, year or exact value**. All seven pages were located within Top-5 in the saved API packet.

| Case | PDF page | Provisional image reading | Raw OCR from matching digits | Raw exact string | Review / numeric eligibility |
|---|---:|---|---|---|---|
| Assets | 7 | 14,595,895,255,468 | 14,595895.255468 | No; invalid grouping | Pending / no |
| Liabilities | 8 | 4,798,551,372,605 | 4798551372605 | No separators | Pending / no |
| Equity | 8 | 9,797,343,882,863 | 9,797,343,882,863 | Yes | Pending / no |
| Cash equivalents | 7 | 2,701,205,916,236 | 2,701,205,916,236 | Yes | Pending / no |
| Inventory | 7 | 2,412,996,843,057 | 2,412,996843,057 | No; invalid grouping | Pending / no |
| Pretax income | 9 | 895,831,372,804 | 895,831,372,804 | Yes | Pending / no |
| Net income | 9 | 730,989,517,218 | 730.989.517.218 | No; convention differs | Pending / no |

Financial meaning requires row alignment, source subtotal/total, sign and parentheses, current 2025 versus prior 2024 column, and KRW versus USD. The cell-specific unit candidate uses original header-word geometry; raw OCR and candidate boxes remain visible. An apparently valid numeric syntax can still be wrong OCR or a wrong column. The V3R3 ranking adjustment cannot make any cell eligible; only the existing source-bound human review workflow can.

Four distinctions for every case: **source located = yes; digit sequence located = yes; exact human-reviewed value = no; numeric answer eligible = no.** Independent owner review may document a corrected reading beside raw OCR and submit it only after source/hash/row/column/period/unit checks. Until then these are retrieval candidates.

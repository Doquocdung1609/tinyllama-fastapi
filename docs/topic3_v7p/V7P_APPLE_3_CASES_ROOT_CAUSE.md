# Apple P0 source inspection and root causes

The local 80-page PDF hashes to `3eb270b22acb7d8d8e9c32a43dc221dec3345f8e4bca02755fdbc1ee16c823de`. Native text and matching text boxes were inspected on PDF pages 25 and 32; `V7P_APPLE_SOURCE_DIAGNOSTIC.json` records those observations. Source-text matches alone are not verified financial cells.

## Confirmed implementation boundaries

- `analysis.eligible_facts` only loads locally reviewed facts. Native retrieval hits do not automatically become numeric operands. Thus an uploaded PDF with no reviewed facts cannot satisfy the current numeric verifier.
- `AnalysisRequest` defaults to assets/EXTRACT/SEPARATE, which contradicts a consolidated revenue growth question when sent explicitly by the form.
- `frontend_api.analysis` previously overlaid the automatic reviewed plan on explicit fields without reporting contradictions. The patch refuses conflicting explicitly supplied plan fields before calculation. Omitted Pydantic defaults can still be replaced by an evidence-supported plan.
- `review_fact` checked financial scope using Vietnamese phrases only. English `consolidated`, `parent company` and `separate financial statements` are now recognized while preserving the requirement for source scope text.
- `assistant_answer.needs_number` omitted some extrema/numeric intent terms. Highest/largest/minimum and net income now remain under numeric abstention safeguards.

## Three acceptance cases

| Case | Source observation | Product acceptance |
|---|---|---|
| Net income FY2025 | Page32 contains Net income and 112,010 under annual headers | NOT_PASSED: automatic row/header/unit binding still required |
| Highest geographic net sales | Page25 contains five segment rows, Americas 178,353, plus a separate total row | NOT_PASSED: complete segment-set verification and argmax not implemented |
| Total net sales growth 2024–2025 | Page25/32 contains 416,161 and 391,035; Decimal formula expected to round to 6.43% | NOT_PASSED: automatic verified operands not yet available |

PyMuPDF default `find_tables()` detected zero tables on both inspected pages. Plain text search is insufficient; a layout-aware adapter must map header geometry, exclude percentage columns and bind scope/unit before any production numerical claim. No Apple values were added to production code. Browser reproduction, real endpoint response JSON and the complete five-way UI setting matrix remain NOT_TESTED in this checkpoint.

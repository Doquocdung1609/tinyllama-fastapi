# Product V2 — demonstrated result

Before checkpoint453d43e: HPG identification returned OCR snippets; Apple FY-prefix and Services questions missed or conflicted; follow-ups lost context; BIDV adjustment and restatement wording were conflated. See `before.json`, `browser-before.json`, `before-desktop.png`, `before-mobile.png`.

After:
- HPG: direct separate parent-company classification; balance page2, asset row page3, income page5. Numerical OCR remains honestly blocked for review.
- BIDV: separate/consolidated retained-earnings sources4/7;72012−70898=1114 millionVND; correct restated totals and growth percentages. Original + adjustment − restated is0 with three independently checked cells.
- Apple: FY2025 sales416161 millionUSD; FY2024 sales391035; change25126 and6.43%; Services share26.23% /24.59%; margin gap38.60 /36.70 percentage points; net income and country/segment distinctions verified from original cells.
- Shared Chat/Search/Lab answers; persistent named sessions, source-bound follow-ups, citations, PDF zoom/rotation and transparent highlight limitations.

Final matrix:53 real local API queries,46 distinct question strings;42 PASS,9 PARTIAL,0 FAIL,2 SEC BLOCKED. Includes16 arithmetic queries,9 adversarial questions,7 multi-turn sequences and6 Search/Lab flows.25 exact expected numeric cases match; no expected page-set mismatch. No false numeric certification observed in the9 adversarial development cases. OCR/missing-year/FX cases and unknown human gold are excluded from numerical-accuracy claims.

Latency of the final selected sequential runs: median2.107s; p95 nearest-rank3.676s; maximum4.943s. These include real retrieval and original-source checks, with a mixture of fresh-process and warm source/model caches. No production load or universal speed claim.

Three live baseline comparisons measure only known target-page inclusion at Top5 on the same source SHA. Candidate vs BM25:1 win,2 ties,0 losses; vs Dense:1/2/0; vs Hybrid:2/1/0. This small development check is not Recall/MRR/nDCG or evidence of general superiority. Raw arms and ordering are preserved in `real-e2e.json`.

Browser:14 real Chromium checks PASS, no page errors, desktop1366×768 and mobile390×844 screenshots. Inline citations open source cells at BIDV4/7 and Apple32; HPG5 displays explicit OCR coordinate limits. Real API restart preserved the renamed two-turn BIDV session exactly. The browser runner initially needed an unambiguous selector for the repeated inline/calculation citation and a settled responsive layout; those harness failures are retained and not counted as product passes.

Tests/build:867 Python suite PASS;49 final targeted gate/product tests PASS;33 React tests PASS; production build PASS. The independent AI reviewer read source PDFs before generated answers and reviewed all52 original matrix cases plus15 repaired cases; no human-gold claim is made. See `INDEPENDENT_REVIEW.md`.

Open product: http://127.0.0.1:18110/app/ . Remaining restrictions: HPG OCR numeric binding, unavailable SEC snapshot/index, bounded supported native layouts and evidence-only causal/narrative capabilities. These are not hidden by the PASS count.

Final frozen-code API smoke:10/10 expected PASS, including BIDV scope difference/restatement identity and Apple extraction, follow-up growth, Services share, margin and geography. See `release-smoke.json`. Final restart again preserved the stored BIDV session.

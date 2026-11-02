# V7A G2 acceptance

**G2: PASS for question-design freeze and blind-package release; source-cell gold remains pending independent review.**

- Coverage: 47 filings, 10 issuers, 94 questions, two slots per filing; forms {'10-K': 24, '10-Q': 18, '20-F': 3, '6-K': 2}.
- Question categories: {'FINANCIAL_NUMERIC': 49, 'FINANCIAL_COMPARATIVE': 26, 'ANSWERABILITY_CHECK': 4, 'FINANCIAL_DISCLOSURE': 11, 'DISCLOSURE_OR_ANSWERABILITY': 4}. Intended answerability is a design hypothesis pending original-source review, not a gold label.
- Agent 1 original: 57/94 questions contained an accession in the query text; redesigned public queries contain 0. Source status: {'PARSER_EXTRACTED_NOT_HTML_VERIFIED': 72, 'SEC_ORIGINAL_WEB_VIEW': 22}. Its proposed values are excluded.
- Agent 1 and Agent 2 agree on 47 accession, issuer, form, report-date and URL metadata records. This validates mapping, not the contents or availability of every original SEC HTML page.
- Original Agent 1 CSV: SHA-256 `65681f0bd3e07eeab9d7a1c505fadf35eb4c62ea3cc0ac0805277412a2f3129a`; V6 sealed 30 unchanged: `01e841d14692477512f1029f2638f353765a9a59f44379dc09783e78bcdcab79`.
- Overlap levels across six reference sets (one strongest match per question/set): {'NO_DIRECT_OVERLAP_FOUND': 464, 'SAME_FILING': 91, 'POTENTIAL_SOURCE_CELL_OVERLAP': 8, 'SAME_FILING_AND_METRIC': 1}. Full row-level report: `V7A_QUESTION_OVERLAP_AUDIT.csv`.
- `question_unseen_exact` is a text-only check. `cell_unseen_provisional` needs source-cell adjudication. Filing or issuer reuse is disclosed, not treated as an automatic exclusion. P5 lacks filing metadata.
- Issuer question counts: {'AAPL': 10, 'AMD': 10, 'AMZN': 10, 'GOOGL': 8, 'INTC': 10, 'META': 6, 'MSFT': 10, 'NVDA': 10, 'TSLA': 10, 'TSM': 10}; numeric, comparative, disclosure and answerability categories are recorded per question.
- Agent 1 proposed values were excluded. Agent 2 supplied 47-filing metadata and zero 94-question judgments. No retrieval or ranking was executed on the 94 questions.
- Blind packages have identical question/source/rubric/read-first bytes and SHA-256 values listed in the freeze manifest; only the blank template filename differs.
- Local validation (2026-11-02): V7A release checks 4/4 PASS; full pytest 740/740 PASS, one existing Starlette/httpx deprecation warning. Rebuild produced the same freeze-manifest SHA-256 in repeated runs.
- Remaining: independent source review, unresolved numeric period/unit checks, and any later adjudication. G3–G10 not started.

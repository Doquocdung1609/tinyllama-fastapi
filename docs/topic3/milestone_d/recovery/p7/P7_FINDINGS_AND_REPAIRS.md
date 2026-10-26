# P7 demonstrated findings and targeted repairs

| Finding | Severity | P6 reproduction | P7 repair and regression |
|---|---|---|---|
| Forged `members.source.filing_id` still yielded a verified numeric answer | HIGH | Clone mutation returned SUPPORTED/23,276,000,000 | `validate_frozen_parent_membership` in `real_source.py`; focused regression and 12-case tamper probe now reject with `FROZEN_PARENT_FILING_ID_MISMATCH` |
| Lexical generation marked FAILED still yielded a numeric HTTP answer | HIGH | Live cloned API returned 200/SUPPORTED | `FrozenResearchSnapshot.search` requires READY; regression and live rerun now 409/no value |
| “net sales fair value” returned ordinary net sales | HIGH | Real PG semantic probe and synthetic fail-first test returned SUPPORTED | P6 selector conservatively refuses valuation qualifiers; real probe and HTTP return NEEDS_CLARIFICATION |
| “percentage-point change” returned comparison values | HIGH | Real PG probe and synthetic fail-first test returned SUPPORTED | P6 selector refuses unsupported percentage-point syntax; real probe and HTTP return UNSUPPORTED_OPERATION |

All changes are restricted to the research path and citation guidance. No D1–D5 historical result, ranking parameter, accepted production route or corpus file was changed. Open limitations: phrase-based semantic vetoes are deliberately narrow; alternate unsupported qualifiers may still need independent testing. Full cross-issuer numeric coverage, exact SEC browser cell landing, full manifest-switch rollback and a new heldout study remain outside this review's verified scope.

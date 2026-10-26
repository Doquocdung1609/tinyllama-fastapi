# P6 adversarial review ledger

Evidence levels are explicit. `UNIT` means isolated synthetic regression; `REAL` means pinned P&G source probe; `HTTP` and `UI` mean live local service/browser. Unchecked cases are not passed by inference.

| Case | Evidence and outcome |
|---|---|
| Wrong/unknown issuer, query/filter conflict | UNIT + REAL/HTTP conflict: no source selection, no numeric claim. |
| Wrong/missing period | UNIT + REAL: missing 2024 period abstains. |
| Reversed change direction | UNIT: `CHANGE_DIRECTION_REQUIRES_OLD_THEN_NEW`; no wrong-sign answer. |
| Incorrect unit multiplier; source header/fact conflict | Existing P0 synthetic regressions reject display/XBRL mismatch. |
| Negative base | UNIT: percent growth refused with `NONPOSITIVE_PERCENT_CHANGE_BASE`. |
| Mixed instant/duration | UNIT: instant observation cannot fill quarter-duration request. |
| Wrong metric; carrying/fair-value | UNIT + REAL: only exact NET SALES accepted; other metrics abstain. |
| Segment/entity confusion | REAL candidate scan: segment/analysis rows yield no eligible P0 cell; duplicated valid parents in UNIT produce clarification. |
| Fabricated parent/source hash | No client parent/hash field exists in P6 API. P0 hash/parent checks reviewed; new end-to-end tamper test NOT_TESTED. |
| Unsupported amendment | UNIT: no unverified original/amendment substitution. |
| Partial extraction | REAL + UI warning retained, selected table separately verified. |
| Invalid generation | UNIT: mismatch refused before search. Live generation tamper NOT_TESTED. |
| Oversized input | HTTP 422 for >2,000-character question; body middleware remains 16 KiB. |
| Missing Dense/Ollama | HTTP D arm no numeric claim; Ollama was not required for BM25 P6. |
| Prompt-injection-like question | REAL probe returns unsupported/no number; source text is never executed. |
| API authorization | HTTP 401 without bearer token. |
| UI citation navigation | UI opened correct SEC URL; target row not visible in destination browser tab. PARTIAL. |
| Restart/pinned generation | HTTP exact answer repeated after API/UI restart on same generation. |
| Concurrent read/publication | UNIT with isolated synthetic lexical index: 16 pinned reads remained on old generation while new generation published. No owner data mutation. |

Open verification risks: no full raw-source mutation/tamper E2E regression for P6, no browser anchor to an exact SEC cell, no multi-issuer numeric scope coverage, no live cleanup/publication load test. There is no demonstrated unresolved HIGH/CRITICAL wrong-number defect in the supported narrow path, but the scope is intentionally small.

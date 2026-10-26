# D5 isolated E2E product and security validation

`scripts/run_d5_e2e_http.py` launched fresh Uvicorn children bound to `127.0.0.1`, sent 21 actual HTTP requests, recorded responses in `D5_LIVE_HTTP_MATRIX_v1.json`, then stopped only its own processes. Twenty requests returned HTTP 200 with typed status; one unauthorized request returned HTTP 401. These status codes do not imply all questions were answered. Synthetic positive claims were limited to the invented D4 issuer. One official SEC PG request returned five source-bound BM25 chunks from frozen generation `8f0a7ba5ed851313a9948ddb465753c54012d94f9c36942239f7b2ec15b5e2fb`, source locator under `pg-20260930.htm`, and `INSUFFICIENT_EVIDENCE / REAL_D2_SOURCE_CONTEXT_UNSUPPORTED_SIZE` with **zero numeric claims**. This is the safe real-data behavior.

In a new, separately authorized in-app browser session, the separate Streamlit research UI loaded at `127.0.0.1:8503` in synthetic mode and `127.0.0.1:8504` in official SEC mode. The synthetic page visibly identified invented data, exposed all seven arm choices, displayed a 100,000,000 USD fixture claim with cell locator, and displayed `BLOCKED / INSUFFICIENT_EVIDENCE` for fixed RRF. The SEC page displayed PG issuer, 10-Q, period, an official SEC Archive link, an HTML structural locator and **Partial extraction** warning; its answer showed `INSUFFICIENT_EVIDENCE`. Clicking the SEC link did not yield a separately observed navigated tab, so actual browser landing at the source is **NOT VERIFIED**; link presence and exact destination were observed. The prior stopped browser session was not reused. Existing legacy Chat/RAG behavior is covered by full regression and unchanged source diff, not a fresh live legacy UI claim.

## 24-scenario ledger

The frozen HTTP record gives exact inputs, environment, observed statuses, generation/manifest and first source locator for the live cases. Test names below cite isolated fixture coverage where HTTP did not reproduce the risk. `LIVE_HTTP` means an actual Uvicorn request; `LIVE_UI` means observed Streamlit browser state; `FIXTURE` means controlled source bytes/test objects, **not live SEC**.

| # | Scenario | Evidence and observed behavior | Gate |
|---|---|---|---|
| 1 | Income-statement figure | LIVE_HTTP synthetic exact net sales SUPPORTED; LIVE_UI synthetic claim/cell locator | VERIFIED_WITH_LIMITATIONS |
| 2 | Multi-year comparison | LIVE_HTTP synthetic ABS_CHANGE SUPPORTED, 10,000,000 USD | VERIFIED_WITH_LIMITATIONS |
| 3 | Instant balance sheet | LIVE_HTTP synthetic current liabilities SUPPORTED at instant date, −125,500 USD | VERIFIED_WITH_LIMITATIONS |
| 4 | Cash-flow evidence | LIVE_HTTP synthetic net income row SUPPORTED, 25,000,000 USD | VERIFIED_WITH_LIMITATIONS |
| 5 | Basic versus diluted EPS | LIVE_HTTP basic EPS 2.74 USD/share; diluted absent → NEEDS_CLARIFICATION | VERIFIED_WITH_LIMITATIONS |
| 6 | Segment versus consolidated | LIVE_HTTP segment question NEEDS_CLARIFICATION; no unsupported claim | PARTIAL |
| 7 | Fair value versus carrying | LIVE_HTTP request NEEDS_CLARIFICATION; no fabricated conversion | PARTIAL |
| 8 | Negative amount | LIVE_HTTP parenthesized synthetic value preserved as −125,500 USD | VERIFIED_WITH_LIMITATIONS |
| 9 | Percent versus points | LIVE_HTTP ambiguous points request NEEDS_CLARIFICATION; D4 unit tests distinguish operations | PARTIAL |
| 10 | Wrong fiscal year | LIVE_HTTP FY2099 NO_ELIGIBLE_EVIDENCE | VERIFIED |
| 11 | Unknown issuer | LIVE_HTTP CIK999 NO_ELIGIBLE_EVIDENCE | VERIFIED |
| 12 | Conflicting filters | LIVE_HTTP query CIK202 with explicit CIK999 returned no evidence/no claim; explicit **conflict classification was not returned** | PARTIAL |
| 13 | Missing SEC evidence | LIVE_HTTP synthetic gross profit returned NEEDS_CLARIFICATION/no claim; no real absent-SEC test | PARTIAL |
| 14 | Amended ambiguity | LIVE_HTTP synthetic 10-K/A absent → NO_ELIGIBLE_EVIDENCE; no real amendment linkage test | PARTIAL |
| 15 | Partial extraction | LIVE_HTTP real PG evidence/abstention; LIVE_UI displayed Partial extraction warning and SEC locator | VERIFIED_WITH_LIMITATIONS |
| 16 | Tampered source | FIXTURE `test_source_integrity_failure_must_not_fallback`, D4 forged claim/citation rejection; no mutation of real frozen source | VERIFIED_WITH_LIMITATIONS |
| 17 | Missing column period | LIVE_HTTP no requested FY → NEEDS_CLARIFICATION; FIXTURE `test_explicit_period_needs_cell_level_check_not_just_d1_metadata` | VERIFIED_WITH_LIMITATIONS |
| 18 | Dense unavailable | LIVE_HTTP and LIVE_UI F mode BLOCKED/no claim, no BM25 relabel | VERIFIED |
| 19 | Ollama unavailable | LIVE_HTTP optional LLM mode UNSUPPORTED_OPERATION/no LLM draft | VERIFIED_WITH_LIMITATIONS |
| 20 | Generation/model mismatch | FIXTURE `test_channel_scope_identity_mismatch_is_blocked`, `test_wrong_metric_missing_cell_or_generation_cannot_answer`; no real vector generation | VERIFIED_WITH_LIMITATIONS |
| 21 | Concurrent reads during publication | Accepted C concurrent build/retention tests only; no live query/publication stress in this research snapshot | NOT_TESTED |
| 22 | Restart/state recovery | Owned synthetic demo reopened twice with same generation and unchanged SQLite modification timestamp; D3 persistence test | VERIFIED_WITH_LIMITATIONS |
| 23 | Mutation/auth failure | LIVE_HTTP unauthenticated query 401; API has no mutation route; full C mutation auth regression passes | VERIFIED_WITH_LIMITATIONS |
| 24 | Prompt injection-like text | LIVE_HTTP query text UNSUPPORTED/no claim; injected **source document** not independently exercised live | PARTIAL |

Security observations: token never printed or committed, 16 KiB body cap, strict schema, single request slot, only localhost research services, no historical owner-data writes. Non-ASCII Authorization header fail-first 500 was repaired on D4 and is locked by regression 401. The first result for a real `net sales` query was a partial segment percentage row rather than a verified net-sales figure; evidence remains labeled partial and numeric answer abstained. SEC link navigation and live legacy UI remain open acceptance gaps.

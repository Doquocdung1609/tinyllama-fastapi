# FAITH-R product V2 — root cause and repair

Worktree: `C:/Users/Admin/.codex/worktrees/topic3-v7p/tinyllama-fastapi`
Branch: `codex/topic3-v7p-verified-financial-chatbot`
Starting checkpoint: `453d43ecdbaf7fe5a59ece5c4026b1bb78276185`; target Draft PR35. No branch/worktree creation, merge, force push, or research-label changes.

## Observed failures and implemented repairs

| Trigger | Before | Repair and observed result |
|---|---|---|
| HPG document identity / statement navigation | Top-K OCR snippets, unrelated subsidiary lines; balance section ranked page13 | Intent-specific literal heading navigation. Direct parent-company classification from original title; balance begins physical page2 and continues3–4; income statement page5. OCR remains explicitly provisional. |
| FY2025, Services or parent-company wording | FY prefix lost; greedy company-name slots produced false issuer conflicts | Typed planner recognizes FY and category metrics; year/category/accounting words excluded from issuer slots. Real wrong-company questions still fail closed. |
| BIDV after-adjustment / percentage questions | Adjustment column or original amount selected as final answer | Separate ORIGINAL / ADJUSTMENT / RESTATED semantics; “sau điều chỉnh” selects RESTATED. Percentage uses adjustment/original. Values34235054 and36264506, ratios0.21% and0.20% source verified. |
| BIDV list of adjustments | Top5 dominated pages3/6 where physical header proof unavailable | Rank original-byte verified adjustment rows before unverified rows, retain scope diversity. Compact partial table on4/7; no claim of exhaustive coverage. |
| Apple Services / geography / margin | Raw snippets; generic sales, country sales and long-lived assets confused | Native source catalog binds numeric row, preceding accounting subsection, physical year column, exact annual date, currency declaration and scale. Services share and gross-margin percentage points use distinct formulas; U.S. country sales never use Americas or long-lived assets. |
| “And in FY2024?” / “Hai mức…” | Narrow keyword follow-up lost metric or previous year | Durable source-fingerprint-bound slots; inherit metric, years, scope and ratio intent only for eligible follow-ups. Seven multi-turn sequences exercised; source switching forks and clears inherited slots. |
| Numeric refusal | Related evidence could disappear or raw OCR was mistaken for an answer | Canonical answer statuses, retained citations and clear missing cell/column explanation. No OCR digit published as certified. |
| Plausible math attached to wrong source | Shared producer verification could trust the proposed graph | Independent gate reopens source bytes and recomputes with separate Decimal implementation; exact claim/calculation operand, source, period, scope, currency/scale, direction and result bindings. Reviewer found and helped close operand and scale bypasses. |

## Actual runtime architecture

`answer_planner_v2.py` builds a typed question plan. `source_cells_v2.py` reads original PDF cells and authenticated extraction headings without creating an index. `answer_composer_v2.py` builds a typed AnswerPlan with Claim and calculation nodes, then renders direct deterministic prose. `independent_verifier_v2.py` independently reopens original files and recalculates proposed results. It does not import the composer, native candidate extractor, producer calculator or adjustment verifier.

Stage A checks SHA, locator identity, source page, native cell bytes, label and row containment, physical column/year/header, period end, scope, metric/accounting subsection, currency and scale. Stage B checks formula semantics, ordered operands, compatible dimensions, denominator, basis, two-decimal HALF_UP percentages, proposed result, claim-to-calculation identity and authorized rendered numerals. OCR is rejected as a numeric operand. Source-fact scope/geography/numeral checks cover bounded templates; they are not arbitrary natural-language entailment.

Chat, Search AUTO and Research Lab candidate use this shared PDF answer pipeline. Existing `faith_r_product_v1` remains a compatibility retrieval-profile key, not the name of the new composer: responses expose `VERIFIED_ANSWER_COMPOSER_V2`, typed plans and `INDEPENDENT_FINANCIAL_GATE_V2`. BM25, Dense and fixed RRF k60 baseline arms remain separate original executions. SEC keeps its existing source/HTML adapter; current SEC data availability is BLOCKED, so V2 SEC numeric acceptance is not claimed.

React shows the direct answer, explanation, inline citations and expandable audited calculation steps with source values, periods, scopes, basis and rounding. Technical traces remain collapsed. Search also shows source-only answers. Display formatting uses strings, not binary floating-point arithmetic.

## Verification and limitations

See `E2E_ANSWER_MATRIX.csv`, `CALCULATION_VERIFICATION.json`, `METRICS.json`, raw real API traces and browser evidence. The matrix merges the complete52-query run, fifteen repaired-case reruns and one added source-backed restatement-identity query; original failing attempts are retained. Final53 rows:42 PASS,9 PARTIAL,0 FAIL,2 BLOCKED. This is development acceptance with independent AI source review, not human gold, locked benchmark relabeling or a generalization claim.

Full suite:867 Python tests PASS;49 targeted gate/product tests PASS after final identity strategy;33 React tests PASS; production build PASS. Source PDF SHA checks remain unchanged3/3. Native citation rendering was checked in Chromium at BIDV4/7 and Apple32; HPG5 transparently reports OCR coordinate uncertainty. Renamed session payload was identical across a real API restart.

## Residual register

- HPG amounts: PARTIAL. Row/quarter/year digit binding is not sufficiently reliable; users can open the statement, rotate the OCR view and review the original. No visual AI observation becomes a human-certified fact.
- SEC: BLOCKED. Compatible product snapshot/source roots and index are unavailable. No research corpus is substituted or downloaded.
- Native catalog covers bounded annual USD and VND restatement layouts. Unsupported instant tables, currencies, layouts or quarter/YTD bindings abstain with sources. No unsupported FX conversion.
- Narrative summaries describe supported report structure and scope. Causal explanations and arbitrary financial-language entailment beyond typed strategies are not certified.
- Browser API tests use real local Chromium/Playwright. Native CUA initialization failed with an OS path error; no native browser-control success is claimed. Desktop and390px browser checks completed through the repository E2E runner.

## Run / rollback

Open `http://127.0.0.1:18110/app/`. The existing startup script creates the local login key; never publish that key. Run `scripts/run_financial_studio.ps1 -Mode Prebuilt -ApiPort 18110 -Workspace <existing-product-workspace>`. Use the already installed Node24 for frontend unit tests. Browser runner: `node frontend/e2e/v2-demo.mjs`; real matrix: `.venv/Scripts/python.exe scripts/faith_r_product_v2_e2e.py` from this worktree. These create ordinary product chat sessions, not research judgments.

Commit SHA is reported in the handoff and obtainable with `git log -1 --format=%H`. Roll back by reviewing and reverting that V2 commit (`git revert <V2-commit>`), rebuilding React and restarting the owned API using the startup script. No reset, research-data restore, merge or force push is required. Existing durable sessions and source PDFs should be retained. Two pre-existing dirty research files are excluded from staging.

Final frozen-code API smoke:10/10 expected PASS, including BIDV scope difference/restatement identity and Apple extraction, follow-up growth, Services share, margin and geography. See `release-smoke.json`. Final restart again preserved the stored BIDV session.

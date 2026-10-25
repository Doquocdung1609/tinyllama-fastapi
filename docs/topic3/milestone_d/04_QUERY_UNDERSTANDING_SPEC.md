# Financial query understanding v1

**Proposal only.** Purpose: explicit scope and intent, not rewriting questions into unsupported facts. Deterministic baseline comes first; learned intent classification is deferred until a measurable rule failure remains.

## Parsing and resolution order

1. Retain raw input; normalize Unicode whitespace/case for matching only. Preserve minus signs, parentheses, decimal separators, `%`, currency symbols and original spans. Reject overlong/invalid requests under existing C bounds; never log credentials.
2. Read explicit filters. Resolve CIK/ticker/company aliases from the pinned corpus catalog, not fuzzy worldwide issuer guesses. Conflicting query and explicit filters require clarification.
3. Identify form/accession, filing date versus report-period phrases, original/amended/as-of wording. Resolve only against available filings, keeping accession and amendment links. Never assume a later filing is an amendment.
4. Resolve requested instant/duration and fiscal/calendar meaning. “FY2025” means issuer fiscal period; “calendar 2025” is a different request. “2025” alone is unresolved unless a single compatible scope exists and is disclosed. A 10-K filed in 2026 can contain 2025 comparative evidence. Build eligible filing membership from actual table contexts; don't blindly set `fiscal_year=2025` on a filing-level API filter.
5. Extract line-item terms and numeric/operator constraints. Keep amount/currency, per-share units, percentages, percentage points and negative values distinct. Parenthetical accounting negative values require a numeric context; `(2025)` in a title is not automatically −2025.
6. Assign intent with recorded rules: comparison when two periods or change operator; table when row/column/segment requested; exact for quoted labels/explicit amount; terminology for definition; paraphrase for explanation without exact label; cross-section when two named evidence regions are needed. Multi-label flags are permitted; an unresolved scope dominates routing.
7. Return raw intent, resolved scope or clarification reason. No hidden date defaults; response shows selected period/filing. Do not claim a numerical probability from a rule count.

## Minimal deterministic vocabulary

Versioned, owner-reviewed aliases map “basic earnings per share” ↔ “basic EPS”; “inventories” does not become “finished goods”; “operating profit” may suggest operating income but records ambiguity if issuer context conflicts. GAAP/non-GAAP, consolidated/segment and carrying/fair value remain separate. No automatic synonym expansion changes the numeric predicate. Proposed expansion budget: at most two approved aliases and one alternative lexical query; primary experiment starts without expansion to isolate routing.

Number record: raw string; candidate Decimal; sign source `{literal,paren,inline_attr}`; unit `{USD,shares,USD/share,percent,unknown}`; multiplier; display precision; scope/row/column provenance. “from 10% to 12%” requests +2 percentage points or +20% relative only when the operation is explicit. Missing unit → unknown, not USD. Conversion uses exact decimal powers after source validation.

## Contract examples and later tests

The strings below are specification cases, not new labeled evaluation questions and not untouched holdout material. Company names are consumed development examples; numbers marked synthetic are not filing claims.

| Input / condition | Expected interpretation | Required test oracle |
|---|---|---|
| “WMT basic EPS FY2026” | WMT CIK, basic EPS, issuer fiscal year; resolve original/amended policy | Correct slot values and disclosed filing/column, not merely filing date |
| “WMT EPS filed during 2026” | Filing-date constraint; report period unspecified | Must not silently convert to FY2026 |
| “NVDA 2025 profit” with multiple compatible periods | Ambiguous label/year | Clarification, zero forced hard exclusions |
| “fiscal 2025 vs calendar 2025” | Distinct periods | No equality assumption; unsupported calendar data → abstain |
| “operating margin fell from 12% to 10%: points?” (synthetic) | −2 percentage points | Percent vs points retained; never −2 dollars |
| “loss (1,250) million” (synthetic) | −1,250 × 10^6, subject to source | Parentheses and million retained; currency unresolved |
| “value in the 2025 10-K/A, not original” | Amended filing only | Explicit amendment linkage; absence → no evidence |
| “as originally reported” | Original accession, no silent restated replacement | Both versions separate, original policy logged |
| UI ticker MSFT but question names KO | Conflicting issuer | Validation/clarification, no search outside scope |
| “debt fair value” | Fair value, not carrying value | Header-role check even when inline concept tags coincide |
| Unsupported quarter / unknown issuer | No catalog match | Typed unsupported/ambiguous result, no broad global fallback |
| Unicode minus, `$`, `USD/share`, Q4 vs year-to-date | Distinct sign/unit/duration | Property cases preserve tokens and reject incompatible joins |

Proposed D1 fixtures include ambiguous ticker aliases, restatement links, duplicated table labels, comparative periods in later filings, null contextRef, mixed units and quoted label spans. Each fixture's expected slots must be authored from source metadata before parser changes; existing C issuer fixtures are compatibility tests, not future held-out evaluation.

## Measurements and limits

Report per-slot precision/recall/F1, exact full-scope match, intent macro-F1, clarification rate and false clarification rate, plus false hard-exclusion rate (gold evidence eliminated by resolver). Evaluate retrieval after resolution separately from oracle-scope retrieval to quantify scope error propagation. Compare explicit-filter-only C baseline with deterministic D1 on identical corpus/query sets. Error review covers issuer, filing date/report date, fiscal/calendar, column duration, amendments, terminology and number semantics. Predeclare no silent wrong-issuer/period verified answers; routing quality cannot excuse scope violations.

A learned router would require separate labels, training resource and leakage audit; small in-domain query counts are insufficient to assume a reliable classifier. Bilingual Vietnamese questions are a separately reported exploratory slice until source-grounded qrels and language coverage exist; do not silently apply English-only synonym accuracy to them.

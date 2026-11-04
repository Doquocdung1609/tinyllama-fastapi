# Independent source-first AI review

One read-only reviewer agent (`/root/source_reviewer_v2`) independently read the three original PDFs before access to generated V2 answers. It made no code, corpus, benchmark or gold-label edits. Its visual HPG reading is AI review, not human image certification.

Twenty independently extracted source facts covered HPG separate/Q4 report identity, asset/income pages and column order; BIDV separate/consolidated original, adjustment and restated cells; Apple annual sales, Services share, percentage-point margins, U.S./Americas and net income. Actual source hashes are recorded in `source-integrity.json`.

Reviewer-discovered gate weaknesses were reproduced and repaired:
1. A valid2025 calculation could be bound to2024 claim operands/scope. Exact claim↔calculation operand lists, scope and period bindings now reject it.
2. Reversed year inputs yielded−6.04% for2025 growth. Ordered current/previous and consolidated/separate/category subtraction now reject reversal.
3. Requested VND could be ignored; requested USD could accept an amount labeled millionUSD. Currency and extraction result-scale bindings now reject both. Regression tests cover these paths.
4. Fiscal-year vs instant parsing falsely rejected retained earnings. Planner now treats stock metrics as INSTANT and independently proves31/12/2024 from the original scope page.
5. A navigation-only heading on HPG5 was falsely required to restate separate scope. Navigation claims now assert the supported location; classification remains separately tied to title evidence.

Final reviewer confirmation: all52 original real E2E outputs and all15 repaired cases were reviewed against independently derived facts. BIDV native values, Apple amounts/calculations and geography agree with sources. HPG numbers remain uncertified. No remaining P0 false numeric certification was observed in reviewed cases. The prior scale bypass now rejects with QUESTION_REQUESTED_SCALE_MISMATCH; repaired HPG navigation reaches physical page5.

The runtime verifier is independent deterministic Python Decimal, not this reviewer or a second online LLM. Review establishes only the tested source bindings and bounded deterministic strategies. It does not prove arbitrary-language entailment, establish human gold, certify OCR or validate a missing SEC source.

# V4 implementation

## Shipped change

1. PDF document QA with `search_profile=auto` uses `unified_search`, matching Search V3R3 only when the workspace advertises that candidate. The API default remains legacy baseline for older clients.
2. `assistant_answer.py` builds a deterministic contract: answer, source references, document/page, metric/period/scope/unit when present, verification status, warnings and retrieval trace. Narrative answers quote source text. Numeric answers carry no values until the existing reviewed-cell verifier returns a supported result.
3. A missing requested year now yields `INSUFFICIENT_EVIDENCE` and hides numeric snippets from other years. Unit questions prefer a source line that actually contains the printed unit.
4. `/studio/research-lab/topic3` reads and validates frozen local results; React displays eight historical arms and keeps them separate from the three live product retrieval arms. SPLADE and Stage-2 are expressly historical.

## Compatibility and boundaries

- Existing SEC answer and Decimal calculation paths remain in place. The PDF workflow does not certify OCR table cells.
- No new model, paid API, retrieval architecture or original-corpus claim was introduced.
- No Apple FY2025 PDF was present in the isolated workspace; the Apple PDF unit ambiguity remains unverified. A Home Depot SEC iXBRL cell provides the verified numeric case.
- Python regression 722 PASS; frontend 10 PASS; production build PASS. Browser evidence is in `V4_REAL_BROWSER_DEMO_QA.md`.

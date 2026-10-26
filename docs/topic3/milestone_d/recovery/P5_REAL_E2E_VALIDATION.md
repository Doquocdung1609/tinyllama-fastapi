# P5 end-to-end acceptance

The isolated source-selected Python probe is real SEC evidence, but is not the requested `Question → D1 → D3 → D2 → D4 → API → Streamlit` workflow. No live FastAPI/Streamlit HTTP/browser test was performed in this checkpoint. The research API still routes through the D5 `ResearchBackend`, whose real `context` is `None` and which correctly abstains for oversized D2 v1 sources. Do not mark the P0/P3 probe as a production or UI pass.

| Scenario | Outcome |
|---|---|
| Real numeric source cell and period comparison via explicit research Python request | VERIFIED_WITH_LIMITATIONS; see probe JSON |
| Live HTTP numerical answer, Streamlit display, source navigation | NOT_TESTED |
| Contradictory issuer query/filter | Fixture/isolated D1 test: `NEEDS_CLARIFICATION`, `ISSUER_CONFLICT`; live HTTP NOT_TESTED |
| Model unavailable fallback, invalid generation, protected authorization | Existing test coverage only; fresh live HTTP NOT_TESTED |
| Restart and concurrent read/publication | NOT_TESTED |
| Legacy Chat/RAG live behavior | NOT_TESTED; full suite result in resource report |

The opt-in API/UI must not imply automatic real QA works until the D1 column catalog, D3 candidate selection, D2 authenticated-cell adapter and D4 verifier are joined under an end-to-end test. Accepted Financial Search and Chat/RAG defaults remain unchanged.

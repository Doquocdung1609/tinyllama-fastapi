# P5 end-to-end acceptance

The isolated source-selected Python probe is real SEC evidence, but is not the requested `Question → D1 → D3 → D2 → D4 → API → Streamlit` workflow. A fresh local Uvicorn process served the opt-in research API on `127.0.0.1:18087` against the isolated read-only snapshot; five live POSTs and one health GET were observed, then the process was stopped. No Streamlit/browser interaction was performed. The research API still routes through the D5 `ResearchBackend`, whose real `context` is `None` and which correctly abstains for oversized D2 v1 sources. Do not mark the P0/P3 probe as an API numeric-answer or UI pass.

| Scenario | Outcome |
|---|---|
| Real numeric source cell and period comparison via explicit research Python request | VERIFIED_WITH_LIMITATIONS; see probe JSON |
| Live HTTP numerical answer | BLOCKED by unchanged D2 v1 cap; BM25 request returned five citations and `INSUFFICIENT_EVIDENCE`/`REAL_D2_SOURCE_CONTEXT_UNSUPPORTED_SIZE` |
| Streamlit display and source navigation | NOT_TESTED |
| Contradictory issuer query/filter | Fixture/isolated D1 test: `NEEDS_CLARIFICATION`, `ISSUER_CONFLICT`; live HTTP NOT_TESTED |
| Unavailable Dense/Fusion channel | LIVE_VERIFIED fail-closed: D and F each returned `BLOCKED`, zero evidence and `DENSE_NOT_AVAILABLE_NO_RESEARCH_VECTORS`; no false ranking score |
| Protected authorization | LIVE_VERIFIED: missing bearer token returned HTTP 401; valid local test token allowed a scoped request |
| Invalid generation | NOT_TESTED live |
| Restart and concurrent read/publication | NOT_TESTED |
| Legacy Chat/RAG live behavior | NOT_TESTED; full suite result in resource report |

The opt-in API/UI must not imply automatic real QA works until the D1 column catalog, D3 candidate selection, D2 authenticated-cell adapter and D4 verifier are joined under an end-to-end test. Accepted Financial Search and Chat/RAG defaults remain unchanged.

Exact local launch: `TOPIC3_RESEARCH_ROOT=<owned-isolated-root> TOPIC3_RESEARCH_API_TOKEN=<local-test-token> TOPIC3_RESEARCH_MODE=real_frozen python -m uvicorn app.research_api:app --host 127.0.0.1 --port 18087 --log-level warning`. Requests were `GET /research/v1/health`, unauthenticated and authenticated `POST /research/v1/query`, and B/D/F requests for `What were CIK 0000080424 net sales?`. A quarter-ended request with an explicit CIK returned `NEEDS_CLARIFICATION` because D1 column metadata is incomplete. Sanitized request/response summaries are in `http_smoke_v1.json`; the local test token is intentionally omitted.

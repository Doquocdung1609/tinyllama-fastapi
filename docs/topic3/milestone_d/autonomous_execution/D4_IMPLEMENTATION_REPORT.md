# D4 implementation report — deterministic research prototype

## Boundary and architecture

D4 is a separate, opt-in path. `app/research_api.py` exports `/research/v1/*`; accepted `app.main` routes, Financial Search defaults, SEC corpus, Qdrant generations and scientific C artifacts were not changed. `research_ui.py` is a separate Streamlit entrypoint. The path is D1 metadata scope → D3 pinned retrieval → D2 source-derived bundle → D4 typed operands and deterministic claim verification. The research API can be configured for an owner-marked frozen SEC lexical snapshot or an explicitly synthetic demo. Neither mode builds embeddings, accesses Ollama or generates LLM prose.

`app/research_qa/contracts.py` defines `financial-numeric-request/v1`, `financial-numeric-claim/v1` and `financial-grounded-answer/v1`. `numeric.py` implements fixed Decimal operations; `verifier.py` reconstructs and checks source-bound evidence and claims; `backend.py` coordinates D1–D4. D3 public search defaults remain unchanged.

## Honest functionality boundary

The retained WMT/NVDA SEC sources exceed the accepted D2 250 KiB verified-context cap; the new PG/COST/HD SEC files are also larger. Thus D4 **cannot** issue a verified numeric claim on the real SEC snapshot. Real mode returns retrieved source evidence and `INSUFFICIENT_EVIDENCE / REAL_D2_SOURCE_CONTEXT_UNSUPPORTED_SIZE` for numeric QA. The positive arithmetic examples run against an isolated, clearly marked invented HTML filing under `example.invalid`; they are not SEC facts. D3 Dense and fixed RRF comparisons remain unavailable because local Ollama is not reachable. No retrieval quality improvement is claimed.

The API requires a configured token and owner-marked research root. A missing token disables POST. Input/body limits and a single concurrent query slot bound local use. Source bytes in the synthetic demo are reconstructed from code on startup and checked through D2 binding; real mode uses the immutable owner-marked snapshot and C source verification.

## Verification

Python 3.13.2 on Windows 11: `python -m compileall -q app scripts`; `python -m pytest -q tests/test_research_api.py tests/test_research_qa.py` → 35 PASS, one deprecation warning; `python -m pytest -q` → 552 PASS, 3 SKIP, one warning; `python -m pytest -q -m "not integration"` → 552 PASS, 3 deselected, one warning. These are fixture and in-process results. Live HTTP and browser results belong to D5 and must be separately labeled.

Checkpoint: **D4_DETERMINISTIC_ONLY**. The path is implemented and tested on synthetic source bytes; real numeric QA and LLM behavior are unverified.

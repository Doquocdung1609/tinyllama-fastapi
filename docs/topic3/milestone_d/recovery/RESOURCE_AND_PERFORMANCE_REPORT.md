# Resource and regression evidence

Environment: Windows, Python 3.13.2, isolated research snapshot with one 1,066,740-byte P&G HTML source. `resource_probe_v1.json` records 7 source-selected exact-cell runs after the visible-unit check. Without allocation tracing: elapsed milliseconds `[1296.678, 745.794, 741.653, 688.935, 799.178, 844.399, 696.531]`; p50 `745.794`, p95 nearest-rank `1296.678` (the cold first call). An earlier run before that check with `tracemalloc` enabled recorded p50 `3027.518`, p95 `5623.051` ms, traced Python peak allocation 62,301,886 bytes and process RSS rise from 46,903,296 to 113,389,568 bytes. Tracing changes runtime substantially and those earlier figures are not directly comparable to the final untraced series. These are one-process, one-source observations, not server capacity or concurrency benchmarks. No GPU used.

Commands/results on recovery branch before delivery:

| Command | Result |
|---|---|
| `python -m pytest -q tests/test_real_sec_recovery.py` | 6 passed after visible-unit repair |
| `python -m compileall -q app scripts` | PASS |
| `python -m pytest -q` (ambient default `SCORE_THRESHOLD=0.7`) | Final repair: 1 failed, 557 passed, 3 skipped, 1 warning, 39.13 s |
| `$env:SCORE_THRESHOLD='0.55'; python -m pytest -q` | Final repair: 558 passed, 3 skipped, 1 warning, 24.49 s |
| `$env:SCORE_THRESHOLD='0.55'; python -m pytest -q -m 'not integration'` | 557 passed, 3 deselected, 1 warning, 25.82 s (run during visible-unit repair) |
| `git diff --check` | PASS |

The sole default-environment failure is pre-existing at D5 HEAD: `tests/test_models.py::test_rag_defaults` asserts `.55`, whereas `app/config.py` defaults `SCORE_THRESHOLD` to `.7`, and `RAGRequest` uses that setting. The recovery did not modify either production default or test. The passing configured run is supplementary evidence, not a retroactive claim that the default run passed. The warning is a Starlette `httpx`/TestClient deprecation. Three existing opt-in skips remain.

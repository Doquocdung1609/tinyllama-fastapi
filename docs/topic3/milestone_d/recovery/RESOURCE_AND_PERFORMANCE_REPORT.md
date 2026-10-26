# Resource and regression evidence

Environment: Windows, Python 3.13.2, isolated research snapshot with one 1,066,740-byte P&G HTML source. `resource_probe_v1.json` records 7 source-selected exact-cell runs. Without allocation tracing: elapsed milliseconds `[1091.288, 627.292, 582.994, 576.815, 651.820, 581.488, 585.409]`; p50 `585.409`, p95 nearest-rank `1091.288` (the cold first call). With `tracemalloc` enabled, p50 `3027.518` and p95 `5623.051` ms; instrumentation changes runtime substantially and is not comparable to the untraced series. Recorded traced Python peak allocation was 62,301,886 bytes; process RSS rose from 46,903,296 to 113,389,568 bytes. These are one-process, one-source observations, not server capacity or concurrency benchmarks. No GPU used.

Commands/results on recovery branch before delivery:

| Command | Result |
|---|---|
| `python -m pytest -q tests/test_real_sec_recovery.py` | 5 passed |
| `python -m compileall -q app scripts` | PASS |
| `python -m pytest -q` (ambient default `SCORE_THRESHOLD=0.7`) | 1 failed, 555 passed, 3 skipped, 1 warning, 27.47 s |
| `$env:SCORE_THRESHOLD='0.55'; python -m pytest -q` | 556 passed, 3 skipped, 1 warning, 23.13 s |
| `git diff --check` | PASS |

The sole default-environment failure is pre-existing at D5 HEAD: `tests/test_models.py::test_rag_defaults` asserts `.55`, whereas `app/config.py` defaults `SCORE_THRESHOLD` to `.7`, and `RAGRequest` uses that setting. The recovery did not modify either production default or test. The passing configured run is supplementary evidence, not a retroactive claim that the default run passed. The warning is a Starlette `httpx`/TestClient deprecation. Three existing opt-in skips remain.

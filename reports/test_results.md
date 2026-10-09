# Test results — 10/10/2026

## Automated suite

| Suite | Result | Evidence |
|---|---:|---|
| Unit/API regression | PASS | `18 passed, 3 skipped` in 1.15 s; integration tests are opt-in. |
| Real media integration | PASS | `3 passed, 18 deselected` in 81.79 s. |
| Import/compile | PASS | `compileall` completed for app, scripts and tests. |
| Dependency consistency | PASS | `pip check`: no broken requirements. |
| Smoke test | PASS | FastAPI 200, Streamlit 200, 8 expected tabs, Ollama/Qdrant/embedding online. |
| Browser reload | PASS | In-app Chromium reload rendered Dashboard with 1 document, 971 chunks/vectors and no console errors. |
| Cross-tab navigation | PASS | Dashboard, Chat, RAG, Chunk Explorer, TTS, Image, Video and System headings rendered. |
| Windows launcher | PASS | `start_genai.ps1 -NoBrowser` started missing services and reported both URLs; repeat invocation avoided duplicates. |

The unit suite uses mocks for API boundaries and deterministic retrieval cases. Media PASS claims come only from the separate real integration run.

## RAG quality

- Re-indexed the real 249-page finance PDF with layout extraction: 971 chunks and 971 Qdrant vectors.
- Measured full pipeline: 397.597 s total (extraction 101.498 s, cleaning 0.040 s, chunking 0.057 s, embedding 283.585 s, Qdrant indexing 12.413 s).
- Retrieval-only benchmark: **16/16 PASS**, average 2.404 s (min 2.292 s, max 3.052 s).
- Generated-answer rubric: **14/16 score at least 7/10**, average 8.44/10.
- Q01: page 155, 9/10. Q09: pages 214–215 included, 8/10. Q12: page 237 and 69%, 10/10.
- Q15 and Q16: no source returned and deterministic grounded refusal, 10/10 each.
- Q04 scored 6/10 because the second driver was misstated. Q13 scored 6/10 because the answer omitted concept drift, independent validation and data monopoly.

Full per-question evidence is in `reports/rag_benchmark.csv`; retrieval timing is in `reports/rag_benchmark_retrieval.csv`.

## Real media evidence

| Capability | Result | Validation |
|---|---:|---|
| Windows SAPI TTS | PASS | Real WAV, nonzero frames/sample rate; benchmark file 139,132 bytes. |
| Tiny-SD image | PASS | Real local PNG at 256×256; nonblank pixel variance; deterministic seed recorded. |
| FFmpeg motion demo | PASS | H.264, 1280×720, yuv420p, 14 FPS, browser-compatible MP4. |
| Stable Video Diffusion | BLOCKED | Guarded at runtime: 4,096 MiB detected, 8,192 MiB minimum configured. No diffusion PASS claimed. |

## Performance observations

- Health: 0.008 s.
- System status: 19.581 s uncached, 0.005 s cached after TTL fix.
- RAG retrieval: 2.642 s representative call.
- RAG generation: 119.406 s on the measured long-context question.
- Warm chat, up to 128 tokens: 20.500 s.
- First streaming chat after an image/model switch: TTFT 150.747 s, total 158.221 s. This includes diffusion unload and cold Llama 3 reload.
- Full 249-page PDF pipeline: 397.597 s; health remained responsive while embedding was `RUNNING`.
- Tiny-SD 256×256, 2 steps: 76.539 s; peak VRAM 2,827 MiB.
- Windows SAPI benchmark: 23.784 s. FFmpeg 28-frame motion demo: 1.106 s.

All performance rows include measured peak RAM, VRAM, CPU and GPU values in `reports/performance_benchmark.csv`.

## Warnings retained

- Starlette emits a deprecation warning for its current `TestClient` transport; it does not fail any test.
- Diffusers emits a NumPy 2 array-copy deprecation warning during the real image test; output validation still passes.

# Performance and resource measurements

Measured 2026-10-12 on Windows with Ollama `qwen2.5:3b`, `nomic-embed-text`, local Tesseract and local Qdrant.

| Workload | n | Mean | P95 / notable |
|---|---:|---:|---:|
| Strict conversational API rows with nonzero latency | 15 | 2,816.3 ms | 19,377.2 ms |
| Structural table/page operations | 3 | 124.9 ms | 137.7 ms |
| New real PDF questions | 4 | 11,345.1 ms | 25,556.8 ms |
| Internal holdout questions | 4 | 8,091.0 ms | 13,214.3 ms |
| OCR preprocessing configurations | 9 | — | 449.2–2,865.4 ms/page |

A measured generative request took 15,038.7 ms inside RAG: embedding 2,303.6 ms, retrieval 3.7 ms, prompt preparation 0.1 ms, Qwen generation 12,730.9 ms. During this request GPU memory reached 2,285 MiB; a later loaded-model snapshot was 2,525/4,096 MiB.

Resource snapshot after both APIs, Streamlit, Ollama and Qdrant were live:

- Physical RAM: 7.84 GB; free 0.74 GB.
- C: free disk: 8.55 GB.
- Production Qdrant: online, 1,947 vectors, dimension 768.
- Isolated API process working set observed: about 546 MB.
- Streamlit/FastAPI smoke: 200 responses; all eight navigation tabs detected.

These are local point measurements, not laboratory maxima. RAM and disk headroom are limited. No heavyweight OCR or vision model was added.

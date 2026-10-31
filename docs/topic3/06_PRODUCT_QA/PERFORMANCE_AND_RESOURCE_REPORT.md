# Measured resources and time

These are measurements on this Windows host, not normalized benchmark estimates.

| Measurement | Actual observation | Boundary |
|---|---:|---|
| Free disk during Prebuilt smoke | 63.60 GiB | C: drive point-in-time |
| API Python working set after two uploads | 543.5 MiB | process snapshot; not peak |
| Available RAM at system screen | 3.6 GB | point-in-time UI status |
| Hòa Phát upload-to-READY | 90.386 s | 24 pages, includes OCR, chunking and indexing; **not OCR-only time** |
| BIDV upload-to-READY | 7.836 s | 8 pages, 2 OCR + 6 native; includes full pipeline |
| Hòa Phát API BM25/Dense/Hybrid | 1208.02 / 359.49 / 398.64 ms | same question, selected PDF, one warm/cold mixed call each; no p50 |
| HD SEC API BM25/Dense/Hybrid | 1492.69 / 7480.28 / 890.56 ms | same question, selected issuer; single calls; Dense cold-load effect possible |
| Author-method offline BM25/Dense/SPLADE embeddings | 2.22 / 28.35 / 123.55 s | 121 author chunks, separate processes; see `../01_REPRODUCTION/BASELINE_BENCHMARK_REPORT.md` |
| Author-method SPLADE peak process RSS | 5,516.5 MiB | observed process peak; minimum system available RAM 0.8 MiB, operational risk |
| Structure BM25 local query p50 | 13.802 ms | 6 queries, embedded Qdrant only, no embedding/network |

No reliable **peak API RAM** or **OCR-only processing time** was instrumented in this smoke. They remain missing measurements, not zero. Browser, Ollama and Qdrant local memory are outside the API process snapshot. The SPLADE corpus build should not run alongside interactive OCR on this limited-RAM machine.

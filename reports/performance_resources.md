# Performance and resources

- Multi-turn real API latency (11 generated turns): mean 4169.3 ms; P95 18929.8 ms.
- OCR/financial/chart real API latency (n=8): mean 5805.5 ms; P95 30131.2 ms. OCR01 includes a cold model load.
- Production regression mean: 29536.4 ms (n=5).
- P0 mean: 7018.2 ms (n=4).
- Measured API process peak working sets: 567.7 MB (production) and 535.1 MB (isolated test).
- GPU snapshot after inference: 2,513 / 4,096 MiB. Ollama serial concurrency is 1.
- C: free disk snapshot: 10.32 GB.
- Processing the two-page bilingual scanned table: 28.089 s total, including 23.223 s embeddings.

These are local snapshots, not laboratory maxima. The design avoids a vision model and uses CPU OCR to stay within the 4 GB GPU limit.

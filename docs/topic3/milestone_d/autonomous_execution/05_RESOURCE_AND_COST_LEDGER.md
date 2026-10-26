# Resource and cost ledger

Preflight Windows11/Python3.13.2,8,221,732KB visible RAM;826,420KB free at sample. C drive15,581,175,808 bytes free. Ollama127.0.0.1:11434 connection refused. No paid service or model download. Do not launch a multi-GB model with this memory headroom. Sequential CPU-only diagnostics; D2 full provenance parse dominates, timings in D2 retained audit v2. New research storage must have an ownership marker and bounded budgets before writing.


## D3 checkpoint addition

D3 owned namespace62,654,330bytes after source freeze/index; no embeddings/Qdrant/model downloads.11-query B service p50/p95~437/1329ms, one descriptive run; not cold/warm throughput comparison. ProcessRSS/VRAM NOT_MEASURED. Source cache reuses C generation/hash-bound behavior,1entry32MiB, per-request byte checks.

## D5 resource snapshot v2

Later OS sample: 8,221,732 KiB visible RAM, 1,070,988 KiB free. D5 one-shot B held-out descriptive p50/p95 `309.45/925.14 ms` over five sequential requests; this includes real C source checks and differs from C end-to-end and D4 synthetic in-process boundaries. D5 21-request HTTP artifact retains per-request timings; no throughput/cold-warm benchmark or process RSS measurement. All local children launched for UI/HTTP smoke testing were stopped; no new paid service, embedding or vector collection was created.

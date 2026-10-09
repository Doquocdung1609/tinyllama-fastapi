# Code audit

## Architecture and endpoint map

| UI tab | API/backend implementation |
|---|---|
| Dashboard | `GET /system/status`, `GET /stats` |
| Chat với Llama 3 | `POST /chat`, `POST /chat/stream`, Ollama generate API |
| Talk to Documents / RAG | `/documents/*`, `POST /rag/query`, pypdf, Ollama embeddings, Qdrant local, Llama 3 |
| Chunk Explorer | `GET /documents/{id}/preview` and saved processed pages |
| English Script → Audio | `/tts/voices`, `/tts/generate`, Windows SAPI/pyttsx3 |
| Text → Image | `POST /image/generate`, Tiny-SD/Diffusers/PyTorch CUDA |
| Image → Video | `POST /video/generate`; separate `POST /video/demo` for labelled FFmpeg motion |
| System / GPU | `GET /system/status`, `/qdrant/status`, `/inference/status`, document deletion |

Backward-compatible `/generate` remains present.

## Findings and repairs

| Priority | Finding | Repair/status |
|---|---|---|
| P1 | pypdf plain extraction inserted intra-word spaces in Vietnamese and harmed retrieval. | Changed to pypdf layout extraction with fallback; index version 2 and safe re-index. |
| P1 | Semantic-only retrieval returned high-score irrelevant chunks for conceptual questions. | Added document filtering and hybrid BM25-style lexical + semantic reranking. |
| P1 | Image/video dependencies and CUDA runtime were absent. | Installed pinned CUDA environment; verified real image generation. |
| P2 | RAG prompts could include irrelevant/large context and generation could be slow. | Bound context to 7,000 chars, reduced max answer tokens, added per-stage timing and deterministic no-context response. |
| P2 | Chunk Explorer rendered all 1,053 chunks. | Added page size and page controls; default renders 20 expanders. |
| P2 | Preview re-extracted the full PDF repeatedly. | Reuses pages persisted in processed JSON before falling back to PDF extraction. |
| P2 | Heavy diffusion tasks had no cross-feature serialization. | Added bounded global heavy-inference lock, stages, resource snapshots and cache release helpers. |
| P2 | Re-index upsert left trailing points when the new document produced fewer chunks. | Prunes stale point IDs after successful upsert; verified 971 chunks = 971 vectors. |
| P2 | Diffusion remained resident before the next Ollama request. | Chat, streaming, RAG generation, document embedding, image and video now share one bounded inference queue; model ownership switches explicitly. |
| P2 | GTX 16-series FP16 VAE/UNet produced a black image. | Detects Turing and uses FP32 for the Tiny-SD pipeline. |
| P2 | TTS could race across requests/COM threads. | Added process lock and COM initialize/uninitialize around SAPI. |
| P3 | Chat waited for the complete Ollama response. | Added `/chat/stream` and Streamlit token streaming; bounded history by character budget. |
| P3 | Dashboard omitted disk/free RAM and optional readiness. | Added cached diagnostics for NVIDIA driver, VRAM, CPU, RAM, disk, FFmpeg, image/video readiness and inference state. |
| P3 | Streamlit blanked after reload due cached `import client`. | Existing `runpy.run_path` repair retained and covered by smoke/E2E checks. |

## Concurrency observations

- FastAPI synchronous routes run in Starlette's worker thread pool, so Ollama and TTS calls do not block the asyncio event loop.
- Document processing uses a FastAPI background task and persists READY documents to JSON.
- Qdrant local mode is intended for a single backend process; duplicate FastAPI instances can contend for its file lock. The launcher prevents duplicate port-bound servers.
- Image/video and Ollama generation remain synchronous at the API boundary to preserve compatibility, but all heavyweight work is serialized and exposes current inference stages. Safe cancellation of active CUDA kernels is not implemented.

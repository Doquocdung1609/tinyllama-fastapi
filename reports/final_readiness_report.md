# Final readiness report — GenAI Learning Studio

## A. Executive Summary

The application is running at `http://127.0.0.1:8501` with FastAPI, Streamlit, Ollama and Qdrant online. Existing user data was retained and backed up before the RAG v2 migration. Core chat, grounded RAG, Chunk Explorer, offline TTS, local image generation, diagnostics and launcher flows are operational. Stable Video Diffusion is truthfully BLOCKED by 4 GB VRAM; a separately labelled FFmpeg motion demo is available and verified.

The Vietnamese RAG index improved from 1,053 whitespace-damaged chunks to 971 layout-extracted, sentence-aware chunks. Retrieval reaches 16/16 on the fixed evaluation set, while generated answers meet the 7/10 gate on 14/16 cases.

## B. Hardware and Runtime

| Item | Detected value |
|---|---|
| OS | Windows 11 Home Single Language, build 10.0.26200 |
| CPU | Intel Core i5-10300H, 4 cores / 8 threads |
| RAM | 7.8 GB usable; about 0.7–1.2 GB available under the final mixed workload |
| GPU | NVIDIA GeForce GTX 1650 Ti, compute capability 7.5 |
| VRAM | 4,096 MiB |
| Driver | 555.97 |
| Python | 3.13.2 |
| PyTorch | 2.6.0+cu124; CUDA available; runtime CUDA 12.4 |
| Ollama | 0.30.10; `llama3:latest`, `nomic-embed-text`, `tinyllama`, `llava` |
| FFmpeg | 8.0 full build, H.264 available |
| Free C: space | About 3.1–3.2 GB after dependencies, model and test artifacts |

## C. Dependency Installation

Installed only in the project `.venv`: PyTorch 2.6.0+cu124, torchvision 0.21.0+cu124, Diffusers 0.41.0, Accelerate 1.15.0, imageio 2.38.1 and imageio-ffmpeg 0.6.0. Sympy was aligned to PyTorch's required 1.13.1. `pip check` reports no broken requirements.

The verified local image model is `models/tiny-sd` (about 0.99 GB, CreativeML OpenRAIL-M). It runs in FP32 on this Turing GPU because the real FP16 test produced NaNs and a black image.

## D. Feature Matrix

| Tab | Before | After | Evidence | Limitations |
|---|---|---|---|---|
| Dashboard | Basic status; reload issue previously observed | Cached real service/hardware/media metrics | Browser reload PASS; 971 chunks/vectors shown | Cold status can take about 20 s under memory pressure |
| Chat | Nonstreaming Ollama call | Streaming, bounded history/context, shared inference queue | API/unit tests; real Vietnamese chat benchmark | Cold reload after diffusion measured TTFT 150.747 s |
| RAG | Vietnamese whitespace damage; Q01/Q09 failed | Layout extraction, hybrid retrieval, numeric grounding, neighbor context, document filter | 16/16 retrieval; 14/16 quality | Q04 and Q13 remain 6/10 |
| Chunk Explorer | Could render all chunks and re-extract PDF | Saved-page preview, pagination, preview/index distinction, complete metadata | Browser tab and unit tests PASS | Token count remains an estimate |
| English Audio | Race/COM risk | Locked Windows SAPI, explicit COM lifecycle, unique WAV | Real WAV integration PASS | Installed voices are en-US only |
| Text → Image | Dependencies/model missing | Real local Tiny-SD PNG, seed/metadata, lazy cache, OOM fallback | Nonblank PNG integration PASS | Tiny-SD quality is modest; FP32 is slow |
| Image → Video | SVD unavailable | Safe SVD guard plus labelled FFmpeg mode | H.264/yuv420p MP4 verified | Genuine diffusion BLOCKED by VRAM |
| System / GPU | Limited runtime details | Real CUDA/driver/VRAM/RAM/disk/model/Qdrant/readiness diagnostics | Smoke and browser PASS | Only 3.1–3.2 GB disk remains free |

## E. RAG Improvements

- Before: Q01 3/10 FAIL, Q09 6/10 FAIL, Q12 9/10 PASS, Q15 10/10 PASS.
- After: Q01 9/10, Q09 8/10, Q12 10/10, Q15 10/10 and Q16 10/10.
- Retrieval-only: 16/16 PASS, average 2.404 s.
- Generated answers: 14/16 at least 7/10; average 8.44/10.
- Missing numeric anchors now remove unrelated future-date/amount sources before generation.
- Re-index replaces stale document vectors, so the collection now contains exactly 971 points.

## F. Performance Improvements

| Workload | Measured wall time | Peak RAM | Peak VRAM |
|---|---:|---:|---:|
| Health | 0.008 s | 5,295 MB | 0 MB |
| System status, uncached | 19.581 s | 6,379 MB | 371 MB |
| System status, cached | 0.005 s | 6,377 MB | 371 MB |
| RAG retrieval | 2.642 s | 6,447 MB | 383 MB |
| RAG with Llama 3 | 119.406 s | 8,025 MB | 2,339 MB |
| Warm chat, 128-token cap | 20.500 s | 7,519 MB | 2,339 MB |
| Tiny-SD, 256×256, 2 steps | 76.539 s | 7,645 MB | 2,827 MB |
| Windows SAPI | 23.784 s | 7,369 MB | 2,339 MB |
| Motion demo, 28 frames | 1.106 s | 6,578 MB | 2,827 MB |
| PDF extraction, 249 pages | 101.498 s | not sampled | not sampled |
| Embedding, 971 chunks | 283.585 s | 5,326→6,518 MB observed | 383→387 MB observed |
| Qdrant indexing, 971 vectors | 12.413 s | not sampled | not sampled |
| Full PDF pipeline | 397.597 s | not sampled | not sampled |

System cache warm latency fell from an invalid 28.510 s measurement to 0.005 s after storing the TTL timestamp at completion. Reducing RAG context after neighbor expansion lowered the representative RAG run from 284.247 s to 119.406 s. Model switching remains expensive: after image generation, chat streaming measured 150.747 s to first byte because Llama 3 must be loaded again within 8 GB RAM. The final launcher restart reached readiness in 10.9 s; a browser reload showed the shell within 3.5 s and all Dashboard metrics within 23.5 s under a cold status refresh.

## G. Tests

- PASS: 18 unit/API tests.
- PASS: 3 real media integration tests.
- PASS: smoke test, launcher, browser reload and all eight navigation entries.
- PASS: real Tiny-SD PNG, Windows SAPI WAV and FFmpeg MP4.
- BLOCKED: real Stable Video Diffusion.
- No failed automated test remains. Two library deprecation warnings are documented.

## H. Remaining Problems

1. SVD requires at least 8 GB VRAM in this configuration; detected VRAM is 4 GB.
2. Llama 3 and Tiny-SD cannot remain resident together. The manager unloads one before loading the other, which prevents OOM but causes long cold-switch latency.
3. System RAM and free disk are tight. The project does not delete user caches or artifacts automatically.
4. Q04 and Q13 need improved retrieval/prompt coverage for fully correct answers.
5. Active CUDA kernels are not forcibly cancelled; queued heavy jobs are bounded and serialized.

## I. Demo Instructions

```powershell
cd C:\Users\Admin\Desktop\AI_thay_Hieu\tinyllama-fastapi
.\start_genai.ps1 -DemoMode
```

Shortest reliable classroom sequence:

1. Dashboard: confirm FastAPI/Ollama/Qdrant and 971 vectors.
2. Chat: ask one short Vietnamese question and wait for streaming.
3. RAG: select the finance PDF and ask Q01 or Q12; open sources/debug.
4. Chunk Explorer: show indexed versus preview chunks.
5. TTS: synthesize a short English sentence with David or Zira.
6. Image: use a saved verified image for a fast explanation, or run 256×256 live and disclose the wait.
7. Video: show SVD BLOCKED, then run the explicitly labelled motion demo.
8. System: show real CUDA, RAM, disk and readiness diagnostics.

Demo Mode may replay saved real artifacts with their metadata; it never labels them as newly generated.

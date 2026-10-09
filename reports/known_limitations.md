# Known limitations

1. **Stable Video Diffusion is BLOCKED.** The detected GPU has 4 GB VRAM; the configured SVD pipeline is deliberately blocked below 8 GB to avoid repeated OOM and system instability.
2. **Motion demo is not generative video.** `/video/demo` applies a Ken Burns effect with FFmpeg and is labelled accordingly in API/UI.
3. **Tiny-SD quality is limited.** It is selected for the actual disk/RAM/VRAM budget. It is faster and smaller than full SD 1.5 but produces lower-detail images.
4. **Tiny-SD uses legacy `.bin` weights.** The selected published repository does not provide safetensors components. Load it only from the recorded model origin.
5. **Turing image inference uses FP32.** FP16 produced a real but black image due NaNs. FP32 is correct but slower and uses more VRAM.
6. **Only 8 GB system RAM is installed.** Closing browsers, IDEs and unrelated GPU/RAM-heavy apps improves diffusion reliability.
7. **Qdrant local mode permits one backend owner.** Start the app through `start_genai.ps1` to avoid duplicate FastAPI instances and local database locks.
8. **Active CUDA cancellation is unsafe.** The manager bounds and serializes heavy work but does not interrupt an already executing CUDA kernel. Queued-job cancellation is not exposed because the backward-compatible endpoints are synchronous.
9. **TTS voices are English only on this machine.** Microsoft David and Zira are available; voice inventory depends on Windows installation.
10. **RAG generation speed depends on Llama 3 residency.** Retrieval is measured separately from LLM generation; cold model load is materially slower.
11. **Model switching is slow.** A real chat immediately after Tiny-SD measured 150.747 seconds to first byte because the manager first released diffusion and then reloaded the 5.3 GB Ollama runtime footprint across CPU/GPU.
12. **Free disk space is low.** About 3.1–3.2 GB remained after installation and verified artifacts. No user model/cache directory is deleted automatically.
13. **Two RAG answers remain below the quality gate.** Q04 and Q13 scored 6/10; full details are preserved in `rag_benchmark.csv`.

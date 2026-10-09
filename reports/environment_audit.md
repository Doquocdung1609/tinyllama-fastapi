# Environment audit — 09/10/2026

## Hardware

| Item | Detected value |
|---|---|
| OS | Windows 11 Home Single Language, build 10.0.26200 |
| CPU | Intel Core i5-10300H, 4 physical cores / 8 logical threads |
| RAM | 8.0 GB installed; about 1.1 GB available at initial audit |
| Storage | SSD, C: 475.95 GB total, 11.3 GB free before ML installation |
| GPU | NVIDIA GeForce GTX 1650 Ti |
| GPU architecture | Compute capability 7.5 (Turing) |
| VRAM | 4,096 MiB total; 3,927 MiB free at initial audit |
| Driver | 555.97 |
| FFmpeg | 8.0 full build; H.264 encode available |

## Runtime before changes

- Python 3.13.2, pip 26.2.1.
- FastAPI 0.142.2, Streamlit 1.65.0, qdrant-client 1.19.1, pypdf 6.19.0.
- `torch`, `diffusers`, `accelerate` were not installed.
- Transformers 5.18.0 was already installed.
- Ollama 0.30.10 was reachable.
- Ollama models: `llama3:latest` (4.7 GB), `nomic-embed-text` (274 MB), `tinyllama`, `llava`.
- Windows SAPI voices: Microsoft David Desktop and Microsoft Zira Desktop, both en-US.
- Hugging Face cache used about 3.93 GB; Ollama model storage used about 9.60 GB.
- Network checks to PyPI and Hugging Face succeeded.

## Runtime after dependency repair

- PyTorch 2.6.0+cu124 imports successfully.
- PyTorch CUDA runtime is 12.4; `torch.cuda.is_available()` is `True`.
- GPU detected by PyTorch as GTX 1650 Ti, compute capability 7.5, 4,096 MiB.
- Diffusers 0.41.0, Accelerate 1.15.0, torchvision 0.21.0+cu124 and imageio-ffmpeg 0.6.0 import successfully.
- `pip check`: no broken requirements.
- Local image model: `models/tiny-sd`, approximately 0.99 GB, CreativeML OpenRAIL-M.

## Resource decision

The machine has enough VRAM for Tiny-SD image generation but not for Stable Video Diffusion. The image pipeline uses FP32 on this Turing GPU because FP16 produced NaN values and a black PNG in a real test. Video diffusion remains blocked below 8 GB VRAM. FFmpeg motion demo is available as a separately labelled non-diffusion mode.

## Final observed state — 10/10/2026

- Qdrant online with 971 vectors at dimension 768; one ready document with 249 pages and 971 chunks.
- Image readiness `READY`; video diffusion readiness `INSUFFICIENT_VRAM`.
- About 3.1–3.2 GB remained free on C: after the model, CUDA wheels and verified outputs.
- Under the final mixed workload, only about 0.7–1.2 GB RAM was available. The shared inference queue is therefore required for stability.

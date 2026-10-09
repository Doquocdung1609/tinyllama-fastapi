"""Optional local Stable Diffusion image generation."""
from datetime import datetime
from functools import lru_cache
from time import monotonic
import logging
import importlib.util
import secrets
from app.config import get_settings
from app.services.inference_manager import (heavy_inference, mark_stage, release_cuda_cache,
                                            release_ollama_gpu)
logger = logging.getLogger(__name__)


@lru_cache(maxsize=2)
def _pipeline(model_id: str, strategy: str):
    import torch
    from diffusers import StableDiffusionPipeline
    # Turing GTX 16-series inference is more reliable in FP32; this avoids
    # black images caused by FP16 NaNs on this specific 4 GB GPU.
    model_dtype = torch.float32 if torch.cuda.get_device_capability(0)[0] < 8 else torch.float16
    pipe = StableDiffusionPipeline.from_pretrained(
        model_id, dtype=model_dtype, use_safetensors=None,
        local_files_only=True, low_cpu_mem_usage=True)
    if hasattr(pipe, "enable_vae_slicing"):
        pipe.enable_vae_slicing()
    elif hasattr(pipe, "vae") and hasattr(pipe.vae, "enable_slicing"):
        pipe.vae.enable_slicing()
    # GTX 16-series cards can produce NaNs when the VAE decodes in FP16.
    # Let Diffusers upcast VAE decoding while keeping UNet inference in FP16.
    if model_dtype == torch.float16 and hasattr(pipe, "vae") and hasattr(pipe.vae, "config"):
        pipe.vae.config.force_upcast = True
    if strategy == "sequential_offload":
        pipe.enable_sequential_cpu_offload()
    else:
        pipe.enable_attention_slicing("max")
        pipe.to("cuda")
    return pipe


def unload_pipeline() -> None:
    _pipeline.cache_clear()
    release_cuda_cache()


def readiness() -> dict:
    settings = get_settings()
    missing = [name for name in ("torch", "diffusers", "accelerate")
               if importlib.util.find_spec(name) is None]
    if missing:
        return {"status": "DEPENDENCY_MISSING", "ready": False, "missing": missing,
                "model": settings.image_model}
    import torch
    if not torch.cuda.is_available():
        return {"status": "CUDA_UNAVAILABLE", "ready": False, "model": settings.image_model,
                "torch": torch.__version__, "torch_cuda": torch.version.cuda}
    try:
        from huggingface_hub import try_to_load_from_cache
        cached = try_to_load_from_cache(settings.image_model, "model_index.json")
    except Exception:
        cached = None
    if not cached and not __import__("pathlib").Path(settings.image_model).exists():
        return {"status": "MODEL_MISSING", "ready": False, "model": settings.image_model,
                "torch": torch.__version__, "torch_cuda": torch.version.cuda}
    total_mb = round(torch.cuda.get_device_properties(0).total_memory / 1024**2)
    return {"status": "READY", "ready": True, "model": settings.image_model,
            "torch": torch.__version__, "torch_cuda": torch.version.cuda,
            "vram_total_mb": total_mb, "strategy": "direct_then_sequential_oom_fallback"}


def generate_image(prompt: str, negative_prompt: str, steps: int, guidance_scale: float,
                   width: int, height: int, seed: int | None) -> dict:
    started = monotonic()
    try:
        import torch
        from diffusers import StableDiffusionPipeline
    except ImportError as exc:
        raise RuntimeError("Stable Diffusion is unavailable. Install optional requirements-image.txt and download a local model.") from exc
    settings = get_settings()
    model_id = settings.image_model
    device = "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cpu":
        raise RuntimeError("Stable Diffusion requires a supported GPU for this project configuration; RAG and chat remain available.")
    actual_seed = seed if seed is not None else secrets.randbelow(2**31 - 1)
    strategy = "direct"
    with heavy_inference("text_to_image"):
        release_ollama_gpu()
        from app.services import video_service
        video_service.unload_pipeline()
        release_cuda_cache()
        try:
            mark_stage("LOADING_MODEL")
            pipe = _pipeline(model_id, strategy)
            mark_stage("RUNNING")
            generator = torch.Generator(device=device).manual_seed(actual_seed)
            with torch.inference_mode():
                image = pipe(prompt, negative_prompt=negative_prompt, num_inference_steps=steps,
                             guidance_scale=guidance_scale, width=width, height=height,
                             generator=generator).images[0]
        except Exception as exc:
            if "out of memory" not in str(exc).lower():
                unload_pipeline()
                raise RuntimeError(f"Không thể nạp/chạy model ảnh local '{model_id}': {exc}") from exc
            logger.warning("direct image generation OOM; retrying with sequential CPU offload")
            unload_pipeline()
            strategy = "sequential_offload"
            try:
                mark_stage("LOADING_MODEL")
                pipe = _pipeline(model_id, strategy)
                mark_stage("RUNNING")
                generator = torch.Generator(device=device).manual_seed(actual_seed)
                with torch.inference_mode():
                    image = pipe(prompt, negative_prompt=negative_prompt, num_inference_steps=min(steps, 20),
                                 guidance_scale=guidance_scale, width=min(width, 512), height=min(height, 512),
                                 generator=generator).images[0]
            except Exception as retry_exc:
                unload_pipeline()
                raise RuntimeError("GPU memory is insufficient even with sequential CPU offload. "
                                   "Close other GPU applications or use 512×512 and at most 20 steps.") from retry_exc
        mark_stage("SAVING")
        settings.image_dir.mkdir(parents=True, exist_ok=True)
        path = settings.image_dir / f"image_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        image.save(path)
        precision = str(next(pipe.unet.parameters()).dtype).replace("torch.", "")
    logger.info("image generated path=%s seconds=%.2f", path.name, monotonic() - started)
    return {"path": str(path), "seed": actual_seed, "model": model_id, "width": image.width,
            "height": image.height, "steps": min(steps, 20) if strategy == "sequential_offload" else steps,
            "strategy": strategy, "precision": precision,
            "generation_seconds": round(monotonic() - started, 2)}

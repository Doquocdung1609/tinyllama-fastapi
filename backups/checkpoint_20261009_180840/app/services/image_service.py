"""Optional local Stable Diffusion image generation."""
from datetime import datetime
from functools import lru_cache
from time import monotonic
import logging
from app.config import get_settings
logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _pipeline(model_id: str):
    import torch
    from diffusers import StableDiffusionPipeline
    return StableDiffusionPipeline.from_pretrained(model_id, torch_dtype=torch.float16, local_files_only=True).to("cuda")


def generate_image(prompt: str, negative_prompt: str, steps: int, guidance_scale: float,
                   width: int, height: int, seed: int | None) -> dict:
    started = monotonic()
    try:
        import torch
        from diffusers import StableDiffusionPipeline
    except ImportError as exc:
        raise RuntimeError("Stable Diffusion is unavailable. Install optional requirements-image.txt and download a local model.") from exc
    model_id = __import__("os").getenv("IMAGE_MODEL", "runwayml/stable-diffusion-v1-5")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cpu":
        raise RuntimeError("Stable Diffusion requires a supported GPU for this project configuration; RAG and chat remain available.")
    try:
        pipe = _pipeline(model_id)
    except RuntimeError as exc:
        if "out of memory" in str(exc).lower():
            raise RuntimeError("GPU memory is insufficient. Reduce image width, height, or inference steps.") from exc
        raise RuntimeError(f"Không thể nạp model ảnh local '{model_id}'. Hãy cấu hình IMAGE_MODEL trỏ tới model đã tải sẵn.") from exc
    generator = torch.Generator(device=device).manual_seed(seed) if seed is not None else None
    try:
        image = pipe(prompt, negative_prompt=negative_prompt, num_inference_steps=steps,
                     guidance_scale=guidance_scale, width=width, height=height, generator=generator).images[0]
    except RuntimeError as exc:
        if "out of memory" in str(exc).lower():
            raise RuntimeError("GPU memory is insufficient. Reduce image width, height, or inference steps.") from exc
        raise
    settings = get_settings(); settings.image_dir.mkdir(parents=True, exist_ok=True)
    path = settings.image_dir / f"image_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    image.save(path)
    logger.info("image generated path=%s seconds=%.2f", path.name, monotonic() - started)
    return {"path": str(path), "seed": seed, "generation_seconds": round(monotonic() - started, 2)}

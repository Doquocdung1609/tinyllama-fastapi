"""Optional image-to-video generation using a locally installed SVD pipeline."""
from datetime import datetime
from functools import lru_cache
from time import monotonic
import logging
from app.config import get_settings
logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _pipeline(model_id: str):
    import torch
    from diffusers import StableVideoDiffusionPipeline
    return StableVideoDiffusionPipeline.from_pretrained(model_id, torch_dtype=torch.float16, variant="fp16", local_files_only=True).to("cuda")


def generate_video(image_path: str, num_frames: int, fps: int) -> dict:
    started = monotonic()
    try:
        import torch
        from diffusers import StableVideoDiffusionPipeline
        from diffusers.utils import export_to_video
    except ImportError as exc:
        raise RuntimeError("Video model unavailable. Install optional video dependencies and configure a local Stable Video Diffusion model.") from exc
    if not torch.cuda.is_available():
        raise RuntimeError("Video generation requires substantial GPU memory. Enable CUDA or use a machine with a supported GPU.")
    from PIL import Image
    import os
    model_id = os.getenv("VIDEO_MODEL", "stabilityai/stable-video-diffusion-img2vid-xt")
    try:
        pipe = _pipeline(model_id)
    except RuntimeError as exc:
        if "out of memory" in str(exc).lower():
            raise RuntimeError("Video generation requires substantial GPU memory. Reduce frame count or decode chunk size.") from exc
        raise RuntimeError(f"Không thể nạp model video local '{model_id}'. Hãy cấu hình VIDEO_MODEL trỏ tới model đã tải sẵn.") from exc
    try:
        frames = pipe(Image.open(image_path).convert("RGB"), num_frames=num_frames).frames[0]
    except RuntimeError as exc:
        if "out of memory" in str(exc).lower():
            raise RuntimeError("Video generation requires substantial GPU memory. Reduce frame count or decode chunk size.") from exc
        raise
    settings = get_settings(); settings.video_dir.mkdir(parents=True, exist_ok=True)
    path = settings.video_dir / f"video_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
    export_to_video(frames, str(path), fps=fps)
    logger.info("video generated path=%s frames=%d fps=%d seconds=%.2f", path.name, len(frames), fps, monotonic() - started)
    return {"path": str(path), "frames": len(frames), "fps": fps, "generation_seconds": round(monotonic() - started, 2)}

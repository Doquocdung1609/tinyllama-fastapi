"""Optional image-to-video generation using a locally installed SVD pipeline."""
from datetime import datetime
from functools import lru_cache
from time import monotonic
import logging
import importlib.util
import subprocess
from app.config import get_settings
from app.services.inference_manager import (heavy_inference, mark_stage, release_cuda_cache,
                                            release_ollama_gpu)
logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _pipeline(model_id: str):
    import torch
    from diffusers import StableVideoDiffusionPipeline
    return StableVideoDiffusionPipeline.from_pretrained(model_id, torch_dtype=torch.float16, variant="fp16", local_files_only=True).to("cuda")


def unload_pipeline() -> None:
    _pipeline.cache_clear()
    release_cuda_cache()


def readiness() -> dict:
    settings = get_settings()
    missing = [name for name in ("torch", "diffusers", "imageio_ffmpeg")
               if importlib.util.find_spec(name) is None]
    if missing:
        return {"status": "DEPENDENCY_MISSING", "ready": False, "missing": missing,
                "model": settings.video_model, "demo_mode": ffmpeg_available()}
    import torch
    if not torch.cuda.is_available():
        return {"status": "CUDA_UNAVAILABLE", "ready": False, "model": settings.video_model,
                "demo_mode": ffmpeg_available()}
    total_mb = round(torch.cuda.get_device_properties(0).total_memory / 1024**2)
    if total_mb < 8192:
        return {"status": "INSUFFICIENT_VRAM", "ready": False, "model": settings.video_model,
                "vram_total_mb": total_mb, "required_vram_mb": 8192,
                "detail": "Stable Video Diffusion không an toàn trên GPU 4 GB.",
                "demo_mode": ffmpeg_available()}
    try:
        from huggingface_hub import try_to_load_from_cache
        cached = try_to_load_from_cache(settings.video_model, "model_index.json")
    except Exception:
        cached = None
    if not cached and not __import__("pathlib").Path(settings.video_model).exists():
        return {"status": "MODEL_MISSING", "ready": False, "model": settings.video_model,
                "vram_total_mb": total_mb, "demo_mode": ffmpeg_available()}
    return {"status": "READY", "ready": True, "model": settings.video_model,
            "vram_total_mb": total_mb, "demo_mode": ffmpeg_available()}


def ffmpeg_available() -> bool:
    try:
        return subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5,
                              check=False, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


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
    settings = get_settings()
    model_id = settings.video_model
    ready = readiness()
    if not ready.get("ready"):
        raise RuntimeError(f"Video diffusion BLOCKED: {ready.get('status')}. {ready.get('detail', '')}".strip())
    with heavy_inference("image_to_video_diffusion"):
        release_ollama_gpu()
        from app.services import image_service
        image_service.unload_pipeline()
        release_cuda_cache()
        try:
            mark_stage("LOADING_MODEL")
            pipe = _pipeline(model_id)
            mark_stage("RUNNING")
            frames = pipe(Image.open(image_path).convert("RGB"), num_frames=num_frames).frames[0]
        except RuntimeError as exc:
            unload_pipeline()
            if "out of memory" in str(exc).lower():
                raise RuntimeError("Video diffusion hết VRAM. Tác vụ đã dừng và giải phóng cache.") from exc
            raise
        mark_stage("SAVING")
        settings.video_dir.mkdir(parents=True, exist_ok=True)
        path = settings.video_dir / f"video_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        export_to_video(frames, str(path), fps=fps)
    logger.info("video generated path=%s frames=%d fps=%d seconds=%.2f", path.name, len(frames), fps, monotonic() - started)
    return {"path": str(path), "frames": len(frames), "fps": fps, "model": model_id,
            "mode": "stable_video_diffusion", "generation_seconds": round(monotonic() - started, 2)}


def create_motion_demo(image_path: str, num_frames: int, fps: int) -> dict:
    """Create a clearly labelled non-generative Ken Burns MP4 with FFmpeg."""
    if not ffmpeg_available():
        raise RuntimeError("FFmpeg chưa sẵn sàng cho chế độ motion demo.")
    started = monotonic()
    settings = get_settings()
    settings.video_dir.mkdir(parents=True, exist_ok=True)
    path = settings.video_dir / f"motion_demo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
    zoompan = ("scale=1280:720:force_original_aspect_ratio=decrease,"
               "pad=1280:720:(ow-iw)/2:(oh-ih)/2,"
               f"zoompan=z='min(max(zoom,pzoom)+0.002,1.12)':d=1:s=1280x720:fps={fps},format=yuv420p")
    command = ["ffmpeg", "-y", "-loop", "1", "-i", image_path, "-vf", zoompan,
               "-frames:v", str(num_frames), "-c:v", "libx264", "-movflags", "+faststart", str(path)]
    completed = subprocess.run(command, capture_output=True, text=True, timeout=300, check=False,
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if completed.returncode != 0 or not path.exists() or path.stat().st_size == 0:
        path.unlink(missing_ok=True)
        raise RuntimeError(f"FFmpeg motion demo thất bại: {completed.stderr[-500:]}")
    return {"path": str(path), "frames": num_frames, "fps": fps,
            "mode": "ken_burns_motion_demo_not_diffusion",
            "generation_seconds": round(monotonic() - started, 2)}

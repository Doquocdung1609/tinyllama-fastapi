"""Optional image-to-video generation using a locally installed SVD pipeline."""
from datetime import datetime
from functools import lru_cache
from time import monotonic
import logging
import importlib.util
import shutil
import subprocess
from app.config import get_settings
from app.services.inference_manager import (heavy_inference, mark_stage, release_cuda_cache,
                                            release_ollama_gpu)
logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _pipeline(model_id: str):
    import torch
    from diffusers import StableVideoDiffusionPipeline
    pipe = StableVideoDiffusionPipeline.from_pretrained(
        model_id, torch_dtype=torch.float16, variant="fp16", local_files_only=True)
    pipe.enable_model_cpu_offload()
    pipe.unet.enable_forward_chunking()
    return pipe


def unload_pipeline() -> None:
    _pipeline.cache_clear()
    release_cuda_cache()


def readiness() -> dict:
    settings = get_settings()
    missing = [name for name in ("torch", "diffusers", "imageio_ffmpeg")
               if importlib.util.find_spec(name) is None]
    if missing:
        return {"status": "DEPENDENCY_MISSING", "ready": False, "missing": missing,
                "model": settings.video_model, "demo_mode": ffmpeg_available(), **_capabilities()}
    import torch
    if not torch.cuda.is_available():
        return {"status": "CUDA_UNAVAILABLE", "ready": False, "model": settings.video_model,
                "demo_mode": ffmpeg_available(), **_capabilities()}
    total_mb = round(torch.cuda.get_device_properties(0).total_memory / 1024**2)
    try:
        import psutil
        ram_total_gb = round(psutil.virtual_memory().total / 1024**3, 1)
        ram_available_gb = round(psutil.virtual_memory().available / 1024**3, 1)
    except ImportError:
        ram_total_gb = ram_available_gb = None
    disk_free_gb = round(shutil.disk_usage(get_settings().video_dir).free / 1024**3, 1)
    try:
        from huggingface_hub import try_to_load_from_cache
        cached = try_to_load_from_cache(settings.video_model, "model_index.json")
    except Exception:
        cached = None
    model_installed = bool(cached or __import__("pathlib").Path(settings.video_model).exists())
    blockers = []
    if total_mb < 8192:
        blockers.append("HARDWARE_VRAM")
    if ram_total_gb is not None and ram_total_gb < 16:
        blockers.append("HARDWARE_RAM")
    if not model_installed:
        blockers.append("MODEL_NOT_AVAILABLE")
    if blockers:
        return {"status": "BLOCKED", "ready": False, "blockers": blockers,
                "model": settings.video_model, "model_installed": model_installed,
                "vram_total_mb": total_mb, "recommended_vram_mb": 8192,
                "ram_total_gb": ram_total_gb, "ram_available_gb": ram_available_gb,
                "recommended_ram_gb": 16, "disk_free_gb": disk_free_gb,
                "detail": "SVD-XT chưa an toàn trên cấu hình 4 GB VRAM / 8 GB RAM; không tải checkpoint hoặc thử OOM.",
                "demo_mode": ffmpeg_available(), **_capabilities()}
    return {"status": "READY", "ready": True, "model": settings.video_model,
            "model_installed": True, "vram_total_mb": total_mb, "ram_total_gb": ram_total_gb,
            "disk_free_gb": disk_free_gb, "demo_mode": ffmpeg_available(), **_capabilities()}


def _capabilities() -> dict:
    return {"backend": "StableVideoDiffusionPipeline", "genuine_diffusion": True,
            "conditioning": "input_image", "text_prompt_supported": False,
            "native_resolution": "1024x576", "trained_frames": 25,
            "supported_controls": ["seed", "num_frames", "fps", "motion_bucket_id",
                                   "noise_aug_strength", "decode_chunk_size"],
            "motion_demo_backend": "ffmpeg_ken_burns", "motion_demo_generative": False}


def ffmpeg_available() -> bool:
    try:
        return subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5,
                              check=False, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def generate_video(image_path: str, num_frames: int, fps: int, seed: int = 42,
                   motion_bucket_id: int = 127, noise_aug_strength: float = .02,
                   decode_chunk_size: int = 2) -> dict:
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
            image = Image.open(image_path).convert("RGB").resize((1024, 576))
            torch.cuda.reset_peak_memory_stats()
            generator = torch.manual_seed(seed)
            frames = pipe(image, num_frames=num_frames, fps=fps,
                          motion_bucket_id=motion_bucket_id,
                          noise_aug_strength=noise_aug_strength,
                          decode_chunk_size=decode_chunk_size,
                          generator=generator).frames[0]
            peak_vram_mb = round(torch.cuda.max_memory_allocated() / 1024**2)
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
            "mode": "stable_video_diffusion_genuine", "generation_seconds": round(monotonic() - started, 2),
            "seed": seed, "motion_bucket_id": motion_bucket_id,
            "noise_aug_strength": noise_aug_strength, "decode_chunk_size": decode_chunk_size,
            "input_resolution": "1024x576", "peak_vram_mb": peak_vram_mb,
            "text_prompt_used": False}


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

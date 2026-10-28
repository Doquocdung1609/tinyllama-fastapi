"""Serialize heavyweight local inference and report real resource usage."""
from contextlib import contextmanager
from datetime import datetime, timezone
import gc
import subprocess
import threading
from time import perf_counter
from typing import Iterator


class ResourceBusyError(RuntimeError):
    pass


_heavy_lock = threading.Lock()
_state_lock = threading.Lock()
_state = {"status": "IDLE", "kind": None, "queued": 0, "last_job": None}
_max_waiting = 2


def _memory_snapshot() -> dict:
    result = {"ram_used_mb": None, "ram_available_mb": None, "vram_used_mb": None,
              "vram_free_mb": None, "gpu_utilization_percent": None}
    try:
        import psutil
        memory = psutil.virtual_memory()
        result.update({"ram_used_mb": round(memory.used / 1024**2),
                       "ram_available_mb": round(memory.available / 1024**2)})
    except ImportError:
        pass
    try:
        completed = subprocess.run([
            "nvidia-smi", "--query-gpu=memory.used,memory.free,utilization.gpu",
            "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=5,
            check=False, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if completed.returncode == 0 and completed.stdout.strip():
            used, free, utilization = [float(value.strip()) for value in completed.stdout.splitlines()[0].split(",")]
            result.update({"vram_used_mb": round(used), "vram_free_mb": round(free),
                           "gpu_utilization_percent": round(utilization, 1)})
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    return result


def mark_stage(stage: str) -> None:
    with _state_lock:
        _state["status"] = stage


def state() -> dict:
    with _state_lock:
        return {**_state, "resources": _memory_snapshot()}


def release_cuda_cache() -> None:
    gc.collect()
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()
    except (ImportError, RuntimeError):
        pass


def release_ollama_gpu() -> None:
    # These are the models configured and intentionally controlled by this app.
    try:
        from app.config import get_settings
        from app.services.ollama_service import unload_model
        settings = get_settings()
        unload_model(settings.ollama_model)
        # Ollama's embedding endpoint handles residency independently. A short
        # empty embedding request with keep_alive=0 is not portable, so leave it
        # alone unless it is currently inactive naturally.
    except Exception:
        pass


def release_diffusion_gpu() -> None:
    """Compatibility hook for retained RAG/Ollama scheduling."""
    release_cuda_cache()


@contextmanager
def heavy_inference(kind: str) -> Iterator[dict]:
    """Bound and serialize the retained local inference queue."""
    with _state_lock:
        if int(_state["queued"]) >= _max_waiting:
            raise ResourceBusyError("Hàng đợi tác vụ nặng đã đầy. Hãy thử lại sau khi tác vụ hiện tại hoàn tất.")
        _state["queued"] = int(_state["queued"]) + 1
        _state["status"] = "QUEUED"
    acquired = False
    started = perf_counter()
    before = _memory_snapshot()
    try:
        acquired = _heavy_lock.acquire(timeout=1800)
        if not acquired:
            raise ResourceBusyError("Tác vụ chờ GPU quá 30 phút và đã dừng an toàn.")
        with _state_lock:
            _state.update({"status": "LOADING_MODEL", "kind": kind,
                           "started_at": datetime.now(timezone.utc).isoformat()})
        yield {"before": before}
        after = _memory_snapshot()
        record = {"kind": kind, "status": "COMPLETED",
                  "wall_seconds": round(perf_counter() - started, 2),
                  "before": before, "after": after,
                  "finished_at": datetime.now(timezone.utc).isoformat()}
        with _state_lock:
            _state["last_job"] = record
            _state["status"] = "COMPLETED"
    except Exception as exc:
        with _state_lock:
            _state["last_job"] = {"kind": kind, "status": "FAILED",
                                  "wall_seconds": round(perf_counter() - started, 2),
                                  "error": str(exc), "before": before,
                                  "after": _memory_snapshot()}
            _state["status"] = "FAILED"
        raise
    finally:
        with _state_lock:
            _state["queued"] = max(0, int(_state["queued"]) - 1)
            _state["kind"] = None
        if acquired:
            _heavy_lock.release()

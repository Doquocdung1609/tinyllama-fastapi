"""Short-lived, truthful runtime diagnostics for Dashboard and System tabs."""
from importlib.metadata import PackageNotFoundError, version
import platform
import shutil
import subprocess
import sys
import threading
from time import monotonic

from app.config import ROOT_DIR, get_settings
from app.services import embedding_service, qdrant_service
from app.services.ollama_service import ollama_status

_cache: tuple[float, dict] | None = None
_lock = threading.Lock()


def _version(name: str) -> str:
    try:
        return version(name)
    except PackageNotFoundError:
        return "not installed"


def _gpu_info() -> dict:
    gpu = {"cuda_available": False, "name": None, "driver_version": None,
           "memory_total_mb": None, "memory_free_mb": None, "memory_used_mb": None,
           "utilization_percent": None, "compute_capability": None,
           "torch": _version("torch"), "torch_cuda": None}
    try:
        completed = subprocess.run([
            "nvidia-smi", "--query-gpu=name,driver_version,memory.total,memory.free,memory.used,utilization.gpu,compute_cap",
            "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=5,
            check=False, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if completed.returncode == 0 and completed.stdout.strip():
            values = [value.strip() for value in completed.stdout.splitlines()[0].split(",")]
            gpu.update({"name": values[0], "driver_version": values[1],
                        "memory_total_mb": round(float(values[2])), "memory_free_mb": round(float(values[3])),
                        "memory_used_mb": round(float(values[4])), "utilization_percent": float(values[5]),
                        "compute_capability": values[6]})
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    try:
        import torch
        gpu["cuda_available"] = torch.cuda.is_available()
        gpu["torch_cuda"] = torch.version.cuda
        if gpu["cuda_available"] and not gpu["name"]:
            gpu["name"] = torch.cuda.get_device_name(0)
            gpu["memory_total_mb"] = round(torch.cuda.get_device_properties(0).total_memory / 1024**2)
    except ImportError:
        gpu["note"] = "PyTorch chưa cài; Ollama dùng runtime riêng."
    return gpu


def _ffmpeg() -> dict:
    try:
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, timeout=5,
                                check=False, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        first = result.stdout.splitlines()[0] if result.stdout else ""
        return {"available": result.returncode == 0, "version": first}
    except (OSError, subprocess.SubprocessError):
        return {"available": False, "version": None}


def status(force: bool = False) -> dict:
    global _cache
    now = monotonic()
    with _lock:
        if not force and _cache and now - _cache[0] < 8:
            return dict(_cache[1])
        settings = get_settings()
        try:
            import psutil
            memory = psutil.virtual_memory()
            cpu = {"model": platform.processor(), "physical_cores": psutil.cpu_count(logical=False),
                   "logical_threads": psutil.cpu_count(logical=True), "utilization_percent": psutil.cpu_percent(.1)}
            ram = {"total_gb": round(memory.total / 1024**3, 1),
                   "available_gb": round(memory.available / 1024**3, 1),
                   "used_percent": memory.percent}
        except ImportError:
            cpu, ram = {"model": platform.processor()}, {"total_gb": None, "available_gb": None}
        disk = shutil.disk_usage(ROOT_DIR)
        result = {"python": sys.version.split()[0], "fastapi": _version("fastapi"),
                  "streamlit": _version("streamlit"), "ollama": ollama_status(),
                  "model": settings.ollama_model, "qdrant": qdrant_service.collection_status(),
                  "embedding": embedding_service.embedding_info(), "gpu": _gpu_info(),
                  "cpu": cpu, "ram": ram, "ram_gb": ram.get("total_gb"),
                  "disk": {"path": str(ROOT_DIR.drive or ROOT_DIR),
                           "total_gb": round(disk.total / 1024**3, 1),
                           "free_gb": round(disk.free / 1024**3, 1)},
                  }
        # Start the TTL after collection completes. On a memory-constrained host,
        # loading torch or querying a busy Ollama can itself exceed the TTL.
        _cache = (monotonic(), result)
        return dict(result)

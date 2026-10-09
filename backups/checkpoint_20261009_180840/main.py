"""FastAPI entry point. Run with: uvicorn main:app --reload"""
from pathlib import Path
import logging
import platform
import sys
from contextlib import asynccontextmanager
from importlib.metadata import version, PackageNotFoundError
from uuid import uuid4
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.config import get_settings
from app.models import ChatRequest, NormalizeRequest, ScriptRequest, ScriptResponse, TTSRequest, ImageGenerationRequest
from app.api.documents import router as documents_router
from app.api.rag import router as rag_router
from app.api.qdrant import router as qdrant_router
from app.services.ollama_service import chat, ollama_status, process_script
from app.services import qdrant_service, rag_service, embedding_service, tts_service, image_service, video_service

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("genai")
settings = get_settings()
settings.prepare_dirs()


@asynccontextmanager
async def lifespan(_app):
    rag_service.load_saved_documents()
    yield


app = FastAPI(title="GenAI Learning Studio", description="Talk to Documents (RAG) với FastAPI, Qdrant và Ollama Llama 3", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(documents_router)
app.include_router(rag_router)
app.include_router(qdrant_router)
app.mount("/audio", StaticFiles(directory=str(settings.audio_dir)), name="audio")
app.mount("/images", StaticFiles(directory=str(settings.image_dir)), name="images")
app.mount("/videos", StaticFiles(directory=str(settings.video_dir)), name="videos")


@app.get("/")
def home():
    return {"message": "GenAI Learning Studio API is running", "docs": "/docs", "model": settings.ollama_model}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/system/status")
def system_status():
    ollama = ollama_status()
    qdrant = qdrant_service.collection_status()
    embedding = embedding_service.embedding_info()
    gpu = {"cuda_available": False, "name": None, "memory_total_mb": None}
    try:
        import torch
        gpu["cuda_available"] = torch.cuda.is_available()
        if gpu["cuda_available"]:
            gpu["name"] = torch.cuda.get_device_name(0)
            gpu["memory_total_mb"] = round(torch.cuda.get_device_properties(0).total_memory / 1024**2)
    except ImportError:
        gpu["note"] = "PyTorch chưa cài; CUDA cho mô hình ảnh/video chưa được kiểm tra. Ollama độc lập với PyTorch."
    try:
        import psutil
        memory = round(psutil.virtual_memory().total / 1024**3, 1)
        cpu = platform.processor()
    except ImportError:
        memory, cpu = None, platform.processor()
    try:
        streamlit_version = version("streamlit")
    except PackageNotFoundError:
        streamlit_version = "not installed"
    try:
        fastapi_version = version("fastapi")
    except PackageNotFoundError:
        fastapi_version = "not installed"
    return {"python": sys.version.split()[0], "fastapi": fastapi_version, "streamlit": streamlit_version, "ollama": ollama,
            "model": settings.ollama_model, "qdrant": qdrant, "embedding": embedding,
            "gpu": gpu, "cpu": cpu, "ram_gb": memory}


@app.post("/chat")
def chat_endpoint(request: ChatRequest):
    try:
        return {"answer": chat(request.message, request.temperature, request.max_tokens, request.history), "model": settings.ollama_model}
    except Exception as exc:
        raise HTTPException(503, f"Không thể gọi Ollama. Hãy chạy Ollama và kiểm tra `ollama list`: {exc}") from exc


@app.post("/tts/normalize")
def normalize_tts(request: NormalizeRequest):
    try:
        return {"original_script": request.script, "processed_script": process_script(request.script)}
    except Exception as exc:
        raise HTTPException(503, f"Không thể chuẩn hóa script bằng Ollama: {exc}") from exc


@app.get("/tts/voices")
def list_tts_voices():
    return {"voices": tts_service.voices(), "default": "Windows SAPI default"}


@app.post("/tts/generate")
def generate_tts(request: TTSRequest):
    try:
        normalized = process_script(request.script) if request.normalize else request.script.strip()
        audio = tts_service.generate_audio(normalized, request.rate, request.volume, request.voice)
        return {"original_script": request.script, "processed_script": normalized,
                "audio_file": f"/audio/{Path(audio['path']).name}", "voice": audio["voice"],
                "duration_seconds": audio["duration_seconds"], "size_bytes": audio["size_bytes"]}
    except Exception as exc:
        raise HTTPException(503, f"Không thể tạo audio: {exc}") from exc


@app.post("/generate", response_model=ScriptResponse)
def legacy_generate(request: ScriptRequest):
    """Backward-compatible endpoint retained from the original project."""
    try:
        processed = process_script(request.script)
        audio = tts_service.generate_audio(processed)
        return ScriptResponse(original_script=request.script, processed_script=processed, audio_file=audio["path"])
    except Exception as exc:
        raise HTTPException(503, str(exc)) from exc


@app.post("/image/generate")
def generate_image(request: ImageGenerationRequest):
    try:
        result = image_service.generate_image(request.prompt, request.negative_prompt, request.steps,
                                              request.guidance_scale, request.width, request.height, request.seed)
        return {"image_url": f"/images/{Path(result['path']).name}", "seed": result["seed"],
                "generation_seconds": result["generation_seconds"]}
    except Exception as exc:
        if isinstance(exc, HTTPException):
            raise
        raise HTTPException(503, str(exc)) from exc


@app.post("/video/generate")
async def generate_video(file: UploadFile = File(...), num_frames: int = Form(14), fps: int = Form(7)):
    allowed_images = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in allowed_images or file.content_type != allowed_images[suffix]:
        raise HTTPException(415, "Tệp đầu vào phải là PNG hoặc JPEG.")
    if not 2 <= num_frames <= 25 or not 1 <= fps <= 30:
        raise HTTPException(422, "Số frame hoặc FPS không hợp lệ.")
    input_path = settings.upload_dir / f"video_input_{uuid4().hex}{suffix}"
    try:
        import aiofiles
        async with aiofiles.open(input_path, "wb") as output:
            size = 0
            while block := await file.read(1024 * 1024):
                size += len(block)
                if size > min(settings.max_upload_mb, 20) * 1024 * 1024:
                    raise HTTPException(413, "Ảnh đầu vào vượt giới hạn 20 MB.")
                await output.write(block)
        result = video_service.generate_video(str(input_path), num_frames, fps)
        return {**result, "video_url": f"/videos/{Path(result['path']).name}", "size_bytes": Path(result["path"]).stat().st_size}
    except Exception as exc:
        if isinstance(exc, HTTPException):
            raise
        raise HTTPException(503, str(exc)) from exc
    finally:
        input_path.unlink(missing_ok=True)
        await file.close()


@app.get("/stats")
def stats():
    docs = rag_service.documents()
    return {"documents": len(docs), "chunks": sum(d.get("chunks", 0) for d in docs),
            "audio_files": len(list(settings.audio_dir.glob("*"))), "images": len(list(settings.image_dir.glob("*"))),
            "videos": len(list(settings.video_dir.glob("*"))), "qdrant": qdrant_service.collection_status()}

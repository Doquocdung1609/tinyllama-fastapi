"""FastAPI entry point. Run with: uvicorn main:app --reload"""
from pathlib import Path
import logging
from contextlib import asynccontextmanager
from uuid import uuid4
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.config import get_settings
from app.models import ChatRequest, NormalizeRequest, ScriptRequest, ScriptResponse, TTSRequest, ImageGenerationRequest
from app.api.documents import router as documents_router
from app.api.rag import router as rag_router
from app.api.qdrant import router as qdrant_router
from app.services.ollama_service import chat, chat_stream, ollama_status, process_script
from app.services import qdrant_service, rag_service, embedding_service, tts_service, image_service, video_service
from app.services.system_service import status as runtime_status
from app.services.inference_manager import state as inference_state

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("genai")
settings = get_settings()
settings.prepare_dirs()


@asynccontextmanager
async def lifespan(_app):
    rag_service.load_saved_documents()
    yield


app = FastAPI(title="GenAI Learning Studio", description="Talk to Documents (RAG) với FastAPI, Qdrant và Ollama", version="1.1.0", lifespan=lifespan)
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
    return runtime_status()


@app.post("/chat")
def chat_endpoint(request: ChatRequest):
    try:
        model = request.model or settings.ollama_model
        return {"answer": chat(request.message, request.temperature, request.max_tokens, request.history, model), "model": model}
    except Exception as exc:
        raise HTTPException(503, f"Không thể gọi Ollama. Hãy chạy Ollama và kiểm tra `ollama list`: {exc}") from exc


@app.post("/chat/stream")
def chat_stream_endpoint(request: ChatRequest):
    return StreamingResponse(chat_stream(request.message, request.temperature, request.max_tokens,
                                         request.history, request.model), media_type="text/plain; charset=utf-8")


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
                "generation_seconds": result["generation_seconds"], "model": result.get("model"),
                "width": result.get("width"), "height": result.get("height"),
                "steps": result.get("steps"), "strategy": result.get("strategy"),
                "precision": result.get("precision")}
    except Exception as exc:
        if isinstance(exc, HTTPException):
            raise
        raise HTTPException(503, str(exc)) from exc


@app.post("/video/generate")
async def generate_video(file: UploadFile = File(...), num_frames: int = Form(14), fps: int = Form(7),
                         seed: int = Form(42), motion_bucket_id: int = Form(127),
                         noise_aug_strength: float = Form(.02), decode_chunk_size: int = Form(2)):
    allowed_images = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in allowed_images or file.content_type != allowed_images[suffix]:
        raise HTTPException(415, "Tệp đầu vào phải là PNG, JPEG hoặc WebP.")
    if (not 2 <= num_frames <= 25 or not 1 <= fps <= 30 or not 0 <= seed <= 2**32 - 1
            or not 1 <= motion_bucket_id <= 255 or not 0 <= noise_aug_strength <= 1
            or not 1 <= decode_chunk_size <= 8):
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
        result = video_service.generate_video(str(input_path), num_frames, fps, seed,
                                              motion_bucket_id, noise_aug_strength, decode_chunk_size)
        return {**result, "video_url": f"/videos/{Path(result['path']).name}", "size_bytes": Path(result["path"]).stat().st_size}
    except Exception as exc:
        if isinstance(exc, HTTPException):
            raise
        raise HTTPException(503, str(exc)) from exc
    finally:
        input_path.unlink(missing_ok=True)
        await file.close()


@app.get("/video/capabilities")
def video_capabilities():
    """Expose the real backend, controls and blockers used by the conditional UI."""
    return video_service.readiness()


@app.post("/video/demo")
async def generate_motion_demo(file: UploadFile = File(...), num_frames: int = Form(70), fps: int = Form(14)):
    """Non-generative FFmpeg motion demo, explicitly separate from diffusion."""
    allowed_images = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in allowed_images or file.content_type != allowed_images[suffix]:
        raise HTTPException(415, "Tệp đầu vào phải là PNG, JPEG hoặc WebP.")
    if not 14 <= num_frames <= 300 or not 5 <= fps <= 30:
        raise HTTPException(422, "Motion demo yêu cầu 14–300 frames và 5–30 FPS.")
    input_path = settings.upload_dir / f"motion_input_{uuid4().hex}{suffix}"
    try:
        import aiofiles
        async with aiofiles.open(input_path, "wb") as output:
            size = 0
            while block := await file.read(1024 * 1024):
                size += len(block)
                if size > min(settings.max_upload_mb, 20) * 1024 * 1024:
                    raise HTTPException(413, "Ảnh đầu vào vượt giới hạn 20 MB.")
                await output.write(block)
        result = video_service.create_motion_demo(str(input_path), num_frames, fps)
        return {**result, "video_url": f"/videos/{Path(result['path']).name}",
                "size_bytes": Path(result["path"]).stat().st_size,
                "disclaimer": "Motion demo dùng hiệu ứng Ken Burns bằng FFmpeg, không phải video diffusion."}
    except Exception as exc:
        if isinstance(exc, HTTPException):
            raise
        raise HTTPException(503, str(exc)) from exc
    finally:
        input_path.unlink(missing_ok=True)
        await file.close()


@app.get("/inference/status")
def get_inference_status():
    return inference_state()


@app.get("/stats")
def stats():
    docs = rag_service.documents()
    return {"documents": len(docs), "chunks": sum(d.get("chunks", 0) for d in docs),
            "audio_files": len(list(settings.audio_dir.glob("*"))), "images": len(list(settings.image_dir.glob("*"))),
            "videos": len(list(settings.video_dir.glob("*"))), "qdrant": qdrant_service.collection_status()}

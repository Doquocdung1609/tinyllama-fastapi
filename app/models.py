"""API schemas used by the FastAPI service."""
from typing import Any
from pydantic import BaseModel, Field
from app.config import get_settings


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: int = Field(default=512, ge=1, le=8192)
    history: list[dict[str, str]] = Field(default_factory=list)


class ChatResponse(BaseModel):
    answer: str
    model: str


class ScriptRequest(BaseModel):
    script: str = Field(min_length=1)


class ScriptResponse(BaseModel):
    original_script: str
    processed_script: str
    audio_file: str


class NormalizeRequest(BaseModel):
    script: str = Field(min_length=1)


class TTSRequest(BaseModel):
    script: str = Field(min_length=1)
    normalize: bool = True
    rate: int = Field(default=175, ge=80, le=300)
    volume: float = Field(default=1.0, ge=0, le=1)
    voice: str | None = None


class TTSResponse(BaseModel):
    original_script: str
    processed_script: str
    audio_file: str
    voice: str
    duration_seconds: float | None = None
    size_bytes: int


class RAGRequest(BaseModel):
    question: str = Field(min_length=1)
    top_k: int = Field(default_factory=lambda: get_settings().top_k, ge=1, le=20)
    score_threshold: float = Field(default_factory=lambda: get_settings().score_threshold, ge=0, le=1)
    document_id: str | None = None
    generate_answer: bool = True


class ChunkMetadata(BaseModel):
    chunk_id: str
    document_id: str
    filename: str
    page: int
    chunk_index: int
    text: str
    original_text: str
    start: int
    end: int
    overlap: int
    token_estimate: int
    vector_id: str | None = None
    embedding_status: str = "pending"
    metadata: dict[str, Any] = Field(default_factory=dict)


class DocumentStatus(BaseModel):
    document_id: str
    filename: str
    status: str
    pages: int = 0
    chunks: int = 0
    indexed_at: str | None = None
    error: str | None = None


class ImageGenerationRequest(BaseModel):
    prompt: str = Field(min_length=1)
    negative_prompt: str = ""
    steps: int = Field(default=25, ge=1, le=100)
    guidance_scale: float = Field(default=7.5, ge=1, le=20)
    width: int = Field(default=512, ge=256, le=1024, multiple_of=8)
    height: int = Field(default=512, ge=256, le=1024, multiple_of=8)
    seed: int | None = None


class VideoGenerationRequest(BaseModel):
    image_path: str
    num_frames: int = Field(default=14, ge=2, le=25)
    fps: int = Field(default=7, ge=1, le=30)

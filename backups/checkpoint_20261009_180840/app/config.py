"""Environment-backed application settings."""
from functools import lru_cache
import os
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT_DIR / ".env")
except ImportError:
    pass


class Settings:
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3:latest")
    embedding_provider: str = os.getenv("EMBEDDING_PROVIDER", "ollama").lower()
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
    jina_model: str = os.getenv("JINA_MODEL", "jinaai/jina-embeddings-v2-base-en")
    qdrant_url: str = os.getenv("QDRANT_URL", "").strip()
    qdrant_path: Path = Path(os.getenv("QDRANT_PATH", str(ROOT_DIR / "qdrant_data")))
    qdrant_collection: str = os.getenv("QDRANT_COLLECTION", "knowledgebase")
    upload_dir: Path = Path(os.getenv("UPLOAD_DIR", str(ROOT_DIR / "uploads")))
    processed_dir: Path = Path(os.getenv("PROCESSED_DIR", str(ROOT_DIR / "processed")))
    audio_dir: Path = Path(os.getenv("TTS_OUTPUT_DIR", str(ROOT_DIR / "audio")))
    image_dir: Path = Path(os.getenv("IMAGE_OUTPUT_DIR", str(ROOT_DIR / "images")))
    video_dir: Path = Path(os.getenv("VIDEO_OUTPUT_DIR", str(ROOT_DIR / "videos")))
    max_upload_mb: int = int(os.getenv("MAX_UPLOAD_MB", "50"))
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "800"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "120"))
    top_k: int = int(os.getenv("TOP_K", "3"))
    score_threshold: float = float(os.getenv("SCORE_THRESHOLD", "0.7"))

    def prepare_dirs(self) -> None:
        for path in (self.upload_dir, self.processed_dir, self.audio_dir, self.image_dir, self.video_dir):
            path.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

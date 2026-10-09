"""Configurable Ollama or SentenceTransformer embedding providers."""
import requests
from functools import lru_cache
from time import monotonic
from app.config import get_settings


class EmbeddingProvider:
    def embed(self, texts: list[str], progress_callback=None) -> list[list[float]]:
        raise NotImplementedError


class OllamaEmbeddingProvider(EmbeddingProvider):
    def embed(self, texts: list[str], progress_callback=None) -> list[list[float]]:
        settings = get_settings()
        if not texts:
            return []
        vectors = []
        for start in range(0, len(texts), 32):
            response = requests.post(f"{settings.ollama_base_url}/api/embed",
                json={"model": settings.embedding_model, "input": texts[start:start + 32]}, timeout=300)
            if response.status_code == 404:
                raise RuntimeError(f"Embedding model '{settings.embedding_model}' is unavailable. Pull it with: ollama pull {settings.embedding_model}")
            response.raise_for_status()
            batch = response.json().get("embeddings", [])
            if len(batch) != len(texts[start:start + 32]) or not batch or not batch[0]:
                raise RuntimeError(f"Embedding model '{settings.embedding_model}' returned invalid vectors. Check the Ollama embedding model.")
            vectors.extend(batch)
            if progress_callback:
                progress_callback(len(vectors), len(texts))
        return vectors


class SentenceTransformerProvider(EmbeddingProvider):
    def __init__(self, model_name: str):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError("sentence-transformers is missing. Install optional requirements-embeddings.txt") from exc
        self.model = SentenceTransformer(model_name)

    def embed(self, texts: list[str], progress_callback=None) -> list[list[float]]:
        result = self.model.encode(texts, normalize_embeddings=True).tolist()
        if progress_callback:
            progress_callback(len(result), len(texts))
        return result


@lru_cache(maxsize=2)
def get_embedding_provider() -> EmbeddingProvider:
    settings = get_settings()
    if settings.embedding_provider in {"jina", "huggingface", "sentence-transformers"}:
        model = settings.jina_model if settings.embedding_provider == "jina" else settings.embedding_model
        return SentenceTransformerProvider(model)
    return OllamaEmbeddingProvider()


_embedding_info_cache: tuple[float, dict] | None = None


def embedding_info() -> dict:
    global _embedding_info_cache
    now = monotonic()
    if _embedding_info_cache and now - _embedding_info_cache[0] < 120:
        return dict(_embedding_info_cache[1])
    settings = get_settings()
    try:
        vector = get_embedding_provider().embed(["dimension probe"])[0]
        result = {"provider": settings.embedding_provider, "model": settings.jina_model if settings.embedding_provider == "jina" else settings.embedding_model,
                  "dimension": len(vector), "available": True}
    except Exception as exc:
        result = {"provider": settings.embedding_provider, "model": settings.embedding_model, "dimension": None,
                  "available": False, "error": str(exc)}
    _embedding_info_cache = (now, result)
    return dict(result)

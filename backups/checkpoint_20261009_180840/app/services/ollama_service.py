"""Small HTTP client for the local Ollama API."""
import requests
import logging
from app.config import get_settings

logger = logging.getLogger(__name__)


def ollama_status() -> dict:
    settings = get_settings()
    try:
        response = requests.get(f"{settings.ollama_base_url}/api/tags", timeout=3)
        response.raise_for_status()
        tags = response.json().get("models", [])
        names = [item.get("name", "") for item in tags]
        processes = []
        gpu_vram_bytes = 0
        try:
            process_response = requests.get(f"{settings.ollama_base_url}/api/ps", timeout=3)
            process_response.raise_for_status()
            processes = process_response.json().get("models", [])
            gpu_vram_bytes = sum(int(item.get("size_vram", 0) or 0) for item in processes)
        except (requests.RequestException, ValueError, TypeError):
            pass
        return {"online": True, "model": settings.ollama_model, "model_available": settings.ollama_model in names,
                "models": names, "running_models": processes, "gpu_vram_bytes": gpu_vram_bytes}
    except requests.RequestException as exc:
        return {"online": False, "model": settings.ollama_model, "model_available": False, "error": str(exc)}


def generate(prompt: str, temperature: float = 0.2, max_tokens: int = 1024) -> str:
    settings = get_settings()
    logger.info("ollama generation started model=%s prompt_chars=%d", settings.ollama_model, len(prompt))
    response = requests.post(f"{settings.ollama_base_url}/api/generate", json={
        "model": settings.ollama_model, "prompt": prompt, "stream": False,
        "options": {"temperature": temperature, "num_predict": max_tokens},
    }, timeout=300)
    response.raise_for_status()
    answer = response.json().get("response", "").strip()
    if not answer:
        raise RuntimeError("Ollama returned an empty response")
    logger.info("ollama generation completed model=%s response_chars=%d", settings.ollama_model, len(answer))
    return answer


def chat(message: str, temperature: float = 0.7, max_tokens: int = 512,
         history: list[dict[str, str]] | None = None) -> str:
    turns = []
    for item in (history or [])[-12:]:
        role = "Assistant" if item.get("role") == "assistant" else "User"
        content = item.get("content", "").strip()
        if content:
            turns.append(f"{role}: {content}")
    turns.append(f"User: {message}\nAssistant:")
    prompt = "Continue this conversation naturally.\n\n" + "\n".join(turns)
    return generate(prompt, temperature, max_tokens)


def process_script(script: str) -> str:
    prompt = ("You are an English speaking assistant. Prepare the English script for text-to-speech. "
              "Preserve its meaning, correct grammar and punctuation, make it natural and easy to pronounce. "
              "Do not add information or explain changes. Return only the final script.\n\n" + script)
    return generate(prompt, temperature=0.2, max_tokens=2048)

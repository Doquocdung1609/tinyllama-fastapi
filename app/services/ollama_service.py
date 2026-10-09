"""Small HTTP client for the local Ollama API."""
import requests
import logging
import json
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
    from app.services.inference_manager import heavy_inference, mark_stage, release_diffusion_gpu
    settings = get_settings()
    logger.info("ollama generation started model=%s prompt_chars=%d", settings.ollama_model, len(prompt))
    with heavy_inference("ollama_generation"):
        release_diffusion_gpu()
        mark_stage("RUNNING")
        response = requests.post(f"{settings.ollama_base_url}/api/generate", json={
            "model": settings.ollama_model, "prompt": prompt, "stream": False,
            "keep_alive": "5m", "options": {"temperature": temperature, "num_predict": max_tokens,
                                              "num_ctx": 4096},
        }, timeout=300)
        response.raise_for_status()
        answer = response.json().get("response", "").strip()
    if not answer:
        raise RuntimeError("Ollama returned an empty response")
    logger.info("ollama generation completed model=%s response_chars=%d", settings.ollama_model, len(answer))
    return answer


def _chat_prompt(message: str, history: list[dict[str, str]] | None = None,
                 context_chars: int = 12000) -> str:
    turns = []
    used = 0
    selected = []
    for item in reversed((history or [])[-20:]):
        role = "Assistant" if item.get("role") == "assistant" else "User"
        content = item.get("content", "").strip()
        cost = len(content) + len(role) + 3
        if content and used + cost <= context_chars:
            selected.append((role, content))
            used += cost
    for role, content in reversed(selected):
        turns.append(f"{role}: {content}")
    turns.append(f"User: {message}\nAssistant:")
    return ("Continue this conversation naturally. Reply in the same language as the user's latest message. "
            "When the user writes Vietnamese, answer in Vietnamese.\n\n" + "\n".join(turns))


def generate_stream(prompt: str, temperature: float = 0.7, max_tokens: int = 512):
    from app.services.inference_manager import heavy_inference, mark_stage, release_diffusion_gpu
    settings = get_settings()
    with heavy_inference("ollama_stream"):
        release_diffusion_gpu()
        mark_stage("RUNNING")
        with requests.post(f"{settings.ollama_base_url}/api/generate", json={
            "model": settings.ollama_model, "prompt": prompt, "stream": True, "keep_alive": "5m",
            "options": {"temperature": temperature, "num_predict": max_tokens, "num_ctx": 4096},
        }, timeout=(10, 300), stream=True) as response:
            response.raise_for_status()
            for line in response.iter_lines(decode_unicode=True):
                if not line:
                    continue
                chunk = json.loads(line).get("response", "")
                if chunk:
                    yield chunk


def chat(message: str, temperature: float = 0.7, max_tokens: int = 512,
         history: list[dict[str, str]] | None = None) -> str:
    return generate(_chat_prompt(message, history), temperature, max_tokens)


def chat_stream(message: str, temperature: float = 0.7, max_tokens: int = 512,
                history: list[dict[str, str]] | None = None):
    yield from generate_stream(_chat_prompt(message, history), temperature, max_tokens)


def unload_model(model_name: str) -> bool:
    """Ask Ollama to release an application-owned model from memory."""
    settings = get_settings()
    try:
        response = requests.post(f"{settings.ollama_base_url}/api/generate",
                                 json={"model": model_name, "keep_alive": 0}, timeout=20)
        return response.ok
    except requests.RequestException:
        return False


def process_script(script: str) -> str:
    prompt = ("You are an English speaking assistant. Prepare the English script for text-to-speech. "
              "Preserve its meaning, correct grammar and punctuation, make it natural and easy to pronounce. "
              "Do not add information or explain changes. Return only the final script.\n\n" + script)
    return generate(prompt, temperature=0.2, max_tokens=2048)

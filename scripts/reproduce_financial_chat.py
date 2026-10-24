"""Two-prompt, ungrounded local Chat reproduction; not a financial accuracy eval."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import requests
from app.config import get_settings
from app.services.ollama_service import _chat_prompt


def reproduce(output: Path) -> dict:
    settings = get_settings()
    question = "Explain the purpose of a balance sheet in one sentence."
    prompts = {"plain_generate": question, "application_chat_wrapper": _chat_prompt(question, [])}
    result = {"timestamp_utc": datetime.now(timezone.utc).isoformat(), "question": question,
              "retrieval_called": False, "source_context_supplied": False,
              "history": [], "cases": [],
              "scope": "Ungrounded general chat. Human assessment required; two answers do not establish accuracy."}
    tags = requests.get(settings.ollama_base_url + "/api/tags", timeout=10)
    tags.raise_for_status()
    result["model_inventory"] = tags.json()
    for name, prompt in prompts.items():
        body = {"model": settings.ollama_model, "prompt": prompt, "stream": False,
                "keep_alive": "5m", "options": {"temperature": 0, "num_predict": 80, "num_ctx": 4096}}
        print(f"Running {name}", flush=True)
        response = requests.post(settings.ollama_base_url + "/api/generate", json=body, timeout=300)
        response.raise_for_status()
        result["cases"].append({"name": name, "request": body, "response": response.json()})
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    for case in reproduce(args.output)["cases"]:
        print(json.dumps({"name": case["name"], "response": case["response"]["response"]}, ensure_ascii=True))

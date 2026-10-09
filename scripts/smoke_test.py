"""Non-destructive local smoke test for backend, UI and eight-tab contract."""
from __future__ import annotations
import argparse
import ast
import json
import sys
from pathlib import Path
import re
import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_TABS = ["Dashboard", "Chat với Llama 3", "Talk to Documents / RAG", "Chunk Explorer",
                 "English Script → Audio", "Text → Image", "Image → Video", "System / GPU"]


def request_ok(url: str, timeout: int = 15):
    started = __import__("time").perf_counter()
    try:
        response = requests.get(url, timeout=timeout)
        return response.ok, round((__import__("time").perf_counter() - started) * 1000, 1), response.status_code
    except requests.RequestException:
        return False, round((__import__("time").perf_counter() - started) * 1000, 1), None


def declared_tabs() -> list[str]:
    tree = ast.parse((ROOT / "client.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "PAGES" for t in node.targets):
            return ast.literal_eval(node.value)
    return []


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", default="http://127.0.0.1:8000")
    parser.add_argument("--ui", default="http://127.0.0.1:8501")
    args = parser.parse_args()
    checks = {}
    checks["fastapi"], checks["fastapi_ms"], checks["fastapi_code"] = request_ok(args.api + "/health")
    checks["streamlit"], checks["streamlit_ms"], checks["streamlit_code"] = request_ok(args.ui)
    tabs = declared_tabs()
    checks["eight_tabs"] = tabs == EXPECTED_TABS
    checks["tabs"] = tabs
    try:
        status = requests.get(args.api + "/system/status", timeout=30).json()
        checks["ollama"] = bool(status.get("ollama", {}).get("online"))
        checks["qdrant"] = bool(status.get("qdrant", {}).get("online"))
        checks["embedding"] = bool(status.get("embedding", {}).get("available"))
        checks["image_status"] = status.get("image", {}).get("status")
        checks["video_status"] = status.get("video", {}).get("status")
    except (requests.RequestException, ValueError):
        checks.update({"ollama": False, "qdrant": False, "embedding": False})
    passed = all(checks.get(name) for name in ("fastapi", "streamlit", "eight_tabs", "ollama", "qdrant", "embedding"))
    checks["passed"] = passed
    print(json.dumps(checks, ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Inspect the real Windows runtime without printing .env values."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.system_service import status  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument("--api", default="http://127.0.0.1:8000",
                        help="Running API used to avoid opening embedded Qdrant twice")
    args = parser.parse_args()
    try:
        response = requests.get(args.api.rstrip("/") + "/system/status", timeout=30)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException:
        data = status(force=True)
    text = json.dumps(data, ensure_ascii=False, indent=2)
    print(text)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    required = (data.get("ollama", {}).get("online"), data.get("qdrant", {}).get("online"),
                data.get("embedding", {}).get("available"))
    return 0 if all(required) else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Read-only local service and six-page contract check; browser evidence is separate."""
from __future__ import annotations
import argparse
import ast
import json
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]
PAGES = ["Tổng quan", "Tìm kiếm tài chính", "Phân tích tài chính AI", "Kho tài liệu",
         "So sánh truy xuất", "Hệ thống & cài đặt"]


def declared_pages():
    tree = ast.parse((ROOT / "product_ui.py").read_text(encoding="utf-8"))
    return next(ast.literal_eval(node.value) for node in tree.body
                if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "PAGES"
                                                     for t in node.targets))


def probe(url):
    try:
        response = requests.get(url, timeout=10)
        return {"status": response.status_code, "reachable": response.ok}
    except requests.RequestException as exc:
        return {"status": None, "reachable": False, "error": type(exc).__name__}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", default="http://127.0.0.1:8000")
    parser.add_argument("--ui", default="http://127.0.0.1:8501")
    args = parser.parse_args()
    result = {"api": probe(args.api + "/health"), "ui": probe(args.ui),
              "pages": declared_pages(), "page_contract": declared_pages() == PAGES,
              "note": "HTTP and source contract only; use browser for interaction verification"}
    result["passed"] = result["api"]["reachable"] and result["ui"]["reachable"] and result["page_contract"]
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

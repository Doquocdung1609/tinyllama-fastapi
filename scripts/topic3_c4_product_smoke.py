"""Run bounded local PR35 HPG/BIDV search and unsupported-answer demo checks."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import time
from urllib.parse import urlparse

import requests


CASES = [
    ("HPG_SCANNED_Q4_2025", "4a92af827aaf1e73e017544d0ff20d0d",
     "Doanh thu thuần quý 4 năm 2025 của Hòa Phát là bao nhiêu?"),
    ("BIDV_REVISED_2024", "2bed2b3c312c8149e6a2ff6ab80c694a",
     "BIDV điều chỉnh báo cáo tài chính hợp nhất năm 2024 theo kết quả KTNN như thế nào?"),
]
EXPECTED_SHA = {
    CASES[0][1]: "4a92af827aaf1e73e017544d0ff20d0d14ae4d368bd9c90d5d6d60a28af8b447",
    CASES[1][1]: "2bed2b3c312c8149e6a2ff6ab80c694a4c710e82f65b1c35a1a943eae4fa32a6",
}


def run(base: str, token_path: Path, out: Path) -> dict:
    if out.exists():
        raise FileExistsError(out)
    parsed = urlparse(base)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"}:
        raise ValueError("Demo smoke only accepts a loopback product API")
    token = token_path.read_text(encoding="utf-8").strip()
    if len(token) < 16:
        raise ValueError("Missing local product token")
    session = requests.Session()
    session.headers["Authorization"] = f"Bearer {token}"
    documents_response = session.get(base + "/studio/documents", timeout=15)
    documents_response.raise_for_status()
    documents = {row["id"]: row for row in documents_response.json()["documents"]}
    for _, document_id, _ in CASES:
        if (document_id not in documents or documents[document_id]["status"] != "READY" or
                documents[document_id]["sha256"] != EXPECTED_SHA[document_id]):
            raise ValueError("Ready document identity/hash changed")
    checks = []
    for name, document_id, question in CASES:
        for mode in ("bm25", "dense", "hybrid"):
            started = time.perf_counter()
            response = session.post(
                base + "/studio/search",
                json={"query": question, "mode": mode, "top_k": 5,
                      "document_ids": [document_id]}, timeout=90)
            elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
            payload = response.json()
            checks.append({
                "case": name, "mode": mode, "http_status": response.status_code,
                "elapsed_wall_ms": elapsed_ms,
                "response_shape": sorted(payload),
                "response_sha256": sha256(response.content).hexdigest(),
                "response": payload,
            })
    question = "Từ báo cáo Hòa Phát này, lợi nhuận sau thuế hợp nhất quý 4 năm 2025 là bao nhiêu?"
    started = time.perf_counter()
    response = session.post(base + "/studio/chat", json={
        "question": question, "document_ids": [CASES[0][1]]}, timeout=120)
    checks.append({
        "case": "HPG_UNSUPPORTED_CONSOLIDATED_NUMBER",
        "mode": "chat", "http_status": response.status_code,
        "elapsed_wall_ms": round((time.perf_counter() - started) * 1000, 2),
        "response_sha256": sha256(response.content).hexdigest(),
        "response": response.json(),
    })
    report = {
        "schema": "c4_pr35_local_product_smoke/v1",
        "product_source": "PR35_DETACHED_WORKTREE",
        "base": base,
        "document_sha256": {key: EXPECTED_SHA[key] for key in sorted(EXPECTED_SHA)},
        "checks": checks,
        "token_logged": False,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")
    print(json.dumps({
        "documents_ready": len(CASES),
        "search_http_statuses": [x["http_status"] for x in checks if x["mode"] != "chat"],
        "chat_http_status": checks[-1]["http_status"],
        "chat_status": checks[-1]["response"].get("status"),
        "private_report_sha256": sha256(out.read_bytes()).hexdigest(),
    }, ensure_ascii=False))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="http://127.0.0.1:18110")
    parser.add_argument("--token-path", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    run(**vars(parser.parse_args()))

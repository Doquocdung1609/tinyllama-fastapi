"""Real PR35 HPG/BIDV paired-language PDF retrieval smoke, no gold claims."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import time

import requests


CASES = (
    ("HPG_PARENT_Q4_2025", "4a92af827aaf1e73e017544d0ff20d0d",
     "Doanh thu thuần quý 4 năm 2025 của công ty mẹ Hòa Phát là bao nhiêu?",
     "What net revenue did Hoa Phat parent company report for Q4 2025?"),
    ("BIDV_REVISED_2024", "2bed2b3c312c8149e6a2ff6ab80c694a",
     "BIDV điều chỉnh báo cáo tài chính hợp nhất năm 2024 theo kết quả KTNN như thế nào?",
     "What changes did BIDV report to its 2024 consolidated financial statements following the State Audit?"),
)
EXPECTED = {
    CASES[0][1]: "4a92af827aaf1e73e017544d0ff20d0d14ae4d368bd9c90d5d6d60a28af8b447",
    CASES[1][1]: "2bed2b3c312c8149e6a2ff6ab80c694a4c710e82f65b1c35a1a943eae4fa32a6",
}


def run(base: str, token_path: Path, private_out: Path, public_out: Path) -> dict:
    if private_out.exists() or public_out.exists():
        raise FileExistsError("Paired PDF smoke already exists")
    if base != "http://127.0.0.1:18110":
        raise ValueError("Only the isolated PR35 demo API is allowed")
    token = token_path.read_text(encoding="utf-8").strip()
    if len(token) < 16:
        raise ValueError("Missing local token")
    session = requests.Session()
    session.headers["Authorization"] = "Bearer " + token
    ready = session.get(base + "/studio/documents", timeout=20).json()["documents"]
    by_id = {d["id"]: d for d in ready}
    if any(by_id[i]["sha256"] != h or by_id[i]["status"] != "READY"
           for i, h in EXPECTED.items()):
        raise ValueError("HPG/BIDV identity or READY status changed")
    rows = []
    for label, document_id, vi, en in CASES:
        for language, question in (("VI", vi), ("EN", en)):
            for mode in ("bm25", "dense", "hybrid"):
                begin = time.perf_counter()
                response = session.post(base + "/studio/search", json={
                    "query": question, "mode": mode, "top_k": 5,
                    "document_ids": [document_id]}, timeout=90)
                payload = response.json()
                rows.append({"case": label, "document_id": document_id,
                             "language": language, "question": question,
                             "mode": mode, "http_status": response.status_code,
                             "wall_ms": round((time.perf_counter()-begin)*1000, 2),
                             "response_sha256": sha256(response.content).hexdigest(),
                             "response": payload})
    private = {"schema": "c4r_pr35_real_pdf_paired_language_smoke/v1",
               "document_sha256": EXPECTED, "token_recorded": False,
               "gold_numeric_or_answer_accuracy": "NOT_EVALUATED",
               "rows": rows}
    private_out.parent.mkdir(parents=True, exist_ok=True)
    private_out.write_text(json.dumps(private, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    public = {"schema": "c4r_pr35_pdf_paired_language_summary/v1",
              "track": "PDF_PRODUCT_RETRIEVAL_SMOKE_NOT_SEC_AUTHOR_BENCHMARK",
              "documents_ready": 2, "questions_per_language": 2,
              "modes": ["bm25", "dense", "hybrid"],
              "runs": len(rows),
              "http_200": sum(r["http_status"] == 200 for r in rows),
              "five_candidates": sum(len(r["response"].get("results", [])) == 5 for r in rows),
              "top1_page_by_case_language_mode": [
                  {"case": r["case"], "language": r["language"], "mode": r["mode"],
                   "page": r["response"].get("results", [{}])[0].get("page")}
                  for r in rows],
              "numeric_gold": "NOT_CREATED_OCR_AND_RESTATEMENT_CONTEXT_REQUIRE_REVIEW",
              "private_sha256": sha256(private_out.read_bytes()).hexdigest()}
    public_out.parent.mkdir(parents=True, exist_ok=True)
    public_out.write_text(json.dumps(public, indent=2) + "\n", encoding="utf-8")
    return public


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base", default="http://127.0.0.1:18110")
    p.add_argument("--token-path", type=Path, required=True)
    p.add_argument("--private-out", type=Path, required=True)
    p.add_argument("--public-out", type=Path, required=True)
    print(json.dumps(run(**vars(p.parse_args())), indent=2))

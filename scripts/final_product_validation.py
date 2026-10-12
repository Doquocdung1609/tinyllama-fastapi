"""Run reproducible real-API checks for OCR, calculations and charts."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from time import perf_counter

import requests


CASES = [
    {"id": "OCR01", "group": "ocr", "document_ids": ["346de5ce23dd806440080956959e3ba6"],
     "question": "Doanh thu năm 2024 là bao nhiêu?", "must": ["250"], "kind": "scanned Vietnamese text"},
    {"id": "OCR02", "group": "ocr", "document_ids": ["376b7d23cb4d1ce4d79e586af77f01c3"],
     "question": "Tính tốc độ tăng trưởng doanh thu từ 2023 đến 2024.",
     "must": ["100", "180", "80%"], "kind": "scanned financial table"},
    {"id": "OCR03", "group": "ocr", "document_ids": ["286e664130f25e6c1a5bfe87f73b6354"],
     "question": "Giá trị năm 2024 trên biểu đồ là bao nhiêu?", "must": ["125"], "kind": "image-only chart"},
    {"id": "T02", "group": "financial", "document_ids": ["efa64d92ebcbb97356bc216486dc66e4"],
     "question": "Tính tốc độ tăng trưởng doanh thu từ 2023 đến 2024.", "must": ["100", "125", "25%"], "kind": "growth"},
    {"id": "T06", "group": "chart", "document_ids": ["d8451f3d524688a42a92241f492e264c"],
     "question": "So sánh đầy đủ chuỗi A và chuỗi B trên biểu đồ.",
     "must": ["Chuỗi A", "Chuỗi B", "tăng", "giảm"], "kind": "multi-series"},
    {"id": "T07", "group": "chart", "document_ids": ["c831772b97d9d406babeec323dc71b29"],
     "question": "Thành phần nào có tỷ trọng cao nhất và bằng bao nhiêu?", "must": ["Cá nhân", "50%"], "kind": "pie maximum"},
    {"id": "T14", "group": "chart", "document_ids": ["431bddd7ab6935001af357b445dd598a"],
     "question": "Đối chiếu nhãn số năm 2024 trên biểu đồ với bảng.", "must": ["125"], "kind": "chart-table"},
    {"id": "T15", "group": "refusal", "document_ids": ["431bddd7ab6935001af357b445dd598a"],
     "question": "Tài liệu có nêu tỷ giá EUR/VND năm 2030 không?", "must": [], "kind": "out-of-document"},
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", default="http://127.0.0.1:8002")
    args = parser.parse_args()
    rows, details = [], []
    for case in CASES:
        started = perf_counter()
        response = requests.post(args.api + "/rag/query", json={
            "question": case["question"], "document_ids": case["document_ids"],
            "top_k": 8, "score_threshold": 0.45, "generate_answer": True,
        }, timeout=180)
        elapsed = round((perf_counter() - started) * 1000, 1)
        payload = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
        answer = payload.get("answer", "")
        refusal = any(term in answer.casefold() for term in
                      ("không cung cấp", "không có đủ", "chưa cung cấp", "không tìm thấy"))
        passed = (response.status_code == 200 and
                  (refusal if case["group"] == "refusal" else all(value.casefold() in answer.casefold() for value in case["must"])))
        citations = payload.get("supporting_sources") or []
        rows.append({
            "case_id": case["id"], "group": case["group"], "kind": case["kind"],
            "status": "PASS" if passed else "FAIL", "question": case["question"],
            "answer": answer, "pages": ",".join(str(item.get("page", "")) for item in citations),
            "evidence_ids": ",".join(str(item.get("evidence_id", "")) for item in citations),
            "calculation_verified": bool((payload.get("calculation_validation") or {}).get("verified")),
            "citation_valid": (payload.get("citation_validation") or {}).get("citation_valid"),
            "latency_ms": elapsed,
        })
        details.append({"case": case, "http_status": response.status_code, "elapsed_ms": elapsed,
                        "passed": passed, "response": payload})
        print(case["id"], "PASS" if passed else "FAIL", answer.replace("\n", " ")[:180])

    reports = Path("reports")
    reports.mkdir(exist_ok=True)
    fields = list(rows[0])
    with (reports / "final_capability_validation.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fields); writer.writeheader(); writer.writerows(rows)
    (reports / "final_capability_validation_details.json").write_text(
        json.dumps(details, ensure_ascii=False, indent=2), encoding="utf-8")
    for filename, groups in {
        "ocr_real_inference.csv": {"ocr"},
        "scanned_pdf_rag_tests.csv": {"ocr"},
        "financial_calculation_benchmark.csv": {"financial", "ocr"},
        "chart_understanding_benchmark.csv": {"chart"},
    }.items():
        selected = [row for row in rows if row["group"] in groups]
        with (reports / filename).open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fields); writer.writeheader(); writer.writerows(selected)


if __name__ == "__main__":
    main()

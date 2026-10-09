"""Run the fixed 16-question retrieval benchmark and optionally generate priority answers."""
from __future__ import annotations
import argparse
import csv
from pathlib import Path
from time import perf_counter
import requests
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

CASES = [
    ("RAG-Q01", "Ba loại đổi mới tài chính căn cứ theo loại hình là gì?", {155}, False),
    ("RAG-Q02", "Phân biệt đổi mới công cụ và đổi mới hậu hợp đồng. Cho ví dụ.", {156}, False),
    ("RAG-Q03", "Theo cách tiếp cận chức năng, đổi mới tài chính được chia thành tám loại nào?", {156,157,158}, False),
    ("RAG-Q04", "Hai yếu tố thúc đẩy đổi mới tài chính theo tài liệu là gì?", {158}, False),
    ("RAG-Q05", "Đổi mới tài chính giúp phân bổ vốn và quản lý rủi ro như thế nào?", {160}, False),
    ("RAG-Q06", "Cho vay theo nhóm trong tài chính vi mô hoạt động dựa trên cơ chế nào và phù hợp trong môi trường nào?", {163}, False),
    ("RAG-Q07", "Việc thay thế chi nhánh bằng ATM ảnh hưởng đến chi phí vận hành ra sao?", {169,170}, False),
    ("RAG-Q08", "Chương 8 mô tả các dòng sản phẩm fintech phổ biến nào?", {181,190,191}, False),
    ("RAG-Q09", "Ngân hàng mở và API liên hệ với nhau như thế nào?", {213,214,215,216}, False),
    ("RAG-Q10", "Điện toán đám mây thay đổi mô hình dịch vụ ngân hàng như thế nào?", {224,225,226,227}, False),
    ("RAG-Q11", "Quy trình huấn luyện một mô hình học máy gồm những bước chính nào?", {233,234}, False),
    ("RAG-Q12", "Trong ví dụ Bayes, nếu 20% dân số mắc bệnh và xét nghiệm chính xác 90%, xác suất thực sự mắc bệnh khi dương tính là bao nhiêu?", {237}, False),
    ("RAG-Q13", "Những rủi ro thực tiễn nào cần cân nhắc khi áp dụng AI trong tài chính?", {246,247}, False),
    ("RAG-Q14", "Tổng hợp mối liên hệ giữa open banking, cloud và AI trong đổi mới dịch vụ ngân hàng.", {213,214,224,225,228,233}, False),
    ("RAG-Q15", "Tài liệu dự báo giá Bitcoin vào ngày 31/12/2026 là bao nhiêu?", set(), True),
    ("RAG-Q16", "Theo tài liệu, ai là Tổng thống Việt Nam năm 2026?", set(), True),
]
PRIORITY = {"RAG-Q01", "RAG-Q09", "RAG-Q12", "RAG-Q15", "RAG-Q16"}


def write_rows(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", default="http://127.0.0.1:8000")
    parser.add_argument("--document-id", required=True)
    parser.add_argument("--output", type=Path, default=Path("reports/rag_benchmark.csv"))
    parser.add_argument("--generate-priority", action="store_true")
    parser.add_argument("--generate-all", action="store_true")
    parser.add_argument("--resume-from", type=Path,
                        help="Reuse already generated answers from a prior benchmark CSV")
    parser.add_argument("--only", nargs="*", help="Run only the listed question IDs")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--threshold", type=float, default=.55)
    args = parser.parse_args(); rows = []
    previous = {}
    if args.resume_from and args.resume_from.exists():
        with args.resume_from.open(newline="", encoding="utf-8-sig") as handle:
            previous = {row["question_id"]: row for row in csv.DictReader(handle)}
    for case_id, question, expected, no_answer in CASES:
        if args.only and case_id not in set(args.only):
            continue
        generate = args.generate_all or (args.generate_priority and case_id in PRIORITY)
        reusable = previous.get(case_id)
        if generate and reusable and reusable.get("answer"):
            rows.append(reusable)
            write_rows(args.output, rows)
            print(case_id, "REUSED", reusable.get("retrieved_pages", ""),
                  f"{reusable.get('latency_seconds', '')}s")
            continue
        payload = {"question": question, "top_k": args.top_k, "score_threshold": args.threshold,
                   "document_id": args.document_id, "generate_answer": generate}
        started = perf_counter()
        response = requests.post(args.api.rstrip("/") + "/rag/query", json=payload, timeout=300)
        elapsed = perf_counter() - started
        response.raise_for_status(); data = response.json(); sources = data.get("sources", [])
        pages = [int(source["page"]) for source in sources if source.get("page") is not None]
        if no_answer:
            retrieval_pass = not pages
        else:
            retrieval_pass = any(any(abs(page - target) <= 1 for target in expected) for page in pages)
        answer = data.get("answer", "")
        refusal_pass = ("không cung cấp đủ thông tin" in answer.casefold() or
                        "do not provide enough information" in answer.casefold()) if no_answer and generate else ""
        rows.append({"question_id": case_id, "top_k": args.top_k, "threshold": args.threshold,
                     "top_similarity_score": round(float(sources[0]["score"]), 4) if sources else "",
                     "retrieved_pages": ",".join(map(str, pages)), "retrieval_pass": retrieval_pass,
                     "answer_generated": generate, "answer": answer.replace("\n", " ")[:1000],
                     "correctness_score": "", "refusal_pass": refusal_pass,
                     "latency_seconds": round(elapsed, 3), "status": "PASS" if retrieval_pass else "FAIL"})
        print(case_id, rows[-1]["status"], pages, f"{elapsed:.2f}s")
        write_rows(args.output, rows)
    print(args.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

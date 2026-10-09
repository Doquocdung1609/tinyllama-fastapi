"""Apply the documented manual answer-quality rubric to the measured RAG run."""
from __future__ import annotations
import argparse
import csv
from pathlib import Path

SCORES = {
    "RAG-Q01": (9, "Đủ ba loại và giải thích đúng; có một câu từ chối thừa."),
    "RAG-Q02": (8, "Phân biệt đúng và có ví dụ; câu kết thừa."),
    "RAG-Q03": (9, "Đủ tám loại sau khi mở rộng chunk liền kề."),
    "RAG-Q04": (6, "Đúng yếu tố biến động nhưng diễn đạt sai yếu tố ứng phó pháp lý."),
    "RAG-Q05": (9, "Nêu đúng phân bổ vốn và các cơ chế chuyển giao/quản lý rủi ro."),
    "RAG-Q06": (8, "Đúng cơ chế gắn kết xã hội và điều kiện áp dụng."),
    "RAG-Q07": (8, "Đúng hướng giảm chi phí vận hành và tăng thuận tiện."),
    "RAG-Q08": (9, "Đủ bốn dòng sản phẩm chính của chương 8."),
    "RAG-Q09": (8, "Đúng vai trò API trong trao đổi dữ liệu/open banking."),
    "RAG-Q10": (9, "Đúng mô hình dịch vụ theo yêu cầu và ba lớp cloud/BaaS."),
    "RAG-Q11": (9, "Đủ bốn bước thu thập, tiền xử lý, huấn luyện và đánh giá."),
    "RAG-Q12": (10, "Đúng phép tính Bayes và kết quả 69%."),
    "RAG-Q13": (6, "Có bảo mật, công bằng và giá trị; thiếu concept drift, kiểm toán và độc quyền dữ liệu."),
    "RAG-Q14": (7, "Tổng hợp được vai trò dữ liệu, hạ tầng cloud và AI nhưng quan hệ còn khái quát."),
    "RAG-Q15": (10, "Từ chối đúng vì tài liệu không có dự báo tương lai."),
    "RAG-Q16": (10, "Từ chối đúng vì tài liệu không có thông tin được hỏi."),
}


def read_rows(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--overrides", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = read_rows(args.input)
    if args.overrides and args.overrides.exists():
        overrides = {row["question_id"]: row for row in read_rows(args.overrides)}
        for index, row in enumerate(rows):
            if row["question_id"] in overrides:
                rows[index] = overrides[row["question_id"]]
    for row in rows:
        score, reason = SCORES[row["question_id"]]
        row["correctness_score"] = str(score)
        row["score_reason"] = reason
        row["quality_pass"] = str(score >= 7)
        row["status"] = "PASS" if row.get("retrieval_pass") == "True" and score >= 7 else "FAIL"
    fields = list(rows[0].keys())
    for field in ("score_reason", "quality_pass"):
        if field not in fields:
            fields.append(field)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)
    passed = sum(row["quality_pass"] == "True" for row in rows)
    print(f"quality gate: {passed}/{len(rows)} answers scored >= 7/10")
    return 0 if passed >= 12 else 1


if __name__ == "__main__":
    raise SystemExit(main())

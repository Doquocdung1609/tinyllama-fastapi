"""Build a reproducible, human-auditable evidence appendix for RAG eval cases."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import unicodedata


def normalized(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).lower()
    return " ".join(re.findall(r"[0-9a-zà-ỹđ]+", value, re.IGNORECASE))


def evidence_score(text: str, elements: list[str], question: str) -> float:
    haystack = normalized(text)
    score = 0.0
    for element in elements:
        phrase = normalized(element)
        if phrase and phrase in haystack:
            score += 8.0
        score += sum(1.0 for term in phrase.split() if len(term) > 2 and term in haystack)
    question_terms = {term for term in normalized(question).split() if len(term) > 3}
    score += sum(0.15 for term in question_terms if term in haystack)
    return score


def compact_excerpt(text: str, elements: list[str], limit: int = 900) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    folded = normalized(text)
    anchors = [normalized(value) for value in elements if normalized(value)]
    positions = [folded.find(anchor) for anchor in anchors if folded.find(anchor) >= 0]
    # Normalization retains one character per visible character for this corpus closely
    # enough to center the audit excerpt without changing the source content.
    start = max(0, (min(positions) if positions else 0) - 220)
    end = min(len(text), start + limit)
    excerpt = text[start:end]
    if start:
        excerpt = "…" + excerpt.split(" ", 1)[-1]
    if end < len(text):
        excerpt = excerpt.rsplit(" ", 1)[0] + "…"
    return excerpt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, default=Path("reports/rag_eval_cases.json"))
    parser.add_argument("--processed", type=Path, required=True)
    parser.add_argument("--json-output", type=Path, default=Path("reports/rag_eval_evidence.json"))
    parser.add_argument("--markdown-output", type=Path, default=Path("reports/rag_eval_evidence.md"))
    args = parser.parse_args()

    cases = json.loads(args.cases.read_text(encoding="utf-8"))
    payload = json.loads(args.processed.read_text(encoding="utf-8"))
    chunks = payload["chunks"]
    records = []
    for case in cases:
        evidence = []
        for page in case["pages"]:
            candidates = [chunk for chunk in chunks if int(chunk.get("page", -1)) == int(page)]
            if not candidates:
                continue
            best = max(candidates, key=lambda item: evidence_score(
                item.get("text") or item.get("cleaned_text", ""),
                case["expected_elements"], case["question"]))
            evidence.append({
                "page": page,
                "chunk_id": best["chunk_id"],
                "chunk_index": best.get("chunk_index"),
                "excerpt": compact_excerpt(best.get("text") or best.get("cleaned_text", ""),
                                           case["expected_elements"]),
            })
        records.append({
            "id": case["id"], "question": case["question"],
            "expected_elements": case["expected_elements"], "expected_refusal": case["refusal"],
            "source_pages": case["pages"], "evidence": evidence,
            "note": ("Câu ngoài phạm vi; không có trang nguồn hợp lệ."
                     if case["refusal"] else "Đoạn nguồn được chọn từ dữ liệu PDF đã xử lý, không từ câu trả lời LLM."),
        })

    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# RAG evaluation evidence appendix", "",
        "Nguồn: dữ liệu PDF đã xử lý `processed/aedb60bc088e4242970a43da1e897bde.json`. "
        "Các đoạn dưới đây được chọn theo ground truth đã xác minh; câu trả lời của mô hình không được dùng làm ground truth.", "",
    ]
    for record in records:
        lines.extend([f"## {record['id']}", "", f"**Câu hỏi:** {record['question']}", ""])
        if record["expected_refusal"]:
            lines.extend(["**Kỳ vọng:** từ chối vì không có bằng chứng trong tài liệu.", ""])
            continue
        lines.extend([f"**Trang nguồn:** {', '.join(map(str, record['source_pages']))}", ""])
        for item in record["evidence"]:
            lines.extend([
                f"- Trang {item['page']} · chunk `{item['chunk_id']}` · index {item['chunk_index']}",
                f"  > {item['excerpt']}", "",
            ])
    args.markdown_output.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {len(records)} cases to {args.json_output} and {args.markdown_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

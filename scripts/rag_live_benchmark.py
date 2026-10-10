"""Run a transparent 30-case RAG evaluation against the real FastAPI endpoint."""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path
import re
import sys
from time import perf_counter
import unicodedata
import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def norm(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.casefold().replace("đ", "d"))
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9%]+", " ", value)).strip()


def element_matches(answer: str, element: str) -> bool:
    alternatives = [value.strip() for value in element.split("|") if value.strip()]
    if len(alternatives) > 1:
        return any(element_matches(answer, value) for value in alternatives)
    answer_norm, element_norm = norm(answer), norm(element)
    aliases = {
        "tri tue nhan tao": ("ai",),
        "api": ("giao dien lap trinh ung dung",),
        "dien toan dam may": ("cloud",),
        "open banking": ("ngan hang mo",),
    }
    if element_norm in answer_norm:
        return True
    if any(re.search(rf"\b{re.escape(alias)}\b", answer_norm)
           for alias in aliases.get(element_norm, ())):
        return True
    tokens = [token for token in element_norm.split() if len(token) > 2 or token.isdigit()]
    return bool(tokens) and sum(token in answer_norm for token in tokens) / len(tokens) >= .75


def refusal_detected(answer: str) -> bool:
    text = norm(answer)
    return any(phrase in text for phrase in (
        "tai lieu khong cung cap du thong tin", "khong co du thong tin",
        "khong tim thay thong tin", "khong du bang chung"))


def near_expected(page: int, expected: list[int]) -> bool:
    return any(abs(page - target) <= 1 for target in expected)


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", default="http://127.0.0.1:8000")
    parser.add_argument("--document-id", required=True)
    parser.add_argument("--cases", type=Path, default=Path("reports/rag_eval_cases.json"))
    parser.add_argument("--output", type=Path, default=Path("reports/rag_live_benchmark.csv"))
    parser.add_argument("--details", type=Path, default=Path("reports/rag_live_benchmark_details.json"))
    parser.add_argument("--model", default="qwen2.5:3b")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--threshold", type=float, default=.55)
    parser.add_argument("--no-generate", action="store_true")
    parser.add_argument("--only", nargs="*")
    parser.add_argument("--cold-first", action="store_true")
    args = parser.parse_args()
    cases = json.loads(args.cases.read_text(encoding="utf-8"))
    if args.only:
        chosen = set(args.only); cases = [case for case in cases if case["id"] in chosen]
    if args.cold_first:
        requests.post("http://127.0.0.1:11434/api/generate",
                      json={"model": args.model, "keep_alive": 0}, timeout=30)

    rows, details = [], []
    for index, case in enumerate(cases):
        payload = {"question": case["question"], "top_k": args.top_k,
                   "score_threshold": args.threshold, "document_id": args.document_id,
                   "generate_answer": not args.no_generate, "model": args.model}
        started = perf_counter()
        response = requests.post(args.api.rstrip("/") + "/rag/query", json=payload, timeout=360)
        elapsed = perf_counter() - started
        response.raise_for_status(); data = response.json()
        retrieved = data.get("retrieved_chunks", [])
        retrieved_pages = [int(item["page"]) for item in retrieved if item.get("page") is not None]
        prompt_items = data.get("included_prompt_context", [])
        prompt_pages = [int(item["page"]) for item in prompt_items if item.get("page") is not None]
        expected = [int(page) for page in case["pages"]]
        if case["refusal"]:
            retrieval_hit = not retrieved_pages
            evidence_precision = 1.0 if not retrieved_pages else 0.0
            prompt_coverage = 1.0 if not prompt_pages else 0.0
        else:
            hits = sum(near_expected(page, expected) for page in retrieved_pages)
            retrieval_hit = hits > 0
            evidence_precision = hits / len(retrieved_pages) if retrieved_pages else 0.0
            prompt_coverage = float(any(near_expected(page, expected) for page in prompt_pages))
        first_hit = next((rank for rank, page in enumerate(retrieved_pages, 1)
                          if near_expected(page, expected)), None) if expected else None
        answer = data.get("answer", "")
        matched = [element for element in case["expected_elements"] if element_matches(answer, element)]
        element_recall = (len(matched) / len(case["expected_elements"])
                          if case["expected_elements"] else 1.0)
        refused = refusal_detected(answer) if not args.no_generate else False
        answer_correct = ((refused and case["refusal"]) or
                          (not case["refusal"] and not refused and element_recall >= .60))
        cited_pages = [int(value) for value in re.findall(r"trang\s+(\d+)", answer, re.IGNORECASE)]
        citation_correct = (bool(cited_pages) and all(near_expected(page, expected) for page in cited_pages)
                            if expected else not cited_pages)
        timings = data.get("timings", {})
        row = {"question_id": case["id"], "category": case["category"], "model": data.get("model", args.model),
               "top_k": args.top_k, "threshold": args.threshold,
               "expected_pages": ",".join(map(str, expected)),
               "retrieved_pages": ",".join(map(str, retrieved_pages)),
               "prompt_pages": ",".join(map(str, prompt_pages)),
               "retrieval_hit": retrieval_hit, "reciprocal_rank": round(1 / first_hit, 4) if first_hit else 0,
               "evidence_precision": round(evidence_precision, 4), "evidence_in_prompt": prompt_coverage,
               "matched_elements": " | ".join(matched), "element_recall": round(element_recall, 4),
               "answer_correct": answer_correct, "expected_refusal": case["refusal"],
               "refused": refused, "cited_pages": ",".join(map(str, cited_pages)),
               "citation_correct": citation_correct,
               "embedding_ms": timings.get("embedding_ms", 0),
               "retrieval_ms": round(timings.get("semantic_search_ms", 0) + timings.get("lexical_search_ms", 0), 1),
               "prompt_ms": timings.get("prompt_preparation_ms", 0),
               "generation_ms": timings.get("generation_ms", 0), "total_ms": timings.get("total_ms", round(elapsed * 1000, 1)),
               "cold_or_warm": "cold" if index == 0 and args.cold_first else "warm",
               "answer": answer.replace("\n", " ")[:1600]}
        rows.append(row)
        details.append({"case": case, "request": payload, "response": data})
        write_csv(args.output, rows)
        args.details.parent.mkdir(parents=True, exist_ok=True)
        args.details.write_text(json.dumps(details, ensure_ascii=False, indent=2), encoding="utf-8")
        print(case["id"], "retrieval", retrieval_hit, "answer", answer_correct,
              "citation", citation_correct, retrieved_pages, f"{elapsed:.1f}s", flush=True)

    count = len(rows) or 1
    supported = [row for row in rows if not row["expected_refusal"]]
    expected_refusals = [row for row in rows if row["expected_refusal"]]
    predicted_refusals = [row for row in rows if row["refused"]]
    summary = {
        "cases": len(rows), "recall_at_k": sum(bool(row["retrieval_hit"]) for row in rows) / count,
        "mrr": sum(float(row["reciprocal_rank"]) for row in supported) / max(1, len(supported)),
        "evidence_precision": sum(float(row["evidence_precision"]) for row in rows) / count,
        "evidence_in_prompt_coverage": sum(float(row["evidence_in_prompt"]) for row in rows) / count,
        "answer_correctness": sum(bool(row["answer_correct"]) for row in rows) / count,
        "citation_accuracy_supported": sum(bool(row["citation_correct"]) for row in supported) / max(1, len(supported)),
        "refusal_recall": sum(bool(row["refused"]) for row in expected_refusals) / max(1, len(expected_refusals)),
        "refusal_precision": sum(bool(row["expected_refusal"]) for row in predicted_refusals) / max(1, len(predicted_refusals)),
        "avg_total_ms": sum(float(row["total_ms"]) for row in rows) / count,
    }
    summary_path = args.output.with_suffix(".summary.json")
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2)); print(args.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Compare Qwen and Llama generation with identical retrieved prompts."""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path
import re
import subprocess
import sys
from time import perf_counter
import requests
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.rag_live_benchmark import element_matches, near_expected, refusal_detected
from app.services.rag_service import _resolve_evidence_citations

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

DEFAULT_IDS = {"RAG-Q01", "RAG-Q03", "RAG-Q04", "RAG-Q09", "RAG-Q12",
               "RAG-Q13", "RAG-Q15", "RAG-Q17", "RAG-Q27", "RAG-Q30"}


def gpu_usage() -> dict:
    try:
        result = subprocess.run(["nvidia-smi", "--query-gpu=memory.used,memory.free,utilization.gpu",
                                 "--format=csv,noheader,nounits"], capture_output=True, text=True,
                                timeout=5, check=False,
                                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        used, free, utilization = [float(value.strip()) for value in result.stdout.splitlines()[0].split(",")]
        return {"gpu_used_mb": used, "gpu_free_mb": free, "gpu_utilization_percent": utilization}
    except Exception:
        return {"gpu_used_mb": "", "gpu_free_mb": "", "gpu_utilization_percent": ""}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", default="http://127.0.0.1:8000")
    parser.add_argument("--ollama", default="http://127.0.0.1:11434")
    parser.add_argument("--document-id", required=True)
    parser.add_argument("--cases", type=Path, default=Path("reports/rag_eval_cases.json"))
    parser.add_argument("--output", type=Path, default=Path("reports/llm_comparison.csv"))
    parser.add_argument("--models", nargs="+", default=["qwen2.5:3b", "llama3:latest"])
    parser.add_argument("--ids", nargs="*", default=sorted(DEFAULT_IDS))
    args = parser.parse_args()
    all_cases = json.loads(args.cases.read_text(encoding="utf-8"))
    cases = [case for case in all_cases if case["id"] in set(args.ids)]

    prompts = []
    for case in cases:
        response = requests.post(args.api.rstrip("/") + "/rag/query", json={
            "question": case["question"], "top_k": 5, "score_threshold": .55,
            "document_id": args.document_id, "generate_answer": False}, timeout=180)
        response.raise_for_status(); data = response.json()
        prompts.append((case, data["final_prompt"], data.get("included_prompt_context", [])))

    rows = []
    for model in args.models:
        requests.post(args.ollama.rstrip("/") + "/api/generate",
                      json={"model": model, "keep_alive": 0}, timeout=30)
        for index, (case, prompt, evidence) in enumerate(prompts):
            try:
                import psutil
                ram_before = psutil.virtual_memory().used / 1024**3
                psutil.cpu_percent(None)
            except ImportError:
                ram_before = 0
            started = perf_counter()
            response = requests.post(args.ollama.rstrip("/") + "/api/generate", json={
                "model": model, "prompt": prompt, "stream": False, "keep_alive": "5m",
                "options": {"temperature": 0, "num_predict": 320, "num_ctx": 4096}}, timeout=600)
            elapsed = perf_counter() - started
            response.raise_for_status(); raw = response.json()
            answer, citation = _resolve_evidence_citations(raw.get("response", "").strip(), evidence)
            elements = case["expected_elements"]
            matched = [element for element in elements if element_matches(answer, element)]
            element_recall = len(matched) / len(elements) if elements else 1.0
            refused = refusal_detected(answer)
            answer_correct = ((case["refusal"] and refused) or
                              (not case["refusal"] and not refused and element_recall >= .60))
            cited_pages = [int(value) for value in re.findall(r"trang\s+(\d+)", answer, re.I)]
            citation_correct = (bool(cited_pages) and all(near_expected(page, case["pages"])
                                  for page in cited_pages)) if case["pages"] else not cited_pages
            try:
                import psutil
                memory = psutil.virtual_memory()
                ram_after = memory.used / 1024**3
                cpu_percent = psutil.cpu_percent(.1)
            except ImportError:
                ram_after = cpu_percent = 0
            process_data = requests.get(args.ollama.rstrip("/") + "/api/ps", timeout=10).json().get("models", [])
            process = next((item for item in process_data if item.get("name") == model), {})
            gpu = gpu_usage()
            eval_count = int(raw.get("eval_count", 0) or 0)
            eval_seconds = float(raw.get("eval_duration", 0) or 0) / 1e9
            rows.append({"model": model, "question_id": case["id"],
                         "cold_or_warm": "cold" if index == 0 else "warm",
                         "answer_correct": answer_correct, "element_recall": round(element_recall, 4),
                         "citation_correct": citation_correct, "refused": refused,
                         "groundedness_pass": answer_correct and citation_correct,
                         "wall_seconds": round(elapsed, 3), "load_seconds": round(float(raw.get("load_duration", 0) or 0) / 1e9, 3),
                         "prompt_eval_seconds": round(float(raw.get("prompt_eval_duration", 0) or 0) / 1e9, 3),
                         "eval_tokens": eval_count, "tokens_per_second": round(eval_count / eval_seconds, 2) if eval_seconds else 0,
                         "ollama_vram_mb": round(float(process.get("size_vram", 0) or 0) / 1024**2, 1),
                         "ram_used_before_gb": round(ram_before, 2), "ram_used_after_gb": round(ram_after, 2),
                         "cpu_percent_after": cpu_percent, **gpu,
                         "citation_fallback_added": citation.get("citation_fallback_added"),
                         "matched_elements": " | ".join(matched), "answer": answer.replace("\n", " ")[:1600]})
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open("w", newline="", encoding="utf-8-sig") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
            print(model, case["id"], answer_correct, citation_correct, f"{elapsed:.1f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

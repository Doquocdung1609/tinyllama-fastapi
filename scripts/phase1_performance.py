"""Measure Phase 1 category latency and resource use on the real local API."""
from __future__ import annotations

import csv
import json
import math
import statistics
import subprocess
import threading
import time
from pathlib import Path

import psutil
import requests

from app.services.pdf_service import extract_pdf

ROOT = Path(__file__).resolve().parents[1]
API = "http://127.0.0.1:8002"
DOCS = {
    "real": "a148b440d6ae7d19cc8b78c462322fc5",
    "finance": "1a5c24c20a89588f2d4ad12abe968f28",
    "mixed": "812a4d9c64e301b44411a427144149ba",
    "multi": "5e459d0415710af7d2494c3e2e3802c0",
}


def percentile(values: list[float], level: float) -> float:
    return sorted(values)[max(0, math.ceil(level * len(values)) - 1)]


def query(question: str, document_id: str, threshold=.35) -> tuple[float, dict]:
    started = time.perf_counter()
    response = requests.post(API + "/rag/query", json={"question": question,
        "document_id": document_id, "top_k": 5, "score_threshold": threshold}, timeout=240)
    elapsed = (time.perf_counter() - started) * 1000
    response.raise_for_status()
    return elapsed, response.json()


def main() -> None:
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    server_pid = next((item.pid for item in psutil.net_connections(kind="inet")
                       if item.laddr and item.laddr.port == 8002 and item.status == "LISTEN"), None)
    server = psutil.Process(server_pid) if server_pid else None
    stop = False
    samples = []
    def sample() -> None:
        while not stop:
            vm = psutil.virtual_memory()
            samples.append({"time": time.time(), "system_available_mb": vm.available / 1024**2,
                            "server_rss_mb": server.memory_info().rss / 1024**2 if server else None})
            time.sleep(.05)
    sampler = threading.Thread(target=sample, daemon=True); sampler.start()

    definitions = [
        ("structural_navigation", 8, "Trang 3 có những bảng, biểu đồ và hình nào?", DOCS["real"], .55),
        ("formula_calculation", 8, "Tính tỷ lệ thanh toán nhanh năm 2024", DOCS["finance"], .35),
        ("deterministic_lookup", 8, "Doanh thu năm 2024 là bao nhiêu?", DOCS["mixed"], .35),
        ("multi_page_synthesis", 5, "So sánh giá trị của mã A15 và A16 trong bảng nhiều trang.", DOCS["multi"], .35),
        ("short_factual_rag", 3, "Mẫu nghiên cứu gồm bao nhiêu quốc gia và bao nhiêu quan sát?", DOCS["real"], .35),
    ]
    raw = []
    for category, count, question, document_id, threshold in definitions:
        for run in range(count):
            elapsed, result = query(question, document_id, threshold)
            timings = result.get("timings") or {}
            raw.append({"category": category, "run": run + 1, "temperature": "cold" if run == 0 else "warm",
                        "end_to_end_ms": round(elapsed, 1),
                        "embedding_ms": timings.get("embedding_ms"), "retrieval_ms": round(
                            float(timings.get("semantic_search_ms") or 0) + float(timings.get("lexical_search_ms") or 0), 1),
                        "rerank_context_prompt_ms": timings.get("prompt_preparation_ms"),
                        "generation_and_citation_ms": timings.get("generation_ms"),
                        "citation_valid": (result.get("citation_validation") or {}).get("citation_valid"),
                        "answer": result.get("answer", "")[:300]})
            print(category, run + 1, round(elapsed, 1))

    native_values = []
    native_path = ROOT / "tests" / "fixtures" / "pdfs" / "C_financial_statement.pdf"
    for run in range(5):
        started = time.perf_counter(); extract_pdf(native_path, "perf", native_path.name)
        native_values.append((time.perf_counter() - started) * 1000)
    for run, elapsed in enumerate(native_values, 1):
        raw.append({"category": "native_pdf_preflight", "run": run,
                    "temperature": "cold" if run == 1 else "warm", "end_to_end_ms": round(elapsed, 1),
                    "embedding_ms": None, "retrieval_ms": None, "rerank_context_prompt_ms": None,
                    "generation_and_citation_ms": None, "citation_valid": None, "answer": "1-page native table"})

    stop = True; sampler.join(timeout=1)
    aggregate = []
    for category in sorted({item["category"] for item in raw}):
        group = [float(item["end_to_end_ms"]) for item in raw if item["category"] == category]
        warm = [float(item["end_to_end_ms"]) for item in raw if item["category"] == category and item["temperature"] == "warm"]
        aggregate.append({"category": category, "sample_size": len(group),
                          "cold_ms": group[0], "warm_p50_ms": round(statistics.median(warm or group), 1),
                          "warm_p95_ms": round(percentile(warm or group, .95), 1),
                          "min_ms": min(group), "max_ms": max(group), "code_commit": commit})
    target = ROOT / "reports" / "phase1_latency_benchmark.csv"
    with target.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(aggregate[0])); writer.writeheader(); writer.writerows(aggregate)
    (ROOT / "reports" / "phase1_latency_raw.json").write_text(
        json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")

    vm, disk = psutil.virtual_memory(), psutil.disk_usage(str(ROOT))
    gpu = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total,memory.used,memory.free,utilization.gpu",
                          "--format=csv,noheader,nounits"], capture_output=True, text=True, check=False).stdout.strip()
    status = requests.get(API + "/system/status", timeout=15).json()
    docs = requests.get(API + "/documents", timeout=15).json()
    resource = ["# Phase 1 resource profile", "", f"- Tested commit: `{commit}`",
                f"- API PID: {server_pid}", f"- System RAM total: {vm.total/1024**3:.2f} GB",
                f"- System RAM available after benchmark: {vm.available/1024**3:.2f} GB",
                f"- Minimum available RAM sampled: {min(x['system_available_mb'] for x in samples)/1024:.2f} GB",
                f"- API RSS peak sampled: {max(x['server_rss_mb'] for x in samples if x['server_rss_mb'] is not None):.1f} MB",
                f"- Disk free: {disk.free/1024**3:.2f} GB", f"- GPU snapshot: `{gpu}`", "",
                "## Process and storage boundaries", "",
                "- PDF extraction and OCR operate one page at a time; rendered PIL images are local variables released after each page.",
                "- Document embedding is batched by the configured provider; duplicate jobs are suppressed by a process lock.",
                "- Tiny-SD and video models are not loaded by ordinary RAG requests.",
                "- Uploads are hash keyed, size bounded, disk guarded, and temporary upload files are removed on errors.",
                "", "## Actual API state", "", "```json",
                json.dumps({"qdrant": status.get("qdrant"), "ollama": status.get("ollama"),
                            "documents": len(docs)}, ensure_ascii=False, indent=2), "```", "",
                "## Reproduce", "", "`PYTHONPATH=. python scripts/phase1_performance.py`", ""]
    (ROOT / "reports" / "phase1_resource_profile.md").write_text("\n".join(resource), encoding="utf-8")
    print(json.dumps(aggregate, indent=2))


if __name__ == "__main__":
    main()

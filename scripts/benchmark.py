"""Reproducible local latency/resource benchmark; results are measured, never estimated."""
from __future__ import annotations
import argparse
import csv
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys
import threading
from time import perf_counter, sleep
import psutil
import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def gpu_sample() -> tuple[float | None, float | None]:
    try:
        result = subprocess.run(["nvidia-smi", "--query-gpu=memory.used,utilization.gpu",
            "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=3, check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if result.returncode == 0:
            a, b = result.stdout.splitlines()[0].split(",")
            return float(a), float(b)
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    return None, None


def measured(name, fn):
    stop = threading.Event(); samples = []
    def sample():
        while not stop.is_set():
            vram, gpu = gpu_sample(); memory = psutil.virtual_memory()
            samples.append((memory.used / 1024**2, vram, gpu, psutil.cpu_percent()))
            stop.wait(.25)
    thread = threading.Thread(target=sample, daemon=True); thread.start()
    started = perf_counter(); status = "PASS"; detail = ""
    try:
        detail = fn()
    except Exception as exc:
        status, detail = "FAIL", str(exc)
    elapsed = perf_counter() - started; stop.set(); thread.join(timeout=2)
    valid_vram = [s[1] for s in samples if s[1] is not None]
    valid_gpu = [s[2] for s in samples if s[2] is not None]
    return {"timestamp_utc": datetime.now(timezone.utc).isoformat(), "workload": name,
            "status": status, "wall_seconds": round(elapsed, 3),
            "peak_ram_used_mb": round(max((s[0] for s in samples), default=0)),
            "peak_vram_used_mb": round(max(valid_vram), 1) if valid_vram else "",
            "peak_gpu_percent": round(max(valid_gpu), 1) if valid_gpu else "",
            "peak_cpu_percent": round(max((s[3] for s in samples), default=0), 1),
            "detail": str(detail)[:500]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", default="http://127.0.0.1:8000")
    parser.add_argument("--document-id")
    parser.add_argument("--output", type=Path, default=Path("reports/performance_benchmark.csv"))
    parser.add_argument("--full", action="store_true", help="Include live chat and RAG generation")
    parser.add_argument("--media", action="store_true", help="Include real TTS, image and FFmpeg motion-demo calls")
    parser.add_argument("--ttft-only", action="store_true", help="Measure streaming chat time to first byte only")
    args = parser.parse_args(); base = args.api.rstrip("/"); rows = []
    def call_chat_stream():
        payload = {"message": "Hãy trả lời bằng tiếng Việt trong một câu: Bạn có thể hỗ trợ người học những việc gì?",
                   "temperature": .2, "max_tokens": 128}
        started = perf_counter(); first_byte = None; size = 0
        with requests.post(base + "/chat/stream", json=payload, timeout=300, stream=True) as response:
            response.raise_for_status()
            for chunk in response.iter_content(chunk_size=1):
                if not chunk:
                    continue
                if first_byte is None:
                    first_byte = perf_counter() - started
                size += len(chunk)
        return {"time_to_first_byte_seconds": round(first_byte or 0, 3), "response_bytes": size}
    if args.ttft_only:
        rows.append(measured("chat_stream_ttft", call_chat_stream))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=rows[0].keys()); writer.writeheader(); writer.writerows(rows)
        print(args.output.resolve())
        return 0 if rows[0]["status"] == "PASS" else 1
    rows.append(measured("health", lambda: requests.get(base + "/health", timeout=10).json()))
    rows.append(measured("system_status_cold", lambda: requests.get(base + "/system/status", timeout=30).json()))
    rows.append(measured("system_status_warm", lambda: requests.get(base + "/system/status", timeout=30).json()))
    if args.document_id:
        payload = {"question": "Ba loại đổi mới tài chính căn cứ theo loại hình là gì?", "top_k": 5,
                   "score_threshold": .55, "document_id": args.document_id, "generate_answer": False}
        rows.append(measured("rag_retrieval", lambda: requests.post(base + "/rag/query", json=payload, timeout=60).json()))
        if args.full:
            payload["generate_answer"] = True
            rows.append(measured("rag_total", lambda: requests.post(base + "/rag/query", json=payload, timeout=300).json()))
    if args.full:
        payload = {"message": "Hãy trả lời bằng tiếng Việt trong một câu: Bạn có thể hỗ trợ người học những việc gì?",
                   "temperature": .2, "max_tokens": 128}
        rows.append(measured("chat_128_tokens", lambda: requests.post(base + "/chat", json=payload, timeout=300).json()))
    if args.media:
        tts_payload = {"script": "This is a real offline speech synthesis benchmark.", "normalize": False,
                       "rate": 175, "volume": 1.0}
        rows.append(measured("tts_windows_sapi", lambda: requests.post(
            base + "/tts/generate", json=tts_payload, timeout=120).json()))
        image_payload = {"prompt": "a small blue robot teaching in a classroom, simple illustration",
                         "negative_prompt": "blurry, black image", "steps": 2, "guidance_scale": 7.0,
                         "width": 256, "height": 256, "seed": 9876}
        image_result = {}
        def call_image():
            response = requests.post(base + "/image/generate", json=image_payload, timeout=600)
            response.raise_for_status(); image_result.update(response.json()); return image_result
        rows.append(measured("tiny_sd_256x256_2_steps", call_image))
        image_url = image_result.get("image_url")
        if image_url:
            image_path = Path("images") / Path(image_url).name
            def call_motion_demo():
                with image_path.open("rb") as handle:
                    response = requests.post(base + "/video/demo", files={"file": (image_path.name, handle, "image/png")},
                                             data={"num_frames": 28, "fps": 14}, timeout=180)
                response.raise_for_status(); return response.json()
            rows.append(measured("ffmpeg_motion_demo_28_frames", call_motion_demo))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys()); writer.writeheader(); writer.writerows(rows)
    print(args.output.resolve())
    return 0 if all(row["status"] == "PASS" for row in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())

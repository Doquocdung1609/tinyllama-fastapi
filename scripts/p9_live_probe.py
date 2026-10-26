"""Launch and stop opt-in research services for a real local HTTP/browser check."""
import argparse
import json
import os
from pathlib import Path
import secrets
import socket
import sqlite3
import subprocess
import sys
from time import perf_counter, sleep

import requests


QUESTION = "What were HD total assets as of August 2, 2026?"


def free_port():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


def start(command, env, ready_url, expected_status=200):
    started = perf_counter()
    process = subprocess.Popen(command, env=env, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL,
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    for _ in range(180):
        if process.poll() is not None:
            raise RuntimeError(f"SERVICE_EXITED:{command[0]}:{process.returncode}")
        try:
            response = requests.get(ready_url, timeout=.3)
            if response.status_code == expected_status:
                return process, (perf_counter() - started) * 1000
        except requests.RequestException:
            pass
        sleep(.1)
    process.terminate()
    process.wait(timeout=10)
    raise RuntimeError(f"SERVICE_NOT_READY:{command[0]}")


def stop(process):
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)


def ask(url, token):
    started = perf_counter()
    response = requests.post(url + "/research/v1/query",
                             headers={"Authorization": "Bearer " + token},
                             json={"workflow": "automatic_real", "question": QUESTION, "arm": "B"},
                             timeout=35)
    body = response.json()
    result = {"http": response.status_code, "answer": body.get("answer", {}).get("status"),
              "values": body.get("answer", {}).get("result_values", []),
              "generation": body.get("generation"), "wall_ms": (perf_counter() - started) * 1000}
    if result["http"] != 200 or result["answer"] != "SUPPORTED" or result["values"] != ["109384000000"]:
        raise AssertionError(f"P9_HTTP_CONTROL_FAILED:{result}")
    return result


def run(root, output):
    root = root.resolve(strict=True)
    if "p7-isolated-review" not in root.name or not (root / "ownership.json").is_file():
        raise ValueError("EXPLICIT_ISOLATED_RESEARCH_CLONE_REQUIRED")
    token = secrets.token_urlsafe(32)
    api_port, ui_port = free_port(), free_port()
    api_url, ui_url = f"http://127.0.0.1:{api_port}", f"http://127.0.0.1:{ui_port}"
    env = dict(os.environ, TOPIC3_RESEARCH_ROOT=str(root), TOPIC3_RESEARCH_API_TOKEN=token,
               TOPIC3_RESEARCH_MODE="real_frozen", TOPIC3_RESEARCH_API_URL=api_url)
    api_command = [sys.executable, "-m", "uvicorn", "app.research_api:app", "--host", "127.0.0.1",
                   "--port", str(api_port), "--log-level", "error"]
    ui_command = [sys.executable, "-m", "streamlit", "run", "research_ui.py", "--server.address",
                  "127.0.0.1", "--server.port", str(ui_port), "--server.headless", "true"]
    api = ui = None
    try:
        api, api_startup = start(api_command, env, api_url + "/research/v1/health")
        if requests.get(api_url + "/research/v1/health", timeout=5).json()["status"] != "ready":
            raise AssertionError("API_NOT_READY")
        first, repeated = ask(api_url, token), ask(api_url, token)
        subprocess.run([sys.executable, "-m", "scripts.p8_http_smoke", "--url", api_url,
                        "--output", str(output.parent / "p9_http_matrix.json")], env=env,
                       check=True, timeout=240)
        ui, ui_startup = start(ui_command, env, ui_url + "/_stcore/health")
        browser_env = dict(env, NODE_PATH=os.environ["P9_NODE_MODULES"],
                           P9_UI_URL=ui_url, P9_CHROME_PATH=os.environ["P9_CHROME_PATH"],
                           P9_UI_OUTPUT=str(output.parent / "p9_browser_results.json"))
        subprocess.run([os.environ.get("P9_NODE", "node"), "scripts/p9_browser_probe.cjs"],
                       env=browser_env, check=True, timeout=120)
        wrong = requests.post(api_url + "/research/v1/query",
                              headers={"Authorization": "Bearer invalid-token"},
                              json={"workflow": "automatic_real", "question": QUESTION}, timeout=5)
        if wrong.status_code != 401:
            raise AssertionError("WRONG_TOKEN_NOT_REJECTED")
        generation = json.loads((root / "frozen_v1/freeze.json").read_text())["generation"]
        with sqlite3.connect(root / "lexical_v1.sqlite3") as db:
            original_state = db.execute("SELECT state FROM generations WHERE generation=?", (generation,)).fetchone()[0]
            db.execute("UPDATE generations SET state='FAILED' WHERE generation=?", (generation,))
        try:
            failed = requests.post(api_url + "/research/v1/query",
                                   headers={"Authorization": "Bearer " + token},
                                   json={"workflow": "automatic_real", "question": QUESTION, "arm": "B"},
                                   timeout=35)
            failed_body = failed.json()
        finally:
            with sqlite3.connect(root / "lexical_v1.sqlite3") as db:
                db.execute("UPDATE generations SET state=? WHERE generation=?", (original_state, generation))
        if failed.status_code != 409 or failed_body.get("answer", {}).get("result_values"):
            raise AssertionError("INVALID_GENERATION_RETURNED_CLAIM")
        restored = ask(api_url, token)
        result = {"schema_version": "topic3-p9-live/v1", "source_clone_only": True,
                  "token_recorded": False, "api_startup_ms": api_startup,
                  "streamlit_startup_ms": ui_startup, "first_query": first,
                  "repeated_query": repeated, "invalid_token_http": wrong.status_code,
                  "invalid_generation_http": failed.status_code,
                  "generation_restored": restored["answer"] == "SUPPORTED",
                  "browser_result": "see p9_browser_results.json",
                  "http_matrix": "see p9_http_matrix.json"}
    finally:
        if ui is not None:
            stop(ui)
        if api is not None:
            stop(api)
    # Repeat after a clean API restart; no writable owner source is involved.
    api, restart_ms = start(api_command, env, api_url + "/research/v1/health")
    try:
        result["api_restart_ms"] = restart_ms
        result["after_restart"] = ask(api_url, token)
    finally:
        stop(api)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.root, args.output)
    print(json.dumps({"api_startup_ms": result["api_startup_ms"],
                      "streamlit_startup_ms": result["streamlit_startup_ms"],
                      "restart_ms": result["api_restart_ms"],
                      "repeated_answer": result["repeated_query"]["answer"]}))

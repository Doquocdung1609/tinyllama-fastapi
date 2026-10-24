"""Opt-in real Ollama/API/Qdrant smoke test using an isolated test collection."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import time

import requests
from reportlab.pdfgen.canvas import Canvas


def verify(base: str, output: Path, collection: str) -> dict:
    def get(path):
        response = requests.get(base + path, timeout=30)
        response.raise_for_status()
        return response.json()

    if collection == "knowledgebase":
        raise ValueError("Use a dedicated verification collection")
    before = get("/qdrant/status")
    if before.get("collection") != collection:
        raise ValueError("Running API does not use the requested isolated collection")
    output.parent.mkdir(parents=True, exist_ok=True)
    pdf = output.parent / "rag-financial-verification.pdf"
    canvas = Canvas(str(pdf), invariant=1)
    lines = ["Acme Verification Company - Financial Note - Fiscal 2025",
             "This is a synthetic fixture for integration, not a SEC disclosure.",
             "Acme Verification Company reported revenue of USD 12.5 million in fiscal 2025.",
             "The company used operating cash flow to finance a solar-powered logistics hub.",
             "The financial year ended on December 31, 2025."]
    for index, line in enumerate(lines):
        canvas.drawString(40, 800 - index * 30, line)
    canvas.save()
    with pdf.open("rb") as stream:
        response = requests.post(base + "/documents/upload", files={
            "file": (pdf.name, stream, "application/pdf")}, timeout=30)
    response.raise_for_status()
    uploaded = response.json()
    document_id = uploaded["document_id"]
    deadline = time.monotonic() + 180
    while True:
        document = get("/documents/" + document_id)
        if document["status"] in {"READY", "PARTIAL", "FAILED", "INTERRUPTED"}:
            break
        if time.monotonic() > deadline:
            raise TimeoutError("PDF did not finish processing within 180 seconds")
        time.sleep(2)
    if document["status"] != "READY":
        raise RuntimeError(f"PDF processing status: {document['status']}")
    response = requests.post(base + "/chat", json={"message":
        "Explain the purpose of a balance sheet in one sentence.",
        "temperature": 0, "max_tokens": 80, "model": "qwen2.5:3b"}, timeout=360)
    response.raise_for_status()
    chat = response.json()
    response = requests.post(base + "/rag/query", json={
        "question": "How did Acme Verification Company use its operating cash flow in fiscal 2025?",
        "document_id": document_id, "top_k": 3, "score_threshold": 0,
        "generate_answer": True, "model": "qwen2.5:3b"}, timeout=360)
    response.raise_for_status()
    rag = response.json()
    after = get("/qdrant/status")
    chunks = get("/documents/" + document_id + "/chunks")
    sources = rag.get("supporting_sources", [])
    citation_ok = bool(sources) and any(source.get("filename") == pdf.name
                  and source.get("page") == 1 for source in sources)
    expected_answer = "solar" in rag.get("answer", "").lower() and "logistics" in rag.get("answer", "").lower()
    errors = {
        "empty_chat": requests.post(base + "/chat", json={"message": ""}, timeout=10).status_code,
        "missing_document": requests.get(base + "/documents/does-not-exist", timeout=10).status_code,
        "invalid_upload": requests.post(base + "/documents/upload", files={
            "file": ("invalid.txt", b"not a PDF", "text/plain")}, timeout=10).status_code,
    }
    result = {"document": document, "chat": chat, "rag": rag, "chunks": chunks,
              "qdrant_before": before, "qdrant_after": after, "error_handling": errors,
              "checks": {"chat_nonempty": bool(chat.get("answer")),
                         "rag_expected_answer": expected_answer, "source_filename_and_page": citation_ok,
                         "qdrant_dimension_768": after.get("dimension") == 768,
                         "error_responses": errors == {"empty_chat": 422, "missing_document": 404,
                                                       "invalid_upload": 415}}}
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--collection", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = verify(args.base_url.rstrip("/"), args.output, args.collection)
    print(json.dumps(result["checks"]))
    raise SystemExit(0 if all(result["checks"].values()) else 1)

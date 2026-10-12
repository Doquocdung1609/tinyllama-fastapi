"""Evaluate the locked Phase 1 implementation on a fresh, manually sealed holdout."""
from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
import sys
import time
import unicodedata
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.services.calculation_service import parse_financial_number

API = "http://127.0.0.1:8002"
REPORT = ROOT / "reports" / "phase1_generalization.csv"
DETAILS = ROOT / "reports" / "phase1_generalization_details.json"


def normalized(value: str) -> str:
    text = unicodedata.normalize("NFKD", value.casefold().replace("đ", "d"))
    return " ".join("".join(char for char in text if not unicodedata.combining(char)).split())


def numeric_values(value: str) -> list[float]:
    found = []
    for raw in re.findall(r"(?<!\w)[-−]?\s*\d+(?:[.,]\d+)*", value):
        parsed = parse_financial_number(raw.replace("−", "-"))
        if parsed:
            found.append(parsed[0])
    return found


def contains_number(answer: str, expected: float) -> bool:
    return any(abs(actual - expected) <= max(1e-9, abs(expected) * 1e-10)
               for actual in numeric_values(answer))


def upload(path: Path) -> dict:
    with path.open("rb") as stream:
        response = requests.post(API + "/documents/upload",
            files={"file": (path.name, stream, "application/pdf")}, timeout=180)
    response.raise_for_status()
    state = response.json()
    for _ in range(900):
        state = requests.get(f"{API}/documents/{state['document_id']}", timeout=15).json()
        if state.get("status") in {"READY", "PARTIAL", "FAILED"}:
            return state
        time.sleep(.5)
    return state


def evaluate(case: dict, payload: dict, latency_ms: float, *, conversation_id: str = "") -> tuple[dict, dict]:
    answer = payload.get("answer") or payload.get("assistant_message", {}).get("content") or ""
    citations = (payload.get("supporting_sources") or
                 payload.get("assistant_message", {}).get("citations") or [])
    included = payload.get("included_prompt_context") or payload.get("rag", {}).get("included_prompt_context") or []
    selected = payload.get("selected_evidence") or payload.get("rag", {}).get("selected_evidence") or []
    evidence_text = " ".join(str(item.get("text") or "") for item in included)
    answer_text, evidence_norm = normalized(answer), normalized(evidence_text)
    phrase_ok = all(normalized(claim) in answer_text for claim in case.get("claims", []))
    numeric_ok = all(contains_number(answer, value) for value in case.get("numbers", []))
    extraction_phrase_ok = all(normalized(claim) in evidence_norm for claim in case.get("evidence_claims", case.get("claims", [])))
    extraction_numeric_ok = all(contains_number(evidence_text, value) for value in case.get("numbers", []))
    refusal = any(value in answer_text for value in (
        "khong cung cap", "khong co du", "chua cung cap", "khong tim thay"))
    cited_pages = {int(item["page"]) for item in citations if item.get("page") is not None}
    expected_pages = set(case.get("pages", []))
    citation_ok = not citations if case.get("refusal") else bool(cited_pages & expected_pages)
    extraction_ok = (True if case.get("refusal") or case.get("structural")
                     else extraction_phrase_ok and extraction_numeric_ok)
    answer_correct = refusal if case.get("refusal") else phrase_ok and numeric_ok
    completeness = answer_correct
    refusal_correct = refusal if case.get("refusal") else not refusal
    unit_ok = all(unit.casefold() in answer.casefold() for unit in case.get("units", []))
    if not case.get("units"):
        unit_ok = True
    context_ok = bool(payload.get("resolution", {}).get("resolved_question")) if case.get("follow_up") else True
    strict = all((answer_correct, completeness, numeric_ok, citation_ok, refusal_correct,
                  context_ok, extraction_ok, unit_ok))
    failures = []
    for name, passed in (("answer", answer_correct), ("completeness", completeness),
                         ("numeric", numeric_ok), ("unit", unit_ok), ("citation", citation_ok),
                         ("refusal", refusal_correct), ("context", context_ok),
                         ("extraction", extraction_ok)):
        if not passed:
            failures.append(name)
    document = case["document"]
    row = {
        "test_id": case["id"], "dataset": "INTERNAL HOLDOUT - SEALED AFTER 32d2509",
        "document_id": document["document_id"], "document_hash": document["content_hash"],
        "conversation_id": conversation_id, "source_pages": ";".join(map(str, case.get("pages", []))),
        "expected_claims": ";".join(case.get("claims", [])),
        "expected_numeric_values": ";".join(str(value) for value in case.get("numbers", [])),
        "actual_answer": answer,
        "selected_evidence": ";".join(str(item.get("source_id")) for item in selected),
        "included_prompt_evidence": ";".join(str(item.get("evidence_id") or item.get("source_id")) for item in included),
        "answer_correct": answer_correct, "answer_complete": completeness,
        "numerical_correct": numeric_ok, "citation_correct": citation_ok,
        "refusal_correct": refusal_correct, "context_resolution_correct": context_ok,
        "extraction_correct": extraction_ok, "correct_user_facing_answer": answer_correct and completeness,
        "unit_correct": unit_ok, "strict_status": "PASS" if strict else "FAIL",
        "failure_category": ";".join(failures),
        "explanation": "all mandatory claim-level checks passed" if strict else "failed: " + ", ".join(failures),
        "latency_ms": round(latency_ms, 1), "model": payload.get("model", "qwen2.5:3b"),
        "code_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    }
    return row, {"case": {key: value for key, value in case.items() if key != "document"}, "response": payload}


def main() -> None:
    sources = {
        "risk": Path(r"C:\Users\Admin\Downloads\Slide HV - Chương 1-Tổng quan.SV.pdf"),
        "paper": Path(r"C:\Users\Admin\Downloads\2506.08726v3.pdf"),
        "scan": Path(r"C:\Users\Admin\Downloads\Đề 4 - d21.PDF"),
    }
    documents = {name: upload(path) for name, path in sources.items()}
    for name, path in sources.items():
        documents[name]["verified_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    cases = [
        {"id": "FH01", "doc": "risk", "q": "Theo mục 1.2, có bao nhiêu loại rủi ro tài chính và gồm những loại nào?",
         "numbers": [4], "claims": ["rủi ro tín dụng", "rủi ro thanh khoản", "rủi ro lãi suất", "rủi ro tỷ giá"], "pages": [18]},
        {"id": "FH02", "doc": "risk", "q": "Rủi ro thanh khoản có bốn đặc điểm nào?",
         "numbers": [4], "claims": ["thiếu hụt dòng tiền", "không đáp ứng đúng hạn", "huy động vốn khẩn cấp", "bán tài sản với giá thấp"], "pages": [22]},
        {"id": "FH03", "doc": "paper", "q": "Trong Table 1, độ chính xác Combined của CoT+cal với GPT4t là bao nhiêu?",
         "numbers": [82.6], "units": ["%"], "claims": [], "pages": [4]},
        {"id": "FH04", "doc": "paper", "q": "Trong Table 1, độ chính xác Combined của PoT với llama3 là bao nhiêu?",
         "numbers": [75.7], "units": ["%"], "claims": [], "pages": [4]},
        {"id": "FH05", "doc": "scan", "q": "Ở Câu 5 trang 2, tài sản rủi ro có tỷ suất sinh lợi và độ lệch chuẩn bao nhiêu?",
         "numbers": [15, 25], "units": ["%"], "claims": ["tỷ suất sinh lợi", "độ lệch chuẩn"], "pages": [2]},
        {"id": "FH06", "doc": "scan", "q": "Ở Câu 4 trang 2, tỷ suất sinh lợi phi rủi ro và của danh mục thị trường lần lượt là bao nhiêu?",
         "numbers": [5, 12], "units": ["%"], "claims": [], "pages": [2]},
        {"id": "FH07", "doc": "risk", "q": "Tài liệu cho biết Basel IV có hiệu lực chính thức vào ngày nào?",
         "numbers": [], "claims": [], "pages": [], "refusal": True},
        {"id": "FH08", "doc": "risk", "q": "Trang 18 có bao nhiêu bảng, biểu đồ và hình/sơ đồ?",
         "numbers": [0], "claims": ["0 bảng", "0 biểu đồ", "0 hình"], "evidence_claims": [],
         "pages": [18], "structural": True},
    ]
    for case in cases:
        case["document"] = documents[case["doc"]]

    rows, details = [], []
    for case in cases:
        started = time.perf_counter()
        response = requests.post(API + "/rag/query", json={"question": case["q"],
            "document_id": case["document"]["document_id"], "top_k": 8,
            "score_threshold": .25}, timeout=300)
        elapsed = (time.perf_counter() - started) * 1000
        response.raise_for_status()
        row, detail = evaluate(case, response.json(), elapsed)
        rows.append(row); details.append(detail)
        print(case["id"], row["strict_status"], row["actual_answer"][:180].replace("\n", " "))

    followups = [
        {"id": "FH09", "doc": "risk", "first": cases[0]["q"], "q": "Loại thứ hai là gì?",
         "numbers": [], "claims": ["rủi ro thanh khoản"], "pages": [18], "follow_up": True},
        {"id": "FH10", "doc": "paper", "first": cases[2]["q"], "q": "Còn PoT với llama3 thì sao?",
         "numbers": [75.7], "units": ["%"], "claims": [], "pages": [4], "follow_up": True},
        {"id": "FH11", "doc": "scan", "first": cases[4]["q"],
         "q": "Còn hai tỷ suất ở Câu 4 ngay phía trên?", "numbers": [5, 12], "units": ["%"],
         "claims": [], "pages": [2], "follow_up": True},
    ]
    for case in followups:
        case["document"] = documents[case["doc"]]
        conversation = requests.post(API + "/conversations", json={
            "title": "phase1-fresh-holdout", "active_document_ids": [case["document"]["document_id"]]}, timeout=30).json()
        endpoint = API + f"/conversations/{conversation['conversation_id']}/messages"
        requests.post(endpoint, json={"content": case["first"], "top_k": 8, "score_threshold": .25}, timeout=300).raise_for_status()
        started = time.perf_counter()
        response = requests.post(endpoint, json={"content": case["q"], "top_k": 8, "score_threshold": .25}, timeout=300)
        elapsed = (time.perf_counter() - started) * 1000
        response.raise_for_status()
        row, detail = evaluate(case, response.json(), elapsed, conversation_id=conversation["conversation_id"])
        rows.append(row); details.append(detail)
        print(case["id"], row["strict_status"], row["actual_answer"][:180].replace("\n", " "))

    with REPORT.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    DETAILS.write_text(json.dumps({"sealed_after_commit": "32d2509", "documents": documents,
                                   "rows": rows, "details": details}, ensure_ascii=False, indent=2), encoding="utf-8")
    print({"total": len(rows), "pass": sum(row["strict_status"] == "PASS" for row in rows),
           "fail": sum(row["strict_status"] == "FAIL" for row in rows)})


if __name__ == "__main__":
    main()

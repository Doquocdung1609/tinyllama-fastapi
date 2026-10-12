"""Re-run the first internal holdout after it became development regression data."""
from __future__ import annotations

import csv
import json
import re
import subprocess
import sys
import time
from pathlib import Path

import pymupdf
import requests
from reportlab.lib import colors
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.services.calculation_service import parse_financial_number

OUT = ROOT / "tmp" / "phase1_holdout"
API = "http://127.0.0.1:8002"


def numeric_claim_present(expected: str, answer: str) -> bool:
    target = parse_financial_number(expected)
    if not target:
        return expected.casefold() in answer.casefold()
    candidates = re.findall(r"(?<!\w)[-−]?\s*\d+(?:[.,]\d+)*", answer)
    for raw in candidates:
        parsed = parse_financial_number(raw.replace("−", "-"))
        if parsed and abs(parsed[0] - target[0]) <= max(1e-9, abs(target[0]) * 1e-12):
            return True
    return False


def subset(source: Path, target: Path, pages: list[int]) -> None:
    original = pymupdf.open(source); output = pymupdf.open()
    for page in pages: output.insert_pdf(original, from_page=page - 1, to_page=page - 1)
    output.save(target); output.close(); original.close()


def chart_fixture(target: Path) -> None:
    pdf = canvas.Canvas(str(target))
    pdf.setFont("Helvetica-Bold", 16); pdf.drawString(55, 790, "CHART 1. AUDITED SALES BAR CHART")
    for index, (year, value) in enumerate(((2024, 90), (2025, 110), (2026, 145))):
        x = 90 + index * 120
        pdf.setFillColor(colors.HexColor("#4472C4")); pdf.rect(x, 300, 60, value * 2, fill=1)
        pdf.setFillColor(colors.black); pdf.drawString(80, 240 - index * 18, f"{year}: {value} USD million")
    pdf.save()


def upload(path: Path) -> dict:
    with path.open("rb") as stream:
        response = requests.post(API + "/documents/upload",
            files={"file": (path.name, stream, "application/pdf")}, timeout=180)
    response.raise_for_status(); document = response.json(); document_id = document["document_id"]
    for _ in range(600):
        state = requests.get(f"{API}/documents/{document_id}", timeout=15).json()
        if state.get("status") in {"READY", "PARTIAL", "FAILED"}: return state
        time.sleep(.5)
    return state


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    sources = {
        "monthly": Path(r"C:\Users\Admin\Downloads\monthly-revenue-03-2026.pdf"),
        "paper": Path(r"C:\Users\Admin\Downloads\Impact_of_Fintechs_Development_on_Bank_Performanc.pdf"),
        "scan2023": OUT / "shs_2023_scan_p20.pdf",
        "scan2025": OUT / "shs_2025_scan_p14_p15.pdf",
        "chart": OUT / "fresh_audited_chart.pdf",
    }
    subset(Path(r"C:\Users\Admin\Downloads\SHS_2023CN_BCTC_KT_24062024095306.pdf"), sources["scan2023"], [20])
    subset(Path(r"C:\Users\Admin\Downloads\_603966_Bao_cao_tai_chinh_nam_2025_1774500281.pdf"), sources["scan2025"], [14, 15])
    chart_fixture(sources["chart"])
    documents = {name: upload(path) for name, path in sources.items()}
    print({name: (value.get("status"), value.get("pages"), value.get("chunks")) for name, value in documents.items()})

    cases = [
        {"id": "H01", "doc": "monthly", "q": "Tổng số đơn hàng trong kỳ là bao nhiêu?", "claims": ["0"], "pages": {1}},
        {"id": "H02", "doc": "monthly", "q": "Giá trị đơn hàng trung bình là bao nhiêu?", "claims": ["0,00"], "pages": {1}},
        {"id": "H03", "doc": "paper", "q": "Trong Bảng 1, biến ROA có bao nhiêu quan sát?", "claims": ["150"], "pages": {10}},
        {"id": "H04", "doc": "paper", "q": "Giá trị trung bình của ROA trong Bảng 1 là bao nhiêu?", "claims": ["0.0051966"], "pages": {10}},
        {"id": "H05", "doc": "scan2023", "q": "Tiền và các khoản tương đương tiền cuối năm 2023 là bao nhiêu?", "claims": ["851889363555"], "pages": {1}},
        {"id": "H06", "doc": "scan2025", "q": "Lợi nhuận kế toán sau thuế TNDN năm 2025 là bao nhiêu?", "claims": ["1343177484141"], "pages": {2}},
        {"id": "H07", "doc": "scan2025", "q": "Lợi nhuận kế toán sau thuế TNDN năm 2024 là bao nhiêu?", "claims": ["-1015614429067"], "pages": {2}},
        {"id": "H08", "doc": "chart", "q": "Năm nào có doanh số cao nhất và bằng bao nhiêu?", "claims": ["2026", "145"], "pages": {1}},
        {"id": "H09", "doc": "monthly", "q": "Báo cáo có nêu tỷ giá EUR/VND năm 2035 không?", "claims": [], "pages": set(), "refusal": True},
    ]
    rows, details = [], []
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    for case in cases:
        document_id = documents[case["doc"]]["document_id"]
        started = time.perf_counter()
        response = requests.post(API + "/rag/query", json={"question": case["q"],
            "document_id": document_id, "top_k": 8, "score_threshold": .25}, timeout=300)
        elapsed = (time.perf_counter() - started) * 1000; payload = response.json(); answer = payload.get("answer", "")
        claims_ok = all(numeric_claim_present(claim, answer) for claim in case["claims"])
        refusal = any(value in answer.casefold() for value in
                      ("không cung cấp", "không có đủ", "chưa cung cấp", "không tìm thấy"))
        citations = payload.get("supporting_sources") or []
        cited_pages = {int(item["page"]) for item in citations if item.get("page")}
        citation_ok = (bool(citations) and bool(cited_pages & case["pages"])) if not case.get("refusal") else not citations
        passed = response.status_code == 200 and ((refusal and citation_ok) if case.get("refusal") else claims_ok and citation_ok)
        rows.append({"test_id": case["id"], "dataset": "DEVELOPMENT REGRESSION", "source_document": sources[case["doc"]].name,
                     "document_id": document_id, "verified_gold_answer": ";".join(case["claims"]) or "grounded refusal",
                     "gold_pages": ";".join(map(str, sorted(case["pages"]))), "question": case["q"], "actual_answer": answer,
                     "retrieved_source_ids": ";".join(str(item.get("source_id")) for item in payload.get("selected_evidence", [])),
                     "included_evidence_ids": ";".join(str(item.get("evidence_id")) for item in payload.get("included_prompt_context", [])),
                     "required_facets": ";".join(case["claims"]) or "refusal", "answer_correct": claims_ok if not case.get("refusal") else refusal,
                     "answer_complete": claims_ok if not case.get("refusal") else refusal,
                     "numerical_correct": claims_ok, "unit_correct": claims_ok,
                     "citation_correct": citation_ok, "refusal_correct": refusal if case.get("refusal") else True,
                     "latency_ms": round(elapsed, 1), "strict_status": "PASS" if passed else "FAIL",
                     "failure_reason": "" if passed else "claim/refusal/citation contract failed", "model": payload.get("model"),
                     "code_commit": commit})
        details.append({"case": {**case, "pages": sorted(case["pages"])}, "response": payload})
        print(case["id"], rows[-1]["strict_status"], answer[:160].replace("\n", " "))

    # Persistent multi-turn probes, assessed separately from the locked single-turn holdout score.
    conversations = []
    for name, turns in {
        "monthly": ["Tổng số đơn hàng trong kỳ là bao nhiêu?", "Giá trị đơn hàng trung bình thì sao?"],
        "paper": ["Trong Bảng 1, biến ROA có bao nhiêu quan sát?", "Giá trị trung bình của biến đó là bao nhiêu?"],
        "scan2025": ["Lợi nhuận sau thuế năm 2025 là bao nhiêu?", "Thế còn năm 2024?"],
        "chart": ["Năm nào có doanh số cao nhất?", "Giá trị của năm đó là bao nhiêu?"],
    }.items():
        created = requests.post(API + "/conversations", json={"active_document_ids": [documents[name]["document_id"]],
                                 "title": f"holdout-{name}"}, timeout=30).json()
        transcript = []
        for turn in turns:
            result = requests.post(API + f"/conversations/{created['conversation_id']}/messages",
                json={"content": turn, "top_k": 8, "score_threshold": .25}, timeout=300).json()
            transcript.append({"question": turn, "answer": result.get("assistant_message", {}).get("content"),
                               "resolved_question": result.get("resolution", {}).get("resolved_question"),
                               "citations": result.get("assistant_message", {}).get("citations")})
        conversations.append({"document_type": name, "conversation_id": created["conversation_id"], "turns": transcript})

    report = ROOT / "reports" / "phase1_development_holdout1_after.csv"
    with report.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    (ROOT / "reports" / "phase1_development_holdout1_after_details.json").write_text(
        json.dumps({"documents": documents, "cases": details, "conversations": conversations},
                   ensure_ascii=False, indent=2), encoding="utf-8")
    print({"total": len(rows), "pass": sum(item["strict_status"] == "PASS" for item in rows)})


if __name__ == "__main__":
    main()

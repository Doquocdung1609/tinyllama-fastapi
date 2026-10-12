"""Run the supported deterministic finance formula set through real FastAPI."""
from __future__ import annotations

import csv
import json
import subprocess
import time
from pathlib import Path

import requests
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet

ROOT = Path(__file__).resolve().parents[1]
API = "http://127.0.0.1:8002"


def fixture(path: Path) -> None:
    pdfmetrics.registerFont(TTFont("Phase1Arial", r"C:\Windows\Fonts\arial.ttf"))
    styles = getSampleStyleSheet(); styles["Title"].fontName = "Phase1Arial"
    data = [["Chỉ tiêu", "2023", "2024", "Đơn vị"],
            ["Doanh thu thuần", "1 tỷ đồng", "1,25 tỷ đồng", "VND"],
            ["Lợi nhuận gộp", "400 triệu đồng", "500 triệu đồng", "VND"],
            ["Lợi nhuận sau thuế", "100 triệu đồng", "150 triệu đồng", "VND"],
            ["Tài sản ngắn hạn", "600 triệu đồng", "750 triệu đồng", "VND"],
            ["Hàng tồn kho", "100 triệu đồng", "150 triệu đồng", "VND"],
            ["Nợ ngắn hạn", "300 triệu đồng", "375 triệu đồng", "VND"],
            ["Tổng nợ", "900 triệu đồng", "1 tỷ đồng", "VND"],
            ["Tổng tài sản", "1,8 tỷ đồng", "2 tỷ đồng", "VND"],
            ["Tổng tài sản bình quân", "1,7 tỷ đồng", "1,9 tỷ đồng", "VND"],
            ["Vốn chủ sở hữu bình quân", "850 triệu đồng", "950 triệu đồng", "VND"],
            ["Lưu chuyển tiền thuần từ hoạt động kinh doanh", "180 triệu đồng", "240 triệu đồng", "VND"],
            ["Chi mua sắm tài sản cố định", "(60) triệu đồng", "(80) triệu đồng", "VND"]]
    table = Table(data, colWidths=[230, 90, 90, 60], repeatRows=1)
    table.setStyle(TableStyle([("FONTNAME", (0, 0), (-1, -1), "Phase1Arial"),
                               ("FONTSIZE", (0, 0), (-1, -1), 8),
                               ("GRID", (0, 0), (-1, -1), .5, colors.grey),
                               ("BACKGROUND", (0, 0), (-1, 0), colors.lightblue)]))
    SimpleDocTemplate(str(path), pagesize=A4).build([
        Paragraph("Bảng 1. Chỉ tiêu tài chính kiểm thử độc lập", styles["Title"]), Spacer(1, 8), table])


def main() -> None:
    pdf = ROOT / "tmp" / "phase1_financial_core.pdf"; fixture(pdf)
    with pdf.open("rb") as stream:
        uploaded = requests.post(API + "/documents/upload",
            files={"file": (pdf.name, stream, "application/pdf")}, timeout=60).json()
    document_id = uploaded["document_id"]
    for _ in range(240):
        state = requests.get(f"{API}/documents/{document_id}", timeout=10).json()
        if state.get("status") in {"READY", "PARTIAL", "FAILED"}: break
        time.sleep(.5)
    cases = [
        ("FIN01", "Revenue growth", "Tính tăng trưởng doanh thu từ 2023 đến 2024", "growth_rate", 25.0, "%"),
        ("FIN02", "Profit growth", "Tính tăng trưởng lợi nhuận sau thuế từ 2023 đến 2024", "growth_rate", 50.0, "%"),
        ("FIN03", "Gross margin", "Tính biên lợi nhuận gộp năm 2024", "financial_ratio", 40.0, "%"),
        ("FIN04", "Net margin", "Tính biên lợi nhuận ròng năm 2024", "financial_ratio", 12.0, "%"),
        ("FIN05", "Current ratio", "Tính tỷ lệ thanh toán hiện hành năm 2024", "financial_ratio", 2.0, "lần"),
        ("FIN06", "Quick ratio", "Tính tỷ lệ thanh toán nhanh năm 2024", "financial_ratio", 1.6, "lần"),
        ("FIN07", "Debt/assets", "Tính tỷ lệ nợ trên tổng tài sản năm 2024", "financial_ratio", 50.0, "%"),
        ("FIN08", "ROA average assets", "Tính ROA năm 2024", "financial_ratio", 150 / 1900 * 100, "%"),
        ("FIN09", "ROE average equity", "Tính ROE năm 2024", "financial_ratio", 150 / 950 * 100, "%"),
        ("FIN10", "Operating cash flow ratio", "Tính tỷ lệ dòng tiền hoạt động năm 2024", "financial_ratio", 240 / 375, "lần"),
        ("FIN11", "Free cash flow", "Tính dòng tiền tự do năm 2024", "free_cash_flow", 160.0, "triệu đồng"),
        ("FIN12", "Absolute difference", "Chênh lệch tuyệt đối doanh thu từ 2023 đến 2024", "absolute_change", .25, "tỷ đồng"),
    ]
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    rows, details = [], []
    for test_id, concept, question, operation, expected, unit in cases:
        started = time.perf_counter()
        response = requests.post(API + "/rag/query", json={"question": question,
            "document_id": document_id, "top_k": 5, "score_threshold": .35}, timeout=180)
        elapsed = (time.perf_counter() - started) * 1000; payload = response.json()
        calculation = payload.get("calculation_validation") or {}; actual = calculation.get("result")
        passed = (response.status_code == 200 and calculation.get("operation") == operation and
                  calculation.get("verified") is True and actual is not None and abs(float(actual) - expected) < 1e-6 and
                  (payload.get("citation_validation") or {}).get("citation_valid"))
        rows.append({"test_id": test_id, "concept": concept, "document_id": document_id, "question": question,
                     "formula": calculation.get("formula", ""), "expected_value": expected, "expected_unit": unit,
                     "actual_value": actual, "actual_unit": calculation.get("result_unit", ""),
                     "citation_source_ids": ";".join(str(item.get("source_id")) for item in payload.get("supporting_sources", [])),
                     "latency_ms": round(elapsed, 1), "status": "PASS" if passed else "FAIL",
                     "failure_reason": "" if passed else json.dumps(calculation, ensure_ascii=False),
                     "code_commit": commit})
        details.append({"case": test_id, "response": payload})
        print(test_id, rows[-1]["status"], actual)
    with (ROOT / "reports" / "phase1_financial_calculations.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    (ROOT / "reports" / "phase1_financial_calculation_details.json").write_text(
        json.dumps(details, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()

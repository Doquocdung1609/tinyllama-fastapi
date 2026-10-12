"""Build independently known scan fixtures and benchmark the local OCR path."""
from __future__ import annotations

import csv
import re
import subprocess
import threading
import time
from pathlib import Path

import psutil
import pymupdf
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from app.services.pdf_service import extract_pdf

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tmp" / "phase1_ocr"
REPORT = ROOT / "reports" / "phase1_ocr_benchmark.csv"
FONT = r"C:\Windows\Fonts\arial.ttf"


def _distance(left: list[str], right: list[str]) -> int:
    previous = list(range(len(right) + 1))
    for i, a in enumerate(left, 1):
        current = [i]
        for j, b in enumerate(right, 1):
            current.append(min(current[-1] + 1, previous[j] + 1,
                               previous[j - 1] + (a != b)))
        previous = current
    return previous[-1]


def _metrics(reference: str, actual: str) -> tuple[float, float]:
    norm = lambda value: re.sub(r"\s+", " ", value).strip().casefold()
    expected, observed = norm(reference), norm(actual)
    cer = _distance(list(expected), list(observed)) / max(1, len(expected)) * 100
    wer = _distance(expected.split(), observed.split()) / max(1, len(expected.split())) * 100
    return round(cer, 2), round(wer, 2)


def _scan(lines: list[str], name: str, *, border: bool = True, low_contrast: bool = False,
          angle: float = 0) -> tuple[Path, str]:
    width, height = 1654, 2339
    background = (242, 242, 238) if low_contrast else "white"
    foreground = (155, 155, 150) if low_contrast else "black"
    image = Image.new("RGB", (width, height), background)
    draw = ImageDraw.Draw(image)
    title_font = ImageFont.truetype(FONT, 42)
    font = ImageFont.truetype(FONT, 34)
    y = 150
    for index, line in enumerate(lines):
        draw.text((120, y), line, fill=foreground, font=title_font if index == 0 else font)
        if border and index >= 1 and index <= 4:
            draw.line((105, y + 48, 1520, y + 48), fill=foreground, width=2)
        y += 105
    if angle:
        image = image.rotate(angle, expand=False, fillcolor=background)
    path = OUT / f"{name}.pdf"
    image.save(path, "PDF", resolution=200)
    return path, " ".join(lines)


def _mixed(lines: list[str]) -> tuple[Path, str]:
    image = Image.new("RGB", (1400, 650), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(FONT, 34)
    y = 35
    for line in lines:
        draw.text((45, y), line, fill="black", font=font)
        y += 105
    image_path = OUT / "mixed_table.png"
    image.save(image_path)
    path = OUT / "mixed_native_image.pdf"
    pdf = canvas.Canvas(str(path), pagesize=A4)
    pdf.setFont("Helvetica", 12)
    pdf.drawString(55, 790, "Audited financial appendix - native text heading")
    pdf.drawImage(ImageReader(str(image_path)), 45, 390, width=505, height=235)
    pdf.save()
    return path, "Audited financial appendix native text heading " + " ".join(lines)


def main() -> None:
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    OUT.mkdir(parents=True, exist_ok=True)
    vi_table = ["BÁO CÁO TÀI CHÍNH", "Chỉ tiêu          2023       2024       Đơn vị",
                "Doanh thu         100        180        tỷ đồng",
                "Lợi nhuận          12         16        tỷ đồng",
                "Tổng tài sản      300        360        tỷ đồng"]
    en_table = ["FINANCIAL STATEMENT", "Metric             2023       2024       Unit",
                "Revenue            100        180        USD million",
                "Profit              12         16        USD million",
                "Total assets       300        360        USD million"]
    bilingual = ["BÁO CÁO / REPORT", "Chỉ tiêu / Metric  2023       2024       Đơn vị / Unit",
                 "Doanh thu / Revenue 100       180        tỷ đồng",
                 "Lợi nhuận / Profit  12        16         tỷ đồng"]
    source_k = pymupdf.open(ROOT / "tests" / "fixtures" / "pdfs" / "K_scanned_financial_table.pdf")
    k_vi = OUT / "known_k_vi.pdf"; k_en = OUT / "known_k_en.pdf"
    vi_doc = pymupdf.open(); vi_doc.insert_pdf(source_k, from_page=0, to_page=0); vi_doc.save(k_vi); vi_doc.close()
    en_doc = pymupdf.open(); en_doc.insert_pdf(source_k, from_page=1, to_page=1); en_doc.save(k_en); en_doc.close(); source_k.close()
    k_vi_reference = ("BÁO CÁO TÀI CHÍNH QUÉT Chỉ tiêu 2023 2024 Đơn vị Doanh thu 100 180 tỷ đồng "
                      "Lợi nhuận 12 16 tỷ đồng Tổng tài sản 300 360 tỷ đồng "
                      "Ghi chú: số liệu tổng hợp dùng cho kiểm thử OCR cục bộ.")
    k_en_reference = ("SCANNED FINANCIAL STATEMENT Metric 2023 2024 Unit Revenue 100 180 USD million "
                      "Profit 12 16 USD million Total assets 300 360 USD million "
                      "Note: synthetic figures for local OCR verification.")
    cases = [
        ("OCR-CLEAN-VI", *_scan(["TÀI LIỆU QUÉT", "Doanh thu năm 2024 là 250 triệu đồng.",
                                  "Lợi nhuận năm 2024 là 40 triệu đồng."], "clean_vi", border=False), [], []),
        ("OCR-TABLE-VI", *_scan(vi_table, "table_vi"), ["100", "180", "12", "16", "300", "360"], ["tỷ đồng"]),
        ("OCR-TABLE-EN", *_scan(en_table, "table_en"), ["100", "180", "12", "16", "300", "360"], ["USD million"]),
        ("OCR-BILINGUAL", *_scan(bilingual, "bilingual"), ["100", "180", "12", "16"], ["tỷ đồng"]),
        ("OCR-BORDERLESS", *_scan(vi_table, "borderless", border=False), ["100", "180", "12", "16", "300", "360"], ["tỷ đồng"]),
        ("OCR-ROTATED", *_scan(vi_table, "rotated", angle=4.0), ["100", "180", "12", "16", "300", "360"], ["tỷ đồng"]),
        ("OCR-LOW-CONTRAST", *_scan(vi_table, "low_contrast", low_contrast=True), ["100", "180", "12", "16", "300", "360"], ["tỷ đồng"]),
        ("OCR-MIXED", *_mixed(vi_table[1:]), ["100", "180", "12", "16", "300", "360"], ["tỷ đồng"]),
        ("OCR-K-VI-FINANCE", k_vi, k_vi_reference, ["100", "180", "12", "16", "300", "360"], ["tỷ đồng"]),
        ("OCR-K-EN-FINANCE", k_en, k_en_reference, ["100", "180", "12", "16", "300", "360"], ["USD million"]),
    ]
    process = psutil.Process()
    rows = []
    for case_id, path, reference, critical_numbers, expected_units in cases:
        peak = process.memory_info().rss
        running = True
        def sample() -> None:
            nonlocal peak
            while running:
                peak = max(peak, process.memory_info().rss)
                time.sleep(.01)
        thread = threading.Thread(target=sample, daemon=True)
        before = process.memory_info().rss
        thread.start(); started = time.perf_counter()
        try:
            pages = extract_pdf(path, case_id.lower(), path.name)
            error = ""
        except Exception as exc:
            pages, error = [], f"{type(exc).__name__}: {exc}"
        elapsed = (time.perf_counter() - started) * 1000
        running = False; thread.join(timeout=1)
        actual = " ".join(page.get("ocr", {}).get("text", "") if page.get("ocr") else page.get("text", "")
                          for page in pages)
        cer, wer = _metrics(reference, actual) if pages else (100.0, 100.0)
        number_tokens = re.findall(r"(?<!\w)\d+(?:[.,]\d+)?(?!\w)", actual)
        numeric_matches = sum(token in number_tokens for token in critical_numbers)
        tables = [table for page in pages for table in page.get("tables", [])]
        normalized_cells = []
        normalization_events = []
        for table in tables:
            normalized_cells.extend(table.get("normalized_columns") or table.get("columns") or [])
            for row in table.get("normalized_rows") or table.get("rows") or []:
                normalized_cells.extend(row)
            normalization_events.extend(table.get("normalization_events") or [])
        normalized_text = " ".join(str(value) for value in normalized_cells)
        is_vi_finance = case_id in {"OCR-TABLE-VI", "OCR-BORDERLESS", "OCR-ROTATED",
                                    "OCR-LOW-CONTRAST", "OCR-MIXED", "OCR-K-VI-FINANCE"}
        expected_headers = ["Chỉ tiêu", "Đơn vị"] if is_vi_finance else ["Metric", "Unit"] if "EN" in case_id else []
        expected_metrics = ["Doanh thu", "Lợi nhuận", "Tổng tài sản"] if is_vi_finance else \
                           ["Revenue", "Profit", "Total assets"] if "EN" in case_id else []
        raw_header_exact = sum(value.casefold() in actual.casefold() for value in expected_headers)
        raw_metric_exact = sum(value.casefold() in actual.casefold() for value in expected_metrics)
        normalized_header_exact = sum(value.casefold() in normalized_text.casefold() for value in expected_headers)
        normalized_metric_exact = sum(value.casefold() in normalized_text.casefold() for value in expected_metrics)
        units_exact = sum(unit.casefold() in actual.casefold() for unit in expected_units)
        status = "PASS" if not error and numeric_matches == len(critical_numbers) and (
            not critical_numbers or bool(tables)) else "PARTIAL" if pages else "FAIL"
        rows.append({
            "test_id": case_id, "source_pdf": str(path), "ground_truth": reference,
            "actual_raw_ocr": actual, "cer_percent": cer, "wer_percent": wer,
            "critical_numeric_exact": f"{numeric_matches}/{len(critical_numbers)}",
            "unit_exact": f"{units_exact}/{len(expected_units)}", "table_count": len(tables),
            "header_exact_raw": f"{raw_header_exact}/{len(expected_headers)}",
            "metric_exact_raw": f"{raw_metric_exact}/{len(expected_metrics)}",
            "header_exact_normalized": f"{normalized_header_exact}/{len(expected_headers)}",
            "metric_exact_normalized": f"{normalized_metric_exact}/{len(expected_metrics)}",
            "normalization_events": len(normalization_events),
            "table_statuses": ";".join(table.get("status", "") for table in tables),
            "row_alignment": ";".join(str(len(table.get("rows", []))) for table in tables),
            "ocr_language": ";".join(sorted({str(page.get('ocr', {}).get('language')) for page in pages if page.get('ocr')})),
            "runtime_ms": round(elapsed, 1), "peak_ram_delta_mb": round((peak - before) / 1024**2, 2),
            "status": status, "error": error, "code_commit": commit,
        })
        print(case_id, status, cer, wer, rows[-1]["critical_numeric_exact"], len(tables))
    with REPORT.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)


if __name__ == "__main__":
    main()

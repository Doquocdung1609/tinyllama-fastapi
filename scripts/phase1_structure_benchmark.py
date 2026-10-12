"""Coordinate-aware PDF structure regression benchmark."""
from __future__ import annotations

import csv
import json
import subprocess
from pathlib import Path

from app.services.pdf_service import _caption_near_bbox, extract_pdf, summarize_extraction

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "pdfs"
REAL = Path(r"C:\Users\Admin\Downloads\CO2_FDI_FINAL_PUBLICATION_READY.pdf")


def main() -> None:
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    extracted: dict[str, list[dict]] = {}
    for name in ("B_mixed_text_table.pdf", "I_multipage_table.pdf",
                 "L_mixed_text_table_chart.pdf", "F_process_diagram.pdf"):
        extracted[name] = extract_pdf(FIXTURES / name, Path(name).stem, name)
    real_pages = extract_pdf(REAL, "real03", REAL.name)
    rows = []
    def add(test_id, layout, source, expected, actual, evidence, passed):
        rows.append({"test_id": test_id, "layout": layout, "source_document": source,
                     "expected": expected, "actual": actual,
                     "coordinate_evidence": json.dumps(evidence, ensure_ascii=False),
                     "status": "PASS" if passed else "FAIL", "code_commit": commit})

    b = extracted["B_mixed_text_table.pdf"][0]["tables"][0]
    add("PDF01", "caption above table", "B_mixed_text_table.pdf",
        "BẢNG 1. KẾT QUẢ KINH DOANH TỔNG HỢP", b.get("caption"),
        {"table_bbox": b.get("bbox"), "caption": b.get("caption_provenance")},
        b.get("caption_status") == "VERIFIED_CAPTION")

    box = [50.0, 200.0, 550.0, 400.0]
    caption, provenance = _caption_near_bbox(
        [{"text": "Table 2: Revenue by segment", "bbox": [50.0, 405.0, 260.0, 420.0]}], box, "table", 800)
    add("PDF02", "caption below table", "synthetic coordinates", "Table 2: Revenue by segment",
        caption, {"table_bbox": box, "caption": provenance}, caption == "Table 2: Revenue by segment")

    caption, provenance = _caption_near_bbox([
        {"text": "Bảng 3. Doanh thu theo", "bbox": [50, 160, 230, 175], "font": "Arial", "font_size": 10},
        {"text": "phân khúc kinh doanh", "bbox": [50, 177, 215, 192], "font": "Arial", "font_size": 10}], box, "table", 800)
    add("PDF03", "multi-line caption", "synthetic coordinates",
        "Bảng 3. Doanh thu theo phân khúc kinh doanh", caption,
        {"table_bbox": box, "caption": provenance}, provenance.get("line_count") == 2)

    lpage = extracted["L_mixed_text_table_chart.pdf"][0]
    unknown = [table.get("caption_status") for table in lpage["tables"]]
    add("PDF04", "tables without captions", "L_mixed_text_table_chart.pdf",
        "2 UNKNOWN_CAPTION", str(unknown), {"bboxes": [table.get("bbox") for table in lpage["tables"]]},
        all(value == "UNKNOWN_CAPTION" for value in unknown))
    add("PDF05", "multiple tables on multi-column page", "L_mixed_text_table_chart.pdf",
        "2 tables; multi-column", f"{len(lpage['tables'])} tables; columns={lpage['diagnostics']['column_count']}",
        {"bboxes": [table.get("bbox") for table in lpage["tables"]]}, len(lpage["tables"]) == 2 and lpage["diagnostics"]["column_count"] == 2)

    first = extracted["I_multipage_table.pdf"][0]["tables"][0]
    second = extracted["I_multipage_table.pdf"][1]["tables"][0]
    add("PDF06", "repeated heading / continued table", "I_multipage_table.pdf",
        "linked page 1 to page 2", f"{first.get('continued_by')} -> {second.get('continued_from')}",
        {"first_caption": first.get("caption"), "second_caption": second.get("caption")},
        first.get("continued_by") == second.get("table_id") and second.get("continued_from") == first.get("table_id"))

    figure = extracted["F_process_diagram.pdf"][0]["figures"]
    add("PDF07", "real captioned diagram", "F_process_diagram.pdf", "one verified diagram",
        figure[0].get("caption") if figure else "none", {"bbox": figure[0].get("bbox") if figure else None}, bool(figure))

    real3 = real_pages[2]; table = real3["tables"][0]
    add("REAL03", "real caption plus table-rule false-figure guard", REAL.name,
        "Cấu trúc mẫu theo nhóm thu nhập; 0 figures",
        f"{table.get('caption')}; {len(real3['figures'])} figures",
        {"table_bbox": table.get("bbox"), "caption": table.get("caption_provenance"),
         "drawing_count": real3["diagnostics"].get("drawing_count")},
        "Cấu trúc mẫu theo nhóm thu nhập" in (table.get("caption") or "") and not real3["figures"])

    summary = summarize_extraction(real_pages)
    add("PDF09", "financial/research PDF with many tables", REAL.name, "13 tables, no false figures",
        f"{summary['tables']} tables; {summary['figures']} figures", summary,
        summary["tables"] == 13 and summary["figures"] == 0)

    target = ROOT / "reports" / "phase1_pdf_structure_benchmark.csv"
    with target.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    print({"total": len(rows), "pass": sum(row["status"] == "PASS" for row in rows)})


if __name__ == "__main__":
    main()

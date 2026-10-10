from pathlib import Path

from app.services.calculation_service import calculate_from_tables, parse_financial_number
from app.services.chunk_service import chunk_pages
from app.services.pdf_service import extract_pdf, render_page_preview, summarize_extraction


FIXTURES = Path(__file__).parent / "fixtures" / "pdfs"


def extracted(name: str):
    path = FIXTURES / name
    pages = extract_pdf(path, path.stem, path.name)
    return pages, summarize_extraction(pages), chunk_pages(pages, path.stem, path.name)


def test_native_table_preserves_headers_values_units_and_negative_numbers():
    pages, summary, chunks = extracted("C_financial_statement.pdf")

    assert summary["table_pages"] == 1 and summary["tables"] == 1
    table = pages[0]["tables"][0]
    assert table["status"] == "OK"
    assert table["columns"] == ["Chỉ tiêu", "2023", "2024", "Đơn vị"]
    assert ["Điều chỉnh giảm", "(25)", "(30)", "triệu đồng"] in table["rows"]
    table_chunk = next(chunk for chunk in chunks if chunk["modality"] == "table")
    assert "| Chỉ tiêu | 2023 | 2024 | Đơn vị |" in table_chunk["text"]
    assert table_chunk["bbox"] and table_chunk["source_id"].startswith("table:")


def test_chart_records_use_explicit_visible_labels():
    pages, summary, chunks = extracted("D_bar_line_charts.pdf")

    assert summary["chart_pages"] == 2 and summary["charts"] == 2
    assert [page["charts"][0]["chart_type"] for page in pages] == ["bar", "line"]
    assert {pair["label"] for pair in pages[0]["charts"][0]["label_value_pairs"]} >= {"2022", "2024"}
    assert sum(chunk["modality"] == "chart" for chunk in chunks) == 2
    assert all(chunk["confidence"] == "HIGH" for chunk in chunks if chunk["modality"] == "chart")


def test_pie_figure_scan_columns_and_multipage_table_detection(tmp_path):
    pie_pages, pie_summary, _ = extracted("E_pie_chart.pdf")
    figure_pages, figure_summary, _ = extracted("F_process_diagram.pdf")
    scan_pages, scan_summary, scan_chunks = extracted("G_scanned_document.pdf")
    column_pages, column_summary, _ = extracted("H_multi_column.pdf")
    multi_pages, multi_summary, multi_chunks = extracted("I_multipage_table.pdf")

    assert pie_summary["charts"] == 1 and pie_pages[0]["charts"][0]["chart_type"] == "pie"
    assert figure_summary["figures"] == 1 and "phê duyệt" in figure_pages[0]["figures"][0]["visible_text"].casefold()
    assert scan_summary["scanned_pages"] == 1 and scan_chunks == []
    assert "OCR_ENGINE_UNAVAILABLE" in scan_summary["warnings"]
    assert scan_pages[0]["diagnostics"]["ocr_status"] == "BLOCKED_ENGINE_UNAVAILABLE"
    assert column_summary["multi_column_pages"] == 1
    assert multi_summary["table_pages"] == 2
    first, second = multi_pages[0]["tables"][0], multi_pages[1]["tables"][0]
    assert first["continued_by"] == second["table_id"]
    assert second["continued_from"] == first["table_id"]
    assert all("| Mã | Quý | Giá trị (tỷ đồng) |" in chunk["text"]
               for chunk in multi_chunks if chunk["modality"] == "table")

    target = tmp_path / "preview.png"
    render_page_preview(FIXTURES / "B_mixed_text_table.pdf", 1, target)
    assert target.exists() and target.stat().st_size > 1000


def test_bilingual_and_plain_text_fixtures_are_not_misclassified():
    _, text_summary, text_chunks = extracted("A_text_only_vi.pdf")
    pages, mixed_summary, mixed_chunks = extracted("J_mixed_vi_en.pdf")

    assert text_summary["text_pages"] == 1 and text_summary["tables"] == 0
    assert {chunk["modality"] for chunk in text_chunks} == {"text"}
    assert mixed_summary["tables"] == 1
    assert "Revenue / Doanh thu" in pages[0]["tables"][0]["markdown"]
    assert {chunk["modality"] for chunk in mixed_chunks} == {"text", "table"}


def test_deterministic_financial_calculations_use_structured_table_evidence():
    _, _, chunks = extracted("C_financial_statement.pdf")
    table = next(chunk for chunk in chunks if chunk["modality"] == "table")
    table["prompt_position"] = 1

    growth = calculate_from_tables("Tính tốc độ tăng trưởng doanh thu từ 2023 đến 2024.", [table])
    ratio = calculate_from_tables("Tính tỷ lệ thanh toán hiện hành năm 2024.", [table])

    assert growth and round(growth["result"], 6) == 25.0
    assert "(1 250 - 1 000) / 1 000" in growth["answer"]
    assert ratio and ratio["result"] == 2.0
    assert ratio["inputs"] == {"Tài sản ngắn hạn": 750.0, "Nợ ngắn hạn": 375.0,
                               "unit": "triệu đồng"}
    assert parse_financial_number("(25) triệu đồng") == (-25.0, "triệu đồng")
    assert parse_financial_number("1.250") == (1250.0, "")

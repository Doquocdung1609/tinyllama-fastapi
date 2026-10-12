from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from app.services.calculation_service import calculate_from_tables, parse_financial_number, verify_financial_claim
from app.services.pdf_service import _caption_near_bbox, extract_pdf
from app.services.rag_service import _ground_draft_answer, _numeric_anchors


def _finance_table(status="OK"):
    return {
        "document_id": "f" * 32, "filename": "finance.pdf", "page": 1,
        "chunk_id": "table-finance", "source_id": "table:p1:t1", "modality": "table",
        "structured_data": {
            "status": status, "confidence": "HIGH" if status == "OK" else "LOW",
            "columns": ["Chỉ tiêu", "2023", "2024", "Đơn vị"],
            "rows": [
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
                ["Chi mua sắm tài sản cố định", "(60) triệu đồng", "(80) triệu đồng", "VND"],
            ],
        },
    }


def test_caption_selection_uses_geometry_and_explicit_unknown():
    table = [50.0, 200.0, 550.0, 400.0]
    lines = [
        {"text": "Bảng 1. Cơ cấu tài sản", "bbox": [50.0, 180.0, 250.0, 195.0]},
        {"text": "Bảng trong phần trước được thảo luận ở đây", "bbox": [50.0, 80.0, 300.0, 95.0]},
    ]
    caption, provenance = _caption_near_bbox(lines, table, "table", 800.0)
    assert caption == "Bảng 1. Cơ cấu tài sản"
    assert provenance["status"] == "VERIFIED_CAPTION" and provenance["position"] == "above"

    below, below_provenance = _caption_near_bbox(
        [{"text": "Table 2: Revenue by segment", "bbox": [50.0, 405.0, 260.0, 420.0]}],
        table, "table", 800.0)
    assert below == "Table 2: Revenue by segment" and below_provenance["position"] == "below"

    unknown, unknown_provenance = _caption_near_bbox(
        [{"text": "Revenue", "bbox": [50.0, 180.0, 120.0, 195.0]}], table, "table", 800.0)
    assert unknown is None and unknown_provenance["status"] == "UNKNOWN_CAPTION"

    multiline, multiline_provenance = _caption_near_bbox([
        {"text": "Bảng 3. Doanh thu theo", "bbox": [50.0, 160.0, 230.0, 175.0], "font": "Arial", "font_size": 10},
        {"text": "phân khúc kinh doanh", "bbox": [50.0, 177.0, 215.0, 192.0], "font": "Arial", "font_size": 10},
    ], table, "table", 800.0)
    assert multiline == "Bảng 3. Doanh thu theo phân khúc kinh doanh"
    assert multiline_provenance["line_count"] == 2


def test_narrative_model_word_and_table_drawing_do_not_create_false_figure(tmp_path: Path):
    path = tmp_path / "narrative-table.pdf"
    pdf = canvas.Canvas(str(path), pagesize=A4)
    pdf.drawString(50, 780, "The variables used in the model are complete.")
    pdf.drawString(50, 740, "Table 1. Sample structure")
    data = [["Group", "Count"], ["A", "10"], ["B", "20"]]
    x0, y0, row_h, col_w = 50, 700, 20, 180
    for row_index, row in enumerate(data):
        y = y0 - row_index * row_h
        for col_index, value in enumerate(row):
            x = x0 + col_index * col_w
            pdf.rect(x, y - row_h, col_w, row_h)
            pdf.drawString(x + 4, y - 14, value)
    pdf.save()

    page = extract_pdf(path, "synthetic", path.name)[0]
    assert page["tables"][0]["caption"] == "Table 1. Sample structure"
    assert page["tables"][0]["caption_status"] == "VERIFIED_CAPTION"
    assert page["figures"] == []


def test_financial_number_units_and_negative_amounts():
    assert parse_financial_number("(1.250,50) triệu đồng") == (-1250.5, "triệu đồng")
    assert parse_financial_number("1.25 billion USD") == (1.25, "billion USD")
    assert parse_financial_number("12,5 percent") == (12.5, "percent")


def test_supported_financial_formula_set_uses_verified_cells_and_units():
    table = _finance_table()
    cases = {
        "Tính tăng trưởng doanh thu từ 2023 đến 2024": ("growth_rate", 25.0),
        "Tính tăng trưởng lợi nhuận sau thuế từ 2023 đến 2024": ("growth_rate", 50.0),
        "Tính biên lợi nhuận gộp năm 2024": ("financial_ratio", 40.0),
        "Tính biên lợi nhuận ròng năm 2024": ("financial_ratio", 12.0),
        "Tính tỷ lệ thanh toán hiện hành năm 2024": ("financial_ratio", 2.0),
        "Tính tỷ lệ thanh toán nhanh năm 2024": ("financial_ratio", 1.6),
        "Tính tỷ lệ nợ trên tổng tài sản năm 2024": ("financial_ratio", 50.0),
        "Tính ROA năm 2024": ("financial_ratio", 150 / 1900 * 100),
        "Tính ROE năm 2024": ("financial_ratio", 150 / 950 * 100),
        "Tính tỷ lệ dòng tiền hoạt động năm 2024": ("financial_ratio", 240 / 375),
        "Tính dòng tiền tự do năm 2024": ("free_cash_flow", 160.0),
        "Chênh lệch tuyệt đối doanh thu từ 2023 đến 2024": ("absolute_change", .25),
    }
    for question, (operation, expected) in cases.items():
        actual = calculate_from_tables(question, [table])
        assert actual and actual["verified"], (question, actual)
        assert actual["operation"] == operation
        assert abs(actual["result"] - expected) < 1e-8, (question, actual)
        assert actual["evidence_ids"] == ["E1"]


def test_roa_rejects_ending_assets_and_uncertain_ocr_cells():
    table = _finance_table()
    table["structured_data"]["rows"] = [row for row in table["structured_data"]["rows"]
                                              if row[0] != "Tổng tài sản bình quân"]
    result = calculate_from_tables("Tính ROA năm 2024", [table])
    assert result["operation"] == "insufficient_calculation_inputs" and result["verified"] is False
    assert "số dư bình quân" in result["answer"]

    uncertain = _finance_table("NEEDS_REVIEW")
    assert calculate_from_tables("Tính tăng trưởng doanh thu từ 2023 đến 2024", [uncertain]) is None


def test_calculation_merges_only_included_slices_of_the_same_table():
    first = _finance_table()
    second = _finance_table()
    rows = first["structured_data"]["rows"]
    first["structured_data"]["table_id"] = "t1"
    second["structured_data"]["table_id"] = "t1"
    first["structured_data"]["rows"] = [row for row in rows if row[0] == "Nợ ngắn hạn"]
    second["structured_data"]["rows"] = [row for row in rows if row[0].startswith("Lưu chuyển tiền")]
    result = calculate_from_tables("Tính tỷ lệ dòng tiền hoạt động năm 2024", [first, second])
    assert result["verified"] is True and result["result"] == 240 / 375
    assert result["evidence_ids"] == ["E1", "E2"]


def test_claim_verification_does_not_cross_company_or_accept_uncertain_ocr():
    company_a = _finance_table()
    company_a["structured_data"]["caption"] = "Báo cáo tài chính Công ty Alpha"
    wrong_company = verify_financial_claim(
        "Lợi nhuận Công ty Beta năm 2024 là 150 triệu đồng đúng không?", [company_a])
    assert wrong_company["verification_status"] == "AMBIGUOUS"

    uncertain = _finance_table("NEEDS_REVIEW")
    result = verify_financial_claim("Lợi nhuận năm 2024 là 150 triệu đồng đúng không?", [uncertain])
    assert result["verification_status"] == "INSUFFICIENT_EVIDENCE"


def test_statistical_roa_questions_are_not_misrouted_to_ratio_calculation():
    table = _finance_table()
    assert calculate_from_tables("Biến ROA có bao nhiêu quan sát?", [table]) is None
    assert calculate_from_tables("Giá trị trung bình của ROA là bao nhiêu?", [table]) is None
    assert calculate_from_tables("Tính ROA năm 2024", [table])["verified"] is True


def test_bilingual_grounding_keeps_exact_numeric_claim_and_normalizes_locale():
    included = [{"text": "Total orders: 0. Average order value: 0.00 USD."}]
    answer, audit = _ground_draft_answer(
        "Tổng số đơn hàng là 0. [E1]\nGiá trị đơn hàng trung bình là 0,00 USD. [E1]",
        included,
        "Tổng số đơn hàng và giá trị đơn hàng trung bình là bao nhiêu?",
    )
    assert audit["kept_claims"] == 2
    assert "Tổng số đơn hàng" in answer and "Giá trị đơn hàng trung bình" in answer
    assert _numeric_anchors("0,00 USD") == _numeric_anchors("0.00 USD") == {"0"}


def test_ocr_text_lookup_preserves_year_order_sign_and_review_flag():
    evidence = [
        {"modality": "text", "text": "Năm 2025    Năm 2024\nVND VND"},
        {"modality": "text", "text": (
            "200 X. LỢI NHUẬN KẾ TOÁN SAU THUẾ TNDN "
            "1343.177.484.141 - 1.015.614.429.067")},
    ]
    current = calculate_from_tables("Lợi nhuận kế toán sau thuế TNDN năm 2025 là bao nhiêu?", evidence)
    prior = calculate_from_tables("Lợi nhuận kế toán sau thuế TNDN năm 2024 là bao nhiêu?", evidence)
    assert current["result"] == 1343177484141 and current["evidence_ids"] == ["E2"]
    assert prior["result"] == -1015614429067
    assert current["verified"] is False and current["requires_source_review"] is True

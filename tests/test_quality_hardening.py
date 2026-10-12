from app.services.calculation_service import (
    analyze_charts,
    verification_retrieval_question,
    verify_financial_claim,
)
from app.services import rag_service


def _table_item():
    return {
        "document_id": "a" * 32, "filename": "finance.pdf", "page": 1,
        "chunk_id": "table-1", "source_id": "table:p1:t1", "modality": "table",
        "structured_data": {
            "status": "OK", "confidence": "HIGH",
            "columns": ["Chỉ tiêu", "2023", "2024", "Đơn vị"],
            "rows": [["Doanh thu", "100", "125", "triệu đồng"],
                     ["Lợi nhuận", "12", "16", "triệu đồng"]],
        },
    }


def test_false_claim_is_retrieved_without_promoting_claimed_number():
    question = "Lợi nhuận năm 2024 là 15 triệu đồng đúng không?"
    retrieval = verification_retrieval_question(question)
    result = verify_financial_claim(question, [_table_item()])

    assert "15" not in retrieval
    assert "2024" in retrieval
    assert result["verification_status"] == "CONTRADICTED"
    assert result["source_value"] == 16
    assert "Không đúng" in result["answer"] and "16 triệu đồng" in result["answer"]
    assert result["evidence_ids"] == ["E1"]


def test_true_claim_is_confirmed_and_missing_claim_is_not_guessed():
    confirmed = verify_financial_claim("Lợi nhuận năm 2024 là 16 triệu đồng phải không?", [_table_item()])
    missing = verify_financial_claim("Kiểm tra lại lợi nhuận năm 2024.", [_table_item()])
    assert confirmed["verification_status"] == "CONFIRMED"
    assert confirmed["source_value"] == 16
    assert missing["verification_status"] == "INSUFFICIENT_EVIDENCE"


def test_claim_verification_supports_years_in_rows():
    item = _table_item()
    item["structured_data"] = {"status": "OK", "columns": ["Năm", "Doanh thu (triệu đồng)", "Lợi nhuận (triệu đồng)"],
                               "rows": [["2023", "100", "12"], ["2024", "125", "16"]]}
    result = verify_financial_claim("Lợi nhuận năm 2024 là 15 triệu đồng đúng không?", [item])
    assert result["verification_status"] == "CONTRADICTED"
    assert result["source_value"] == 16 and result["source_unit"] == "triệu đồng"
    assert result["source_cells"] == [{"row": "Lợi nhuận (triệu đồng)", "column": "2024", "value": "16"}]


def test_ambiguous_claim_requests_the_missing_period():
    result = verify_financial_claim("Doanh thu là 125 triệu đồng đúng không?", [_table_item()])
    assert result["verification_status"] == "AMBIGUOUS"
    assert "năm" in result["answer"]


def test_dual_axis_chart_does_not_compare_incompatible_units():
    chart = {"modality": "chart", "structured_data": {"chart_type": "dual_axis", "dual_axis": True,
        "axes": [{"unit": "tỷ đồng"}, {"unit": "%"}], "label_value_pairs": [
            {"label": "Doanh thu 2024", "value": "125 tỷ đồng"},
            {"label": "Biên lợi nhuận 2024", "value": "12%"}]}}
    result = analyze_charts("So sánh hai chuỗi trên biểu đồ", [chart])
    assert result["operation"] == "chart_axis_mismatch"
    assert result["verified"] is False


def test_image_chart_without_exact_labels_returns_qualified_limit():
    chart = {"modality": "chart", "structured_data": {"chart_type": "line", "label_value_pairs": []}}
    result = analyze_charts("Giá trị chính xác là bao nhiêu?", [chart])
    assert result["operation"] == "chart_capability_limit"
    assert "không thể xác nhận" in result["answer"]


def test_structural_inventory_and_second_table_explanation(monkeypatch):
    tables = [
        {"source_id": "table:p1:t1", "table_id": "t1", "columns": ["Chỉ tiêu", "2024"],
         "rows": [["Doanh thu", "125"]], "markdown": "table one", "status": "OK", "confidence": "HIGH"},
        {"source_id": "table:p1:t2", "table_id": "t2", "columns": ["Dòng tiền", "2023", "2024"],
         "rows": [["Kinh doanh", "20", "28"]], "markdown": "table two", "status": "OK", "confidence": "HIGH"},
    ]
    chunks = [{"document_id": "a" * 32, "filename": "mixed.pdf", "page": 1,
               "chunk_id": table["table_id"], "source_id": table["source_id"], "modality": "table",
               "text": table["markdown"], "structured_data": table} for table in tables]
    page = {"document_id": "a" * 32, "filename": "mixed.pdf", "page": 1,
            "tables": tables, "charts": [{"source_id": "chart:p1:c1", "chart_id": "c1",
                                             "chart_type": "bar", "title": "Doanh thu"}],
            "figures": [], "chunks": chunks}
    monkeypatch.setattr(rag_service, "page_inspection", lambda *_: page)

    inventory = rag_service._structural_document_answer(
        "Trang 1 có các bảng và biểu đồ nào?", "a" * 32, None)
    explanation = rag_service._structural_document_answer(
        "Giải thích bảng thứ hai trên trang 1. Bảng cần tìm có source ID table:p1:t2.", "a" * 32, None)

    assert "2 bảng, 1 biểu đồ" in inventory["answer"]
    assert inventory["structural_validation"]["status"] == "FULL"
    assert explanation["supporting_sources"][0]["source_id"] == "table:p1:t2"
    assert all(term in explanation["answer"] for term in ("Dòng tiền", "2023", "2024", "20", "28", "không ghi rõ đơn vị"))
    assert set(explanation["structural_validation"]["required_facets"]) <= set(
        explanation["structural_validation"]["covered_facets"])

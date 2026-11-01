"""Assistant retrieval routing keeps legacy behavior and numeric abstention."""

from app.product import frontend_api
from app.product.analysis import AnalysisRequest
from app.product.assistant_answer import contract, reviewed_plan


class _Workspace:
    def search(self, question, mode, top_k, document_ids):
        return {"generation": "legacy", "results": [{"text": "legacy source"}]}


def test_document_qa_explicitly_shares_production_search(monkeypatch):
    calls = []

    def search(payload):
        calls.append(payload)
        return {"generation": "locked-gen", "results": [{"text": "source row", "source_sha256": "raw-hash"}]}

    monkeypatch.setattr(frontend_api, "workspace", lambda: _Workspace())
    monkeypatch.setattr(frontend_api, "unified_search", search)
    monkeypatch.setattr(frontend_api, "eligible_facts", lambda *_: [])
    request = AnalysisRequest(question="Total assets in 2025?", document_ids=["pdf-1"], search_profile="production_v3")
    result = frontend_api.analysis(request)
    assert calls[0].source == "USER_UPLOADS"
    assert calls[0].document_ids == ["pdf-1"]
    assert calls[0].mode == "hybrid"
    assert calls[0].search_profile == "production_v3"
    assert result["status"] == "SOURCE_EXCERPTS"
    assert result["generation"] == "locked-gen"
    assert result["values"] == []


def test_document_qa_default_remains_legacy(monkeypatch):
    monkeypatch.setattr(frontend_api, "workspace", lambda: _Workspace())
    monkeypatch.setattr(frontend_api, "eligible_facts", lambda *_: [])
    result = frontend_api.analysis(AnalysisRequest(question="Total assets?", document_ids=["pdf-1"]))
    assert result["search_profile"] == "baseline"
    assert result["generation"] == "legacy"
    assert result["values"] == []


def test_extractive_narrative_and_numeric_warning():
    hits = {"generation": "g1", "results": [{"chunk_id": "c1", "page": 3, "source_sha256": "raw", "text": "The board approved the revised report."}]}
    narrative = contract("Why was the report revised?", hits, "production_v3")
    assert narrative["answer"] == "Tài liệu ghi: “The board approved the revised report.”"
    assert narrative["verification_status"] == "SOURCE_TEXT_UNREVIEWED"
    numeric = contract("How much were total assets?", hits, "production_v3")
    assert numeric["verification_status"] == "NUMERIC_UNVERIFIED"
    assert numeric["values"] == []
    assert numeric["evidence_references"][0]["source_sha256"] == "raw"


def test_numeric_question_for_absent_year_hides_unrelated_values():
    hits = {"generation": "g1", "results": [{"chunk_id": "c1", "page": 6,
             "report_period": "2024", "text": "TỔNG TÀI SẢN 2,760,906,964"}]}
    answer = contract("Tổng tài sản BIDV năm 2037 là bao nhiêu?", hits, "production_v3")
    assert answer["status"] == "INSUFFICIENT_EVIDENCE"
    assert answer["citations"] == []
    assert answer["values"] == []
    assert "kỳ được hỏi" in answer["answer"]


def test_unit_question_prefers_source_line_with_unit():
    hits = {"results": [
        {"chunk_id": "a", "text": "Quý IV năm | 2025 | 2024"},
        {"chunk_id": "b", "text": "Báo cáo kết quả kinh doanh\nQuý IV năm 2025 Quý IV năm 2024\nVND VND\nDoanh thu"},
    ]}
    answer = contract("Đơn vị báo cáo kết quả kinh doanh quý IV năm 2025 là gì?", hits, "production_v3")
    assert "VND VND" in answer["answer"]
    assert answer["answer_source_chunk_id"] == "b"


def test_reason_question_prefers_causal_statement_over_header():
    hits = {"results": [
        {"chunk_id": "header", "text": "BIDV công bố điều chỉnh báo cáo tài chính riêng lẻ hợp nhất năm 2024 đã kiểm toán"},
        {"chunk_id": "reason", "text": "BIDV điều chỉnh báo cáo tài chính 2024 theo kết quả Kiểm toán Nhà nước."},
    ]}
    answer = contract("BIDV công bố điều chỉnh báo cáo tài chính 2024 vì lý do gì?", hits, "production_v3")
    assert "theo kết quả Kiểm toán Nhà nước" in answer["answer"]
    assert answer["answer_source_chunk_id"] == "reason"


def test_reviewed_plan_requires_unique_period_scope_and_metric():
    facts = [{"metric": "assets", "period": "2025-12-31", "issuer": "HPG", "statement_scope": "SEPARATE", "currency": "VND", "basis": "AS_REPORTED"},
             {"metric": "assets", "period": "2024-12-31", "issuer": "HPG", "statement_scope": "SEPARATE", "currency": "VND", "basis": "AS_REPORTED"}]
    aliases = {"assets": ["tong tai san", "total assets"]}
    plan = reviewed_plan("Tong tai san cong ty me HPG 2025 so voi 2024 thay doi bao nhieu?", facts, aliases)
    assert plan["operation"] == "ABS_CHANGE"
    assert plan["current_period"] == "2025-12-31"
    assert reviewed_plan("Tong tai san HPG 2025?", facts + [dict(facts[0])], aliases) is None
    assert reviewed_plan("Tong tai san hop nhat HPG 2025?", facts, aliases) is None


def test_auto_uses_v3r3_only_for_owned_workspace(monkeypatch):
    class Controlled(_Workspace):
        search_candidate_version = "V3R3"

    seen = []
    monkeypatch.setattr(frontend_api, "workspace", lambda: Controlled())
    monkeypatch.setattr(frontend_api, "unified_search", lambda payload: (seen.append(payload.search_profile) or {"generation": "g", "results": []}))
    monkeypatch.setattr(frontend_api, "eligible_facts", lambda *_: [])
    result = frontend_api.analysis(AnalysisRequest(question="What were total assets in 2025?", document_ids=["pdf-1"], search_profile="auto"))
    assert seen == ["production_v3r3"]
    assert result["status"] == "INSUFFICIENT_EVIDENCE"


def test_direct_question_uses_only_existing_verified_fact(monkeypatch):
    fact = {"metric": "assets", "period": "2025-12-31", "issuer": "HPG", "statement_scope": "SEPARATE", "currency": "VND", "basis": "AS_REPORTED"}
    monkeypatch.setattr(frontend_api, "workspace", lambda: _Workspace())
    monkeypatch.setattr(frontend_api, "unified_search", lambda _: {"generation": "g", "results": [{"text": "row", "page": 3}]})
    monkeypatch.setattr(frontend_api, "eligible_facts", lambda *_: [fact])
    plans = []
    def verified(_, request):
        plans.append(request)
        return {"status": "SUPPORTED", "answer": "Reviewed cell", "values": ["100"], "citations": [fact], "verification": "DECIMAL_WITH_LOCALLY_REVIEWED_SOURCE_CELLS"}
    monkeypatch.setattr(frontend_api, "numeric_answer", verified)
    result = frontend_api.analysis(AnalysisRequest(question="Tong tai san cong ty me HPG 2025 la bao nhieu?", document_ids=["pdf-1"], search_profile="production_v3"))
    assert result["status"] == "SUPPORTED"
    assert plans[0].current_period == "2025-12-31"
    assert result["verification_status"] == "DECIMAL_WITH_LOCALLY_REVIEWED_SOURCE_CELLS"
    assert result["retrieval_trace"]["generation"] == "g"

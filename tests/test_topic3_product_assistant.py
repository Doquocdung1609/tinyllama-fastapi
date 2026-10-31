"""Assistant retrieval routing keeps legacy behavior and numeric abstention."""

from app.product import frontend_api
from app.product.analysis import AnalysisRequest


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
    result = frontend_api.analysis(AnalysisRequest(question="Total assets?", document_ids=["pdf-1"]))
    assert result["search_profile"] == "baseline"
    assert result["generation"] == "legacy"
    assert result["values"] == []

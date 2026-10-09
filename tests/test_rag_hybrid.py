from app.services import rag_service


class Provider:
    def embed(self, texts):
        return [[0.1, 0.2] for _ in texts]


class Point:
    def __init__(self, score, payload):
        self.score = score
        self.payload = payload


def test_hybrid_retrieval_rescues_exact_vietnamese_terms(monkeypatch):
    correct = {"filename": "finance.pdf", "document_id": "doc", "page": 155,
               "chunk_id": "correct", "text": "Căn cứ loại hình đổi mới tài chính, ba loại gồm đổi mới sản phẩm, đổi mới chuyển đổi rủi ro và đổi mới quy trình."}
    wrong = Point(.92, {"filename": "finance.pdf", "document_id": "doc", "page": 87,
                         "chunk_id": "wrong", "text": "Thông tin chung về doanh nghiệp."})
    monkeypatch.setattr(rag_service, "get_embedding_provider", lambda: Provider())
    monkeypatch.setattr(rag_service.qdrant_service, "search", lambda vector, limit, document_id=None: [wrong])
    monkeypatch.setattr(rag_service, "chunks_for", lambda document_id=None: [correct])
    monkeypatch.setattr(rag_service, "generate", lambda prompt, **kwargs: "Ba loại đổi mới (finance.pdf, trang 155).")

    result = rag_service.query("Ba loại đổi mới tài chính là gì?", 3, .5, "doc")

    assert result["sources"][0]["page"] == 155
    assert result["sources"][0]["lexical_score"] > 0
    assert result["retrieval_method"] == "hybrid_bm25_semantic"


def test_no_matching_context_returns_without_generation(monkeypatch):
    monkeypatch.setattr(rag_service, "get_embedding_provider", lambda: Provider())
    monkeypatch.setattr(rag_service.qdrant_service, "search", lambda vector, limit, document_id=None: [])
    monkeypatch.setattr(rag_service, "chunks_for", lambda document_id=None: [])
    monkeypatch.setattr(rag_service, "generate", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("must not generate")))

    result = rag_service.query("Giá Bitcoin năm 2026?", 3, .95, "doc")

    assert result["sources"] == []
    assert "không cung cấp đủ thông tin" in result["answer"]
    assert result["timings"]["generation_ms"] < 10


def test_document_filter_is_forwarded(monkeypatch):
    seen = {}
    monkeypatch.setattr(rag_service, "get_embedding_provider", lambda: Provider())
    monkeypatch.setattr(rag_service, "chunks_for", lambda document_id=None: [])
    def search(vector, limit, document_id=None):
        seen["document_id"] = document_id
        return []
    monkeypatch.setattr(rag_service.qdrant_service, "search", search)
    rag_service.query("Câu hỏi", 1, .9, "chosen-doc")
    assert seen["document_id"] == "chosen-doc"


def test_missing_numeric_anchor_rejects_high_semantic_match(monkeypatch):
    unrelated = {"filename": "finance.pdf", "document_id": "doc", "page": 10,
                 "chunk_id": "unrelated", "text": "Bitcoin và các công nghệ tài chính."}
    monkeypatch.setattr(rag_service, "get_embedding_provider", lambda: Provider())
    monkeypatch.setattr(rag_service.qdrant_service, "search",
                        lambda vector, limit, document_id=None: [Point(.95, unrelated)])
    monkeypatch.setattr(rag_service, "chunks_for", lambda document_id=None: [unrelated])
    monkeypatch.setattr(rag_service, "generate", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("must not generate")))

    result = rag_service.query("Giá Bitcoin ngày 31/12/2026 là bao nhiêu?", 3, .55, "doc")

    assert result["sources"] == []
    assert "không cung cấp đủ thông tin" in result["answer"]


def test_context_expands_adjacent_chunks_without_changing_retrieval_scores():
    chunks = [
        {"chunk_id": "a", "chunk_index": 10, "document_id": "doc", "text": "items one to three"},
        {"chunk_id": "b", "chunk_index": 11, "document_id": "doc", "text": "items four to eight"},
    ]
    retrieved = [{**chunks[0], "score": .8}]

    expanded = rag_service._context_with_neighbors(retrieved, chunks)

    assert [item["chunk_id"] for item in expanded] == ["a", "b"]
    assert expanded[1]["context_role"] == "adjacent"
    assert "score" not in expanded[1]

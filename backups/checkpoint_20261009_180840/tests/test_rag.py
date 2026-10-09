from app.services import rag_service


def test_query_uses_sources_and_prompt(monkeypatch):
    class Provider:
        def embed(self, texts): return [[0.1, 0.2] for _ in texts]
    class Point:
        score = .91
        payload = {"filename":"guide.pdf", "page":2, "chunk_id":"c1", "text":"The limit is ten."}
    monkeypatch.setattr(rag_service, "get_embedding_provider", lambda: Provider())
    monkeypatch.setattr(rag_service.qdrant_service, "search", lambda vector, limit: [Point()])
    monkeypatch.setattr(rag_service, "generate", lambda prompt, **kwargs: "The limit is ten (guide.pdf, page 2).")
    result = rag_service.query("What is the limit?", 3, .7)
    assert result["sources"][0]["page"] == 2
    assert "The limit is ten." in result["context"]
    assert "Question: What is the limit?" in result["final_prompt"]

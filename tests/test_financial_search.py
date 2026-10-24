"""Deterministic test suite: does not require Ollama, Qdrant server or GPU."""
from collections import namedtuple
import pytest
from app.services import financial_search_service as fs

CHUNKS = [
    {"chunk_id": "a", "document_id": "sec1", "filename": "10k.pdf", "page": 1,
     "text": "Revenue 2024 was 120 million USD",
     "metadata": {"ticker": "ABC", "fiscal_year": 2024}},
    {"chunk_id": "b", "document_id": "sec1", "filename": "10k.pdf", "page": 2,
     "text": "Liquidity and cash flow from operations",
     "metadata": {"ticker": "ABC", "fiscal_year": 2024}},
    {"chunk_id": "c", "document_id": "sec2", "filename": "10k.pdf", "page": 3,
     "text": "Revenue 2023 was 70 million USD",
     "metadata": {"ticker": "XYZ", "fiscal_year": 2023}},
]


def test_bm25_exact_and_unmatched():
    results = fs.bm25_rank("Revenue 2024", CHUNKS, 5)
    assert results[0]["chunk_id"] == "a"
    assert results[0]["bm25_score"] > 0
    assert fs.bm25_rank("unfindable", CHUNKS, 5) == []


def test_rrf_uses_ranks_not_raw_cosine():
    results = fs.reciprocal_rank_fusion(
        [{"chunk_id": "a", "bm25_score": 500.}, {"chunk_id": "b", "bm25_score": 5.}],
        [{"chunk_id": "b", "dense_score": .8}, {"chunk_id": "a", "dense_score": .99}])
    assert [x["chunk_id"] for x in results] == ["a", "b"]
    assert abs(results[0]["rrf_score"] - 1 / 61 - 1 / 62) < 1e-10


def test_explicit_document_scope_filters_other_document_results(monkeypatch):
    monkeypatch.setattr(fs.rag_service, "chunks_for", lambda scope: CHUNKS)
    class Encoder:
        def embed(self, texts):
            return [[.1, .2]]
    Point = namedtuple("Point", "payload score")
    monkeypatch.setattr(fs, "get_embedding_provider", lambda: Encoder())
    monkeypatch.setattr(fs.qdrant_service, "search", lambda *args: [
        Point({"chunk_id": "c", "document_id": "sec2"}, .99),
        Point({"chunk_id": "a", "document_id": "sec1"}, .9)])
    result = fs.search("Revenue 2024", ["sec1"], "hybrid", top_k=5)
    assert result["results"]
    assert all(row["document_id"] == "sec1" for row in result["results"])
    assert result["results"][0]["chunk_id"] == "a"
    assert result["results"][0]["page"] == 1


def test_metadata_filters_never_guess(monkeypatch):
    monkeypatch.setattr(fs.rag_service, "chunks_for", lambda scope: CHUNKS)
    assert fs.search("Revenue", ["sec1"], "bm25", filters={"ticker": "XYZ"})["results"] == []
    assert len(fs.search("Revenue", ["sec1"], "bm25",
                         filters={"ticker": "ABC"})["results"]) == 1


def test_explicit_scope_and_no_oracle():
    with pytest.raises(ValueError, match="Explicit document_ids"):
        fs.search("revenue", [], "bm25")
    assert "oracle" not in fs.search.__code__.co_varnames


def test_cross_encoder_really_rescores_candidates():
    class FakeEncoder:
        def predict(self, pairs, **kwargs):
            assert len(pairs) == 2
            return [.1, .9]
    hits = [{"chunk_id": "a", "text": "foo"}, {"chunk_id": "b", "text": "bar"}]
    ranked = fs.cross_encoder_rerank("question", hits, FakeEncoder())
    assert [r["chunk_id"] for r in ranked] == ["b", "a"]
    assert ranked[0]["rerank_score"] == .9


def test_absent_cross_encoder_fails_closed(monkeypatch):
    monkeypatch.delenv("FINANCIAL_RERANKER_PATH", raising=False)
    fs._cross_encoder.cache_clear()
    with pytest.raises(RuntimeError, match="FINANCIAL_RERANKER_PATH"):
        fs.search("revenue", ["sec1"], "hybrid_rerank")

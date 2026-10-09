import pytest
from app.services.chunk_service import chunk_pages, clean_text


def test_empty_text_returns_no_chunks():
    assert chunk_pages([{"page": 1, "text": "   "}], "doc", "x.pdf", 20, 2) == []


def test_short_text_preserves_page_and_metadata():
    result = chunk_pages([{"page": 4, "text": "A short policy statement."}], "doc", "policy.pdf", 100, 10)
    assert len(result) == 1
    assert result[0]["page"] == 4
    assert result[0]["metadata"]["document_id"] == "doc"
    assert result[0]["filename"] == "policy.pdf"


def test_chunk_size_and_overlap():
    text = " ".join(f"word{i}" for i in range(80))
    chunks = chunk_pages([{"page": 1, "text": text}], "d", "a.pdf", 80, 20)
    assert len(chunks) > 1
    assert all(len(chunk["text"]) <= 80 for chunk in chunks)
    assert chunks[1]["start"] < chunks[0]["end"]
    with pytest.raises(ValueError):
        chunk_pages([{"page": 1, "text": text}], "d", "a.pdf", 20, 20)


def test_cleaning_keeps_meaning_and_removes_extra_whitespace():
    assert clean_text("  hello   world\n\n\n again ") == "hello world\nagain"

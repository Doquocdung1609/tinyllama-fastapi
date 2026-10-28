"""Isolated product PDF proof with a deterministic fake vector provider."""
from hashlib import sha256
from threading import Event, Thread
from time import perf_counter

import pymupdf
import pytest

from app.product.workspace import PdfWorkspace, DIMENSION


class FixtureEmbedder:
    def identity(self):
        return {"model": "synthetic-test-only", "dimension": DIMENSION}

    def embed(self, texts, *, query=False):
        vectors = []
        for text in texts:
            value = [0.0] * DIMENSION
            for token in text.casefold().split():
                value[int.from_bytes(sha256(token.encode()).digest()[:2], "big") % DIMENSION] += 1.0
            vectors.append(value)
        return vectors


def fixture_pdf():
    pdf = pymupdf.open()
    page = pdf.new_page(width=595, height=842)
    page.insert_text((72, 90), "Financial statement of Synthetic Sample Company")
    page.insert_text((72, 120), "Total assets were 125 million USD at December 31, 2025.")
    page.insert_text((72, 150), "Cash and cash equivalents were 20 million USD.")
    data = pdf.tobytes()
    pdf.close()
    return data


def test_pdf_upload_three_modes_highlight_restart_and_tamper(tmp_path):
    root = tmp_path / "studio_workspace"
    pdf_bytes = fixture_pdf()
    workspace = PdfWorkspace(root, embedder=FixtureEmbedder())
    try:
        item = workspace.add_pdf("financial.pdf", pdf_bytes, "Synthetic Sample Company", "PDF", "2025")
        assert item["status"] == "UPLOADED"
        result = workspace.process(item["id"])
        assert result["status"] == "READY" and result["chunks"] >= 1
        assert workspace.add_pdf("duplicate.pdf", pdf_bytes)["duplicate"] is True
        ranks = {}
        for mode in ("bm25", "dense", "hybrid"):
            output = workspace.search("total assets", mode)
            assert output["status"] == "READY"
            assert output["results"] and output["results"][0]["source_sha256"] == sha256(pdf_bytes).hexdigest()
            assert output["results"][0]["provenance_status"] == "VERIFIED_LOCAL_PDF_BYTES"
            ranks[mode] = output["results"][0]
        chunk = ranks["hybrid"]
        first = workspace.first_chunk(item["id"])
        assert first["chunk_id"] == chunk["chunk_id"]
        assert first["page"] == 1 and first["source_sha256"] == sha256(pdf_bytes).hexdigest()
        png, status = workspace.page_image(item["id"], chunk["page"], [chunk["chunk_id"]])
        assert png.startswith(b"\x89PNG") and status == "EXACT_EXTRACTED_LINE_COORDINATES"
        png, status = workspace.page_image(item["id"], chunk["page"], [chunk["chunk_id"]], "Total assets")
        assert png.startswith(b"\x89PNG") and status == "EXACT_PDF_TEXT_MATCH"
        workspace.close()
        workspace = PdfWorkspace(root, embedder=FixtureEmbedder())
        assert workspace.document(item["id"])["status"] == "READY"
        assert workspace.search("total assets", "hybrid")["results"]
        path = root / "files" / f"{item['id']}.pdf"
        path.write_bytes(pdf_bytes[:-1] + bytes([pdf_bytes[-1] ^ 1]))
        with pytest.raises(ValueError, match="PDF_SOURCE_HASH_MISMATCH"):
            workspace.search("total assets", "bm25")
        with pytest.raises(ValueError, match="PDF_SOURCE_HASH_MISMATCH"):
            workspace.first_chunk(item["id"])
    finally:
        workspace.close()


def test_pdf_invalid_source_and_delete_confirmation_boundary(tmp_path):
    workspace = PdfWorkspace(tmp_path / "owned", embedder=FixtureEmbedder())
    try:
        with pytest.raises(ValueError, match="PDF_SIGNATURE_REQUIRED"):
            workspace.add_pdf("wrong.pdf", b"not a pdf")
        item = workspace.add_pdf("good.pdf", fixture_pdf())
        with pytest.raises(ValueError, match="DOCUMENT_PROCESSING_IN_PROGRESS"):
            workspace.delete(item["id"])
        assert workspace.process(item["id"])["status"] == "READY"
        assert workspace.delete(item["id"])
        assert workspace.document(item["id"]) is None
    finally:
        workspace.close()


def test_progress_can_be_read_and_delete_is_blocked_during_embedding(tmp_path):
    started, release = Event(), Event()

    class PausingEmbedder(FixtureEmbedder):
        def embed(self, texts, *, query=False):
            if not query:
                started.set()
                assert release.wait(10)
            return super().embed(texts, query=query)

    workspace = PdfWorkspace(tmp_path / "owned", embedder=PausingEmbedder())
    item = workspace.add_pdf("financial.pdf", fixture_pdf())
    worker = Thread(target=workspace.process, args=(item["id"],))
    try:
        worker.start()
        assert started.wait(10)
        tick = perf_counter()
        current = workspace.document(item["id"])
        assert perf_counter() - tick < 1
        assert current["status"] == "PROCESSING" and current["stage"] == "EMBEDDING"
        with pytest.raises(ValueError, match="DOCUMENT_PROCESSING_IN_PROGRESS"):
            workspace.delete(item["id"])
    finally:
        release.set()
        worker.join(15)
        assert not worker.is_alive()
        assert workspace.document(item["id"])["status"] == "READY"
        workspace.close()


def test_restart_downgrades_tampered_pdf_from_ready(tmp_path):
    root = tmp_path / "owned"
    original = fixture_pdf()
    workspace = PdfWorkspace(root, embedder=FixtureEmbedder())
    item = workspace.add_pdf("financial.pdf", original)
    assert workspace.process(item["id"])["status"] == "READY"
    workspace.close()
    path = root / "files" / f"{item['id']}.pdf"
    path.write_bytes(original + b"tampered")
    workspace = PdfWorkspace(root, embedder=FixtureEmbedder())
    try:
        current = workspace.document(item["id"])
        assert current["status"] == "FAILED"
        assert current["error_code"] == "PDF_SOURCE_HASH_MISMATCH"
        assert workspace.search("total assets", "bm25")["status"] == "NO_READY_DOCUMENTS"
    finally:
        workspace.close()

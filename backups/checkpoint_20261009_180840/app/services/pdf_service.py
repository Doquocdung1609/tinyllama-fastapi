"""PDF extraction that preserves the source page for retrieval citations."""
from pathlib import Path


def extract_pdf(path: str | Path, document_id: str, filename: str) -> list[dict]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("pypdf is not installed. Install requirements.txt.") from exc
    reader = PdfReader(str(path))
    pages = []
    for index, page in enumerate(reader.pages, start=1):
        pages.append({"document_id": document_id, "filename": filename, "page": index,
                      "text": page.extract_text() or ""})
    if not pages or not any(item["text"].strip() for item in pages):
        raise ValueError("PDF không có văn bản có thể trích xuất; tài liệu scan cần OCR.")
    return pages

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
        # Layout extraction avoids spurious intra-word spaces in PDFs whose
        # glyphs are individually positioned (common in Vietnamese teaching
        # material). Keep a fallback for older pypdf releases.
        try:
            text = page.extract_text(extraction_mode="layout") or ""
        except (TypeError, ValueError):
            text = page.extract_text() or ""
        pages.append({"document_id": document_id, "filename": filename, "page": index,
                      "text": text, "extraction_mode": "layout"})
    if not pages or not any(item["text"].strip() for item in pages):
        raise ValueError("PDF không có văn bản có thể trích xuất; tài liệu scan cần OCR.")
    return pages

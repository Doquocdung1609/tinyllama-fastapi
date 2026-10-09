"""Text cleaning and page-aware chunking helpers."""
import re
from collections import Counter
from typing import Any


def clean_text(text: str) -> str:
    text = text.replace("\x00", " ").replace("\ufeff", " ")
    text = re.sub(r"[ \t]+", " ", text)
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    if len(lines) >= 4:
        counts = Counter(line for line in lines if len(line) < 140)
        repeated = {line for line, count in counts.items() if count >= max(3, len(lines) // 4)}
        lines = [line for line in lines if line not in repeated]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def chunk_pages(pages: list[dict[str, Any]], document_id: str, filename: str,
                chunk_size: int = 800, chunk_overlap: int = 120) -> list[dict[str, Any]]:
    if chunk_size < 1 or chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("chunk_size must be positive and chunk_overlap must be smaller than chunk_size")
    chunks = []
    stride = chunk_size - chunk_overlap
    for page_item in pages:
        original = page_item.get("text", "") or ""
        cleaned = clean_text(original)
        page = int(page_item.get("page", 1))
        start = 0
        while start < len(cleaned):
            end = min(start + chunk_size, len(cleaned))
            # Prefer a nearby word boundary without creating very short chunks.
            if end < len(cleaned):
                boundary = cleaned.rfind(" ", start + int(chunk_size * .65), end)
                if boundary > start:
                    end = boundary
            content = cleaned[start:end].strip()
            if content:
                idx = len(chunks)
                chunks.append({"chunk_id": f"{document_id}-{idx:05d}", "document_id": document_id,
                    "filename": filename, "page": page, "chunk_index": idx, "text": content,
                    "original_text": original, "cleaned_text": cleaned, "start": start, "end": end,
                    "overlap": chunk_overlap if start else 0, "token_estimate": max(1, round(len(content) / 4)),
                    "embedding_status": "pending", "vector_id": None,
                    "metadata": {"document_id": document_id, "filename": filename, "page": page,
                                 "chunk_index": idx, "start": start, "end": end}})
            if end >= len(cleaned):
                break
            start = max(start + 1, end - chunk_overlap)
    return chunks

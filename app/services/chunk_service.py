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


def _preferred_boundary(text: str, start: int, target: int, chunk_size: int) -> int:
    """Prefer paragraph/sentence boundaries without creating tiny chunks."""
    floor = start + int(chunk_size * .62)
    candidates = []
    for marker in ("\n\n", "\n", ". ", "? ", "! ", "; ", ": ", ", ", " "):
        position = text.rfind(marker, floor, target)
        if position >= floor:
            candidates.append(position + (0 if marker == " " else len(marker)))
            # Earlier marker classes are semantically stronger. Use the last
            # occurrence of the first class that has a viable boundary.
            return candidates[-1]
    return target


def chunk_pages(pages: list[dict[str, Any]], document_id: str, filename: str,
                chunk_size: int = 800, chunk_overlap: int = 120) -> list[dict[str, Any]]:
    if chunk_size < 1 or chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("chunk_size must be positive and chunk_overlap must be smaller than chunk_size")
    chunks = []

    def append_chunk(page: int, content: str, *, modality: str = "text",
                     original_text: str = "", cleaned_text: str = "",
                     start: int = 0, end: int | None = None, overlap: int = 0,
                     source_id: str | None = None, bbox: list[float] | None = None,
                     extraction_method: str | None = None,
                     structured_data: dict[str, Any] | None = None,
                     confidence: str | None = None) -> None:
        idx = len(chunks)
        source_id = source_id or f"text:p{page}:chunk{idx}"
        metadata = {"document_id": document_id, "filename": filename, "page": page,
                    "chunk_index": idx, "start": start,
                    "end": len(content) if end is None else end, "modality": modality,
                    "source_id": source_id, "bbox": bbox,
                    "extraction_method": extraction_method, "confidence": confidence}
        chunks.append({
            "chunk_id": f"{document_id}-{idx:05d}", "document_id": document_id,
            "filename": filename, "page": page, "chunk_index": idx, "text": content,
            "original_text": original_text or content, "cleaned_text": cleaned_text or content,
            "start": start, "end": len(content) if end is None else end,
            "overlap": overlap, "token_estimate": max(1, round(len(content) / 4)),
            "embedding_status": "pending", "vector_id": None, "modality": modality,
            "source_id": source_id, "bbox": bbox, "extraction_method": extraction_method,
            "structured_data": structured_data, "confidence": confidence,
            "metadata": metadata,
        })

    for page_item in pages:
        original = page_item.get("text", "") or ""
        cleaned = clean_text(original)
        page = int(page_item.get("page", 1))
        start = 0
        while start < len(cleaned):
            end = min(start + chunk_size, len(cleaned))
            if end < len(cleaned):
                end = _preferred_boundary(cleaned, start, end, chunk_size)
            content = cleaned[start:end].strip()
            if content:
                append_chunk(page, content, modality=("ocr_text" if page_item.get("extraction_mode") == "ocr"
                                                      else "text"),
                             original_text=original, cleaned_text=cleaned, start=start, end=end,
                             overlap=chunk_overlap if start else 0,
                             source_id=f"text:p{page}:chars{start}-{end}",
                             extraction_method=page_item.get("extraction_mode"),
                             confidence=page_item.get("diagnostics", {}).get("extraction_quality"))
            if end >= len(cleaned):
                break
            start = max(start + 1, end - chunk_overlap)

        # Tables are chunked by logical row groups. Every group repeats the
        # caption, units and column headers, so row/column relationships survive.
        for table in page_item.get("tables", []):
            columns = [str(value) for value in table.get("columns", [])]
            rows = [[str(value) for value in row] for row in table.get("rows", [])]
            caption = table.get("caption") or "Bảng không có tiêu đề đọc được"
            max_rows = max(1, min(25, chunk_size // max(80, sum(len(value) for value in columns) + 20)))
            groups = [rows[index:index + max_rows] for index in range(0, len(rows), max_rows)] or [[]]
            for group_index, group in enumerate(groups, start=1):
                all_rows = [columns] + group if columns else group
                width = max((len(row) for row in all_rows), default=0)
                padded = [(row + [""] * width)[:width] for row in all_rows]
                markdown = ""
                if padded:
                    markdown = "\n".join([
                        "| " + " | ".join(padded[0]) + " |",
                        "| " + " | ".join(["---"] * width) + " |",
                        *("| " + " | ".join(row) + " |" for row in padded[1:]),
                    ])
                first_row = (group_index - 1) * max_rows + 1
                last_row = first_row + len(group) - 1
                content = (f"TABLE {table.get('table_id')}\nSource: {table.get('source_id')}\nCaption: {caption}\n"
                           f"Rows: {first_row}-{max(first_row, last_row)}\n{markdown}")
                structured = {**table, "rows": group, "row_range": [first_row, max(first_row, last_row)]}
                append_chunk(page, content, modality="table", source_id=table.get("source_id"),
                             bbox=table.get("bbox"), extraction_method=table.get("extraction_method"),
                             structured_data=structured, confidence=table.get("confidence"))

        for chart in page_item.get("charts", []):
            pairs = chart.get("label_value_pairs", [])
            values = "\n".join(f"- {item['label']}: {item['value']}" for item in pairs)
            content = (f"CHART {chart.get('chart_id')}\nTitle: {chart.get('title') or 'Không đọc được'}\n"
                       f"Type: {chart.get('chart_type')}\nVisible label/value data:\n"
                       f"{values or '[Không có nhãn số chính xác]'}\n"
                       f"Uncertainty: {chart.get('uncertainty') or 'Dữ liệu lấy từ nhãn hiện hữu trong PDF.'}")
            append_chunk(page, content, modality="chart", source_id=chart.get("source_id"),
                         bbox=chart.get("bbox"), extraction_method=chart.get("extraction_source"),
                         structured_data=chart, confidence=chart.get("confidence"))

        for figure in page_item.get("figures", []):
            visible = clean_text(figure.get("visible_text", ""))
            content = (f"FIGURE {figure.get('figure_id')}\nCaption: {figure.get('caption')}\n"
                       f"Visible labels/text:\n{visible}\nUncertainty: {figure.get('uncertainty')}")
            append_chunk(page, content, modality="figure", source_id=figure.get("source_id"),
                         bbox=figure.get("bbox"), extraction_method=figure.get("extraction_method"),
                         structured_data=figure, confidence=figure.get("confidence"))
    return chunks

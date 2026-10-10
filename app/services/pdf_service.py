"""Modality-aware PDF inspection and extraction.

Native text and geometry are preferred. OCR and visual interpretation are
capabilities with explicit readiness states; they are never silently simulated.
"""
from __future__ import annotations

from pathlib import Path
from time import perf_counter
import re
import shutil
import unicodedata
from typing import Any


def _clean_cell(value: Any) -> str:
    return re.sub(r"\s+", " ", "" if value is None else str(value)).strip()


def _table_markdown(rows: list[list[str]]) -> str:
    if not rows:
        return ""
    width = max(len(row) for row in rows)
    normalized = [(row + [""] * width)[:width] for row in rows]
    escaped = [[cell.replace("|", "\\|").replace("\n", " ") for cell in row]
               for row in normalized]
    return "\n".join([
        "| " + " | ".join(escaped[0]) + " |",
        "| " + " | ".join(["---"] * width) + " |",
        *("| " + " | ".join(row) + " |" for row in escaped[1:]),
    ])


def _nearest_caption(text: str, kind: str) -> str | None:
    cue = r"(?:bảng|table)" if kind == "table" else r"(?:biểu\s*đồ|chart)"
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines() if line.strip()]
    return next((line for line in lines if re.search(rf"\b{cue}\b", line, re.IGNORECASE)), None)


def _table_family(caption: str | None) -> str | None:
    if not caption:
        return None
    normalized = unicodedata.normalize("NFKD", caption.casefold().replace("đ", "d"))
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    match = re.search(r"\b(?:bang|table)\s*([a-z0-9]+)", normalized)
    return match.group(1) if match else None


def _page_columns(blocks: list[tuple], page_width: float) -> int:
    text_blocks = [block for block in blocks if len(block) >= 7 and block[6] == 0
                   and _clean_cell(block[4])]
    left = [block for block in text_blocks if float(block[0]) < page_width * .45]
    right = [block for block in text_blocks if float(block[0]) > page_width * .50]
    return 2 if len(left) >= 2 and len(right) >= 2 else 1


def _chart_type(text: str) -> str:
    lowered = text.casefold()
    if any(word in lowered for word in ("biểu đồ tròn", "pie chart", "pie")):
        return "pie"
    if any(word in lowered for word in ("biểu đồ đường", "line chart", "đường dữ liệu")):
        return "line"
    if any(word in lowered for word in ("biểu đồ cột", "bar chart", "column chart")):
        return "bar"
    return "unspecified"


def _visible_label_values(text: str) -> list[dict]:
    """Read only explicit label/value pairs printed in PDF text layers."""
    pairs: list[dict] = []
    pattern = re.compile(
        r"(?m)^\s*([^\n:|]{1,60}?)\s*[:|]\s*"
        r"([()\-+]?\d[\d.,()\s]*\s*(?:%|triệu\s+đồng|tỷ\s+đồng|VND|USD)?)\s*$",
        re.IGNORECASE)
    for match in pattern.finditer(text):
        pair = {"label": _clean_cell(match.group(1)), "value": _clean_cell(match.group(2))}
        if pair not in pairs:
            pairs.append(pair)
    return pairs[:100]


def extraction_capabilities() -> dict:
    try:
        import pymupdf  # noqa: F401
        pymupdf = True
    except ImportError:
        pymupdf = False
    try:
        import pdfplumber  # noqa: F401
        table = True
    except ImportError:
        table = False
    try:
        import pytesseract  # noqa: F401
        ocr_module = True
    except ImportError:
        ocr_module = False
    tesseract = shutil.which("tesseract")
    return {
        "pymupdf": pymupdf,
        "pdfplumber": table,
        "native_text": pymupdf,
        "native_tables": table,
        "ocr": bool(ocr_module and tesseract),
        "ocr_engine": tesseract,
        "ocr_languages": [],
        "vision": False,
        "vision_detail": "Không cài model Vision; chart chỉ dùng dữ liệu/nhãn hiện hữu trong PDF.",
    }


def extract_pdf(path: str | Path, document_id: str, filename: str) -> list[dict]:
    """Inspect each page and return text plus structured modality evidence."""
    started = perf_counter()
    capabilities = extraction_capabilities()
    if not capabilities["pymupdf"]:
        raise RuntimeError("PyMuPDF chưa được cài; không thể chạy PDF preflight đa phương thức.")
    import pymupdf as fitz

    pdf_path = str(path)
    document = fitz.open(pdf_path)
    plumber = None
    if capabilities["pdfplumber"]:
        import pdfplumber
        plumber = pdfplumber.open(pdf_path)
    pages: list[dict] = []
    try:
        for index, page in enumerate(document, start=1):
            page_started = perf_counter()
            text = page.get_text("text", sort=True) or ""
            blocks = page.get_text("blocks", sort=True) or []
            images = page.get_images(full=True) or []
            try:
                drawings = page.get_drawings() or []
            except Exception:
                drawings = []
            width, height = float(page.rect.width), float(page.rect.height)
            usable_chars = len(re.sub(r"\s+", "", text))
            scanned = usable_chars < 40 and bool(images)
            missing_text = usable_chars < 20
            warnings: list[str] = []
            if scanned:
                warnings.append("SCANNED_PAGE_REQUIRES_OCR")
                if not capabilities["ocr"]:
                    warnings.append("OCR_ENGINE_UNAVAILABLE")
            if missing_text and not images:
                warnings.append("MISSING_OR_CORRUPT_TEXT_LAYER")

            tables: list[dict] = []
            if plumber is not None:
                try:
                    found = plumber.pages[index - 1].find_tables()
                    for table_number, found_table in enumerate(found, start=1):
                        raw_rows = found_table.extract() or []
                        rows = [[_clean_cell(cell) for cell in row] for row in raw_rows]
                        rows = [row for row in rows if any(row)]
                        columns = max((len(row) for row in rows), default=0)
                        status = "OK" if len(rows) >= 2 and columns >= 2 else "NEEDS_REVIEW"
                        tables.append({
                            "modality": "table", "document_id": document_id,
                            "filename": filename, "page": index,
                            "table_id": f"{document_id}-p{index:04d}-t{table_number:02d}",
                            "source_id": f"table:p{index}:t{table_number}",
                            "caption": _nearest_caption(text, "table"),
                            "bbox": [round(float(value), 2) for value in found_table.bbox],
                            "extraction_method": "pdfplumber_native_table",
                            "columns": rows[0] if rows else [],
                            "rows": rows[1:] if len(rows) > 1 else [],
                            "all_rows": rows, "markdown": _table_markdown(rows),
                            "status": status,
                            "confidence": "HIGH" if status == "OK" else "LOW",
                        })
                except Exception as exc:
                    warnings.append(f"TABLE_EXTRACTION_ERROR:{type(exc).__name__}")

            chart_cue = bool(re.search(r"\b(?:biểu\s*đồ|chart)\b", text, re.IGNORECASE))
            charts: list[dict] = []
            if chart_cue and (len(drawings) >= 2 or images):
                visible_pairs = _visible_label_values(text)
                charts.append({
                    "modality": "chart", "document_id": document_id,
                    "filename": filename, "page": index,
                    "chart_id": f"{document_id}-p{index:04d}-c01",
                    "source_id": f"chart:p{index}:c1",
                    "title": _nearest_caption(text, "chart"),
                    "chart_type": _chart_type(text),
                    "bbox": [0.0, 0.0, round(width, 2), round(height, 2)],
                    "visible_text": text.strip(),
                    "label_value_pairs": visible_pairs,
                    "numerical_series": visible_pairs,
                    "extraction_source": "native_visible_labels",
                    "confidence": "HIGH" if visible_pairs else "QUALITATIVE_ONLY",
                    "uncertainty": (None if visible_pairs else
                                    "Không có nhãn số máy đọc được; chỉ cho phép kết luận định tính."),
                })

            figures: list[dict] = []
            figure_lines = [line.strip() for line in text.splitlines()
                            if re.search(r"\b(?:hình|figure|sơ\s*đồ|diagram|quy\s*trình)\b",
                                         line, re.IGNORECASE)]
            if figure_lines and (drawings or images):
                figures.append({
                    "modality": "figure", "document_id": document_id,
                    "filename": filename, "page": index,
                    "figure_id": f"{document_id}-p{index:04d}-f01",
                    "source_id": f"figure:p{index}:f1",
                    "caption": _clean_cell(figure_lines[0]),
                    "bbox": [0.0, 0.0, round(width, 2), round(height, 2)],
                    "visible_text": text.strip(),
                    "extraction_method": "native_caption_and_labels",
                    "confidence": "LABELS_ONLY",
                    "uncertainty": "Không diễn giải pixel hoặc quan hệ không được nhãn văn bản hỗ trợ.",
                })

            page_types = ["text"] if usable_chars >= 40 else []
            if tables:
                page_types.append("table")
            if charts:
                page_types.append("chart")
            if figures:
                page_types.append("figure")
            if scanned:
                page_types.append("scanned")
            if len(set(page_types)) > 1:
                page_types.append("mixed")
            quality = "HIGH" if usable_chars >= 100 else "MEDIUM" if usable_chars >= 40 else "LOW"
            pages.append({
                "document_id": document_id, "filename": filename, "page": index,
                "text": text, "extraction_mode": "pymupdf_native" if text.strip() else "none",
                "page_types": sorted(set(page_types)), "tables": tables,
                "charts": charts, "figures": figures,
                "diagnostics": {
                    "width": round(width, 2), "height": round(height, 2),
                    "rotation": int(page.rotation), "text_chars": len(text),
                    "usable_text_chars": usable_chars, "text_blocks": len(blocks),
                    "image_count": len(images), "drawing_count": len(drawings),
                    "column_count": _page_columns(blocks, width),
                    "table_count": len(tables), "chart_count": len(charts),
                    "figure_count": len(figures), "scanned": scanned,
                    "needs_ocr": scanned or missing_text,
                    "ocr_status": "AVAILABLE_NOT_RUN" if capabilities["ocr"] and scanned else
                                  "BLOCKED_ENGINE_UNAVAILABLE" if scanned else "NOT_REQUIRED",
                    "extraction_quality": quality, "warnings": warnings,
                    "processing_ms": round((perf_counter() - page_started) * 1000, 1),
                },
            })
    finally:
        document.close()
        if plumber is not None:
            plumber.close()
    previous_by_family: dict[str, dict] = {}
    for page_item in pages:
        for table in page_item.get("tables", []):
            family = _table_family(table.get("caption"))
            if not family:
                continue
            table["continuation_group"] = f"table-family:{family}"
            previous = previous_by_family.get(family)
            if previous and int(table["page"]) == int(previous["page"]) + 1:
                table["continued_from"] = previous["table_id"]
                previous["continued_by"] = table["table_id"]
            previous_by_family[family] = table
    if not pages:
        raise ValueError("PDF không có trang.")
    total_ms = round((perf_counter() - started) * 1000, 1)
    for item in pages:
        item["diagnostics"]["document_extraction_ms"] = total_ms
    return pages


def summarize_extraction(pages: list[dict]) -> dict:
    """Create document-level preflight diagnostics without invented scores."""
    page_count = lambda name: sum(name in page.get("page_types", []) for page in pages)
    warnings = sorted({warning for page in pages
                       for warning in page.get("diagnostics", {}).get("warnings", [])})
    return {
        "schema_version": 3, "total_pages": len(pages),
        "text_pages": page_count("text"), "table_pages": page_count("table"),
        "chart_pages": page_count("chart"), "figure_pages": page_count("figure"),
        "scanned_pages": page_count("scanned"), "mixed_pages": page_count("mixed"),
        "multi_column_pages": sum(page.get("diagnostics", {}).get("column_count", 1) > 1
                                  for page in pages),
        "rotated_pages": sum(bool(page.get("diagnostics", {}).get("rotation")) for page in pages),
        "tables": sum(len(page.get("tables", [])) for page in pages),
        "charts": sum(len(page.get("charts", [])) for page in pages),
        "figures": sum(len(page.get("figures", [])) for page in pages),
        "ocr_pages_processed": 0, "warnings": warnings,
        "capabilities": extraction_capabilities(),
    }


def render_page_preview(path: str | Path, page_number: int, output_path: str | Path,
                        dpi: int = 120) -> Path:
    import pymupdf as fitz
    document = fitz.open(str(path))
    try:
        if page_number < 1 or page_number > len(document):
            raise ValueError("Số trang nằm ngoài tài liệu.")
        page = document[page_number - 1]
        scale = dpi / 72
        pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        pixmap.save(str(target))
        return target
    finally:
        document.close()

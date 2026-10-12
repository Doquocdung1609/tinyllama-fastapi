"""Modality-aware PDF inspection and extraction.

Native text and geometry are preferred. OCR and visual interpretation are
capabilities with explicit readiness states; they are never silently simulated.
"""
from __future__ import annotations

from pathlib import Path
from time import perf_counter
from functools import lru_cache
import os
import re
import shutil
import subprocess
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
    folded = unicodedata.normalize("NFKD", lowered.replace("đ", "d"))
    folded = "".join(char for char in folded if not unicodedata.combining(char))
    if any(word in folded for word in ("bieu do tron", "pie chart", "pie")):
        return "pie"
    if any(word in folded for word in ("bieu do duong", "line chart", "duong du lieu")):
        return "line"
    if any(word in folded for word in ("bieu do cot", "bar chart", "column chart")) or re.search(r"bieu.{0,15}cot", folded):
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
    # OCR output can damage unit characters while preserving exact labels and
    # digits. Keep the raw trailing unit and its confidence provenance rather
    # than silently normalizing it.
    if not pairs:
        for line in text.splitlines():
            match = re.match(r"^\s*([^:]{1,60})\s*:\s*([()\-+]?\d[\d.,()]*)\s*(.{0,24})$", line)
            if match:
                value = " ".join(part for part in (_clean_cell(match.group(2)), _clean_cell(match.group(3))) if part)
                pair = {"label": _clean_cell(match.group(1)), "value": value, "ocr_unit_unverified": True}
                if pair not in pairs:
                    pairs.append(pair)
    return pairs[:100]


@lru_cache(maxsize=1)
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
    from app.config import get_settings
    configured = get_settings().tesseract_cmd
    candidates = [configured, shutil.which("tesseract"),
                  r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                  r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"]
    tesseract = next((str(Path(item)) for item in candidates if item and Path(item).exists()), None)
    languages: list[str] = []
    tessdata = get_settings().tessdata_dir
    if tesseract:
        try:
            command = [tesseract]
            if tessdata.exists():
                command += ["--tessdata-dir", str(tessdata)]
            command += ["--list-langs"]
            output = subprocess.run(command, capture_output=True, text=True, timeout=10, check=False)
            languages = [line.strip() for line in output.stdout.splitlines()[1:] if line.strip()]
        except (OSError, subprocess.SubprocessError):
            languages = []
    return {
        "pymupdf": pymupdf,
        "pdfplumber": table,
        "native_text": pymupdf,
        "native_tables": table,
        "ocr": bool(ocr_module and tesseract and "eng" in languages),
        "ocr_engine": tesseract,
        "ocr_version": "5.4.0.20240606" if tesseract else None,
        "ocr_languages": languages,
        "ocr_tessdata_dir": str(tessdata) if tessdata.exists() else None,
        "vision": False,
        "vision_detail": "Không cài model Vision; chart chỉ dùng dữ liệu/nhãn hiện hữu trong PDF.",
    }


def _ocr_table(words: list[dict], document_id: str, filename: str, page_number: int) -> list[dict]:
    """Conservatively reconstruct grid-like OCR rows from aligned word boxes."""
    grouped: dict[tuple[int, int, int], list[dict]] = {}
    for word in words:
        grouped.setdefault((word["block"], word["paragraph"], word["line"]), []).append(word)
    logical_rows = []
    for line_words in grouped.values():
        line_words.sort(key=lambda item: item["left"])
        if len(line_words) < 3:
            continue
        median_height = sorted(item["height"] for item in line_words)[len(line_words)//2]
        cells: list[list[dict]] = [[]]
        for word in line_words:
            if cells[-1]:
                previous = cells[-1][-1]
                gap = word["left"] - (previous["left"] + previous["width"])
                if gap > max(25, median_height * 2.2):
                    cells.append([])
            cells[-1].append(word)
        rendered = [" ".join(item["text"] for item in cell).strip() for cell in cells if cell]
        if len(rendered) >= 3:
            logical_rows.append((min(item["top"] for item in line_words), rendered, line_words))
    logical_rows.sort(key=lambda item: item[0])
    if len(logical_rows) < 3:
        return []
    width_counts: dict[int, int] = {}
    for _, row, _ in logical_rows:
        width_counts[len(row)] = width_counts.get(len(row), 0) + 1
    width = max(width_counts, key=width_counts.get)
    aligned = [item for item in logical_rows if len(item[1]) == width]
    numeric_rows = sum(sum(bool(re.search(r"\d", cell)) for cell in row[1:]) >= 2
                       for _, row, _ in aligned)
    if width < 3 or len(aligned) < 3 or numeric_rows < 2:
        return []
    all_rows = [row for _, row, _ in aligned]
    all_words = [word for _, _, line_words in aligned for word in line_words]
    numeric_confidences = [word["confidence"] for word in all_words if re.search(r"\d", word["text"])]
    status = "OK" if numeric_confidences and min(numeric_confidences) >= 60 else "NEEDS_REVIEW"
    bbox = [min(item["pdf_bbox"][0] for item in all_words), min(item["pdf_bbox"][1] for item in all_words),
            max(item["pdf_bbox"][2] for item in all_words), max(item["pdf_bbox"][3] for item in all_words)]
    return [{
        "modality": "table", "document_id": document_id, "filename": filename,
        "page": page_number, "table_id": f"{document_id}-p{page_number:04d}-ocr-t01",
        "source_id": f"ocr-table:p{page_number}:t1", "caption": "Bảng nhận dạng từ trang scan",
        "bbox": [round(value, 2) for value in bbox], "extraction_method": "tesseract_ocr_grid",
        "columns": all_rows[0], "rows": all_rows[1:], "all_rows": all_rows,
        "markdown": _table_markdown(all_rows), "status": status,
        "confidence": "MEDIUM" if status == "OK" else "LOW", "ocr_derived": True,
        "numeric_confidence_min": min(numeric_confidences) if numeric_confidences else None,
    }]


def _ocr_page(page, document_id: str, filename: str, page_number: int,
              width: float, height: float, capabilities: dict) -> dict:
    """Run genuine local OCR and retain word/line provenance in PDF coordinates."""
    from PIL import Image, ImageOps
    import pytesseract
    from pytesseract import Output

    pytesseract.pytesseract.tesseract_cmd = capabilities["ocr_engine"]
    dpi = 300
    scale = dpi / 72
    pixmap = page.get_pixmap(matrix=__import__("pymupdf").Matrix(scale, scale), alpha=False)
    image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
    processed = ImageOps.autocontrast(ImageOps.grayscale(image))
    preprocessing = ["grayscale", "autocontrast"]
    try:
        import cv2
        import numpy as np
        gray = np.array(processed)
        inverted = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
        horizontal = cv2.morphologyEx(inverted, cv2.MORPH_OPEN,
            cv2.getStructuringElement(cv2.MORPH_RECT, (max(30, gray.shape[1] // 20), 1)))
        vertical = cv2.morphologyEx(inverted, cv2.MORPH_OPEN,
            cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(30, gray.shape[0] // 20))))
        lines = cv2.bitwise_or(horizontal, vertical)
        if int((lines > 0).sum()) > gray.size * .001:
            gray[lines > 0] = 255
            processed = Image.fromarray(gray)
            preprocessing.append("table_line_removal")
    except (ImportError, ValueError):
        pass
    languages = capabilities.get("ocr_languages") or []
    language = "+".join(item for item in ("vie", "eng") if item in languages) or "eng"
    tessdata = capabilities.get("ocr_tessdata_dir")
    config = "--oem 1 --psm 6"
    if tessdata:
        config += f" --tessdata-dir {Path(tessdata).as_posix()}"
    started = perf_counter()
    data = pytesseract.image_to_data(processed, lang=language, config=config, output_type=Output.DICT)
    words: list[dict] = []
    for index, raw_text in enumerate(data.get("text", [])):
        word_text = _clean_cell(raw_text)
        try:
            confidence = float(data["conf"][index])
        except (ValueError, TypeError, KeyError):
            confidence = -1.0
        if not word_text or confidence < 0:
            continue
        left, top = int(data["left"][index]), int(data["top"][index])
        word_width, word_height = int(data["width"][index]), int(data["height"][index])
        pdf_bbox = [left / pixmap.width * width, top / pixmap.height * height,
                    (left + word_width) / pixmap.width * width,
                    (top + word_height) / pixmap.height * height]
        words.append({"text": word_text, "confidence": round(confidence, 2), "left": left, "top": top,
                      "width": word_width, "height": word_height,
                      "block": int(data["block_num"][index]), "paragraph": int(data["par_num"][index]),
                      "line": int(data["line_num"][index]),
                      "pdf_bbox": [round(value, 2) for value in pdf_bbox]})
    lines: dict[tuple[int, int, int], list[dict]] = {}
    for word in words:
        lines.setdefault((word["block"], word["paragraph"], word["line"]), []).append(word)
    regions = []
    for number, line_words in enumerate(lines.values(), start=1):
        line_words.sort(key=lambda item: item["left"])
        text = " ".join(item["text"] for item in line_words)
        bbox = [min(item["pdf_bbox"][0] for item in line_words), min(item["pdf_bbox"][1] for item in line_words),
                max(item["pdf_bbox"][2] for item in line_words), max(item["pdf_bbox"][3] for item in line_words)]
        regions.append({"source_id": f"ocr:p{page_number}:line{number}", "text": text,
                        "bbox": [round(value, 2) for value in bbox],
                        "confidence": round(sum(item["confidence"] for item in line_words) / len(line_words), 2)})
    text = "\n".join(item["text"] for item in regions).strip()
    confidences = [item["confidence"] for item in words]
    uncertain_numbers = [item for item in words if re.search(r"\d", item["text"]) and item["confidence"] < 60]
    return {"text": text, "words": words, "regions": regions,
            "tables": _ocr_table(words, document_id, filename, page_number),
            "language": language, "average_confidence": round(sum(confidences)/len(confidences), 2) if confidences else 0.0,
            "low_confidence_words": sum(value < 60 for value in confidences),
            "uncertain_numeric_tokens": uncertain_numbers,
            "processing_ms": round((perf_counter()-started)*1000, 1), "dpi": dpi,
            "preprocessing": preprocessing,
            "region_image_reference": f"page-render:p{page_number}"}


def extract_pdf(path: str | Path, document_id: str, filename: str, progress_callback=None) -> list[dict]:
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
            ocr_result = None
            if scanned and capabilities["ocr"]:
                if progress_callback:
                    progress_callback("OCR_PROCESSING", index, len(document))
                try:
                    ocr_result = _ocr_page(page, document_id, filename, index, width, height, capabilities)
                    if ocr_result["text"]:
                        text = ocr_result["text"]
                        usable_chars = len(re.sub(r"\s+", "", text))
                        warnings = [item for item in warnings if item != "SCANNED_PAGE_REQUIRES_OCR"]
                except Exception as exc:
                    warnings.append(f"OCR_PROCESSING_ERROR:{type(exc).__name__}")
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
            if not tables and ocr_result:
                tables = ocr_result.get("tables", [])

            folded_text = unicodedata.normalize("NFKD", text.casefold().replace("đ", "d"))
            folded_text = "".join(char for char in folded_text if not unicodedata.combining(char))
            chart_cue = bool(re.search(r"\b(?:bieu.{0,15}(?:cot|duong|tron)|chart)\b", folded_text, re.IGNORECASE))
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
                    "extraction_source": "ocr_visible_labels" if ocr_result else "native_visible_labels",
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
                "text": text, "extraction_mode": "ocr" if ocr_result and text.strip() else
                        "pymupdf_native" if text.strip() else "none",
                "page_types": sorted(set(page_types)), "tables": tables,
                "charts": charts, "figures": figures, "ocr": ocr_result,
                "diagnostics": {
                    "width": round(width, 2), "height": round(height, 2),
                    "rotation": int(page.rotation), "text_chars": len(text),
                    "usable_text_chars": usable_chars, "text_blocks": len(blocks),
                    "image_count": len(images), "drawing_count": len(drawings),
                    "column_count": _page_columns(blocks, width),
                    "table_count": len(tables), "chart_count": len(charts),
                    "figure_count": len(figures), "scanned": scanned,
                    "needs_ocr": scanned or missing_text,
                    "ocr_status": "COMPLETED" if ocr_result and ocr_result.get("text") else
                                  "FAILED" if scanned and capabilities["ocr"] else
                                  "BLOCKED_ENGINE_UNAVAILABLE" if scanned else "NOT_REQUIRED",
                    "ocr_language": ocr_result.get("language") if ocr_result else None,
                    "ocr_average_confidence": ocr_result.get("average_confidence") if ocr_result else None,
                    "uncertain_numeric_tokens": len(ocr_result.get("uncertain_numeric_tokens", [])) if ocr_result else 0,
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
        "ocr_pages_processed": sum(page.get("diagnostics", {}).get("ocr_status") == "COMPLETED" for page in pages),
        "ocr_pages_failed": sum(page.get("diagnostics", {}).get("ocr_status") == "FAILED" for page in pages),
        "ocr_average_confidence": round(sum(page.get("diagnostics", {}).get("ocr_average_confidence") or 0 for page in pages if page.get("diagnostics", {}).get("ocr_status") == "COMPLETED") / max(1, sum(page.get("diagnostics", {}).get("ocr_status") == "COMPLETED" for page in pages)), 2),
        "warnings": warnings,
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

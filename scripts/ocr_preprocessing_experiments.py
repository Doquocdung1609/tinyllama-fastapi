"""Controlled local OCR experiments for the same scanned financial table page."""
from __future__ import annotations

import csv
import re
import time
import unicodedata
from pathlib import Path

import cv2
import numpy as np
import psutil
import pymupdf
import pytesseract
from PIL import Image, ImageEnhance, ImageOps


ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "tests/fixtures/pdfs/K_scanned_financial_table.pdf"
REPORTS = ROOT / "reports"
REFERENCE = """BÁO CÁO TÀI CHÍNH QUÉT
Chỉ tiêu 2023 2024 Đơn vị
Doanh thu 100 180 tỷ đồng
Lợi nhuận 12 16 tỷ đồng
Tổng tài sản 300 360 tỷ đồng
Ghi chú: số liệu tổng hợp dùng cho kiểm thử OCR cục bộ."""
HEADER = ["Chỉ tiêu", "2023", "2024", "Đơn vị"]
NUMBERS = ["100", "180", "12", "16", "300", "360"]


def norm(value: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", value).strip())


def distance(left, right):
    previous = list(range(len(right) + 1))
    for i, a in enumerate(left, 1):
        current = [i]
        for j, b in enumerate(right, 1):
            current.append(min(current[-1] + 1, previous[j] + 1, previous[j - 1] + (a != b)))
        previous = current
    return previous[-1]


def metrics(actual: str):
    reference, actual = norm(REFERENCE), norm(actual)
    cer = distance(list(reference), list(actual)) / max(1, len(reference))
    wer = distance(reference.split(), actual.split()) / max(1, len(reference.split()))
    folded = unicodedata.normalize("NFKD", actual.casefold()).encode("ascii", "ignore").decode()
    header = sum(unicodedata.normalize("NFKD", token.casefold()).encode("ascii", "ignore").decode() in folded for token in HEADER)
    seen_numbers = re.findall(r"(?<!\d)(?:100|180|12|16|300|360)(?!\d)", actual)
    numeric = sum(seen_numbers.count(value) >= NUMBERS.count(value) for value in set(NUMBERS))
    lines = [line for line in actual.splitlines() if line.strip()]
    folded_lines = [unicodedata.normalize("NFKD", line.casefold()).encode("ascii", "ignore").decode() for line in lines]
    structure = sum(any(unicodedata.normalize("NFKD", label.casefold()).encode("ascii", "ignore").decode() in line
                        for line in folded_lines) for label in ("Doanh thu", "Lợi nhuận", "Tổng tài sản"))
    return round(cer * 100, 2), round(wer * 100, 2), header, numeric, structure


def deskew(gray: np.ndarray) -> np.ndarray:
    coords = np.column_stack(np.where(gray < 220))
    if len(coords) < 10:
        return gray
    angle = cv2.minAreaRect(coords[:, ::-1].astype(np.float32))[-1]
    angle = -(90 + angle) if angle < -45 else -angle
    if abs(angle) > 5:
        return gray
    center = (gray.shape[1] // 2, gray.shape[0] // 2)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    return cv2.warpAffine(gray, matrix, (gray.shape[1], gray.shape[0]), flags=cv2.INTER_CUBIC,
                          borderMode=cv2.BORDER_REPLICATE)


def remove_lines(gray: np.ndarray) -> np.ndarray:
    inverted = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    horizontal = cv2.morphologyEx(inverted, cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_RECT, (max(30, gray.shape[1] // 20), 1)))
    vertical = cv2.morphologyEx(inverted, cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(30, gray.shape[0] // 20))))
    result = gray.copy(); result[cv2.bitwise_or(horizontal, vertical) > 0] = 255
    return result


def ocr(image: np.ndarray, psm: int, language: str = "vie+eng") -> str:
    config = f"--oem 1 --psm {psm} --tessdata-dir {(ROOT / 'tools/tessdata').as_posix()}"
    return pytesseract.image_to_string(Image.fromarray(image), lang=language, config=config).strip()


def row_ocr(gray: np.ndarray) -> str:
    binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    projection = (binary > 0).sum(axis=1)
    active = projection > max(4, gray.shape[1] * .003)
    spans, start = [], None
    for index, value in enumerate(active):
        if value and start is None: start = index
        if start is not None and (not value or index == len(active)-1):
            end = index if not value else index + 1
            if end - start >= 8: spans.append((max(0, start-8), min(gray.shape[0], end+8)))
            start = None
    return "\n".join(ocr(gray[a:b, :], 7) for a, b in spans if b-a > 10)


def main():
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    page = pymupdf.open(PDF)[0]
    pix = page.get_pixmap(matrix=pymupdf.Matrix(300/72, 300/72), alpha=False)
    rgb = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    contrast = np.array(ImageOps.autocontrast(Image.fromarray(gray)))
    adaptive = cv2.adaptiveThreshold(contrast, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                     cv2.THRESH_BINARY, 41, 15)
    variants = [
        ("A_original", gray, 6, "vie+eng", "full_page"),
        ("B_deskew", deskew(gray), 6, "vie+eng", "full_page"),
        ("C_contrast", contrast, 6, "vie+eng", "full_page"),
        ("D_adaptive_threshold", adaptive, 6, "vie+eng", "full_page"),
        ("E_table_line_removal", remove_lines(contrast), 6, "vie+eng", "table_region"),
        ("F_psm4", remove_lines(contrast), 4, "vie+eng", "table_region"),
        ("G_psm11", contrast, 11, "vie+eng", "table_region"),
        ("H_vietnamese_only", remove_lines(contrast), 6, "vie", "table_region"),
    ]
    rows, texts = [], {}
    process = psutil.Process()
    for name, image, psm, language, region in variants:
        before = process.memory_info().rss; started = time.perf_counter()
        actual = ocr(image, psm, language)
        elapsed = round((time.perf_counter() - started) * 1000, 1)
        cer, wer, header, numeric, structure = metrics(actual)
        rows.append({"experiment": name, "input": str(PDF), "page": 1, "region": region, "dpi": 300,
                     "preprocessing": name[2:], "ocr_language": language, "engine": "Tesseract 5.4 OEM1",
                     "psm": psm, "cer_percent": cer, "wer_percent": wer,
                     "header_exact_tokens": f"{header}/4", "numeric_cell_exact": f"{numeric}/6",
                     "table_row_alignment": f"{structure}/3", "execution_ms": elapsed,
                     "ram_delta_mb": round((process.memory_info().rss-before)/1048576, 2), "actual_text": norm(actual)})
        texts[name] = actual
    started = time.perf_counter(); before = process.memory_info().rss
    row_actual = row_ocr(remove_lines(contrast)); elapsed = round((time.perf_counter()-started)*1000, 1)
    cer, wer, header, numeric, structure = metrics(row_actual)
    rows.append({"experiment": "I_row_level", "input": str(PDF), "page": 1, "region": "detected_rows", "dpi": 300,
                 "preprocessing": "contrast+line_removal+row_segmentation", "ocr_language": "vie+eng",
                 "engine": "Tesseract 5.4 OEM1", "psm": 7, "cer_percent": cer, "wer_percent": wer,
                 "header_exact_tokens": f"{header}/4", "numeric_cell_exact": f"{numeric}/6",
                 "table_row_alignment": f"{structure}/3", "execution_ms": elapsed,
                 "ram_delta_mb": round((process.memory_info().rss-before)/1048576, 2), "actual_text": norm(row_actual)})
    texts["I_row_level"] = row_actual
    REPORTS.mkdir(exist_ok=True)
    with (REPORTS / "ocr_preprocessing_experiments.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    best = min(rows, key=lambda row: (float(row["cer_percent"]), -int(row["numeric_cell_exact"].split('/')[0])))
    baseline = rows[0]
    before_after = [{"sample": "Vietnamese scanned financial table", "metric": key,
                     "before_method": baseline["experiment"], "before": baseline[key],
                     "after_method": best["experiment"], "after": best[key]}
                    for key in ("cer_percent", "wer_percent", "header_exact_tokens", "numeric_cell_exact", "table_row_alignment", "execution_ms")]
    before_after += [{"sample": "Vietnamese scanned financial table", "metric": "ocr_text",
                      "before_method": baseline["experiment"], "before": norm(texts[baseline["experiment"]]),
                      "after_method": best["experiment"], "after": norm(texts[best["experiment"]])}]
    with (REPORTS / "ocr_table_before_after.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(before_after[0])); writer.writeheader(); writer.writerows(before_after)
    print({"baseline": baseline["experiment"], "baseline_cer": baseline["cer_percent"],
           "best": best["experiment"], "best_cer": best["cer_percent"], "rows": len(rows)})


if __name__ == "__main__":
    main()

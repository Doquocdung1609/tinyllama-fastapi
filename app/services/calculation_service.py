"""Deterministic calculations over verified structured table evidence."""
from __future__ import annotations

import re
import unicodedata
from typing import Any


def _norm(value: str) -> str:
    text = unicodedata.normalize("NFKD", value.casefold().replace("đ", "d"))
    return "".join(char for char in text if not unicodedata.combining(char))


def parse_financial_number(value: Any) -> tuple[float, str] | None:
    original = str(value).strip()
    if not original or not re.search(r"\d", original):
        return None
    negative = bool(re.search(r"\(\s*[\d.,\s]+\s*\)", original))
    unit_match = re.search(r"(%|triệu\s+đồng|tỷ\s+đồng|VND|USD)", original, re.IGNORECASE)
    unit = unit_match.group(1) if unit_match else ""
    cleaned = re.sub(r"[^\d,.-]", "", original).strip(".")
    if not cleaned:
        return None
    if "," in cleaned and "." in cleaned:
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        tail = cleaned.rsplit(",", 1)[1]
        cleaned = cleaned.replace(",", "" if len(tail) == 3 and unit != "%" else ".")
    elif "." in cleaned:
        tail = cleaned.rsplit(".", 1)[1]
        if len(tail) == 3 and unit != "%":
            cleaned = cleaned.replace(".", "")
    try:
        number = float(cleaned)
    except ValueError:
        return None
    if negative and number > 0:
        number = -number
    return number, unit


def _table_candidates(included: list[dict]) -> list[dict]:
    candidates = []
    for position, item in enumerate(included, 1):
        if (item.get("modality") or "text") != "table":
            continue
        data = item.get("structured_data") or {}
        columns, rows = data.get("columns") or [], data.get("rows") or []
        if data.get("status") != "OK" or not columns or not rows:
            continue
        candidates.append({"position": position, "item": item, "data": data,
                           "columns": [str(value) for value in columns],
                           "rows": [[str(value) for value in row] for row in rows]})
    return candidates


def _best_row(question: str, rows: list[list[str]]) -> list[str] | None:
    query = set(re.findall(r"[a-z0-9]+", _norm(question)))
    scored = []
    for row in rows:
        label = row[0] if row else ""
        tokens = set(re.findall(r"[a-z0-9]+", _norm(label)))
        score = len(query & tokens) / max(1, len(tokens))
        scored.append((score, row))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return scored[0][1] if scored and scored[0][0] > 0 else (rows[0] if len(rows) == 1 else None)


def _format_number(value: float) -> str:
    return f"{value:,.2f}".rstrip("0").rstrip(".").replace(",", " ")


def _find_named_row(rows: list[list[str]], aliases: tuple[str, ...]) -> list[str] | None:
    for row in rows:
        label = _norm(row[0] if row else "")
        if any(alias in label for alias in aliases):
            return row
    return None


def _row_unit(columns: list[str], row: list[str]) -> str:
    for index, column in enumerate(columns):
        if any(term in _norm(column) for term in ("don vi", "unit", "currency")) and index < len(row):
            return row[index].strip()
    return ""


def calculate_from_tables(question: str, included: list[dict]) -> dict | None:
    """Return a sourced deterministic answer for supported table operations."""
    normalized = _norm(question)
    tables = _table_candidates(included)
    if not tables:
        return None
    wants_growth = "tang truong" in normalized or "percentage change" in normalized
    wants_highest = any(term in normalized for term in ("cao nhat", "lon nhat", "highest", "largest"))
    wants_current_ratio = any(term in normalized for term in
                              ("ty le thanh toan hien hanh", "current ratio"))
    wants_debt_ratio = any(term in normalized for term in ("ty le no", "debt ratio"))
    wants_margin = any(term in normalized for term in ("bien loi nhuan", "profit margin"))
    if not any((wants_growth, wants_highest, wants_current_ratio, wants_debt_ratio, wants_margin)):
        return None

    for table in tables:
        columns, rows, position = table["columns"], table["rows"], table["position"]
        evidence_id = f"E{position}"
        years = re.findall(r"\b(?:19|20)\d{2}\b", question)
        if wants_growth:
            row = _best_row(question, rows)
            if not row:
                continue
            year_columns = [(idx, value) for idx, value in enumerate(columns)
                            if re.fullmatch(r"(?:19|20)\d{2}", value.strip())]
            requested = [(idx, year) for idx, year in year_columns if not years or year in years]
            if len(requested) < 2:
                requested = year_columns[:2]
            if len(requested) < 2:
                continue
            (old_idx, old_year), (new_idx, new_year) = requested[0], requested[-1]
            if max(old_idx, new_idx) >= len(row):
                continue
            old, new = parse_financial_number(row[old_idx]), parse_financial_number(row[new_idx])
            if not old or not new or old[0] == 0 or old[1] != new[1]:
                continue
            unit = old[1] or _row_unit(columns, row)
            rate = (new[0] - old[0]) / abs(old[0]) * 100
            answer = (f"Tốc độ tăng trưởng {row[0]} từ {old_year} đến {new_year}: "
                      f"({_format_number(new[0])} - {_format_number(old[0])}) / "
                      f"{_format_number(abs(old[0]))} × 100 = {_format_number(rate)}%. [{evidence_id}]")
            return {"operation": "growth_rate", "formula": "(new-old)/abs(old)*100",
                    "inputs": {old_year: old[0], new_year: new[0], "unit": unit},
                    "result": rate, "result_unit": "%", "answer": answer,
                    "evidence_ids": [evidence_id], "verified": True}

        if wants_highest:
            row = _best_row(question, rows)
            if row:
                values = []
                for index, cell in enumerate(row[1:], start=1):
                    parsed = parse_financial_number(cell)
                    if parsed and index < len(columns):
                        values.append((parsed[0], parsed[1], columns[index], cell))
                if values:
                    value, unit, label, original = max(values, key=lambda item: item[0])
                    answer = (f"Giá trị cao nhất của {row[0]} là {original} tại {label}. "
                              f"[{evidence_id}]")
                    return {"operation": "maximum", "inputs": values, "result": value,
                            "result_unit": unit, "answer": answer,
                            "evidence_ids": [evidence_id], "verified": True}
            flat = []
            for row_item in rows:
                for index, cell in enumerate(row_item[1:], start=1):
                    parsed = parse_financial_number(cell)
                    if parsed:
                        flat.append((parsed[0], parsed[1], row_item[0],
                                     columns[index] if index < len(columns) else str(index), cell))
            if flat:
                value, unit, row_label, column_label, original = max(flat, key=lambda item: item[0])
                answer = (f"Chỉ tiêu có giá trị lớn nhất là {row_label}: {original} "
                          f"({column_label}). [{evidence_id}]")
                return {"operation": "maximum", "inputs": flat, "result": value,
                        "result_unit": unit, "answer": answer,
                        "evidence_ids": [evidence_id], "verified": True}

        ratio_spec = None
        if wants_current_ratio:
            ratio_spec = (("tai san ngan han", "current assets"),
                          ("no ngan han", "current liabilities"), False,
                          "Tỷ lệ thanh toán hiện hành")
        elif wants_debt_ratio:
            ratio_spec = (("tong no", "no phai tra", "total liabilities"),
                          ("tong tai san", "total assets"), True, "Tỷ lệ nợ")
        elif wants_margin:
            ratio_spec = (("loi nhuan", "profit"), ("doanh thu", "revenue"), True,
                          "Biên lợi nhuận")
        if ratio_spec:
            numerator = _find_named_row(rows, ratio_spec[0])
            denominator = _find_named_row(rows, ratio_spec[1])
            if numerator and denominator:
                requested_year = next((year for year in re.findall(r"\b(?:19|20)\d{2}\b", question)
                                       if year in columns), None)
                preferred_index = columns.index(requested_year) if requested_year else None
                column_index = (preferred_index if preferred_index is not None and
                                preferred_index < min(len(numerator), len(denominator)) and
                                parse_financial_number(numerator[preferred_index]) and
                                parse_financial_number(denominator[preferred_index]) else
                                next((index for index in range(1, min(len(numerator), len(denominator)))
                                      if parse_financial_number(numerator[index]) and
                                      parse_financial_number(denominator[index])), None))
                if column_index is None:
                    continue
                top = parse_financial_number(numerator[column_index])
                bottom = parse_financial_number(denominator[column_index])
                if not top or not bottom or bottom[0] == 0 or top[1] != bottom[1]:
                    continue
                unit = top[1] or _row_unit(columns, numerator)
                denominator_unit = bottom[1] or _row_unit(columns, denominator)
                if unit != denominator_unit:
                    continue
                multiplier = 100 if ratio_spec[2] else 1
                result = top[0] / bottom[0] * multiplier
                suffix = "%" if multiplier == 100 else " lần"
                answer = (f"{ratio_spec[3]} = {numerator[0]} / {denominator[0]} = "
                          f"{_format_number(top[0])} / {_format_number(bottom[0])} = "
                          f"{_format_number(result)}{suffix}. [{evidence_id}]")
                return {"operation": "financial_ratio", "formula": "numerator/denominator",
                        "inputs": {numerator[0]: top[0], denominator[0]: bottom[0],
                                   "unit": unit}, "result": result,
                        "result_unit": suffix.strip(), "answer": answer,
                        "evidence_ids": [evidence_id], "verified": True}
    return None

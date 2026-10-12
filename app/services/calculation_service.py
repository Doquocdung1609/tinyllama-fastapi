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


def _column_unit(column: str) -> str:
    match = re.search(r"(%|triệu\s+đồng|tỷ\s+đồng|VND|USD(?:\s+million)?)", column, re.IGNORECASE)
    return match.group(1) if match else ""


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
    wants_growth = ("tang truong" in normalized or "percentage change" in normalized or
                    "tang bao nhieu phan tram" in normalized or "giam bao nhieu phan tram" in normalized)
    wants_highest = any(term in normalized for term in ("cao nhat", "lon nhat", "highest", "largest"))
    wants_current_ratio = any(term in normalized for term in
                              ("ty le thanh toan hien hanh", "current ratio"))
    wants_debt_ratio = any(term in normalized for term in ("ty le no", "debt ratio"))
    wants_margin = any(term in normalized for term in ("bien loi nhuan", "profit margin"))
    record_ids = list(dict.fromkeys(re.findall(r"\b[A-Za-z]+\d+\b", question, re.IGNORECASE)))
    wants_record_comparison = len(record_ids) >= 2 and any(term in normalized for term in ("so sanh", "doi chieu"))
    wants_lookup = (bool(re.search(r"\b(?:19|20)\d{2}\b", question)) and
                    any(term in normalized for term in ("bao nhieu", "gia tri", "the con", "chi tieu dang noi den")) and
                    not any(term in normalized for term in ("tai sao", "vi sao")) and
                    not any((wants_current_ratio, wants_debt_ratio, wants_margin)))
    if not any((wants_growth, wants_highest, wants_current_ratio, wants_debt_ratio, wants_margin,
                wants_record_comparison, wants_lookup)):
        return None

    if wants_record_comparison:
        found = []
        for table in tables:
            for row in table["rows"]:
                if row and any(row[0].casefold() == record_id.casefold() for record_id in record_ids):
                    found.append({"record_id": row[0], "row": row, "columns": table["columns"],
                                  "evidence_id": f"E{table['position']}", "item": table["item"]})
        if len({item["record_id"].casefold() for item in found}) == len(record_ids):
            details, evidence_ids, numeric_values = [], [], []
            for record_id in record_ids:
                item = next(value for value in found if value["record_id"].casefold() == record_id.casefold())
                cells = [f"{column}: {item['row'][index]}" for index, column in enumerate(item["columns"][1:], start=1)
                         if index < len(item["row"])]
                details.append(f"{item['record_id']} — " + ", ".join(cells) + f". [{item['evidence_id']}]")
                evidence_ids.append(item["evidence_id"])
                numeric_values.extend(parse_financial_number(cell) for cell in item["row"][1:])
            return {"operation": "record_comparison", "inputs": found,
                    "result": [item[0] for item in numeric_values if item], "verified": True,
                    "evidence_ids": list(dict.fromkeys(evidence_ids)), "answer": "\n".join(details)}

    for table in tables:
        columns, rows, position = table["columns"], table["rows"], table["position"]
        evidence_id = f"E{position}"
        years = re.findall(r"\b(?:19|20)\d{2}\b", question)
        if wants_growth:
            row = _best_row(question, rows)
            year_columns = [(idx, value) for idx, value in enumerate(columns)
                            if re.fullmatch(r"(?:19|20)\d{2}", value.strip())]
            # Layout A: one metric per row, years are columns.
            if not row or len(year_columns) < 2:
                # Layout B: one year per row, metrics are columns.
                target_index = next((index for index, column in enumerate(columns[1:], start=1)
                    if set(re.findall(r"[a-z0-9]+", _norm(column))) &
                       set(re.findall(r"[a-z0-9]+", normalized))), None)
                year_rows = {item[0].strip(): item for item in rows
                             if item and re.fullmatch(r"(?:19|20)\d{2}", item[0].strip())}
                requested_years = years if len(years) >= 2 else sorted(year_rows)[:2]
                if "nam truoc" in normalized or "so voi" in normalized:
                    requested_years = sorted(requested_years, key=int)
                if target_index is not None and len(requested_years) >= 2 and all(year in year_rows for year in requested_years[:2]):
                    old_year, new_year = requested_years[0], requested_years[-1]
                    old_row, new_row = year_rows[old_year], year_rows[new_year]
                    if target_index < len(old_row) and target_index < len(new_row):
                        old, new = parse_financial_number(old_row[target_index]), parse_financial_number(new_row[target_index])
                        if old and new and old[0] != 0:
                            unit = old[1] or new[1] or _column_unit(columns[target_index])
                            rate = (new[0] - old[0]) / abs(old[0]) * 100
                            answer = (f"{columns[target_index]} {old_year}: {_format_number(old[0])} {unit}; "
                                      f"{new_year}: {_format_number(new[0])} {unit}. Tăng trưởng = "
                                      f"({_format_number(new[0])} - {_format_number(old[0])}) / "
                                      f"{_format_number(abs(old[0]))} × 100 = {_format_number(rate)}%. [{evidence_id}]")
                            return {"operation": "growth_rate", "formula": "(new-old)/abs(old)*100",
                                    "inputs": {old_year: old[0], new_year: new[0], "unit": unit},
                                    "result": rate, "result_unit": "%", "answer": answer,
                                    "evidence_ids": [evidence_id], "verified": True,
                                    "source_cells": [{"row": old_year, "column": columns[target_index], "value": old_row[target_index]},
                                                     {"row": new_year, "column": columns[target_index], "value": new_row[target_index]}]}
                continue
            requested = [(idx, year) for idx, year in year_columns if not years or year in years]
            if len(requested) < 2:
                requested = year_columns[:2]
            if len(requested) < 2:
                continue
            if "nam truoc" in normalized or "so voi" in normalized:
                requested = sorted(requested, key=lambda item: int(item[1]))
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

        if wants_lookup:
            requested_year = years[-1] if years else None
            query_tokens = set(re.findall(r"[a-z0-9]+", normalized))
            # Metric rows, year columns.
            row = _best_row(question, rows)
            if row and requested_year in columns:
                column_index = columns.index(requested_year)
                if column_index < len(row):
                    parsed = parse_financial_number(row[column_index])
                    if parsed:
                        unit = parsed[1] or _row_unit(columns, row)
                        return {"operation": "table_cell_lookup", "inputs": {"row": row[0], "column": requested_year},
                                "result": parsed[0], "result_unit": unit, "verified": True,
                                "evidence_ids": [evidence_id],
                                "answer": f"{row[0]} năm {requested_year} là {row[column_index]} {unit}. [{evidence_id}]"}
            # Year rows, metric columns.
            year_row = next((item for item in rows if item and item[0].strip() == requested_year), None)
            metric_index = next((index for index, column in enumerate(columns[1:], start=1)
                                 if set(re.findall(r"[a-z0-9]+", _norm(column))) & query_tokens), None)
            if year_row and metric_index is not None and metric_index < len(year_row):
                parsed = parse_financial_number(year_row[metric_index])
                if parsed:
                    unit = parsed[1] or _column_unit(columns[metric_index])
                    return {"operation": "table_cell_lookup", "inputs": {"row": requested_year, "column": columns[metric_index]},
                            "result": parsed[0], "result_unit": unit, "verified": True,
                            "evidence_ids": [evidence_id],
                            "answer": f"{columns[metric_index]} năm {requested_year} là {year_row[metric_index]} {unit}. [{evidence_id}]"}

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


def analyze_charts(question: str, included: list[dict]) -> dict | None:
    """Answer exact chart-label tasks without asking a text-only LLM to inspect pixels."""
    normalized = _norm(question)
    for position, item in enumerate(included, 1):
        if (item.get("modality") or "text") != "chart":
            continue
        data = item.get("structured_data") or {}
        pairs = data.get("label_value_pairs") or []
        parsed = []
        for pair in pairs:
            number = parse_financial_number(pair.get("value", ""))
            if number:
                parsed.append({"label": str(pair.get("label", "")), "raw": str(pair.get("value", "")),
                               "number": number[0], "unit": number[1]})
        if not parsed:
            continue
        evidence_id = f"E{position}"
        if any(term in normalized for term in ("cao nhat", "lon nhat", "ty trong cao nhat")):
            highest = max(parsed, key=lambda entry: entry["number"])
            return {"operation": "chart_maximum", "inputs": parsed, "result": highest["number"],
                    "result_unit": highest["unit"], "verified": True, "evidence_ids": [evidence_id],
                    "answer": f"{highest['label']} chiếm tỷ trọng cao nhất: {highest['raw']}. [{evidence_id}]"}
        years = re.findall(r"\b(?:19|20)\d{2}\b", question)
        if years and any(term in normalized for term in ("doi chieu", "nhan so", "bieu do", "chart")):
            matches = [entry for entry in parsed if any(year in entry["label"] for year in years)]
            if matches:
                details = "; ".join(f"{entry['label']}: {entry['raw']}" for entry in matches)
                return {"operation": "chart_label_lookup", "inputs": matches,
                        "result": [entry["number"] for entry in matches], "verified": True,
                        "evidence_ids": [evidence_id],
                        "answer": f"Nhãn số trên biểu đồ ghi {details}. [{evidence_id}]"}
        if any(term in normalized for term in ("chuoi", "series")) or "khac biet" in normalized:
            series: dict[str, list[dict]] = {}
            for entry in parsed:
                label = entry["label"]
                year_match = re.search(r"\b(?:19|20)\d{2}\b", label)
                series_name = label[:year_match.start()].strip() if year_match else label
                series.setdefault(series_name or "Chuỗi", []).append({**entry, "year": year_match.group(0) if year_match else ""})
            if len(series) >= 2:
                statements = []
                coverage = []
                for name, values in series.items():
                    values.sort(key=lambda entry: entry["year"])
                    trend = "tăng" if values[-1]["number"] > values[0]["number"] else "giảm" if values[-1]["number"] < values[0]["number"] else "không đổi"
                    statements.append(f"{name} {trend} từ {values[0]['raw']} ({values[0]['year']}) đến {values[-1]['raw']} ({values[-1]['year']})")
                    coverage.append(name)
                return {"operation": "chart_series_comparison", "inputs": series,
                        "series_coverage": coverage, "verified": True, "evidence_ids": [evidence_id],
                        "answer": "; trong khi ".join(statements) + f". [{evidence_id}]"}
    return None

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
    unit_match = re.search(
        r"(%|phần\s*trăm|percent|nghìn\s*(?:đồng|vnd)?|nghin\s*(?:dong|vnd)?|thousand\s*(?:vnd|usd)?|"
        r"triệu\s*(?:đồng|vnd)?|trieu\s*(?:dong|vnd)?|million\s*(?:vnd|usd)?|tỷ\s*(?:đồng|vnd)?|ty\s*(?:dong|vnd)?|"
        r"billion\s*(?:vnd|usd)?|nghìn\s*tỷ\s*(?:đồng|vnd)?|trillion\s*(?:vnd|usd)?|"
        r"VND|VNĐ|USD|EUR|lần|times)", original, re.IGNORECASE)
    unit = re.sub(r"\s+", " ", unit_match.group(1)).strip() if unit_match else ""
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


def _unit_signature(unit: str) -> tuple[str, float]:
    """Map a displayed financial unit to currency/dimension and magnitude."""
    value = _norm(unit).strip()
    currency = ""
    if any(token in value for token in ("usd", "$")):
        currency = "USD"
    elif "eur" in value:
        currency = "EUR"
    elif any(token in value for token in ("dong", "vnd", "vnđ")):
        currency = "VND"
    if any(token in value for token in ("nghin ty", "trillion")):
        scale = 1_000_000_000_000.0
    elif any(token in value for token in ("ty", "billion")):
        scale = 1_000_000_000.0
    elif any(token in value for token in ("trieu", "million")):
        scale = 1_000_000.0
    elif any(token in value for token in ("nghin", "thousand")):
        scale = 1_000.0
    else:
        scale = 1.0
    if value in {"%", "phan tram", "percent"}:
        return "%", .01
    if value in {"lan", "times"}:
        return "ratio", 1.0
    return currency, scale


def _same_dimension(left: tuple[float, str], right: tuple[float, str]) -> bool:
    left_kind, _ = _unit_signature(left[1])
    right_kind, _ = _unit_signature(right[1])
    return not left_kind or not right_kind or left_kind == right_kind


def _base_value(value: tuple[float, str]) -> float:
    return value[0] * _unit_signature(value[1])[1]


def _table_candidates(included: list[dict]) -> list[dict]:
    grouped: dict[tuple, dict] = {}
    for position, item in enumerate(included, 1):
        if (item.get("modality") or "text") != "table":
            continue
        data = item.get("structured_data") or {}
        columns, rows = data.get("columns") or [], data.get("rows") or []
        if data.get("status") != "OK" or not columns or not rows:
            continue
        key = (item.get("document_id"), item.get("page"),
               data.get("table_id") or item.get("source_id") or item.get("chunk_id"))
        candidate = grouped.setdefault(key, {
            "position": position, "positions": [], "item": item, "items": [], "data": data,
            "columns": [str(value) for value in columns], "rows": [], "row_positions": [],
        })
        candidate["positions"].append(position)
        candidate["items"].append(item)
        for row in rows:
            normalized = [str(value) for value in row]
            if normalized not in candidate["rows"]:
                candidate["rows"].append(normalized)
                candidate["row_positions"].append(position)
    return list(grouped.values())


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


def _ocr_text_cell_lookup(question: str, included: list[dict]) -> dict | None:
    """Recover a clearly aligned financial row when OCR grid reconstruction drops it.

    The value and year order must both appear in included evidence.  Because the
    structure came from OCR prose rather than a verified table cell, the result
    is explicitly marked for source-image review.
    """
    year_match = re.search(r"\b(?:19|20)\d{2}\b", question)
    normalized = _norm(question)
    if not year_match or not any(term in normalized for term in ("bao nhieu", "gia tri", "the con")):
        return None
    requested_year = year_match.group(0)
    header_years: list[str] = []
    for item in included:
        for line in str(item.get("text") or "").splitlines():
            years = list(dict.fromkeys(re.findall(r"\b(?:19|20)\d{2}\b", line)))
            if requested_year in years and len(years) >= 2 and len(years) > len(header_years):
                header_years = years
    if not header_years:
        return None

    ignored = {"bao", "nhieu", "gia", "tri", "nam", "la", "cua", "the", "con", requested_year}
    query_tokens = set(re.findall(r"[a-z0-9]+", normalized)) - ignored
    amount_pattern = re.compile(r"(?<![\d.,])[-−]?\s*\d+(?:[.,]\d{3})+(?![\d.,])")
    candidates = []
    for position, item in enumerate(included, 1):
        for line in str(item.get("text") or "").splitlines():
            amounts = [value.strip().replace("−", "-") for value in amount_pattern.findall(line)]
            if len(amounts) < len(header_years):
                continue
            label = amount_pattern.sub(" ", line)
            label_tokens = set(re.findall(r"[a-z0-9]+", _norm(label)))
            overlap = len(query_tokens & label_tokens) / max(1, len(query_tokens))
            if overlap >= .45:
                candidates.append((overlap, position, item, line, amounts[-len(header_years):]))
    if not candidates:
        return None
    _, position, item, line, amounts = max(candidates, key=lambda value: value[0])
    column_index = header_years.index(requested_year)
    raw_value = amounts[column_index]
    parsed = parse_financial_number(raw_value)
    if not parsed:
        return None
    unit = "VND" if re.search(r"\bVND\b", " ".join(str(value.get("text") or "") for value in included),
                              re.IGNORECASE) else parsed[1]
    label = amount_pattern.sub(" ", line)
    label = re.sub(r"^\s*\d+(?:[.]\d+)?\s+", "", label).strip(" -–—|:")
    return {"operation": "ocr_text_cell_lookup", "inputs": {"row": label, "column": requested_year},
            "result": parsed[0], "result_unit": unit, "verified": False,
            "requires_source_review": True, "evidence_ids": [f"E{position}"],
            "answer": (f"Theo dòng OCR, {label.lower()} năm {requested_year} là {raw_value}"
                       f"{(' ' + unit) if unit else ''}. [E{position}] "
                       "Giá trị này được đọc từ ảnh scan và cần đối chiếu ảnh gốc trước khi sử dụng chính thức.")}


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


def _value_at_period(columns: list[str], row: list[str], requested_year: str | None) -> tuple[int, tuple[float, str]] | None:
    if requested_year and requested_year in columns:
        index = columns.index(requested_year)
        if index < len(row) and (parsed := parse_financial_number(row[index])):
            return index, parsed
    for index in range(1, min(len(columns), len(row))):
        if parsed := parse_financial_number(row[index]):
            return index, parsed
    return None


def _row_unit(columns: list[str], row: list[str]) -> str:
    for index, column in enumerate(columns):
        if any(term in _norm(column) for term in ("don vi", "unit", "currency")) and index < len(row):
            return row[index].strip()
    return ""


_VERIFICATION_CUES = (
    "dung khong", "phai khong", "dung chua", "chinh xac khong", "co dung", "co chinh xac",
    "kiem tra", "xac minh", "doi chieu", "toi nghi", "so nay", "claim verification",
)


def is_verification_question(question: str) -> bool:
    """Detect a request to verify a user-provided factual or numeric claim."""
    normalized = _norm(question)
    return any(cue in normalized for cue in _VERIFICATION_CUES)


def verification_retrieval_question(question: str) -> str:
    """Remove untrusted claimed numbers from retrieval without changing years.

    A false value is the hypothesis being checked, so requiring it to occur in
    source evidence guarantees a false refusal. The original question remains
    available to the verifier and is never overwritten in message storage.
    """
    if not is_verification_question(question):
        return question
    return re.sub(
        r"(?<![\w])[-+]?\d+(?:[.,]\d+)?(?![\w])",
        lambda match: match.group(0) if re.fullmatch(r"(?:19|20)\d{2}", match.group(0)) else " ",
        question,
    )


def _claimed_numbers(question: str) -> list[tuple[float, str, str]]:
    claims = []
    for match in re.finditer(
            r"(?<![\w])([-+]?\d+(?:[.,]\d+)?)\s*(%|triệu\s+đồng|tỷ\s+đồng|VND|USD|lần)?(?![\w])",
            question, flags=re.IGNORECASE):
        raw = match.group(0).strip()
        if re.fullmatch(r"(?:19|20)\d{2}", match.group(1)):
            continue
        parsed = parse_financial_number(raw)
        if parsed:
            claims.append((parsed[0], (match.group(2) or parsed[1] or "").strip(), raw))
    return claims


def _explicit_company(question: str) -> str | None:
    match = re.search(r"\b(?:công\s+ty|company)\s+([A-ZÀ-Ỹ][\wÀ-ỹ.&-]*)", question,
                      flags=re.IGNORECASE)
    return _norm(match.group(1)) if match else None


def verify_financial_claim(question: str, included: list[dict]) -> dict | None:
    """Compare a user's financial claim with structured source cells.

    The return value is deterministic and exposes a four-way verification
    status. It never promotes a number in the question to source evidence.
    """
    if not is_verification_question(question):
        return None
    normalized = _norm(question)
    tables = _table_candidates(included)
    claims = _claimed_numbers(question)
    years = re.findall(r"\b(?:19|20)\d{2}\b", question)
    company = _explicit_company(question)
    if not claims:
        return {"operation": "claim_verification", "verification_status": "INSUFFICIENT_EVIDENCE",
                "verified": False, "evidence_ids": [],
                "answer": "Chưa có giá trị cụ thể trong câu hỏi để đối chiếu. Vui lòng nêu số liệu hoặc phép tính cần kiểm tra."}
    if not tables:
        return {"operation": "claim_verification", "verification_status": "INSUFFICIENT_EVIDENCE",
                "verified": False, "evidence_ids": [],
                "answer": "Không có bảng dữ liệu đủ cấu trúc để kiểm tra khẳng định này."}

    matches = []
    for table in tables:
        columns, rows = table["columns"], table["rows"]
        table_context = _norm(" ".join(str(value) for value in (
            table["data"].get("caption"), table["item"].get("filename")) if value))
        if company and company not in table_context:
            continue
        year = years[-1] if years else None
        row = _best_row(question, rows)
        index = None
        label = row[0] if row else ""
        # Layout A: metrics in rows and periods in columns.
        if row and year and year in columns:
            index = columns.index(year)
        elif row and len([column for column in columns if re.fullmatch(r"(?:19|20)\d{2}", column.strip())]) == 1:
            index = next(i for i, column in enumerate(columns) if re.fullmatch(r"(?:19|20)\d{2}", column.strip()))
            year = columns[index].strip()
        # Layout B: periods in rows and metrics in columns.
        elif year and any(str(candidate[0]).strip() == year for candidate in rows if candidate):
            row = next(candidate for candidate in rows if candidate and str(candidate[0]).strip() == year)
            query_tokens = set(re.findall(r"[a-z0-9]+", normalized))
            scored_columns = []
            for candidate_index, column in enumerate(columns[1:], 1):
                tokens = set(re.findall(r"[a-z0-9]+", _norm(column)))
                scored_columns.append((len(tokens & query_tokens) / max(1, len(tokens)), candidate_index, column))
            scored_columns.sort(reverse=True)
            if scored_columns and scored_columns[0][0] > 0:
                _, index, label = scored_columns[0]
        if not row or index is None or index >= len(row):
            continue
        source = parse_financial_number(row[index])
        if not source:
            continue
        unit = source[1] or _row_unit(columns, row) or _column_unit(columns[index])
        row_tokens = set(re.findall(r"[a-z0-9]+", _norm(label)))
        query_tokens = set(re.findall(r"[a-z0-9]+", normalized))
        context_tokens = set(re.findall(r"[a-z0-9]+", table_context))
        score = (len(row_tokens & query_tokens) / max(1, len(row_tokens)) +
                 .1 * len(context_tokens & query_tokens) / max(1, len(context_tokens)))
        row_position = table["row_positions"][table["rows"].index(row)] if row in table["rows"] else table["position"]
        matches.append({"score": score, "row": row, "label": label, "year": year, "source": source[0],
                        "cell_value": row[index], "source_column": columns[index],
                        "unit": unit, "evidence_id": f"E{row_position}", "table": table})
    matches.sort(key=lambda item: item["score"], reverse=True)
    if not matches or matches[0]["score"] <= 0:
        return {"operation": "claim_verification", "verification_status": "AMBIGUOUS",
                "verified": False, "evidence_ids": [],
                "answer": "Chưa xác định được duy nhất chỉ tiêu và kỳ báo cáo cần kiểm tra. Vui lòng nêu rõ chỉ tiêu và năm."}
    if len(matches) > 1 and matches[0]["score"] == matches[1]["score"] and (
            matches[0]["label"] != matches[1]["label"] or matches[0]["source"] != matches[1]["source"]):
        return {"operation": "claim_verification", "verification_status": "AMBIGUOUS",
                "verified": False, "evidence_ids": [],
                "answer": "Có nhiều ô dữ liệu phù hợp nhưng cho kết quả khác nhau. Vui lòng chỉ rõ bảng hoặc đơn vị cần kiểm tra."}

    match = matches[0]
    claim_value, claim_unit, claim_raw = claims[-1]
    source_value = match["source"]
    unit_compatible = not claim_unit or not match["unit"] or _norm(claim_unit) == _norm(match["unit"])
    equal = unit_compatible and abs(claim_value - source_value) <= max(1e-9, abs(source_value) * 1e-9)
    label, year, unit, evidence_id = match["label"], match["year"], match["unit"], match["evidence_id"]
    unit_text = f" {unit}" if unit else ""
    if equal:
        status = "CONFIRMED"
        answer = (f"Đúng. Theo bảng, {label.lower()} năm {year} là "
                  f"{_format_number(source_value)}{unit_text}. [{evidence_id}]")
    else:
        status = "CONTRADICTED"
        reason = "khác đơn vị" if not unit_compatible else "khác giá trị"
        answer = (f"Không đúng. Khẳng định {claim_raw} {reason} với nguồn. Theo bảng, "
                  f"{label.lower()} năm {year} là {_format_number(source_value)}{unit_text}. [{evidence_id}]")
    return {"operation": "claim_verification", "verification_status": status,
            "claim": {"value": claim_value, "unit": claim_unit, "raw": claim_raw,
                      "metric": label, "year": year},
            "source_value": source_value, "source_unit": unit, "verified": True,
            "evidence_ids": [evidence_id], "answer": answer,
            "source_cells": [{"row": label, "column": year, "value": match["cell_value"]}]}


def calculate_from_tables(question: str, included: list[dict]) -> dict | None:
    """Return a sourced deterministic answer for supported table operations."""
    normalized = _norm(question)
    tables = _table_candidates(included)
    if not tables:
        return _ocr_text_cell_lookup(question, included)
    wants_growth = ("tang truong" in normalized or "percentage change" in normalized or
                    "tang bao nhieu phan tram" in normalized or "giam bao nhieu phan tram" in normalized)
    wants_highest = any(term in normalized for term in ("cao nhat", "lon nhat", "highest", "largest"))
    wants_current_ratio = any(term in normalized for term in
                              ("ty le thanh toan hien hanh", "current ratio"))
    wants_quick_ratio = any(term in normalized for term in
                            ("ty le thanh toan nhanh", "he so thanh toan nhanh", "quick ratio"))
    wants_debt_ratio = any(term in normalized for term in ("ty le no", "debt ratio"))
    statistic_lookup = any(term in normalized for term in (
        "bao nhieu quan sat", "so quan sat", "observation", "trung binh", "mean",
        "do lech chuan", "standard deviation", "gia tri nho nhat", "minimum",
        "gia tri lon nhat", "maximum"))
    wants_roa = ((bool(re.search(r"\broa\b", normalized)) or
                  "loi nhuan tren tong tai san" in normalized) and not statistic_lookup)
    wants_roe = ((bool(re.search(r"\broe\b", normalized)) or
                  "loi nhuan tren von chu so huu" in normalized) and not statistic_lookup)
    wants_gross_margin = any(term in normalized for term in ("bien loi nhuan gop", "gross margin"))
    wants_net_margin = any(term in normalized for term in ("bien loi nhuan rong", "net margin"))
    wants_margin = (any(term in normalized for term in ("bien loi nhuan", "profit margin")) and
                    not wants_gross_margin)
    wants_ocf_ratio = any(term in normalized for term in
                          ("ty le dong tien hoat dong", "operating cash flow ratio"))
    wants_free_cash_flow = any(term in normalized for term in
                               ("dong tien tu do", "free cash flow", "fcf"))
    wants_absolute_change = any(term in normalized for term in
                                ("chenh lech", "thay doi tuyet doi", "absolute change", "tang bao nhieu ")) and not wants_growth
    record_ids = list(dict.fromkeys(re.findall(r"\b[A-Za-z]+\d+\b", question, re.IGNORECASE)))
    wants_record_comparison = len(record_ids) >= 2 and any(term in normalized for term in ("so sanh", "doi chieu"))
    wants_lookup = (bool(re.search(r"\b(?:19|20)\d{2}\b", question)) and
                    any(term in normalized for term in ("bao nhieu", "gia tri", "the con", "chi tieu dang noi den")) and
                    not any(term in normalized for term in ("tai sao", "vi sao")) and
                    not any((wants_current_ratio, wants_quick_ratio, wants_debt_ratio, wants_margin,
                             wants_gross_margin, wants_net_margin, wants_roa, wants_roe,
                             wants_ocf_ratio, wants_free_cash_flow, wants_absolute_change)))
    if not any((wants_growth, wants_highest, wants_current_ratio, wants_debt_ratio, wants_margin,
                wants_quick_ratio, wants_gross_margin, wants_net_margin, wants_roa, wants_roe,
                wants_ocf_ratio, wants_free_cash_flow, wants_absolute_change,
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
        evidence_ids = [f"E{value}" for value in table.get("positions", [position])]
        citation_text = " ".join(f"[{value}]" for value in evidence_ids)
        years = re.findall(r"\b(?:19|20)\d{2}\b", question)
        if wants_absolute_change:
            row = _best_row(question, rows)
            year_columns = [(idx, value) for idx, value in enumerate(columns)
                            if re.fullmatch(r"(?:19|20)\d{2}", value.strip())]
            requested = [(idx, year) for idx, year in year_columns if not years or year in years]
            if row and len(requested) >= 2:
                old_idx, old_year = requested[0]
                new_idx, new_year = requested[-1]
                if max(old_idx, new_idx) < len(row):
                    old, new = parse_financial_number(row[old_idx]), parse_financial_number(row[new_idx])
                    if old and new and _same_dimension(old, new):
                        old_base, new_base = _base_value(old), _base_value(new)
                        result_base = new_base - old_base
                        display_scale = _unit_signature(new[1] or old[1])[1]
                        result = result_base / display_scale
                        unit = new[1] or old[1] or _row_unit(columns, row)
                        return {"operation": "absolute_change", "formula": "new-old",
                                "inputs": {old_year: old[0], new_year: new[0], "unit": unit},
                                "result": result, "result_unit": unit, "verified": True,
                                "evidence_ids": evidence_ids,
                                "source_cells": [{"row": row[0], "column": old_year, "value": row[old_idx]},
                                                 {"row": row[0], "column": new_year, "value": row[new_idx]}],
                                "answer": f"Mức thay đổi tuyệt đối {row[0]} từ {old_year} đến {new_year} = "
                                          f"{_format_number(new[0])} - {_format_number(old[0])} = "
                                          f"{_format_number(result)} {unit}. {citation_text}"}
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
                        if old and new and _base_value(old) != 0 and _same_dimension(old, new):
                            unit = old[1] or new[1] or _column_unit(columns[target_index])
                            rate = (_base_value(new) - _base_value(old)) / abs(_base_value(old)) * 100
                            answer = (f"{columns[target_index]} {old_year}: {_format_number(old[0])} {unit}; "
                                      f"{new_year}: {_format_number(new[0])} {unit}. Tăng trưởng = "
                                      f"({_format_number(new[0])} - {_format_number(old[0])}) / "
                                      f"{_format_number(abs(old[0]))} × 100 = {_format_number(rate)}%. {citation_text}")
                            return {"operation": "growth_rate", "formula": "(new-old)/abs(old)*100",
                                    "inputs": {old_year: old[0], new_year: new[0], "unit": unit},
                                    "result": rate, "result_unit": "%", "answer": answer,
                                    "evidence_ids": evidence_ids, "verified": True,
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
            if not old or not new or _base_value(old) == 0 or not _same_dimension(old, new):
                continue
            unit = old[1] or _row_unit(columns, row)
            rate = (_base_value(new) - _base_value(old)) / abs(_base_value(old)) * 100
            answer = (f"Tốc độ tăng trưởng {row[0]} từ {old_year} đến {new_year}: "
                      f"({_format_number(new[0])} - {_format_number(old[0])}) / "
                      f"{_format_number(abs(old[0]))} × 100 = {_format_number(rate)}%. {citation_text}")
            return {"operation": "growth_rate", "formula": "(new-old)/abs(old)*100",
                    "inputs": {old_year: old[0], new_year: new[0], "unit": unit},
                    "result": rate, "result_unit": "%", "answer": answer,
                    "evidence_ids": evidence_ids, "verified": True}

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
                              f"{citation_text}")
                    return {"operation": "maximum", "inputs": values, "result": value,
                            "result_unit": unit, "answer": answer,
                            "evidence_ids": evidence_ids, "verified": True}
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
                          f"({column_label}). {citation_text}")
                return {"operation": "maximum", "inputs": flat, "result": value,
                        "result_unit": unit, "answer": answer,
                        "evidence_ids": evidence_ids, "verified": True}

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
                                "evidence_ids": evidence_ids,
                                "answer": f"{row[0]} năm {requested_year} là {row[column_index]} {unit}. {citation_text}"}
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
                            "evidence_ids": evidence_ids,
                            "answer": f"{columns[metric_index]} năm {requested_year} là {year_row[metric_index]} {unit}. {citation_text}"}

        if wants_free_cash_flow:
            operating = _find_named_row(rows, ("luu chuyen tien thuan tu hoat dong kinh doanh",
                                                "dong tien tu hoat dong kinh doanh", "operating cash flow"))
            capex = _find_named_row(rows, ("chi mua sam tai san co dinh", "chi tieu von", "capital expenditure", "capex"))
            if operating and capex:
                year = years[-1] if years else None
                op_value, capex_value = _value_at_period(columns, operating, year), _value_at_period(columns, capex, year)
                if op_value and capex_value and op_value[0] == capex_value[0] and _same_dimension(op_value[1], capex_value[1]):
                    op_base, capex_base = _base_value(op_value[1]), abs(_base_value(capex_value[1]))
                    scale = _unit_signature(op_value[1][1] or capex_value[1][1])[1]
                    result = (op_base - capex_base) / scale
                    unit = op_value[1][1] or capex_value[1][1] or _row_unit(columns, operating)
                    period = columns[op_value[0]]
                    return {"operation": "free_cash_flow", "formula": "operating_cash_flow-capex",
                            "inputs": {operating[0]: op_value[1][0], capex[0]: capex_value[1][0], "unit": unit},
                            "result": result, "result_unit": unit, "verified": True,
                            "evidence_ids": evidence_ids,
                            "answer": f"Dòng tiền tự do {period} = {_format_number(op_value[1][0])} - "
                                      f"{_format_number(abs(capex_value[1][0]))} = {_format_number(result)} {unit}. {citation_text}"}

        if wants_quick_ratio:
            current_assets = _find_named_row(rows, ("tai san ngan han", "current assets"))
            inventory = _find_named_row(rows, ("hang ton kho", "inventory"))
            liabilities = _find_named_row(rows, ("no ngan han", "current liabilities"))
            year = years[-1] if years else None
            if current_assets and inventory and liabilities:
                values = [_value_at_period(columns, row, year) for row in (current_assets, inventory, liabilities)]
                if all(values) and len({value[0] for value in values}) == 1 and all(
                        _same_dimension(values[0][1], value[1]) for value in values[1:]):
                    asset, stock, debt = (_base_value(value[1]) for value in values)
                    if debt:
                        result = (asset - stock) / debt
                        period = columns[values[0][0]]
                        return {"operation": "financial_ratio", "formula": "(current_assets-inventory)/current_liabilities",
                                "inputs": {current_assets[0]: values[0][1][0], inventory[0]: values[1][1][0],
                                           liabilities[0]: values[2][1][0]}, "result": result,
                                "result_unit": "lần", "verified": True, "evidence_ids": evidence_ids,
                                "answer": f"Tỷ lệ thanh toán nhanh {period} = ({_format_number(values[0][1][0])} - "
                                          f"{_format_number(values[1][1][0])}) / {_format_number(values[2][1][0])} = "
                                          f"{_format_number(result)} lần. {citation_text}"}

        ratio_spec = None
        if wants_current_ratio:
            ratio_spec = (("tai san ngan han", "current assets"),
                          ("no ngan han", "current liabilities"), False,
                          "Tỷ lệ thanh toán hiện hành")
        elif wants_debt_ratio:
            ratio_spec = (("tong no", "no phai tra", "total liabilities"),
                          ("tong tai san", "total assets"), True, "Tỷ lệ nợ")
        elif wants_gross_margin:
            ratio_spec = (("loi nhuan gop", "gross profit"), ("doanh thu thuan", "doanh thu", "revenue"), True,
                          "Biên lợi nhuận gộp")
        elif wants_net_margin:
            ratio_spec = (("loi nhuan sau thue", "loi nhuan rong", "net income", "net profit"),
                          ("doanh thu thuan", "doanh thu", "revenue"), True, "Biên lợi nhuận ròng")
        elif wants_roa:
            ratio_spec = (("loi nhuan sau thue", "loi nhuan rong", "net income"),
                          ("tong tai san binh quan", "average total assets"), True, "ROA")
        elif wants_roe:
            ratio_spec = (("loi nhuan sau thue", "loi nhuan rong", "net income"),
                          ("von chu so huu binh quan", "average equity"), True, "ROE")
        elif wants_ocf_ratio:
            ratio_spec = (("luu chuyen tien thuan tu hoat dong kinh doanh", "dong tien tu hoat dong kinh doanh", "operating cash flow"),
                          ("no ngan han", "current liabilities"), False, "Tỷ lệ dòng tiền hoạt động")
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
                if not top or not bottom or bottom[0] == 0 or not _same_dimension(top, bottom):
                    continue
                unit = top[1] or _row_unit(columns, numerator)
                denominator_unit = bottom[1] or _row_unit(columns, denominator)
                multiplier = 100 if ratio_spec[2] else 1
                result = _base_value(top) / _base_value(bottom) * multiplier
                suffix = "%" if multiplier == 100 else " lần"
                answer = (f"{ratio_spec[3]} = {numerator[0]} / {denominator[0]} = "
                          f"{_format_number(top[0])}{(' ' + top[1]) if top[1] else ''} / "
                          f"{_format_number(bottom[0])}{(' ' + bottom[1]) if bottom[1] else ''} = "
                          f"{_format_number(result)}{suffix}. {citation_text}")
                return {"operation": "financial_ratio", "formula": "numerator/denominator",
                        "inputs": {numerator[0]: top[0], denominator[0]: bottom[0],
                                   "unit": unit}, "result": result,
                        "input_units": {numerator[0]: top[1] or unit,
                                        denominator[0]: bottom[1] or denominator_unit},
                        "result_unit": suffix.strip(), "answer": answer,
                        "evidence_ids": evidence_ids, "verified": True}
    if any((wants_current_ratio, wants_quick_ratio, wants_debt_ratio, wants_margin,
            wants_gross_margin, wants_net_margin, wants_roa, wants_roe,
            wants_ocf_ratio, wants_free_cash_flow, wants_absolute_change, wants_growth)):
        detail = ("ROA/ROE yêu cầu số dư bình quân của kỳ; số dư cuối kỳ không được tự động thay thế."
                  if wants_roa or wants_roe else
                  "Thiếu một hoặc nhiều ô dữ liệu cùng kỳ và cùng đơn vị cần cho công thức.")
        return {"operation": "insufficient_calculation_inputs", "verified": False,
                "evidence_ids": [], "result": None,
                "answer": f"Không đủ dữ liệu đã kiểm chứng để tính chỉ tiêu này. {detail}"}
    return None


def analyze_charts(question: str, included: list[dict]) -> dict | None:
    """Answer exact chart-label tasks without asking a text-only LLM to inspect pixels."""
    normalized = _norm(question)
    for position, item in enumerate(included, 1):
        if (item.get("modality") or "text") != "chart":
            continue
        data = item.get("structured_data") or {}
        pairs = data.get("label_value_pairs") or []
        evidence_id = f"E{position}"
        chart_type = _norm(str(data.get("chart_type") or "unknown")).replace(" ", "_")
        is_diagram = chart_type in {"flowchart", "diagram", "organizational_graph", "network_diagram"}
        if is_diagram:
            return {"operation": "chart_capability_limit", "verified": False,
                    "evidence_ids": [evidence_id], "chart_type": chart_type,
                    "answer": "Nguồn này là sơ đồ, không phải biểu đồ số. Tôi chỉ có thể mô tả các nhãn đọc được, không suy diễn giá trị số. "
                              f"[{evidence_id}]"}
        parsed = []
        for pair in pairs:
            number = parse_financial_number(pair.get("value", ""))
            if number:
                parsed.append({"label": str(pair.get("label", "")), "raw": str(pair.get("value", "")),
                               "number": number[0], "unit": number[1]})
        if not parsed:
            return {"operation": "chart_capability_limit", "verified": False,
                    "evidence_ids": [evidence_id], "chart_type": chart_type,
                    "answer": "Biểu đồ không có nhãn giá trị máy đọc được đủ tin cậy; không thể xác nhận giá trị số chính xác. "
                              f"[{evidence_id}]"}
        units = {_norm(entry["unit"]) for entry in parsed if entry["unit"]}
        dual_axis = bool(data.get("dual_axis") or len(data.get("axes") or []) > 1 or "dual_axis" in chart_type)
        if dual_axis and len(units) > 1 and any(term in normalized for term in ("so sanh", "khac biet", "cao hon", "thap hon")):
            return {"operation": "chart_axis_mismatch", "verified": False,
                    "evidence_ids": [evidence_id], "chart_type": chart_type,
                    "units": sorted(units),
                    "answer": "Các chuỗi dùng trục hoặc đơn vị khác nhau nên không thể so sánh trực tiếp độ cao hay giá trị giữa chúng. "
                              f"[{evidence_id}]"}
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
                requested = {name for name in series if _norm(name) in normalized}
                explicit = set(re.findall(r"(?:chuoi|series)\s+(?!thu\b)[a-z0-9]+", normalized))
                if explicit and len(requested) < len(explicit):
                    return {"operation": "chart_series_incomplete", "verified": False,
                            "evidence_ids": [evidence_id], "series_coverage": sorted(series),
                            "answer": "Không đọc được đầy đủ mọi chuỗi được yêu cầu từ biểu đồ; cần nhãn hoặc dữ liệu nguồn rõ hơn để so sánh. "
                                      f"[{evidence_id}]"}
                series_units = {name: {_norm(v["unit"]) for v in values if v["unit"]}
                                for name, values in series.items()}
                nonempty_units = {unit for values in series_units.values() for unit in values}
                if len(nonempty_units) > 1:
                    return {"operation": "chart_unit_mismatch", "verified": False,
                            "evidence_ids": [evidence_id], "series_coverage": sorted(series),
                            "units": sorted(nonempty_units),
                            "answer": "Các chuỗi có đơn vị khác nhau nên không thể so sánh trực tiếp giá trị giữa chúng. "
                                      f"[{evidence_id}]"}
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

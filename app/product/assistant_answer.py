"""Deterministic, source-bound answer contract for PDF document questions.

Retrieval evidence is never sufficient to certify a numeric cell. Reviewed
facts are routed through the existing Decimal verifier in analysis.py.
"""

from __future__ import annotations

import re
from datetime import date

from app.product.pdf_extract import folded


NUMERIC_TERMS = (
    'bao nhieu', 'how much', 'how many', 'what were', 'what was',
    'so lieu', 'gia tri', 'tong tai san', 'total assets', 'doanh thu',
    'revenue', 'net sales', 'loi nhuan', 'profit', 'chenh lech',
    'tang truong', 'growth', 'phan tram', 'percent', 'ty le', 'ratio',
    'net income', 'highest', 'largest', 'maximum', 'lowest', 'minimum',
)


def needs_number(question: str) -> bool:
    value = folded(question)
    return any(term in value for term in NUMERIC_TERMS)


def selected_period(question: str, facts: list[dict]) -> str | None:
    """Choose only when the question identifies exactly one reviewed period."""
    dates = []
    for day, month, year in re.findall(r'\b(\d{1,2})/(\d{1,2})/(20\d{2})\b', question):
        try:
            dates.append(date(int(year), int(month), int(day)).isoformat())
        except ValueError:
            return None
    if dates:
        matches = {f['period'] for f in facts if f['period'] in dates}
    else:
        years = set(re.findall(r'\b20\d{2}\b', question))
        matches = {f['period'] for f in facts if f['period'][:4] in years}
    return next(iter(matches)) if len(matches) == 1 else None


def reviewed_plan(question: str, facts: list[dict], aliases: dict[str, list[str]]) -> dict | None:
    """Plan a verified extract/change only with unique reviewed facts and periods."""
    q = folded(question)
    metrics = [m for m, names in aliases.items() if any(name in q for name in names)]
    if len(metrics) != 1:
        return None
    metric = metrics[0]
    candidates = [f for f in facts if f.get('metric') == metric]
    if not candidates:
        return None
    years = set(re.findall(r'\b20\d{2}\b', question))
    exact_dates = set()
    for day, month, year in re.findall(r'\b(\d{1,2})/(\d{1,2})/(20\d{2})\b', question):
        try:
            exact_dates.add(date(int(year), int(month), int(day)).isoformat())
        except ValueError:
            return None
    periods = sorted({f['period'] for f in candidates if f['period'] in exact_dates} if exact_dates else
                     {f['period'] for f in candidates if f['period'][:4] in years})
    compare = any(t in q for t in ('so voi', 'chenh lech', 'thay doi', 'tang bao nhieu', 'growth', 'change', 'compared'))
    if len(periods) != (2 if compare else 1):
        return None
    selected = [f for f in candidates if f['period'] in periods]
    if len(selected) != len(periods) or len({(f['issuer'], f['statement_scope'], f['currency'], f['basis']) for f in selected}) != 1:
        return None
    scope = selected[0]['statement_scope']
    if ('hop nhat' in q and scope != 'CONSOLIDATED') or (any(t in q for t in ('rieng', 'cong ty me')) and scope != 'SEPARATE'):
        return None
    operation = 'PERCENT_CHANGE' if compare and any(t in q for t in ('phan tram', 'ty le', 'percent', 'growth rate')) else 'ABS_CHANGE' if compare else 'EXTRACT'
    return {'operation': operation, 'metric': metric, 'current_period': periods[-1],
            'previous_period': periods[0] if compare else '', 'statement_scope': scope,
            'basis': selected[0]['basis']}


def contract(question: str, result: dict, profile: str) -> dict:
    hits = result.get('results', [])
    numeric = needs_number(question)
    requested_years = set(re.findall(r'\b20\d{2}\b', question))
    available_years = {str(hit.get('report_period', ''))[:4] for hit in hits if hit.get('report_period')}
    period_missing = bool(numeric and requested_years and available_years and
                          not requested_years.intersection(available_years))
    first = hits[0] if hits else None
    support = first
    if hits and not numeric:
        terms = {t for t in re.findall(r'[a-z0-9]+', folded(question)) if len(t) > 2}
        asks_unit = any(term in folded(question) for term in ('don vi', 'currency', 'unit'))
        def quality(hit):
            source = folded(hit.get('text', ''))
            words = re.findall(r'[a-z0-9]+', source)
            overlap = len(terms.intersection(words))
            causal = any(term in folded(question) for term in ('vi sao', 'ly do', 'why', 'reason')) and any(
                term in source for term in ('theo ket qua', 'because', 'due to', 'according to the results'))
            unit = asks_unit and any(term in source for term in ('vnd', 'usd', 'trieu dong', 'million dollars'))
            return overlap + (10 if causal else 0) + (3 if unit else 0) - (3 if len(words) < 15 else 0)
        support = max(hits, key=quality)
    warning = ('Không có bằng chứng cho kỳ được hỏi trong tài liệu đã chọn.' if period_missing else
               'Số liệu trong trích đoạn chưa được đối chiếu ô nguồn, kỳ và đơn vị.'
               if numeric and hits else 'Không tìm thấy bằng chứng trong tài liệu đã chọn.' if not hits else
               'Nội dung trích từ tài liệu; hãy mở trang nguồn để đối chiếu ngữ cảnh.')
    if period_missing:
        answer = 'Không đủ bằng chứng trong tài liệu đã chọn cho kỳ được hỏi; chưa thể trả lời số liệu.'
    elif not first:
        answer = 'Không đủ bằng chứng trong tài liệu đã chọn để trả lời câu hỏi này.'
    elif numeric:
        answer = 'Đã tìm thấy đoạn nguồn liên quan. Chưa thể xác nhận giá trị số từ các ô đã được kiểm chứng.'
    else:
        source_text = support.get('text', '')
        if any(term in folded(question) for term in ('don vi', 'currency', 'unit')):
            lines = [line.strip() for line in source_text.splitlines() if line.strip()]
            matched = next((i for i, line in enumerate(lines) if re.search(r'\b(?:VND|USD)\b|triệu đồng', line, re.I)), None)
            source_text = ' '.join(lines[max(0, matched - 1):matched + 1]) if matched is not None else source_text
        snippet = ' '.join(source_text.split())[:360].rstrip(' ,;')
        answer = f"Tài liệu ghi: “{snippet}”" if snippet else 'Có nguồn liên quan; cần mở trang để xem nội dung.'
    visible_hits = [] if period_missing else hits
    refs = [{k: hit.get(k) for k in ('chunk_id', 'document_id', 'page', 'issuer', 'filename',
                                     'source_sha256', 'statement_scope', 'unit', 'report_period')}
            for hit in visible_hits]
    return {
        'status': 'SOURCE_EXCERPTS' if visible_hits else 'INSUFFICIENT_EVIDENCE',
        'answer': answer,
        'citations': visible_hits,
        'evidence_references': refs,
        'values': [],
        'verification_status': 'NUMERIC_UNVERIFIED' if numeric and visible_hits else 'SOURCE_TEXT_UNREVIEWED' if visible_hits else 'INSUFFICIENT_EVIDENCE',
        'warnings': [warning],
        'metric': result.get('intent', {}).get('metric') if isinstance(result.get('intent'), dict) else None,
        'period': first.get('report_period') if first else None,
        'answer_source_chunk_id': support.get('chunk_id') if support and not period_missing else None,
        'statement_scope': first.get('statement_scope') if first else None,
        'unit': first.get('unit') if first else None,
        'retrieval_trace': {'profile': profile, 'generation': result.get('generation'),
                            'latency_ms': result.get('latency_ms'),
                            'top_ids': [h.get('chunk_id') for h in hits],
                            'evidence_status': result.get('evidence_status')},
        'search_profile': profile,
        'generation': result.get('generation'),
    }

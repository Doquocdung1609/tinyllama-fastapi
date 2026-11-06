"""Comparisons over separately bound PDF operands."""
from decimal import Decimal, localcontext
import re

from app.product.analysis import eligible_facts
from app.product.document_financial_cells import LABELS, cached_facts
from app.product.document_page_map import page_entry
from app.product.financial_understanding import ALIASES
from app.product.native_statement_cells import catalog
from app.product.ocr_candidate_answer import eligible_candidate
from app.product.pdf_extract import folded
from app.product.pdf_ocr_financial_v3 import HUMAN, explicit_cover_scope
from app.product.statement_question_answer import UNITS, _display, _key, _rows, _table, _choose

ASSET = {'assets': ('tong tai san', 'tong cong tai san', 'total assets')}
METRICS = {
    **ASSET, 'equity': ('von chu so huu', 'tong von chu so huu', 'total equity'),
    'paid_in_capital': ('von gop cua chu so huu', 'paid in capital'),
    'liabilities': ('no phai tra', 'tong no phai tra', 'total liabilities'),
    'net_income': ('loi nhuan sau thue', 'net income', 'net profit'),
}
SCALE = {'VND': Decimal(1), 'TRIEU_VND': Decimal(1000000), 'NGHIN_VND': Decimal(1000), 'TY_VND': Decimal(1000000000)}
BILLION = SCALE['TY_VND']


def _ocr_cells(workspace, doc, metrics, year, kind):
    chosen = {}
    cover_scope = None
    for number, page, error in workspace.iter_document_evidence(doc['id'], doc['pages']):
        if not page:
            continue
        if number == 1:
            cover_scope = explicit_cover_scope(folded(page['text']))
        observed = cached_facts(doc, page, page_entry(doc, number, page, error), cover_scope, None)
        rows = {r['id']: r for r in page['tables']}
        for cell in observed:
            metric = cell['metric_id']
            if (metric not in metrics or cell['statement_scope'] != 'SEPARATE' or cell['period_type'] != kind
                    or not cell['period_end'].startswith(year) or cell['unit'] not in SCALE or cell['value'] is None):
                continue
            row = rows.get(cell['row_id'])
            raw = next((c for c in row['cells'] if c.get('cell_id') == cell['column_id']), None) if row else None
            # Checkpoint candidates must satisfy the same admissibility gate as
            # OCR chat. Notes reconstructed from positioned words require a header box.
            if not ((row and raw and eligible_candidate(row, raw)) or cell['citation'].get('header_box')):
                continue
            refs = chosen.setdefault(metric, [])
            refs.append({**cell['citation'], 'value': cell['value'], 'value_raw': cell['raw'],
                         'row_label': LABELS[metric], 'period': cell['period_end'], 'period_type': kind,
                         'review_status': cell['review_status'], 'currency': 'VND', 'scale': str(SCALE[cell['unit']])})
    try:
        reviews = eligible_facts(workspace, [doc['id']])
    except ValueError:
        reviews = []
    for review in reviews:
        for candidate in chosen.get(review['metric'], []):
            if (review.get('review_status') == HUMAN and review['row_id'] == candidate['row_id']
                    and review['page'] == candidate['page'] and review['cell_id'] == candidate['column_id']
                    and review['period'] == candidate['period'] and review['box'] == candidate['box']):
                candidate.update(value=review['value'], value_raw=review['source_display'], review_status=HUMAN,
                                 verification=HUMAN, text=f"{candidate['row_label']} · {review['source_display']}")
    result = {}
    for metric, candidates in chosen.items():
        if kind == 'INSTANT':
            close = max(c['period'] for c in candidates)
            candidates = [c for c in candidates if c['period'] == close]
        if len({c['value'] for c in candidates}) != 1:
            continue
        result[metric] = min(candidates, key=lambda c: (c['review_status'] != HUMAN, c['page']))
    return result


def _native_cells(cells, metrics, year, kind, basis):
    rows = _rows([c for c in cells if c['period'] == year and c['period_type'] == kind])
    result = {}
    for metric in metrics:
        matches = [_choose(rows, label, 'SEPARATE', False) for label in METRICS.get(metric, (metric,))]
        matches = [row[basis] for row in matches if row and row.get(basis, {}).get('value') is not None]
        if len(matches) == 1:
            result[metric] = matches[0]
    return result


def _profiles(workspace, docs, profiles, catalogs):
    refs, rows = [], []
    for doc in docs:
        profile = profiles[doc['id']]
        cells = catalogs[doc['id']]
        scopes = {c['statement_scope'] for c in cells} or set(profile['statement_scopes'])
        scope = ' và '.join(label for key, label in [('SEPARATE', 'riêng'), ('CONSOLIDATED', 'hợp nhất')] if key in scopes)
        methods = set()
        first_readable = None
        units = {c['unit'] for c in cells}
        for number, page, error in workspace.iter_document_evidence(doc['id'], doc['pages']):
            if page and page['text'].strip():
                methods.add(page['method'])
                if not first_readable:
                    first_readable = page_entry(doc, number, page, error)['citation']
                units.update(c['unit'] for row in page['tables'] for c in row['cells'] if c.get('unit') in SCALE)
        examples = []
        if cells:
            for key in sorted(scopes):
                match = next((c for c in cells if c['statement_scope'] == key), None)
                if match:
                    examples.append(match)
        elif first_readable:
            examples.append(first_readable)
        refs.extend(examples)
        rows.append((doc['filename'], 'Bảng điều chỉnh báo cáo tài chính' if cells else 'Báo cáo tài chính',
                     scope or 'Chưa rõ', ', '.join(sorted({c['period'] for c in cells})) or profile['report_year'] or 'Chưa rõ',
                     ', '.join(UNITS.get(unit, unit) for unit in sorted(units)) or 'Chưa rõ',
                     ', '.join({'NATIVE': 'lớp chữ PDF', 'OCR': 'OCR', 'REGION_FUSION': 'lớp chữ và OCR'}.get(m, 'chưa rõ')
                               for m in sorted(methods)) or 'Chưa đọc được',
                     ' '.join(f'[{i}]' for i in range(len(refs) - len(examples) + 1, len(refs) + 1))))
    return {'status': 'SOURCE_EXCERPTS', 'answer_status': 'SOURCE_EXCERPTS', 'citations': refs, 'values': [],
            'answer': _table(('PDF', 'Loại báo cáo', 'Phạm vi', 'Năm trong nguồn', 'Đơn vị', 'Trích xuất', 'Nguồn'), rows)}


def _qualifier(question, issuer, own, other, fallback):
    aliases = '|'.join(map(re.escape, sorted(ALIASES[issuer], key=len, reverse=True)))
    competitors = '|'.join(re.escape(a) for a in sorted(ALIASES[other], key=len, reverse=True))
    mention = re.search(rf'\b(?:{aliases})\b', question)
    if not mention:
        return None, None
    tail = question[mention.end():]
    next_issuer = re.search(rf'\b(?:{competitors})\b', tail)
    if next_issuer:
        before_peer = tail[:next_issuer.start()]
        tail = re.split(r'\b(?:va|voi|versus|and|with)\b', before_peer, maxsplit=1)[0]
    before = question[:mention.start()]
    prefix = re.split(r'\b(?:va|voi|versus|and|with)\b', before)[-1]
    if re.search(rf'\b(?:{competitors})\b', prefix):
        prefix = ''
    dates = re.findall(r'\b20\d{2}\b', tail)
    if not dates:
        dates = re.findall(r'\b20\d{2}\b', prefix)
    years = set(dates)
    if len(years) > 1:
        return None, None
    year = next(iter(years), own or fallback)
    kind = 'Q4' if re.search(r'\b(?:quy\s*(?:iv|4)|q4)\b', prefix + ' ' + tail) else 'FY'
    return year, kind


def compare(workspace, question, docs, profiles, issuers):
    q = _key(question)
    if len(docs) != 2 or len(issuers) != 2 or not all(len(profiles[d['id']]['source_identities']) == 1 for d in docs):
        return None
    if not re.search(r'\b(?:so sanh|doi chieu|khac biet|ty le|compare|ratio)\b', q):
        return None
    all_scopes = re.search(r'\b(?:hop nhat|consolidated)\b', q)
    profiles_requested = 'trich xuat' in q and ('loai bao cao' in q or 'pham vi' in q)
    ratio = 'no phai tra' in q and 'tai san' in q and 'ty le' in q
    capital = 'von chu so huu' in q and 'von gop' in q
    assets = 'tong tai san' in q and not ratio
    income = 'loi nhuan sau thue' in q
    if not profiles_requested and (all_scopes or sum(map(bool, (ratio, capital, assets, income))) != 1):
        return None
    catalogs = {d['id']: catalog(workspace, d) for d in docs}
    if profiles_requested:
        return _profiles(workspace, docs, profiles, catalogs)
    if 'bao cao rieng' not in q and 'rieng' not in q and not capital:
        return None
    blocks, refs, table_rows, missing = [], [], [], []
    operands = {}
    for doc in docs:
        doc_id = doc['id']
        profile = profiles[doc_id]
        issuer = profile['source_identities'][0]
        other = next(iter(issuers - {issuer}))
        year, kind = _qualifier(q, issuer, profile['report_year'], other, str(doc.get('report_period') or '')[:4])
        native = catalogs[doc_id]
        if not year or not year.isdigit():
            missing.append(f'{issuer}: chưa xác định được kỳ')
            continue
        metrics = (('von va cac quy',) if native else ('equity', 'paid_in_capital')) if capital else (
            ('assets', 'liabilities', 'equity', 'von va cac quy') if ratio else ('assets',) if assets else ('net_income',))
        kind = kind if income else 'INSTANT'
        if native:
            cells = _native_cells(native, metrics, year, kind, 'RESTATED')
        else:
            cells = _ocr_cells(workspace, doc, metrics, year, kind)
        for metric, cell in cells.items():
            cell = {**cell, 'issuer': issuer}
            refs.append(cell)
            amount = Decimal(cell['value']) * Decimal(cell['scale'])
            state = ('Đối chiếu lớp chữ PDF' if cell.get('verification_status') == 'NATIVE_CELL_VERIFIED'
                     else 'Người duyệt đã đối chiếu' if cell.get('review_status') == HUMAN else 'Ứng viên OCR')
            period = cell.get('period_end') or cell['period']
            if kind == 'Q4':
                period = f'Quý IV/{year}'
            elif kind == 'FY':
                period = f'Năm {year}'
            table_rows.append((issuer, cell['row_label'], period, f"{cell['value_raw']} {UNITS[cell['unit']]}",
                               _display(amount / BILLION), state, f'[{len(refs)}]'))
            operands.setdefault(issuer, {})[metric] = (amount, len(refs), state)
        required = set(metrics)
        if ratio:
            required = {'assets', 'liabilities'}
            equity_key = next((m for m in ('equity', 'von va cac quy') if m in cells), None)
            if ('liabilities' not in cells and 'assets' in cells and equity_key and native and
                    re.search(r'\b(?:suy ra|derive)\b', q)):
                asset, equity = cells['assets'], cells[equity_key]
                if all(asset.get(k) == equity.get(k) for k in ('table_id', 'period_end', 'statement_scope', 'basis', 'currency', 'scale')):
                    amounts = operands[issuer]
                    a, e = amounts['assets'], amounts[equity_key]
                    derived = a[0] - e[0]
                    if derived >= 0:
                        amounts['liabilities'] = (derived, a[1], a[2])
                        amounts['derived_equity'] = e
                        required = {'assets'}
        absent = required - cells.keys()
        if absent:
            missing.append(f"{issuer}: " + ', '.join(LABELS.get(m, m) for m in sorted(absent)) + f' ({year}, báo cáo riêng)')
    if table_rows:
        blocks.append(_table(('Doanh nghiệp', 'Chỉ tiêu · báo cáo riêng', 'Kỳ', 'Giá trị nguồn', 'Tỷ đồng',
                              'Đối chiếu', 'Nguồn'), table_rows))
        blocks.append('Quy đổi sang tỷ đồng: số gốc × hệ số đơn vị nguồn ÷ 1.000.000.000 '
                      '(hệ số 1 đối với đồng, 1.000.000 đối với triệu đồng).')
    preliminary = any(row[5] == 'Ứng viên OCR' for row in table_rows)
    calculations = []
    with localcontext() as ctx:
        ctx.prec = 38
        if capital:
            blocks.append('“Vốn và các quỹ” và “Vốn chủ sở hữu” là các nhóm tổng hợp theo cách trình bày của từng báo cáo. '
                          '“Vốn góp của chủ sở hữu” là một thành phần của vốn chủ sở hữu. '
                          'Cần đọc các dòng cấu thành trước khi coi hai nhóm tổng hợp có cùng phạm vi.')
        elif ratio:
            for issuer, values in operands.items():
                assets_value = values.get('assets')
                debt = values.get('liabilities')
                if assets_value and assets_value[0] and debt:
                    derived = values.get('derived_equity')
                    if derived:
                        blocks.append(f"Nợ phải trả {issuer} (tính từ phương trình kế toán) = tổng tài sản − "
                                      f"{'vốn và các quỹ' if 'von va cac quy' in values else 'vốn chủ sở hữu'} = "
                                      f"{_display(debt[0]/BILLION)} tỷ đồng. [{assets_value[1]}][{derived[1]}]")
                    debt_refs = f"[{assets_value[1]}][{derived[1]}]" if derived else f"[{debt[1]}][{assets_value[1]}]"
                    result = debt[0] / assets_value[0] * 100
                    calculations.append(str(result))
                    blocks.append(f"**{issuer}**: {_display(debt[0]/BILLION)} ÷ {_display(assets_value[0]/BILLION)} "
                                  f"× 100 = **{_display(result)}%**. {debt_refs}")
            blocks.append('Hai tỷ lệ không đủ để kết luận doanh nghiệp nào an toàn hơn. '
                          'Cần xét cấu trúc nguồn vốn và chuẩn an toàn phù hợp với từng ngành.')
        elif len(operands) == 2:
            metric = 'assets' if assets else 'net_income'
            if all(metric in values for values in operands.values()):
                a, b = sorted((values[metric] for values in operands.values()), reverse=True)
                delta = (a[0] - b[0]) / BILLION
                calculations.append(str(delta))
                blocks.append(f"Chênh lệch: {_display(a[0]/BILLION)} − {_display(b[0]/BILLION)} = "
                              f"**{_display(delta)} tỷ đồng**. [{a[1]}][{b[1]}]")
                if assets and b[0] > 0:
                    multiple = a[0] / b[0]
                    calculations.append(str(multiple))
                    blocks.append(f"Quy mô lớn hơn **{_display(multiple)} lần**, tính bằng giá trị lớn chia giá trị nhỏ. "
                                  f"[{a[1]}][{b[1]}] Hai số thuộc hai doanh nghiệp, ở các ngày và ngành khác nhau.")
                if income:
                    blocks.append('Chênh lệch này so sánh hai doanh nghiệp và các kỳ được ghi trong bảng. '
                                  'Không thể diễn giải nó như tăng trưởng qua các năm.')
    if missing:
        blocks.append('Chưa đủ ô nguồn cho ' + '; '.join(missing) + '.')
    if preliminary:
        blocks.insert(0, '**Đối chiếu sơ bộ.** Các phép tính có dùng ô OCR ứng viên được đánh dấu trong bảng.')
    if not refs:
        return None
    status = 'PARTIAL_VERIFIED' if missing else 'CANDIDATE_RECONCILIATION' if preliminary else 'VERIFIED_ANSWER'
    return {'status': 'SUPPORTED' if status == 'VERIFIED_ANSWER' else 'SOURCE_EXCERPTS', 'answer_status': status,
            'answer': '\n\n'.join(blocks), 'citations': refs, 'operands': refs,
            'values': calculations if status == 'VERIFIED_ANSWER' else [],
            'candidate_values': calculations if preliminary else [], 'source_document_ids': [d['id'] for d in docs]}

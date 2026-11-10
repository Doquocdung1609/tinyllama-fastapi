"""Plan restatement questions against the labels and columns actually present."""
from collections import defaultdict
from datetime import date
from decimal import Decimal, localcontext
import re

from app.product.document_page_map import page_entry
from app.product.financial_understanding import document_profile, issuers, requested_unit
from app.product.native_statement_cells import catalog, label_key, _reading
from app.product.pdf_extract import folded

SCOPE = {'SEPARATE': 'Riêng', 'CONSOLIDATED': 'Hợp nhất'}
BASIS = {'ORIGINAL': 'Đã công bố', 'ADJUSTMENT': 'Điều chỉnh', 'RESTATED': 'Trình bày lại'}
UNITS = {'TRIEU_VND': 'triệu đồng', 'NGHIN_VND': 'nghìn đồng', 'TY_VND': 'tỷ đồng',
         'VND': 'đồng', 'USD': 'USD', 'MILLION_USD': 'triệu USD'}
RESTATEMENT = re.compile(r'\bdieu chinh\b|\btrinh bay lai\b|\bda cong bo\b|\b(?:restated|restatement|adjustments?|previously reported)\b')
DIFFERENCE = re.compile(r'khac.{0,90}bao nhieu|chenh lech|difference|differ')
INVENTORY = re.compile(r'\bkiem ke\b|\blist\b|\binventory\b')
QUARTER = re.compile(r'\b(?:quy\s*(?:iv|iii|ii|i|[1-4])|q[1-4]|quarter(?:ly)?)\b')
SCOPES = {'SEPARATE': r'\brieng\b|cong ty me|\bseparate\b|parent company',
          'CONSOLIDATED': r'\bhop nhat\b|\bconsolidated\b'}


def _key(text):
    text = label_key(text)
    text = re.sub(r'\bthuoc (?:ve )?co dong\b', 'cua co dong', text)
    text = re.sub(r'\b(?:tndn|thue thu nhap doanh nghiep)\b', '', text)
    return ' '.join(text.split())


def _contains(needle, haystack):
    return bool(needle) and f' {needle} ' in f' {haystack} '


def _rows(cells):
    grouped = defaultdict(dict)
    for cell in cells:
        grouped[cell['document_id'], cell['row_id']][cell['basis']] = cell
    return list(grouped.values())


def _identity(row):
    return next(iter(row.values()))


def _labels(rows, q, strict=False):
    keys = {_key(_identity(row)['row_label']) for row in rows}
    direct = [key for key in keys if _contains(key, q)]
    direct = [key for key in direct if not any(key != other and _contains(key, other) for other in direct)]
    if direct:
        # A shorter reference to an allowance can be resolved only by a
        # shared explicit parent label and a unique child in the source.
        if 'du phong rui ro' in q and not any('du phong rui ro' in key for key in direct):
            children = [key for key in keys if key.startswith('du phong rui ro ')
                        and any(_contains(parent, key) for parent in direct)]
            if len(children) == 1:
                direct.extend(children)
        return sorted(direct, key=lambda key: q.find(key) if key in q else len(q))
    # Quoted labels are strict. Otherwise allow word order changes only when
    # every distinctive word of a single source label is present.
    if strict:
        return []
    terms = set(q.split())
    reordered = [key for key in keys if len(set(key.split())) >= 3 and set(key.split()) <= terms]
    maximal = [key for key in reordered if not any(set(key.split()) < set(other.split()) for other in reordered)]
    return maximal if len(maximal) == 1 else []


def _choose(rows, key, scope, adjustment):
    matches = [row for row in rows if _key(_identity(row)['row_label']) == key
               and _identity(row)['statement_scope'] == scope]
    if len(matches) > 1 and adjustment:
        parents = [row for row in matches if re.match(r'^[IVXLCDM]+[.] ', _identity(row)['row_label_raw'])]
        children = [row for row in matches if re.match(r'^\d+[.] ', _identity(row)['row_label_raw'])]
        if len(parents) == 1 and children and all(_identity(row)['page'] == _identity(parents[0])['page'] and
                _identity(row)['row_box'][1] > _identity(parents[0])['row_box'][1] for row in children):
            return parents[0]
    return matches[0] if len(matches) == 1 else None


def _display(value):
    value = Decimal(value)
    result = f'{value:,.0f}' if value == value.to_integral() else f'{value:,.4f}'.rstrip('0')
    return result.translate(str.maketrans(',.', '.,'))


def _table(head, rows):
    def clean(v):
        return str(v).replace('|', '/').replace('\n', ' ')
    return '\n'.join(['| ' + ' | '.join(head) + ' |', '| ' + ' | '.join(['---'] * len(head)) + ' |',
                      *('| ' + ' | '.join(map(clean, row)) + ' |' for row in rows)])


def _response(answer, refs, *, complete=False, values=(), operands=(), answer_status=None, **fields):
    return {'status': 'SUPPORTED' if complete else 'SOURCE_EXCERPTS',
            'answer_status': answer_status or ('VERIFIED_ANSWER' if complete else 'PARTIAL_VERIFIED' if refs else 'NEEDS_CLARIFICATION'),
            'answer': answer, 'citations': refs, 'values': list(values), 'operands': list(operands),
            'verification_status': 'NATIVE_STATEMENT_SOURCE_CELLS' if refs else 'NO_BOUND_SOURCE_CELL', **fields}


def _inventory(workspace, doc, cells):
    scopes = {c['page']: c for c in cells}
    refs, rows = [], []
    for number, page, error in workspace.iter_document_evidence(doc['id'], doc['pages']):
        entry = page_entry(doc, number, page, error)
        title, sample = entry['title'], entry['sample']
        if number in scopes:
            cell = scopes[number]
            title = ('Bảng cân đối kế toán' if cell['statement_type'] == 'BALANCE_SHEET' else
                     'Báo cáo kết quả kinh doanh' if cell['statement_type'] == 'INCOME_STATEMENT' else
                     'Báo cáo lưu chuyển tiền tệ') + ' · ' + SCOPE[cell['statement_scope']].lower()
            sample = cell['row_label']
        elif page and re.search(r'cong bo thong tin|disclosure', folded(page['text'])):
            title = 'Công bố thông tin'
        refs.append(entry['citation'])
        rows.append((number, entry['printed_page'] or '—', title, sample, entry['reading_status'], f'[{len(refs)}]'))
    return _response(f"Đã kiểm kê **{len(rows)}/{doc['pages']} trang PDF**.\n\n" +
                     _table(('Trang PDF', 'Trang in', 'Nội dung', 'Thông tin tiêu biểu', 'Tình trạng đọc', 'Nguồn'), rows),
                     refs, document_inventory=True, answer_status='DOCUMENT_INVENTORY')


def answer(workspace, question, document_ids):
    q = _key(question)
    literal = folded(question)
    inventory = bool(INVENTORY.search(q) and re.search(r'\btrang\b|\bpages?\b', q))
    adjustment = bool(RESTATEMENT.search(q))
    if not (inventory or adjustment) or (inventory and 'von gop' in q):
        return None
    named = set(issuers(question))
    docs = [workspace.document(doc_id) for doc_id in dict.fromkeys(document_ids)]
    if len(docs) > 1:
        docs = [doc for doc in docs if named and named.intersection(
            document_profile(workspace, doc).get('source_identities', []))]
    if len(docs) != 1 or not docs[0] or not hasattr(workspace, 'source_file'):
        return None
    doc = docs[0]
    profile = document_profile(workspace, doc)
    source_issuers = set(profile['source_identities'])
    if named and not named.intersection(source_issuers):
        return None
    if len(source_issuers) == 1:
        doc = {**doc, 'issuer': next(iter(source_issuers))}
    cells = catalog(workspace, doc)
    if not cells:
        return None
    if inventory:
        return _inventory(workspace, doc, cells)

    years = set(re.findall(r'\b20\d{2}\b', q))
    years_in_source = {c['period'] for c in cells}
    if (years and not years <= years_in_source) or QUARTER.search(q):
        available = ', '.join(sorted(years_in_source))
        requested = ', '.join(sorted(years))
        return _response(f"PDF đang chọn có bảng điều chỉnh cho năm {available}. Tôi chưa thấy cột "
                         f"{'theo quý ' if QUARTER.search(q) else 'cho năm '}{requested} trong các bảng này.",
                         [], reason='REQUESTED_PERIOD_ABSENT')
    scopes = [scope for scope, pattern in SCOPES.items() if re.search(pattern, q)]
    scoped = [c for c in cells if (not scopes or c['statement_scope'] in scopes) and (not years or c['period'] in years)]
    requested_dates = set()
    for day, month, year in re.findall(r'\b(\d{1,2})/(\d{1,2})/(20\d{2})\b', literal):
        try:
            requested_dates.add(date(int(year), int(month), int(day)).isoformat())
        except ValueError:
            return _response('Ngày bạn nêu không hợp lệ. Vui lòng kiểm tra lại ngày và tháng.', [])
    if requested_dates:
        matched = [c for c in scoped if c['period_end'] in requested_dates]
        if {c['period_end'] for c in matched} != requested_dates:
            return _response('Bảng nguồn chưa xác nhận đủ các ngày bạn yêu cầu. '
                             'Tôi cần tiêu đề cột hoặc trang ghi đúng ngày để chọn số.', [],
                             reason='REQUESTED_DATE_UNBOUND')
        scoped = matched
    rows = _rows(scoped)
    quoted = [_key(label) for label in re.findall(r'["“]([^"”]+)["”]', question)
              if re.search(r'[a-z]', _key(label))]
    keys = _labels(rows, q, strict=bool(quoted))
    if quoted:
        known = {_key(_identity(row)['row_label']) for row in rows}
        unresolved = [label for label in quoted if label not in known]
        if unresolved:
            return _response('Chưa gắn được nhãn trong dấu ngoặc kép với một dòng nguồn duy nhất: ' +
                             ', '.join(unresolved) + '.', [], reason='REQUESTED_LABEL_UNBOUND')
    if not keys:
        return None
    if not scopes:
        scopes = list(dict.fromkeys(c['statement_scope'] for c in scoped if _key(c['row_label']) in keys))
        if len(scopes) > 1:
            return _response('Báo cáo có dòng này ở cả bảng riêng và bảng hợp nhất. Bạn muốn dùng phạm vi nào?',
                             [], reason='REQUESTED_SCOPE_AMBIGUOUS')
    basis = list(BASIS)
    ratio = bool(re.search(r'\b(?:ty le|ty trong|ratio)\b', q))
    percent_change = not ratio and bool(re.search(r'\b(?:phan tram|percent|percentage)\b|%', literal))
    compare = bool(DIFFERENCE.search(q)) and not percent_change
    if ratio:
        compare = False
    adjustment_only = bool(re.search(r'muc dieu chinh|chenh lech dieu chinh|adjustment amount', q)
                           and not re.search(r'truoc va sau|before and after|da cong bo', q))
    if ratio:
        basis = ['RESTATED']
    elif compare:
        basis = ['ADJUSTMENT' if adjustment_only else 'RESTATED']
    elif re.search(r'(?:co dung|equal to|is .* equal|xac nhan).*', q):
        basis = ['RESTATED']
    elif re.search(r'duoc dieu chinh bao nhieu va gia tri trinh bay lai', q):
        basis = ['ADJUSTMENT', 'RESTATED']
    elif re.search(r'\b(?:trinh bay lai|restated|updated)\b', q) and not re.search(r'dieu chinh|before|original|previously', q):
        basis = ['RESTATED']
    elif re.search(r'\b(?:muc dieu chinh|adjustment amount)\b', q) and not re.search(r'truoc|sau|before|after', q):
        basis = ['ADJUSTMENT']
    refs, missing, blocks, amounts = [], [], [], []
    if re.search(r'\b(?:vi sao|tai sao|nguyen nhan|why|reason)\b', q):
        missing.append('lý do điều chỉnh trong phần giải trình')
    unit_requested = requested_unit(question)
    if unit_requested not in (None, '%') and unit_requested not in {c['unit'] for c in scoped}:
        # Show the source units and make the unfulfilled conversion explicit.
        missing.append('quy đổi sang đơn vị yêu cầu')
    table_rows = []
    for scope in scopes:
        for key in keys:
            selected = _choose(rows, key, scope, adjustment)
            if not selected:
                missing.append(f'{key} ({SCOPE[scope].lower()})')
                continue
            for kind in basis:
                cell = selected.get(kind)
                if not cell:
                    missing.append(f"{_identity(selected)['row_label']} · {BASIS[kind].lower()}")
                    continue
                refs.append(cell)
                amount = cell['value']
                unit = UNITS.get(cell['unit'], cell['unit'])
                table_rows.append((cell['row_label'], SCOPE[scope], cell['period_end'] or cell['period'],
                                   BASIS[kind], f'{_display(amount)} {unit}' if amount is not None else 'Dấu gạch in',
                                   f'[{len(refs)}]'))
                if amount is not None:
                    amounts.append(amount)
            if basis == list(BASIS) and all(selected.get(b, {}).get('value') is not None for b in BASIS):
                old, change, new = (Decimal(selected[b]['value']) for b in BASIS)
                if old + change == new:
                    sign = '+' if change >= 0 else '−'
                    blocks.append(f"**{_identity(selected)['row_label']}**: {_display(old)} {sign} "
                                  f"{_display(abs(change))} = **{_display(new)}** {unit}.")
                    if percent_change and old != 0:
                        with localcontext() as ctx:
                            ctx.prec = 38
                            growth = (new - old) / abs(old) * 100
                        blocks.append(f"Mức thay đổi = ({_display(new)} − {_display(old)}) ÷ "
                                      f"|{_display(old)}| × 100 = **{_display(growth)}%**.")
                        amounts.append(str(growth))
                    elif percent_change:
                        missing.append('tỷ lệ thay đổi vì giá trị ban đầu bằng 0')
                else:
                    missing.append(f"phép cộng của {_identity(selected)['row_label']}: ba ô nguồn không khớp")
    if ratio:
        dimensions = ('period', 'period_type', 'period_end', 'currency', 'scale', 'basis', 'statement_scope')
        if (len(refs) == 2 and len(amounts) == 2 and len(keys) == 2 and
                all(refs[0][k] == refs[1][k] for k in dimensions) and Decimal(amounts[1]) and
                re.search(r'\b(?:tren|chia cho|divided by|to)\b', q)):
            with localcontext() as ctx:
                ctx.prec = 38
                result = Decimal(amounts[0]) / Decimal(amounts[1]) * 100
            blocks.append(f"**Tỷ lệ: {_display(result)}%.** {_display(amounts[0])} ÷ "
                          f"{_display(amounts[1])} × 100. [1][2]")
            amounts = [str(result)]
        else:
            missing.append('tử số và mẫu số có cùng kỳ, phạm vi, đơn vị và cột trình bày')
    if compare and len(refs) == 2 and len(amounts) == 2:
        if len({(c['period'], c['period_type'], c['period_end'], c['currency'], c['scale'], c['basis']) for c in refs}) == 1:
            left, right = sorted(refs, key=lambda c: c['statement_scope'] != 'CONSOLIDATED') if len(scopes) == 2 else refs
            a, b = Decimal(left['value']), Decimal(right['value'])
            result = abs(a - b)
            blocks.append(f"**Chênh lệch: {_display(result)} {UNITS.get(left['unit'], left['unit'])}.** "
                          f"{_display(max(a, b))} − {_display(min(a, b))} = {_display(result)}. [1][2]")
            amounts = [str(result)]
        else:
            missing.append('hai toán hạng cùng kỳ, đơn vị và cơ sở trình bày')
    elif compare:
        missing.append('hai ô nguồn phù hợp để tính chênh lệch')
    if percent_change and basis != list(BASIS):
        missing.append('cột đã công bố và trình bày lại để tính mức thay đổi phần trăm')
    assertion = re.search(r'(?<!\d)\d{1,3}(?:[.,]\d{3}){2,}(?!\d)', question)
    if assertion and len(refs) == 1 and amounts:
        cell = refs[0]
        proposed = _reading(assertion[0])
        if proposed is not None:
            actual = Decimal(amounts[0])
            blocks.append(f"**{'Đúng' if proposed == actual else 'Không'}**. Báo cáo ghi "
                          f"**{_display(actual)} {UNITS.get(cell['unit'], cell['unit'])}** cho dòng “{cell['row_label']}”. [1]")
            alternatives = [c for c in scoped if c['basis'] == cell['basis'] and c['statement_scope'] == cell['statement_scope']
                            and c['statement_type'] == cell['statement_type'] and c['value'] is not None and
                            Decimal(c['value']) == proposed and c['row_id'] != cell['row_id']]
            if proposed != actual and len(alternatives) == 1:
                alternate = alternatives[0]
                refs.append(alternate)
                blocks.append(f"Số {_display(proposed)} thuộc dòng “{alternate['row_label']}”. [2]")
    if not refs:
        return _response('Tìm thấy nhãn trong PDF nhưng chưa phân biệt được dòng hoặc cột cần dùng: ' +
                         ', '.join(missing) + '.', [], reason='SOURCE_ROW_OR_COLUMN_AMBIGUOUS')
    if not blocks and table_rows and not missing:
        last = table_rows[-1]
        blocks.append(f"“{last[0]}”, {last[1].lower()}, cột {last[3].lower()}: **{last[4]}**. {last[5]}")
    blocks.append(_table(('Chỉ tiêu', 'Phạm vi', 'Kỳ', 'Cột nguồn', 'Giá trị', 'Nguồn'), table_rows))
    if missing:
        blocks.append('Còn thiếu bằng chứng cho ' + '; '.join(missing) + '.')
    return _response('\n\n'.join(blocks), refs, complete=not missing, values=amounts, operands=refs,
                     source_document_ids=[doc['id']], statement_question={'rows': keys, 'scopes': scopes, 'bases': basis})

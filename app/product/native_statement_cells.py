"""Source-checked cells for native statement restatements.

The table layout and accounting basis come from the PDF header. A cell is
bound independently of whether its row satisfies an accounting equation.
"""
from collections import Counter
from datetime import date
from functools import lru_cache
from hashlib import file_digest
import re

import pymupdf

from app.product.analysis import parse_number
from app.product.document_page_map import source_ref
from app.product.pdf_extract import folded
from app.product.source_cells_v2 import cell_id, lines, union_box
from app.product.source_units import units_in

BASES = {
    'ORIGINAL': r'(?:(?:previously|as) reported|original(?:ly reported)?|da cong bo|truoc dieu chinh)',
    'ADJUSTMENT': r'(?:adjustments?|changes?|dieu chinh)',
    'RESTATED': r'(?:restated|updated|trinh bay lai|sau dieu chinh)',
}
NUMBER = re.compile(r'\(?[+−-]?\d[\d.,]*\)?')
DASHES = {'-', '–', '—', '−'}
OUTLINE = re.compile(r'^(?:[IVXLCDM]+|\d+|[A-Z])\s*[.)]\s+')
TITLES = {
    'BALANCE_SHEET': r'bang can doi ke toan|balance sheets?|statements? of financial position',
    'INCOME_STATEMENT': r'bao cao ket qua (?:hoat dong )?kinh doanh|statements? of (?:operations|income|profit or loss)',
    'CASH_FLOW': r'bao cao luu chuyen tien te|statements? of cash flows?',
}


def label_key(label):
    return ' '.join(re.findall(r'[a-z0-9]+', folded(label)))


def _center(box):
    return (box[0] + box[2]) / 2


def _header(rows):
    # Search source phrases on individual lines or in a narrow stack of
    # neighboring lines. A stacked phrase must keep the same horizontal band.
    for i, (y, _) in enumerate(rows):
        bands = {basis: {} for basis in BASES}
        nearby = [ws for yy, ws in rows[i:i + 5] if yy - y < 42]
        for j, ws in enumerate(nearby):
            for k in range(len(ws)):
                for size in range(1, min(5, len(ws) - k) + 1):
                    prefix = ws[k:k + size]
                    if any(b[0] - a[2] > 12 for a, b in zip(prefix, prefix[1:])):
                        break
                    variants = [prefix]
                    if j + 1 < len(nearby):
                        center = _center(union_box(prefix))
                        below = [v for v in nearby[j + 1] if abs(_center(v) - center) < 28]
                        variants.extend(prefix + below[s:s + n] for s in range(len(below))
                                        for n in range(1, min(4, len(below) - s) + 1))
                    for phrase in variants:
                        name = label_key(' '.join(w[4] for w in phrase))
                        for basis, pattern in BASES.items():
                            if re.fullmatch(pattern, name):
                                box = tuple(union_box(phrase))
                                bands[basis][box] = name
        # The same single-line phrase is seen in multiple windows. Distinct
        # competing positions within one band are ambiguous.
        if not all(len(matches) == 1 for matches in bands.values()):
            continue
        boxes = {basis: next(iter(matches)) for basis, matches in bands.items()}
        centers = sorted(_center(b) for b in boxes.values())
        if min(b - a for a, b in zip(centers, centers[1:])) >= 24:
            return boxes
    return None


def _context(rows, boxes, previous):
    bottom = max(b[3] for b in boxes.values())
    top = [(y, ws) for y, ws in rows if y < bottom]
    strings = [' '.join(w[4] for w in ws) for _, ws in top]
    matches = [(kind, label_key(s)) for s in strings for kind, p in TITLES.items() if re.search(p, label_key(s))]
    text = folded(' '.join(strings))
    scopes = {scope for scope, p in [('SEPARATE', r'\brieng\b|parent.company|\bseparate\b'),
                                      ('CONSOLIDATED', r'\bhop nhat\b|\bconsolidated\b')]
              if any(re.search(p, s) for _, s in matches) or (not matches and re.search(p, text))}
    scope = next(iter(scopes)) if len(scopes) == 1 else None
    kinds = {kind for kind, _ in matches}
    kind = next(iter(kinds)) if len(kinds) == 1 else None
    units = {(u['unit'], u['currency'], u['multiplier']) for s in strings
             if re.search(r'don vi|unit|\bin (?:millions?|thousands?|vnd|usd)', folded(s))
             for u in units_in(s) if u['multiplier']}
    years = set(re.findall(r'\b(?:19|20)\d\d\b', text))
    if len(years) != 1:
        return None
    year = next(iter(years))
    if scope and kind and len(units) == 1:
        dates = set(re.findall(r'\b(\d{1,2})[/-](\d{1,2})[/-]((?:19|20)\d\d)\b', text))
        end = None
        if len(dates) == 1:
            d, m, yy = next(iter(dates))
            try:
                end = date(int(yy), int(m), int(d)).isoformat()
            except ValueError:
                return None
        if kind == 'BALANCE_SHEET' and not end:
            return None
        if kind != 'BALANCE_SHEET' and re.search(r'\b(?:q[1-4]|quy|quarter|months?|thang)\b', text):
            return None
        unit, currency, scale = next(iter(units))
        return dict(statement_scope=scope, statement_type=kind, period=year,
                    period_type='INSTANT' if kind == 'BALANCE_SHEET' else 'FY',
                    period_end=end, unit=unit, currency=currency, scale=scale)
    if not previous or kind or scope or units or previous['period'] != year:
        return None
    if any(abs(_center(boxes[b]) - _center(previous['headers'][b])) > 12 for b in boxes):
        return None
    # A repeated header without its own title can continue the prior table
    # only with an explicit continuation marker or a balance-sheet section.
    following = label_key(' '.join(w[4] for y, ws in rows if bottom < y < bottom + 45 for w in ws))
    if not re.search(r'\btiep theo\b|\bcontinued\b|no phai tra va von chu so huu|liabilities and (?:stockholders |shareholders )?equity', following):
        return None
    return {key: value for key, value in previous.items() if key != 'headers'}


def _row_candidates(rows, headers):
    columns = sorted(headers, key=lambda key: _center(headers[key]))
    centers = [_center(headers[key]) for key in columns]
    edges = [(a + b) / 2 for a, b in zip(centers, centers[1:])]
    left = centers[0] - (centers[1] - centers[0]) * .65
    right = centers[-1] + (centers[-1] - centers[-2]) * .65
    after = max(b[3] for b in headers.values())
    wrapped = []
    for y, ws in rows:
        if y < after:
            continue
        name = [w for w in ws if w[2] < left]
        label = ' '.join(w[4] for w in name)
        if not re.search(r'[a-z]', label_key(label)):
            wrapped = []
            continue
        values = {basis: [] for basis in columns}
        for w in ws:
            x = _center(w)
            if left < x < right and (NUMBER.fullmatch(w[4]) or w[4] in DASHES):
                values[columns[sum(x > edge for edge in edges)]].append(w)
        if not any(values.values()):
            wrapped = name
            continue
        if any(len(v) > 1 for v in values.values()):
            wrapped = []
            continue
        if (wrapped and not OUTLINE.match(label) and
                0 <= y - min(w[1] for w in wrapped) < 18 and abs(name[0][0] - wrapped[0][0]) < 5
                and not all(w[4].isupper() for w in wrapped)):
            name = wrapped + name
            label = ' '.join(w[4] for w in name)
        wrapped = []
        yield label, name, values


def _reading(raw, locale=None):
    values = {}
    for convention in ('vi_VN', 'en_US'):
        try:
            values[convention] = parse_number(raw.replace('−', '-'), convention)
        except ValueError:
            pass
    if len(set(values.values())) == 1:
        return next(iter(values.values()))
    return values.get(locale)


@lru_cache(maxsize=4)
def _read(path, source_hash):
    with open(path, 'rb') as stream:
        if file_digest(stream, 'sha256').hexdigest() != source_hash:
            raise ValueError('PDF_SOURCE_HASH_MISMATCH')
    found = []
    previous = None
    with pymupdf.open(path) as pdf:
        for page in pdf:
            if page.rotation:
                previous = None
                continue
            rows = lines(page.get_text('words'))
            # The table must declare its basis near the start of the page.
            early = [(y, ws) for y, ws in rows if y < page.rect.height * .42]
            heading_text = label_key(' '.join(w[4] for _, ws in early for w in ws))
            signals = (r'cong bo|before|truoc|original|reported', r'chinh|adjust|change',
                       r'trinh|sau|restat|updated')
            header = _header(early) if all(re.search(term, heading_text) for term in signals) else None
            context = _context(rows, header, previous) if header else None
            if not context:
                previous = None
                continue
            context.setdefault('context_page', page.number + 1)
            previous = {**context, 'headers': header}
            candidates = list(_row_candidates(rows, header))
            counts = Counter('en_US' if ',' in w[4] else 'vi_VN'
                             for _, _, vs in candidates for words in vs.values() for w in words
                             if re.search(r'\d(?:,\d{3}){2,}|\d(?:\.\d{3}){2,}', w[4]))
            locale = next(iter(counts)) if len(counts) == 1 else None
            for raw_label, name, values in candidates:
                label = OUTLINE.sub('', raw_label).strip()
                normalized = label_key(label)
                if not normalized:
                    continue
                for basis, words in values.items():
                    if not words:
                        continue
                    box = union_box(words)
                    raw = words[0][4]
                    if ''.join(page.get_text(clip=pymupdf.Rect(box) + (-.5, -.5, .5, .5)).split()) != raw:
                        continue
                    marker = 'PRINTED_DASH' if raw in DASHES else None
                    amount = None if marker else _reading(raw, locale)
                    if amount is None and marker is None:
                        continue
                    found.append(dict(**context, page=page.number + 1, box=box, basis=basis,
                                      header_box=list(header[basis]), row_box=union_box(name), row_label=label,
                                      row_label_raw=raw_label, row_label_normalized=normalized, value_raw=raw,
                                      printed_marker=marker, value=str(amount) if amount is not None else None))
    return found


def catalog(workspace, doc):
    path = workspace.source_file(doc['id'])
    records = _read(str(path), doc['sha256'])
    result = []
    for cached in records:
        row = {k: v.copy() if isinstance(v, list) else v for k, v in cached.items()}
        context = {**row, 'metric': row['row_label_normalized'], 'document_id': doc['id'], 'source_sha256': doc['sha256']}
        record = source_ref(doc, row['page'], f"{row['row_label']} · {row['value_raw']}",
                            box=row['box'], identity=cell_id(context), extraction_method='NATIVE',
                            verification_status='NATIVE_CELL_VERIFIED', verification='NATIVE_STATEMENT_SOURCE_CELL', **{k: v for k, v in row.items() if k not in ('page', 'box')})
        record.update(metric='local:' + row['row_label_normalized'],
                      period_start=None, column_label=row['basis'],
                      table_id=f"{doc['id']}:{row['context_page']}:{row['statement_type']}",
                      row_id=f"{row['page']}:{row['row_box'][1]:.2f}",
                      column_id=f"{row['page']}:{row['basis']}")
        result.append(record)
    return result

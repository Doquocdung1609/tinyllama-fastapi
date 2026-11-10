"""Opt-in scan recovery. OCR observations are candidates, never reviewed facts."""
from datetime import date
import os
from pathlib import Path
import re
from threading import Lock

from PIL import Image, ImageOps
import pymupdf
import pytesseract

from app.product import pdf_extract as base
from app.product import pdf_ocr_financial_v2 as baseline

VERSION = 'studio-vietnamese-financial-ocr-v3'
AUTOMATED = 'AUTOMATED_EXTRACTION'
CROSSCHECKED = 'AUTOMATED_CROSSCHECKED_CANDIDATE'
HUMAN = 'HUMAN_SOURCE_VERIFIED'
PAGE_LOCK = Lock()
MAX_REREADS = 6
METRIC_LABELS = {
    'assets': 'Tổng cộng tài sản', 'liabilities': 'Nợ phải trả',
    'equity': 'Vốn chủ sở hữu', 'net_revenue': 'Doanh thu thuần',
    'net_income': 'Lợi nhuận sau thuế', 'operating_cashflow': 'Lưu chuyển tiền thuần từ hoạt động kinh doanh',
}
AMOUNT = re.compile(r'(?:\(\d{1,3}(?:\.\d{3})*\)|[-−]?\d{1,3}(?:\.\d{3})*)\Z')
STROKES = {'-', '–', '—', '−'}


def statement_type(text):
    title = base.folded(text[:950])
    if re.search(r'bang can doi ke toan|bao cao tinh hinh tai chinh', title):
        return 'BALANCE_SHEET'
    if 'ket qua hoat dong kinh doanh' in title:
        return 'INCOME_STATEMENT'
    if re.search(r'luu chuyen tien te|luu chuyen tien mat', title):
        return 'CASH_FLOW'
    return 'NOTES' if 'thuyet minh' in title or re.search(r'\bb\s*09[a-z]?\s*dn\b',title) else 'UNKNOWN'


def metric_for(row, kind):
    label = base.folded(row['row_label'])
    if kind == 'BALANCE_SHEET':
        if re.match(r'tong (?:cong )?tai san\b', label):
            return 'assets'
        # The printed subtotal equation and statement heading jointly
        # disambiguate an unreadable total label, regardless of its row code.
        if (row.get('item_code') and re.search(
                rf'\(\s*{re.escape(row["item_code"])}\s*=\s*100\s*\+\s*200\s*\)', label)):
            return 'assets'
        if re.match(r'(?:tong (?:cong )?)?no phai tra\b', label):
            return 'liabilities'
        if re.match(r'(?:tong (?:cong )?)?von chu so huu\b', label):
            return 'equity'
    if kind == 'INCOME_STATEMENT':
        if re.match(r'(?:\d+[.]?\s+)?doanh thu thuan\b', label):
            return 'net_revenue'
        if 'loi nhuan sau thue' in label and 'chua phan phoi' not in label:
            return 'net_income'
    if kind == 'CASH_FLOW' and re.search(r'tien thuan tu (?:cac )?hoat dong kinh doanh', label):
        return 'operating_cashflow'
    return None


def periods(label, kind):
    if not label:
        return None, None, None
    if found := re.match(r'^(\d{1,2})/(\d{1,2})/(20\d{2})(?:\s|$)', label):
        day, month, year = map(int, found.groups())
        try:
            return None, date(year, month, day).isoformat(), 'INSTANT'
        except ValueError:
            return None, None, None
    if kind in {'CASH_FLOW', 'INCOME_STATEMENT'} and (found := re.fullmatch(r'(Q4|FY) (20\d{2})', label)):
        period, year = found.groups()
        return f'{year}-{"10" if period == "Q4" else "01"}-01', f'{year}-12-31', '3M_Q4' if period == 'Q4' else 'FY'
    return None, None, None


def crop(page, source_box, dpi, angle):
    clip = pymupdf.Rect(source_box) & page.rect
    if clip.is_empty:
        return None
    pix = page.get_pixmap(dpi=dpi, clip=clip, colorspace=pymupdf.csGRAY, alpha=False)
    result = Image.frombytes('L', (pix.width, pix.height), pix.samples)
    return result.rotate(-angle, expand=True) if angle else result


def numeric_rereads(page, box, angle):
    observations = []
    padded = [box[0]-3, box[1]-3, box[2]+3, box[3]+3]
    for dpi, contrast in ((330, False), (420, True)):
        img = crop(page, padded, dpi, angle)
        if img is None:
            continue
        if contrast:
            img = ImageOps.autocontrast(img, cutoff=2)
        try:
            raw = pytesseract.image_to_string(ImageOps.expand(img, border=10, fill=255),
                    lang='vie+eng', config=f'--dpi {dpi} --psm 7', timeout=8).strip()
        except (OSError, RuntimeError, pytesseract.TesseractError):
            raw = ''
        observations.append({'engine': 'Tesseract', 'dpi': dpi, 'contrast': contrast, 'raw': raw})
    return observations


def recognized_zero(words, cell, reading_y):
    if cell.get('binding_status')!='GEOMETRIC_CANDIDATE':
        return None
    anchor=cell['column_right_anchor']
    choices=[w for w in words if w['text']=='0' and abs(baseline.cy(w)-reading_y)<=5
             and abs(baseline.right(w)-anchor)<=13]
    return choices[0] if len(choices)==1 else None


def detect_marker(page, cell, row, angle, width, height):
    """Only classify image regions with geometrically anchored provision columns."""
    if not re.search(r'du phong$', base.folded(cell.get('period') or '')):
        return 'OCR_NOT_DETECTED', None
    y = row['reading_y']
    x = cell['column_right_anchor']
    rect = [x-24, y-6, x-4, y+6]
    source = base.inverse_box(rect, angle, width, height)
    dpi = 420
    img = crop(page, source, dpi, angle)
    if img is None:
        return 'STRUCTURE_UNKNOWN', None
    visible = img.point(lambda p: 255 if p < 170 else 0).getbbox()
    bounds = img.point(lambda p: 255 if p < 110 else 0).getbbox()
    if not visible:
        return 'EMPTY_CELL', source
    if not bounds:
        return 'OCR_NOT_DETECTED', source
    x0, y0, x1, y1 = bounds
    scale = dpi/72
    w, h = (x1-x0)/scale, (y1-y0)/scale
    if 1 <= w <= 6 and .15 <= h <= 2.1 and w >= 2*h:
        mark = [rect[0]+x0/scale, rect[1]+y0/scale, rect[0]+x1/scale, rect[1]+y1/scale]
        return 'PRINTED_DASH', base.inverse_box(mark, angle, width, height)
    return 'OCR_NOT_DETECTED', source


def paddle_rereads(page, requests, angle):
    """Optional subprocess in a pinned local CPU environment, one batch per page."""
    executable = os.getenv('STUDIO_OCR_PADDLE_PYTHON')
    if not executable or not requests:
        return {}
    import json
    import subprocess
    from tempfile import TemporaryDirectory
    worker = Path(__file__).resolve().parents[2]/'scripts'/'fis_paddle_ocr_crops.py'
    with TemporaryDirectory(prefix='fis-ocr-') as folder:
        paths = {}
        for key, box in requests:
            img = crop(page, [box[0]-3, box[1]-3, box[2]+3, box[3]+3], 330, angle)
            if img is not None:
                paths[key] = str(Path(folder)/f'{key}.png')
                ImageOps.expand(img, border=10, fill=255).save(paths[key])
        try:
            process = subprocess.run([executable, str(worker), folder], timeout=105, check=True,
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return json.loads((Path(folder)/'result.json').read_text(encoding='utf-8'))
        except (OSError, subprocess.SubprocessError, ValueError):
            return {}


def select_candidate(original, observations):
    reads = [o['raw'] for o in observations if AMOUNT.fullmatch(o['raw'])]
    if len(reads) >= 2 and len(set(reads)) == 1:
        return reads[0], CROSSCHECKED, 'REREAD_AGREEMENT' if reads[0] == original else 'REREAD_DIFFERS_FROM_BASELINE'
    if len(set([original, *reads])) > 1:
        return original, AUTOMATED, 'OCR_ENGINE_DISAGREEMENT'
    return original, AUTOMATED, 'OCR_REREAD_INCONCLUSIVE'


def enrich(page, result, document_id, cover_scope=None):
    angle = result['engine'].get('correction_clockwise', 0)
    kind = statement_type(result['text'])
    rows = baseline.arithmetic_warnings(result['tables'])
    words=[word for line in result['lines'] for word in line['words']]
    scope_conflict = any(r.get('scope') and cover_scope and r['scope'] != cover_scope for r in rows)
    for row in rows:
        row['statement_type'] = kind
        row['statement_scope'] = row.get('scope') or (cover_scope if not scope_conflict else None)
        row['scope_origin'] = 'PAGE_HEADING' if row.get('scope') else 'DOCUMENT_COVER' if row['statement_scope'] else None
        row['row_label_raw'] = row['row_label']
        row['metric'] = metric_for(row, kind)
        row['row_label_normalized'] = METRIC_LABELS.get(row['metric'], row['row_label'])
    pending = []
    for row in rows:
        if row.get('structure_status') != 'OCR_GEOMETRIC_CANDIDATE':
            continue
        for cell in row['cells']:
            text = cell['text']
            start, end, period_kind = periods(cell.get('period'), kind)
            cell.update(document_id=document_id,page=result['page'],table_id=row['table_id'],row_id=row['id'],
                        item_code=row.get('item_code'),row_label_raw=row['row_label_raw'],
                        row_label_normalized=row['row_label_normalized'],metric=row['metric'],
                        statement_type=kind,statement_scope=row['statement_scope'],
                        column_id=cell['cell_id'],period_start=start,period_end=end,period_type=period_kind,
                        source_box=cell['box'],raw_value=text,numeric_value=None,
                        ocr_engine='Tesseract',review_status=AUTOMATED,observations=[])
            marker = 'PRINTED_DASH' if text in STROKES else 'PRINTED_ZERO' if text == '0' else None
            zero=recognized_zero(words,cell,row['reading_y']) if not text else None
            if zero:
                marker='PRINTED_ZERO'
                cell.update(text='0',box=zero['box'],source_box=zero['box'],raw_value='0',
                            blank=False,confidence=zero['confidence'])
            elif not text and cell.get('binding_status')!='GEOMETRIC_CANDIDATE':
                marker='STRUCTURE_UNKNOWN'
            elif not text:
                marker, box = detect_marker(page,cell,row,angle,result['width'],result['height'])
                if marker=='PRINTED_DASH':
                    cell.update(text='-',box=box,source_box=box,blank=False,ocr_engine='IMAGE_STROKE')
                else:
                    cell['inspection_box'] = box
            cell['printed_marker'] = marker
            if cell['box'] and not marker and (
                    (cell.get('confidence') or 0) < 80 or not AMOUNT.fullmatch(text) or row.get('warnings')):
                priority = (0 if (cell.get('confidence') or 0) < 80 else 1, cell.get('confidence') or 0)
                pending.append((priority,cell))
    pending.sort(key=lambda item:item[0])
    selected = [c for _,c in pending[:MAX_REREADS]]
    reads = {c['cell_id']:numeric_rereads(page,c['box'],angle) for c in selected}
    paddle = paddle_rereads(page, [(c['cell_id'],c['box']) for c in selected
        if any(o['raw'] != c['raw_value'] for o in reads[c['cell_id']])],angle)
    for cell in selected:
        observations = reads[cell['cell_id']]
        if cell['cell_id'] in paddle:
            observations.append({'engine':'PP-OCRv6_small','raw':paddle[cell['cell_id']]})
        chosen, status, warning = select_candidate(cell['raw_value'],observations)
        cell.update(text=chosen,review_status=status,ocr_warning=warning,observations=observations)
        if chosen != cell['raw_value']:
            cell['ocr_engine'] = 'LOCAL_CROP_REREAD'
    for row in rows:
        for cell in row['cells']:
            if 'review_status' not in cell:
                continue
            if AMOUNT.fullmatch(cell['text']):
                text=cell['text'].replace('.','').replace('−','-')
                cell['numeric_value'] = '-'+text[1:-1] if text.startswith('(') else text
    result['tables'] = rows
    return result


def extract_page(page, number, document_id=None, cover_scope=None):
    with PAGE_LOCK:
        result=baseline.extract_page(page,number)
        result['version']=VERSION
        if result['method']=='OCR':
            return enrich(page,result,document_id,cover_scope)
        return result


def explicit_cover_scope(text):
    title=base.folded(text[:1300])
    separate=bool(re.search(r'bao cao tai chinh rieng\b',title))
    consolidated=bool(re.search(r'bao cao tai chinh hop nhat\b',title))
    return ('SEPARATE' if separate else 'CONSOLIDATED') if separate != consolidated else None


def extract_document(path, document_id, checkpoint, save_progress):
    cover=checkpoint(1)
    scope=explicit_cover_scope(cover['text']) if cover else None
    def extract(page, number):
        nonlocal scope
        result=extract_page(page,number,document_id,scope)
        if number==1:
            scope=explicit_cover_scope(result['text'])
        return result
    return base.extract_document(path,document_id,checkpoint,save_progress,extractor=extract,version=VERSION)

"""Experimental, source-coordinate layout for Vietnamese scanned statements."""
from decimal import Decimal
from functools import partial
import re
from statistics import median

from app.product import pdf_extract as base

VERSION = 'studio-vietnamese-financial-ocr-v2'
AMOUNT = re.compile(r'^(?:\([0-9]{1,3}(?:\.[0-9]{3})+\)|[−-]?[0-9]{1,3}(?:\.[0-9]{3})+)$')
DATE = re.compile(r'^\d{1,2}/\d{1,2}/20\d{2}$')
DASH = {'-', '–', '—'}
CODE = re.compile(r'^\d{2,3}[a-z]?$')


def right(word):
    return word['rx'] + word['rw']


def cx(word):
    return (word['rx'] + right(word)) / 2


def cy(word):
    return word['ry'] + word['rh'] / 2


def union(words):
    return [min(w['box'][0] for w in words), min(w['box'][1] for w in words),
            max(w['box'][2] for w in words), max(w['box'][3] for w in words)]


def groups(words, tolerance):
    rows = []
    for word in sorted(words, key=cy):
        if rows and cy(word)-median(map(cy, rows[-1])) <= tolerance:
            rows[-1].append(word)
        else:
            rows.append([word])
    return [sorted(row, key=lambda w:w['rx']) for row in rows]


def column_headers(words):
    units = [w for w in words if w['text'].strip('.,()').upper() == 'VND']
    candidates = [row for row in groups(units, 15) if 2 <= len(row) <= 6]
    if len(candidates) != 1:
        return []
    unit_row = candidates[0]
    headers = []
    for index, unit in enumerate(unit_row):
        distances = [abs(cx(unit)-cx(w)) for w in unit_row if w is not unit]
        if min(distances)<28:
            return []
        span = min(38, min(distances)*.47)
        nearby = [w for w in words if abs(cx(w)-cx(unit))<=span and 2<cy(unit)-cy(w)<31]
        dates = [w for w in nearby if DATE.fullmatch(w['text'])]
        years = [w for w in nearby if re.fullmatch(r'20\d{2}',w['text'])]
        header = None
        period = None
        if len(dates)==1 and (not years or cy(dates[0])>=max(map(cy,years))-3):
            header = period = dates[0]['text']
        elif len(years)==1:
            year = years[0]
            tokens = [w for w in words if abs(cy(w)-cy(year))<5 and year['rx']-85<w['rx']<year['rx']]
            tokens = sorted(tokens, key=lambda w:w['rx'])
            # Only contiguous words immediately before the year belong to the column.
            prefix = []
            left = year['rx']
            for w in reversed(tokens):
                if left-right(w)>11:
                    break
                prefix.insert(0,w['text'])
                left=w['rx']
            phrase = base.folded(' '.join(prefix))
            if re.search(r'\bquy\s+(?:iv|4)\b',phrase):
                period = 'Q4 '+year['text']
            elif re.search(r'\bnam\b',phrase):
                period = 'FY '+year['text']
            header = ' '.join(prefix+[year['text']])
        headers.append({'index':index,'period':period,'header':header,'unit':'VND',
                        'center':cx(unit),'unit_word':unit})
    dates = sorted((w for w in words if DATE.fullmatch(w['text'])
                    and 14<min(cy(u) for u in unit_row)-cy(w)<32),key=cx)
    if len(headers)==4 and len(dates)==2:
        # Two dates above two adjacent cost/provision groups, only when all
        # four subheaders are physically present.
        labels = []
        for h in headers:
            local = sorted((w for w in words if abs(cx(w)-h['center'])<28
                            and 2<cy(h['unit_word'])-cy(w)<16),key=lambda w:w['rx'])
            label = base.folded(' '.join(w['text'] for w in local))
            labels.append('Giá gốc' if 'gia goc' in label else 'Dự phòng' if 'du phong' in label else None)
        if labels==['Giá gốc','Dự phòng']*2 and all(
                abs(cx(dates[i])-sum(h['center'] for h in headers[2*i:2*i+2])/2)<30 for i in range(2)):
            for i,h in enumerate(headers):
                h['period'] = h['header'] = f"{dates[i//2]['text']} {labels[i]}"
    return headers


def reconstruct(words, number, scope=None):
    headers = column_headers(words)
    if not headers:
        return []
    bottom = max(cy(h['unit_word']) for h in headers)
    possible = [w for w in words if cy(w)>bottom+8 and AMOUNT.fullmatch(w['text'])]
    if not possible:
        return []
    for h in headers:
        distance = min(abs(h['center']-other['center']) for other in headers if other is not h)
        right_limit = min(72, distance*.74)
        ends = [right(w) for w in possible if h['center']-14<=right(w)<=h['center']+right_limit]
        h['anchor'] = median(ends) if len(ends)>=2 else h['center']+right_limit*.65
        h['tolerance'] = min(19, distance*.36)
    buckets = []
    for word in words:
        if cy(word)<=bottom+8 or (not AMOUNT.fullmatch(word['text']) and word['text'] not in DASH):
            continue
        h = min(headers,key=lambda item:abs(item['anchor']-right(word)))
        if abs(h['anchor']-right(word))<=h['tolerance']:
            buckets.append({**word,'column':h['index']})
    numeric_rows = [row for row in groups(buckets,5) if any(AMOUNT.fullmatch(w['text']) for w in row)]
    if len(numeric_rows)<2:
        return []
    # A solitary short decimal after a gap is prose, not a continuation of the table.
    while len(numeric_rows)>2:
        last=numeric_rows[-1]
        if (median(map(cy,last))-median(map(cy,numeric_rows[-2]))<=45
                or len(last)>1 or any(len(re.sub(r'\D','',w['text']))>=6 for w in last)):
            break
        numeric_rows.pop()
    centers = [median(map(cy,row)) for row in numeric_rows]
    left_limit = min(h['center'] for h in headers)-max(24, min(h['center'] for h in headers)*.10)
    slope = (cy(headers[-1]['unit_word'])-cy(headers[0]['unit_word']))/(headers[-1]['center']-headers[0]['center'])
    slope = max(-.045,min(.045,slope)) if len(headers)==2 else 0
    def label_y(word):
        return cy(word)-slope*(cx(word)-headers[0]['center'])
    text_rows = groups([w for w in words if bottom<label_y(w)<centers[-1]+15 and right(w)<left_limit
                       and not AMOUNT.fullmatch(w['text'])],4.5)
    code_words = [w for row in text_rows for w in row if CODE.fullmatch(w['text']) and w['rx']>left_limit*.55]
    code_x = median([w['rx'] for w in code_words]) if len(code_words)>=2 else None
    assigned = [[] for _ in numeric_rows]
    for line in text_rows:
        # Attach individual words rather than a whole line: skew can put the
        # code and amount a few points above the start of the label.
        for word in line:
            nearest=min(range(len(centers)),key=lambda i:abs(centers[i]-label_y(word)))
            if abs(centers[nearest]-label_y(word))<=14:
                assigned[nearest].append(word)
    starts = [w['rx'] for bucket in assigned for w in bucket if w['confidence']>=89
              and len(w['text'])>=3 and w['text'][0].isupper()
              and (code_x is None or w['rx']<code_x-18)]
    # A repeated left margin identifies the body even if the scan has vertical letterhead.
    first_margin = next((x for x in sorted(starts) if sum(abs(y-x)<=3 for y in starts)>=5),None)
    rows = []
    table_id = f'p{number}-ocr-v2'
    for i, row in enumerate(numeric_rows):
        label_words = [w for w in assigned[i] if (code_x is None or w['rx']<code_x-10)
                       and (first_margin is None or w['rx']>=first_margin-9)]
        label_lines = groups(label_words,4.5)
        if len(label_lines)>1 and code_x is not None:
            # A line that already has a code belongs to its own row.
            other_codes = [w for w in code_words if abs(w['rx']-code_x)<13
                           and abs(label_y(w)-centers[i])>5]
            label_lines = [line for line in label_lines if not any(
                abs(label_y(code)-median(map(label_y,line)))<4 for code in other_codes)]
        label = ' '.join(' '.join(w['text'] for w in line) for line in label_lines)
        if not any(c.isalpha() for c in label):
            continue
        codes = [w['text'] for w in assigned[i] if code_x is not None and abs(w['rx']-code_x)<13 and CODE.fullmatch(w['text'])]
        cells = []
        for h in headers:
            options = [w for w in row if w['column']==h['index']]
            w = options[0] if len(options)==1 else None
            cells.append({'cell_id':f'{table_id}-r{i}-c{h["index"]}', 'column_index':h['index'],
                          'text':w['text'] if w else '', 'box':w['box'] if w else None,
                          'confidence':w['confidence'] if w else None,'blank':not w,
                          'column_right_anchor':h['anchor'],'period':h['period'],
                          'column_label':h['header'],'unit':h['unit'],'scope':scope,
                          'binding_status':'AMBIGUOUS' if len(options)>1 or not h['period'] else 'GEOMETRIC_CANDIDATE',
                          'verification':'OCR_UNVERIFIED'})
        rows.append({'id':f'{table_id}-r{i}','table_id':table_id,'row_label':label,
                     'normalized_label':base.folded(label),'item_code':codes[0] if len(codes)==1 else None,
                     'reading_y':centers[i],'box':union(row+[w for line in label_lines for w in line]),'cells':cells,
                     'scope':scope,'structure_status':'OCR_GEOMETRIC_CANDIDATE'})
    return rows


def arithmetic_warnings(rows):
    """Only check relationships printed in the OCR labels. Never edit a value."""
    by_code = {}
    for row in rows:
        code = row.get('item_code')
        if code:
            by_code.setdefault(code, []).append(row)
    result = []
    for row in rows:
        label = row['row_label']
        code = row.get('item_code')
        formula = re.search(r'\(([0-9]{2,3})\s*=\s*([0-9]{2,3}(?:\s*[+−-]\s*[0-9]{2,3})+)\)', label)
        if not formula or formula[1]!=code:
            result.append(row)
            continue
        terms = re.findall(r'([+−-]?)\s*([0-9]{2,3})',formula[2])
        if any(len(by_code.get(item,[]))!=1 for _,item in terms):
            result.append(row)
            continue
        warnings = []
        for column, target in enumerate(row['cells']):
            if any(column>=len(by_code[item][0]['cells']) for _,item in terms):
                continue
            values = [by_code[item][0]['cells'][column] for _,item in terms]
            texts = [target['text'],*[value['text'] for value in values]]
            if not target.get('period') or any(value.get('period')!=target['period'] or value.get('unit')!=target['unit']
                                               for value in values) or not all(AMOUNT.fullmatch(t) for t in texts):
                continue
            def amount(text):
                return Decimal(text.replace('.','').replace('−','-').strip('()')) * (-1 if text.startswith('(') else 1)
            expected = sum(amount(t)*(-1 if sign in {'-','−'} else 1) for (sign,_),t in zip(terms,texts[1:],strict=True))
            if amount(texts[0])!=expected:
                warnings.append(f"OCR_ARITHMETIC_MISMATCH · {target['period']} · {formula[0]}")
        result.append({**row,'warnings':warnings} if warnings else row)
    return result


def extract_page(page, number):
    result = base.extract_page(page, number, ocr=partial(base._ocr,dpi=300,psm=3,grayscale=True))
    result['version'] = VERSION
    if result['method']!='OCR':
        return result
    words = [w for line in result['lines'] for w in line['words']]
    heading = base.folded(result['text'][:950])
    scope = 'SEPARATE' if 'cong ty me' in heading else 'CONSOLIDATED' if 'hop nhat' in heading else None
    rows = reconstruct(words,number,scope)
    result['ocr_warnings'] = ['OCR_UNVERIFIED'] if rows else ['OCR_UNVERIFIED','TABLE_HEADER_OR_GEOMETRY_UNRESOLVED']
    if rows:
        result['tables'] = rows
    return result


def extract_document(path, document_id, checkpoint, save_progress):
    return base.extract_document(path,document_id,checkpoint,save_progress,extractor=extract_page,version=VERSION)

"""Bounded page extraction. Coordinates are real, in the rotated PDF viewport.

Table rows are candidates, never automatically source-verified numeric facts.
No SEC/iXBRL authentication is applied to ordinary uploaded PDFs.
"""
from collections import defaultdict
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import shutil
import unicodedata

import pymupdf

VERSION = "studio-page-evidence-v2"
DPI = 240


def folded(value):
    normalized=''.join(c for c in unicodedata.normalize('NFD', value.casefold().replace('đ', 'd'))
                       if unicodedata.category(c) != 'Mn')
    return re.sub(r'\s+',' ',normalized).strip()


def ocr_capability():
    import pytesseract
    from app.config import get_settings
    settings=get_settings()
    command = settings.tesseract_cmd or shutil.which('tesseract')
    if not command:
        return {'status': 'OCR_NOT_INSTALLED', 'languages': []}
    pytesseract.pytesseract.tesseract_cmd = command
    folder = str(settings.tessdata_dir)
    # Environment avoids pytesseract's Windows shlex quoting ambiguity for paths with spaces.
    os.environ['TESSDATA_PREFIX'] = str(Path(folder).resolve())
    config = ''
    try:
        languages = pytesseract.get_languages(config=config)
        return {'status': 'READY' if {'vie', 'eng'} <= set(languages) else 'OCR_VI_LANGUAGE_MISSING',
                'languages': languages, 'engine': 'Tesseract', 'dpi': DPI}
    except (OSError, RuntimeError):
        return {'status': 'OCR_NOT_INSTALLED', 'languages': []}


def inverse_box(box, angle, width, height):
    """Inverse of PIL clockwise quarter-turn, in original rendered pixels."""
    x0,y0,x1,y1 = box
    if angle == 90:
        return [y0, height-x1, y1, height-x0]
    if angle == 180:
        return [width-x1, height-y1, width-x0, height-y0]
    if angle == 270:
        return [width-y1, x0, width-y0, x1]
    return list(box)


def _ocr(page, *, dpi=DPI, psm=3, grayscale=False):
    from PIL import Image
    import pytesseract
    capability = ocr_capability()
    if capability['status'] != 'READY':
        raise ValueError(capability['status'])
    scale = min(dpi/72, (12_000_000 / max(1,page.rect.width*page.rect.height))**.5)
    pix = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale),
                          colorspace=pymupdf.csGRAY if grayscale else pymupdf.csRGB, alpha=False)
    image = Image.frombytes('L' if grayscale else 'RGB', [pix.width,pix.height], pix.samples)
    original_width, original_height = image.size
    from app.config import get_settings
    folder = str(get_settings().tessdata_dir)
    os.environ['TESSDATA_PREFIX'] = str(Path(folder).resolve())
    config = ''
    angle, orientation = 0, 'NOT_DETERMINED'
    try:
        osd = pytesseract.image_to_osd(image, config=config, output_type=pytesseract.Output.DICT, timeout=35)
        if float(osd.get('orientation_conf',0)) >= 2:
            angle = int(osd.get('rotate',0)) % 360
            orientation = 'OSD'
    except (pytesseract.TesseractError, RuntimeError):
        pass
    if angle:
        image = image.rotate(-angle, expand=True)
    data = pytesseract.image_to_data(image, lang='vie+eng', config=f'--psm {psm}' if dpi==DPI and not grayscale else f'--dpi {dpi} --psm {psm}',
                                     output_type=pytesseract.Output.DICT, timeout=100)
    words=[]
    for i, raw in enumerate(data['text']):
        text=unicodedata.normalize('NFC',raw.strip())
        if not text or float(data['conf'][i]) < 0:
            continue
        x,y,w,h=(int(data[k][i]) for k in ('left','top','width','height'))
        box=inverse_box([x,y,x+w,y+h],angle,original_width,original_height)
        box=[box[0]*page.rect.width/original_width,box[1]*page.rect.height/original_height,
             box[2]*page.rect.width/original_width,box[3]*page.rect.height/original_height]
        # Reading coordinates are in the corrected image; source box is inverse mapped.
        words.append({'text':text,'box':box,'confidence':float(data['conf'][i]),
                      'rx':x/scale,'ry':y/scale,'rh':h/scale,
                      **({'rw':w/scale} if grayscale else {}),
                      'line':[data[k][i] for k in ('block_num','par_num','line_num')]})
    return words, {'engine':'Tesseract','language':'vie+eng','dpi':dpi,'psm':psm,
                   'correction_clockwise':angle,'orientation_method':orientation}


def _lines(words):
    # Merge words with near-equal baselines, across OCR blocks, retaining columns.
    rows=[]
    for word in sorted(words,key=lambda w:(w['ry'],w['rx'])):
        target=next((row for row in reversed(rows[-6:]) if abs(row['y']-word['ry']) < max(2.5, word['rh']*.45)),None)
        if target is None:
            target={'y':word['ry'],'words':[]};rows.append(target)
        target['words'].append(word)
    result=[]
    for row in sorted(rows,key=lambda r:r['y']):
        ws=sorted(row['words'],key=lambda w:w['rx'])
        boxes=[w['box'] for w in ws]
        result.append({'text':' '.join(w['text'] for w in ws),'words':ws,'reading_y':row['y'],
                       'box':[min(b[0] for b in boxes),min(b[1] for b in boxes),max(b[2] for b in boxes),max(b[3] for b in boxes)]})
    return result


def table_candidates(lines, page_number, correction=0):
    def right(word):
        box=word['box']
        width=word.get('rw',(box[3]-box[1]) if correction in {90,270} else (box[2]-box[0]))
        return word['rx']+width
    def number(word):
        return bool(re.fullmatch(r'\(?[+−-]?\d[\d.,]*\)?',word['text']) and
                    len(word['text'].replace('.','').replace(',','').strip('()-'))>=4)
    clusters=[]
    for w in (w for line in lines for w in line['words'] if number(w)):
        end=right(w)
        cluster=next((c for c in clusters if abs(c['x']-end)<13),None)
        if cluster is None:clusters.append({'x':end,'points':[end]})
        else:
            cluster['points'].append(end);cluster['x']=sum(cluster['points'])/len(cluster['points'])
    anchors=sorted(c['x'] for c in clusters if len(c['points'])>=3)
    rows=[]
    for n,line in enumerate(lines):
        ws=line['words']
        cells=[w for w in ws if number(w)]
        if not cells and anchors and sum(c.isalpha() for c in line['text'])>6:
            cells=[w for w in ws if (re.fullmatch(r'\(?[+−-]?\d[\d.,]*\)?',w['text']) or w['text'] in {'-','—','–'})
                   and right(w)>=anchors[0]-22]
        if not cells:
            continue
        cutoff=min(w['rx'] for w in cells)
        label=' '.join(w['text'] for w in ws if w['rx']<cutoff)
        if sum(c.isalpha() for c in label)<4:
            # Multi-line financial labels can sit just above/below their code/value baseline.
            neighbors=[candidate for candidate in lines[max(0,n-1):n+2]
                       if candidate is not line and abs(candidate['reading_y']-line['reading_y'])<16
                       and sum(c.isalpha() for c in candidate['text'])>6
                       and not any(re.fullmatch(r'\(?\d[\d.,]{5,}\)?',w['text']) for w in candidate['words'])]
            if neighbors:
                neighbor=min(neighbors,key=lambda x:abs(x['reading_y']-line['reading_y']))
                label=neighbor['text']+' '+label
        if len(label)<3:
            continue
        slots={}
        if 2<=len(anchors)<=8:
            for w in ws:
                if re.fullmatch(r'\(?[+−-]?\d[\d.,]*\)?',w['text']) or w['text'] in {'-','—','–'}:
                    nearest=min(range(len(anchors)),key=lambda i:abs(anchors[i]-right(w)))
                    if abs(anchors[nearest]-right(w))<22:slots[nearest]=w
        if len(slots)>=1:
            parsed_cells=[{'column_index':i,'text':slots[i]['text'] if i in slots else '',
                           'box':slots[i]['box'] if i in slots else None,
                           'confidence':slots[i]['confidence'] if i in slots else None,
                           'verification':'NUMERIC_EVIDENCE_UNVERIFIED',
                           'blank':i not in slots,'column_right_anchor':anchor} for i,anchor in enumerate(anchors)]
        else:
            parsed_cells=[{'column_index':i,'text':w['text'],'box':w['box'],'confidence':w['confidence'],
                           'verification':'NUMERIC_EVIDENCE_UNVERIFIED'} for i,w in enumerate(cells)]
        rows.append({'id':f'p{page_number}-r{n}','table_id':f'p{page_number}-table-candidates',
                     'reading_y':line['reading_y'],
                     'row_label':label,'item_code':next((w['text'] for w in ws if re.fullmatch(r'\d{2,3}[a-z]?',w['text'])),None),
                     'box':line['box'],'cells':parsed_cells,
                     'structure_status':'TABLE_STRUCTURE_UNVERIFIED'})
    return rows


def extract_page(page, number, *, ocr=None):
    native=page.get_text('words')
    text=page.get_text('text')
    image_area=sum(pymupdf.Rect(info['bbox']).get_area() for info in page.get_image_info())
    ratio=min(1.,image_area/max(page.rect.get_area(),1))
    letters=sum(c.isalpha() for c in text)
    signature=bool(re.search(r'digitally signed|signature|ky so|signed by',folded(text)))
    use_ocr=(letters < 60 or (ratio > .65 and (letters < 400 or signature)))
    if use_ocr:
        words,engine=(ocr or _ocr)(page)
        kind='SIGNATURE_ONLY' if signature and letters else 'SCANNED' if letters<60 else 'MIXED'
        method='OCR'
    else:
        words=[]
        for x0,y0,x1,y1,word,block,line,position in native:
            rect=pymupdf.Rect(x0,y0,x1,y1)*page.rotation_matrix
            words.append({'text':unicodedata.normalize('NFC',word),'box':list(rect),'confidence':None,
                          'rx':rect.x0,'ry':rect.y0,'rh':rect.height,'line':[block,line]})
        engine={'engine':'PyMuPDF','version':pymupdf.VersionBind}
        method='NATIVE';kind='MIXED' if ratio>.2 else 'TEXT'
    lines=_lines(words)
    return {'page':number,'pdf_type':kind,'method':method,'original_rotation':page.rotation,
            'width':page.rect.width,'height':page.rect.height,'coordinate_space':'ROTATED_PDF_VIEWPORT_POINTS',
            'engine':engine,'text':'\n'.join(x['text'] for x in lines),'lines':lines,
            'tables':table_candidates(lines,number,engine.get('correction_clockwise',0)),'status':'EXTRACTED' if lines else 'EMPTY',
            'native_page_hash':sha256(text.encode()).hexdigest(),'version':VERSION}


def extract_document(path, document_id, checkpoint, save_progress, *, extractor=None, version=VERSION):
    """Checkpoint callbacks own persistence; only one rendered page lives at a time."""
    extractor = extractor or extract_page
    chunks=[]
    with pymupdf.open(path) as pdf:
        if pdf.is_encrypted or not 1 <= len(pdf) <= 250:
            raise ValueError('PDF_PAGE_LIMIT_OR_ENCRYPTED')
        completed=0;errors=[]
        for number,page in enumerate(pdf,1):
            saved=checkpoint(number)
            if not saved:
                try:
                    saved=extractor(page,number)
                except Exception as exc:
                    code=str(exc)
                    saved={'page':number,'status':'FAILED','error':code if code.isupper() else 'OCR_PAGE_FAILED','version':version,
                           'method':'OCR','pdf_type':'SCANNED','lines':[],'tables':[],'text':''}
                save_progress(number,saved,len(pdf))
            if saved['status']=='FAILED':
                errors.append(saved.get('error','OCR_PAGE_FAILED'));continue
            completed+=1
            group=[];length=0
            def flush():
                nonlocal group,length
                if not group:return
                content='\n'.join(line['text'] for line in group)
                chunks.append({'id':f'pdf_{document_id}_{number}_{len(chunks):05d}','document_id':document_id,'page':number,
                    'text':content,'text_hash':sha256(content.encode()).hexdigest(),
                    'page_text_hash':saved['native_page_hash'],'line_boxes':[line['box'] for line in group]})
                group=[];length=0
            for line in saved['lines']:
                if group and length+len(line['text'])>700:flush()
                group.append(line);length+=len(line['text'])
            flush()
            if len(chunks)>3000 or sum(len(c['text']) for c in chunks)>2_000_000:
                raise ValueError('PDF_TEXT_LIMIT')
        if errors:
            raise ValueError(errors[0])
        if not chunks or sum(sum(c.isalpha() for c in x['text']) for x in chunks)<60:
            raise ValueError('PDF_NO_EXTRACTABLE_TEXT')
        return len(pdf),chunks

"""Bounded region OCR and provenance-preserving fusion. No financial certification."""
from hashlib import sha256
import json
import math
import re
import statistics
import time
import unicodedata

import cv2
import numpy as np
import pymupdf

from app.product import pdf_extract as legacy

VERSION='studio-region-evidence-v3r.1'
POLICY={'analysis_dpi':120,'ocr_dpi':300,'alternate_dpi':450,'max_pixels':12_000_000,
        'unrepresented_ink':.35,'max_regions':40,'minimum_confidence':60,'psm_primary':3,'psm_alternate':11}
NUMERIC=re.compile(r'^\(?[+−-]?\d[\d.,]*\)?$')


def policy_hash():
    from pathlib import Path
    return sha256(Path(__file__).read_text(encoding='utf-8').encode()).hexdigest()


def _intersection(a,b):
    r=pymupdf.Rect(a)&pymupdf.Rect(b)
    return max(0,r.get_area())


def _reading(box,angle,width,height):
    x0,y0,x1,y1=box
    return {0:[x0,y0,x1,y1],90:[height-y1,x0,height-y0,x1],180:[width-x1,height-y1,width-x0,height-y0],270:[y0,width-x1,y1,width-x0]}.get(angle,list(box))


def _native(page):
    result=[]
    for x0,y0,x1,y1,text,block,line,position in page.get_text('words'):
        box=list(pymupdf.Rect(x0,y0,x1,y1)*page.rotation_matrix)
        result.append({'text':unicodedata.normalize('NFC',text),'box':box,'confidence':None,'source':'NATIVE','region_id':'native','line':[block,line]})
    return result


def _image_regions(page):
    rects=[]
    for info in page.get_image_info():
        rect=(pymupdf.Rect(info['bbox'])*page.rotation_matrix)&page.rect
        if rect.is_empty:continue
        if not any(_intersection(rect,r)>.98*min(rect.get_area(),r.get_area()) for r in rects):rects.append(rect)
    merged=[]
    for rect in sorted(rects,key=lambda r:(r.y0,r.x0)):
        touched=[i for i,r in enumerate(merged) if _intersection(rect,r)>.2*min(rect.get_area(),r.get_area())]
        for i in reversed(touched):rect|=merged.pop(i)
        merged.append(rect)
    return merged


def _render(page,box,dpi):
    rect=pymupdf.Rect(box);scale=min(dpi/72,math.sqrt(POLICY['max_pixels']/max(rect.get_area(),1)))
    pix=page.get_pixmap(matrix=pymupdf.Matrix(scale,scale),clip=rect,alpha=False)
    return pix,scale


def _raster_features(page,box,represented):
    pix,scale=_render(page,box,POLICY['analysis_dpi']);arr=np.frombuffer(pix.samples,dtype=np.uint8).reshape(pix.height,pix.width,pix.n)
    gray=cv2.cvtColor(arr,cv2.COLOR_RGB2GRAY)
    ink=cv2.threshold(gray,0,255,cv2.THRESH_BINARY_INV|cv2.THRESH_OTSU)[1]
    horizontal=cv2.morphologyEx(ink,cv2.MORPH_OPEN,np.ones((1,max(15,pix.width//25)),np.uint8))
    vertical=cv2.morphologyEx(ink,cv2.MORPH_OPEN,np.ones((max(15,pix.height//25),1),np.uint8))
    text=cv2.subtract(ink,cv2.bitwise_or(horizontal,vertical))
    mask=np.zeros_like(text)
    for w in represented:
        r=pymupdf.Rect(w['box'])&pymupdf.Rect(box)
        if r.is_empty:continue
        x0=max(0,int((r.x0-box.x0-1.5)*scale));y0=max(0,int((r.y0-box.y0-1.5)*scale))
        x1=min(pix.width,int((r.x1-box.x0+1.5)*scale)+1);y1=min(pix.height,int((r.y1-box.y0+1.5)*scale)+1)
        mask[y0:y1,x0:x1]=255
    count,labels,stats,centroids=cv2.connectedComponentsWithStats(text)
    components=[s for s in stats[1:] if 2<=s[2]<=max(80,pix.width*.12) and 3<=s[3]<=max(80,pix.height*.15) and s[4]>=3]
    row_bins={int((s[1]+s[3]/2)/max(5,scale*5)) for s in components}
    grid_rows=sum(np.count_nonzero(horizontal,axis=1)>pix.width*.25)
    ink_count=int(np.count_nonzero(text));missing=int(np.count_nonzero(cv2.bitwise_and(text,cv2.bitwise_not(mask))))
    text_like=len(components)>=18 and (len(row_bins)>=2 or len(components)>=30)
    return {'text_components':len(components),'text_row_bins':len(row_bins),'grid_scanlines':int(grid_rows),
        'unrepresented_ink_fraction':missing/max(1,ink_count),'text_like':bool(text_like),'raster_sha256':sha256(pix.samples).hexdigest(),
        'analysis_pixel_size':[pix.width,pix.height]}


def _language(native):
    text=legacy.folded(' '.join(w['text'] for w in native))
    if re.search(r'bao cao|cong ty|tai san|thuyet minh',text):return 'vie+eng'
    return 'eng' if re.search(r'consolidated|financial|statement|subsidiaries',text) else 'vie+eng'


def _join_numeric(words):
    """Fuse only adjacent numeric token fragments;retain original token components."""
    rows=legacy._lines(words);result=[]
    for row in rows:
        pending=None
        for w in row['words']:
            numeric=bool(NUMERIC.fullmatch(w['text']) or w['text'] in {'(',')','−','-'})
            if numeric and pending is not None and 0<=w['rx']-(pending['rx']+pending['rw'])<max(1.5,w['rh']*.5):
                pending['components'].append(w['text']);pending['text']+=w['text']
                pending['box']=list(pymupdf.Rect(pending['box'])|pymupdf.Rect(w['box']))
                pending['rw']=w['rx']+w['rw']-pending['rx'];pending['confidence']=min(pending['confidence'],w['confidence'])
            else:
                if pending is not None:result.append(pending);pending=None
                if numeric:pending={**w,'components':[w['text']]}
                else:result.append(w)
        if pending is not None:result.append(pending)
    return result


def _ocr_pass(page,box,language,dpi,psm,angle=0):
    from PIL import Image
    import pytesseract
    pix,scale=_render(page,box,dpi);im=Image.frombytes('RGB',[pix.width,pix.height],pix.samples)
    width,height=im.size
    if angle:im=im.rotate(-angle,expand=True)
    data=pytesseract.image_to_data(im,lang=language,config=f'--psm {psm}',output_type=pytesseract.Output.DICT,timeout=100)
    words=[]
    for i,raw in enumerate(data['text']):
        text=unicodedata.normalize('NFC',raw.strip());confidence=float(data['conf'][i])
        if not text or confidence<0:continue
        x,y,w,h=(int(data[k][i]) for k in ['left','top','width','height'])
        restored=legacy.inverse_box([x,y,x+w,y+h],angle,width,height)
        source=[box.x0+restored[0]/scale,box.y0+restored[1]/scale,box.x0+restored[2]/scale,box.y0+restored[3]/scale]
        words.append({'text':text,'box':source,'confidence':confidence,'rx':x/scale,'ry':y/scale,'rw':w/scale,'rh':h/scale,
            'source':'OCR','line':[data[k][i] for k in ['block_num','par_num','line_num']],'ocr_pass':f'{dpi}:{psm}'})
    return _join_numeric(words)


def _ocr_region(page,box,language):
    from PIL import Image
    import pytesseract
    if legacy.ocr_capability()['status']!='READY':raise ValueError('OCR_NOT_AVAILABLE')
    pix,_=_render(page,box,150);im=Image.frombytes('RGB',[pix.width,pix.height],pix.samples);angle=0
    try:
        osd=pytesseract.image_to_osd(im,output_type=pytesseract.Output.DICT,timeout=25)
        if float(osd.get('orientation_conf',0))>=3:angle=int(osd.get('rotate',0))%360
    except (pytesseract.TesseractError,RuntimeError):pass
    primary=_ocr_pass(page,box,language,300,3,angle)
    numbers=[w for w in primary if NUMERIC.fullmatch(w['text']) and len(re.sub(r'\D','',w['text']))>=4]
    # Low-confidence numeric text gets a second independent layout pass,not a guessed correction.
    alternate=_ocr_pass(page,box,language,450,11,angle) if numbers and any(w['confidence']<60 for w in numbers) else []
    artifacts=[w for w in primary+alternate if not any(c.isalnum() for c in w['text']) and w['text'] not in {'-','−','(',')','%','$','₩','€'}]
    primary=[w for w in primary if w not in artifacts];alternate=[w for w in alternate if w not in artifacts]
    conflicts=[];result=list(primary)
    for w in alternate:
        if not NUMERIC.fullmatch(w['text']) or len(re.sub(r'\D','',w['text']))<4:continue
        overlap=[old for old in result if NUMERIC.fullmatch(old['text']) and _intersection(w['box'],old['box'])>.35*min(pymupdf.Rect(w['box']).get_area(),pymupdf.Rect(old['box']).get_area())]
        if not overlap:result.append(w);continue
        old=max(overlap,key=lambda p:_intersection(w['box'],p['box']))
        old_digits=re.sub(r'\D','',old['text']);new_digits=re.sub(r'\D','',w['text'])
        # Sparse-layout OCR can emit a short fragment over a complete amount.
        # Never replace an entire cell with that fragment because its confidence is high.
        if len(new_digits)<len(old_digits)-2 or pymupdf.Rect(w['box']).width<.65*pymupdf.Rect(old['box']).width:
            old.setdefault('fragment_readings',[]).append({'text':w['text'],'box':w['box'],'confidence':w['confidence']})
            continue
        options=[{'text':old['text'],'confidence':old['confidence'],'box':old['box'],'ocr_pass':old.get('ocr_pass')},
                 {'text':w['text'],'confidence':w['confidence'],'box':w['box'],'ocr_pass':w.get('ocr_pass')}]
        if re.sub(r'\D','',old['text'])!=re.sub(r'\D','',w['text']):conflicts.append({'box':old['box'],'readings':options})
        if w['confidence']>old['confidence']:
            result.remove(old);result.append({**w,'alternatives':options})
        else:old['alternatives']=options
    header_pass=None
    if not angle and numbers:
        first_amount=min((w['box'][1] for w in numbers if len(re.sub(r'\D','',w['text']))>=6),default=box.y0)
        bottom=min(first_amount-2,box.y0+box.height*.3)
        if bottom>box.y0+12:
            header_box=pymupdf.Rect(box.x0,box.y0,box.x1,bottom)
            old_header=[w for w in result if pymupdf.Rect(w['box']).y1<=bottom]
            years={w['text'] for w in old_header if re.fullmatch(r'(?:19|20)\d{2}',w['text'])}
            if len(years)<2:
                header=_ocr_pass(page,header_box,language,450,6)
                new_years={w['text'] for w in header if re.fullmatch(r'(?:19|20)\d{2}',w['text'])}
                if len(new_years)>len(years):
                    result=[w for w in result if w not in old_header]+header
                header_pass={'box':list(header_box),'psm':6,'dpi':450,'raw_words':[{'text':w['text'],'box':w['box'],'confidence':w['confidence']} for w in header],
                    'used':len(new_years)>len(years)}
    return result,{'engine':'Tesseract','language':language,'dpi':300,'alternate_dpi':450 if alternate else None,
        'psm':3,'alternate_psm':11 if alternate else None,'correction_clockwise':angle,'numeric_reading_conflicts':conflicts,
        'header_pass':header_pass,
        'nonsemantic_ocr_artifacts':[{'text':w['text'],'box':w['box'],'confidence':w['confidence']} for w in artifacts]}


def _fuse(native,ocr):
    result=list(native);duplicates=0;conflicts=[]
    for w in ocr:
        match=next((p for p in result if (p.get('source')=='NATIVE' or legacy.folded(p['text'])==legacy.folded(w['text'])) and _intersection(p['box'],w['box'])>.55*min(pymupdf.Rect(p['box']).get_area(),pymupdf.Rect(w['box']).get_area())
            and abs(pymupdf.Rect(p['box']).width-pymupdf.Rect(w['box']).width)<max(5,pymupdf.Rect(w['box']).width)),None)
        if match:
            duplicates+=1
            if legacy.folded(match['text'])!=legacy.folded(w['text']):conflicts.append({'box':w['box'],'kept':match['text'],'alternative':w['text']})
        else:result.append(w)
    return result,duplicates,conflicts


def extract_page(page,number,prior=None):
    started=time.perf_counter();native=_native(page);text=page.get_text('text');regions=[];ocr=[];warnings=[];angles=[]
    prior_words=[]
    if prior:
        prior_words=[{**w,'source':'PRIOR_OCR' if w.get('confidence') is not None else 'PRIOR_NATIVE'} for line in prior.get('lines',[]) for w in line['words']]
    images=_image_regions(page)
    for i,box in enumerate(images):
        region_id=f'p{number}-image{i}';baseline=prior_words or native;features=_raster_features(page,box,baseline)
        r={'id':region_id,'box':list(box),'features':features,'source':'EMBEDDED_IMAGE','verification':'NUMERIC_EVIDENCE_UNVERIFIED'}
        if i>=POLICY['max_regions']:
            r['status']='UNPROCESSED_REGION_LIMIT';warnings.append(r['status']);regions.append(r);continue
        if not features['text_like']:
            r.update(status='DECORATIVE_OR_SPARSE_IMAGE',kind='NON_TABLE_IMAGE');regions.append(r);continue
        if features['unrepresented_ink_fraction']<=POLICY['unrepresented_ink']:
            inherited=[w for w in prior_words if _intersection(w['box'],box)>.5*pymupdf.Rect(w['box']).get_area()]
            if inherited:
                ocr.extend({**w,'region_id':region_id} for w in inherited)
                angles.append(prior.get('engine',{}).get('correction_clockwise',0))
            r.update(status='REPRESENTED_BY_PRIOR_CHECKPOINT' if inherited else 'REPRESENTED_BY_NATIVE',kind='REPRESENTED_TEXT_IMAGE');regions.append(r);continue
        try:
            words,engine=_ocr_region(page,box,_language(native));ocr.extend({**w,'region_id':region_id} for w in words);angles.append(engine['correction_clockwise'])
            r.update(status='OCR_COMPLETE' if words else 'OCR_EMPTY',engine=engine,kind='TEXT_IMAGE',ocr_words=len(words))
            if not words:warnings.append('TEXT_LIKE_REGION_OCR_EMPTY')
            elif _raster_features(page,box,native+words)['unrepresented_ink_fraction']>.5:
                warnings.append('REGION_TEXT_COVERAGE_REMAINS_UNCERTAIN')
        except Exception as exc:
            r.update(status='OCR_FAILED',error=str(exc) if str(exc).isupper() else 'REGION_OCR_FAILED',kind='TEXT_IMAGE');warnings.append('REGION_OCR_FAILED')
        regions.append(r)
    # A page without embedded image objects can still be native;do not fabricate raster regions.
    words,duplicates,fusion_conflicts=_fuse(native,ocr)
    angle=max(set(angles),key=angles.count) if angles else 0
    for w in words:
        b=_reading(w['box'],angle,page.rect.width,page.rect.height);w.update(rx=b[0],ry=b[1],rw=b[2]-b[0],rh=b[3]-b[1])
    lines=legacy._lines(words);tables=[]
    region_keys=list(dict.fromkeys(w.get('region_id','native') for w in words))
    for rid in region_keys:
        rw=[w for w in words if w.get('region_id','native')==rid];rl=legacy._lines(rw)
        candidates=legacy.table_candidates(rl,number,angle)
        financial=[r for r in candidates if sum(bool(c['text']) for c in r['cells'])>=2]
        region=next((r for r in regions if r['id']==rid),None)
        # Text images such as footnotes/logos are not financial tables merely because OCR ran.
        if region:region['kind']='TABLE_IMAGE_CANDIDATE' if len(financial)>=3 else 'TEXT_IMAGE'
        if len(financial)<3 and rid!='native':continue
        first_amount=min((l['reading_y'] for l in rl if any(len(re.sub(r'\D','',w['text']))>=5 and NUMERIC.fullmatch(w['text']) for w in l['words'])),default=float('inf'))
        source_headers=[l for l in rl if l['reading_y']<first_amount]
        for j,row in enumerate(candidates):
            row.update(id=f'p{number}-{rid}-r{j}',table_id=f'p{number}-{rid}-table',region_id=rid,
                source_region=region['box'] if region else [0,0,page.rect.width,page.rect.height],verification='NUMERIC_EVIDENCE_UNVERIFIED')
            above=source_headers+[l for l in rl if l['reading_y']<row['reading_y'] and row['reading_y']-l['reading_y']<90 and l not in source_headers]
            row['header_candidates']=[{'text':l['text'],'box':l['box']} for l in above if re.search(r'(?:19|20)\d{2}|vnd|usd|won|dollar|dong|trieu|million',legacy.folded(l['text']))]
            row['header_word_candidates']=[{'text':w['text'],'box':w['box'],'confidence':w.get('confidence')} for l in source_headers for w in l['words']]
            for cell in row['cells']:
                cell['source']=next((w['source'] for w in rw if cell.get('box') and _intersection(w['box'],cell['box'])>.5*pymupdf.Rect(w['box']).get_area()),'UNKNOWN')
                cell['financial_evidence_status']='FINANCIAL_EVIDENCE_REVIEW_PENDING'
                cell['column_header_candidates']=row['header_candidates']
                if cell.get('box'):
                    cx=(cell['box'][0]+cell['box'][2])/2
                    years=[w for w in row['header_word_candidates'] if re.fullmatch(r'(?:19|20)\d{2}',w['text'])]
                    if years:cell['period_year_candidate']=min(years,key=lambda w:abs((w['box'][0]+w['box'][2])/2-cx))
                    units=[]
                    for w in row['header_word_candidates']:
                        t=legacy.folded(w['text'])
                        unit='KRW' if 'won' in t or t=='krw' else 'USD' if 'dollar' in t or t=='usd' else 'VND' if t in {'vnd','dong'} else None
                        if unit:units.append({**w,'unit':unit})
                    if units:cell['currency_candidate']=min(units,key=lambda w:abs((w['box'][0]+w['box'][2])/2-cx))
            tables.append(row)
    coverage='EXTRACTION_COVERAGE_WARNING' if warnings else 'EXTRACTION_COMPLETE'
    return {'page':number,'version':VERSION,'pdf_type':'MIXED_IMAGE' if images and native else 'SCANNED' if images else 'TEXT','method':'REGION_FUSION' if ocr else 'NATIVE',
        'width':page.rect.width,'height':page.rect.height,'original_rotation':page.rotation,'coordinate_space':'ROTATED_PDF_VIEWPORT_POINTS',
        'engine':{'engine':'PyMuPDF+TesseractRegions','correction_clockwise':angle,'policy':POLICY},'text':'\n'.join(l['text'] for l in lines),'lines':lines,'tables':tables,'regions':regions,
        'status':'EXTRACTED' if words else 'EMPTY','native_page_hash':sha256(text.encode()).hexdigest(),'extraction_coverage_status':coverage,'coverage_warnings':warnings,
        'fusion':{'native_words':len(native),'ocr_or_prior_words':len(ocr),'duplicates_merged':duplicates,'conflicts':fusion_conflicts},
        'prior_checkpoint_sha256':prior.get('_parent_sha') or sha256(json.dumps(prior,ensure_ascii=False,sort_keys=True).encode()).hexdigest() if prior else None,
        'timings_ms':{'region_extraction':round((time.perf_counter()-started)*1000,3)},'financial_evidence_status':'FINANCIAL_EVIDENCE_REVIEW_PENDING'}


def extract_document(path,document_id,checkpoint,save_progress,prior=None):
    from pathlib import Path
    source_sha256=sha256(Path(path).read_bytes()).hexdigest()
    chunks=[]
    with pymupdf.open(path) as pdf:
        if pdf.is_encrypted or not 1<=len(pdf)<=250:raise ValueError('PDF_PAGE_LIMIT_OR_ENCRYPTED')
        total_pages=len(pdf)
        for number,page in enumerate(pdf,1):
            saved=checkpoint(number)
            if not saved:
                saved=extract_page(page,number,prior(number) if prior else None)
                for row in saved.get('tables',[]):row.update(source_sha256=source_sha256,page=number)
                save_progress(number,saved,len(pdf))
            group=[];length=0
            def flush():
                nonlocal group,length
                if not group:return
                text='\n'.join(l['text'] for l in group)
                chunks.append({'id':f'pdf_{document_id}_{number}_{len(chunks):05d}','document_id':document_id,'page':number,'text':text,
                    'text_hash':sha256(text.encode()).hexdigest(),'page_text_hash':saved['native_page_hash'],'line_boxes':[l['box'] for l in group]});group=[];length=0
            for line in saved['lines']:
                if group and length+len(line['text'])>700:flush()
                group.append(line);length+=len(line['text'])
            flush()
            if len(chunks)>3000 or sum(len(c['text']) for c in chunks)>2_000_000:raise ValueError('PDF_TEXT_LIMIT')
    if not chunks:raise ValueError('PDF_NO_EXTRACTABLE_TEXT')
    return total_pages,chunks

"""Narrow original-PDF verifier for three-column restatement tables.

Only native text, independently checked cell rectangles, ordered semantic
headers, explicit period/unit/scope and a continued-table link can qualify.
Arithmetic is a final consistency check, never the sole verification.
"""
from decimal import Decimal
import re
import pymupdf
from app.product.pdf_extract import folded
from app.product.analysis import parse_number

VERSION='NATIVE_ADJUSTMENT_COLUMNS_V1'

def verify_rows(w,hits):
    pdfs={}
    try:
        for h in hits:
            if not h.get('adjustment_columns_candidate') or h.get('extraction_method')!='NATIVE':continue
            h.pop('adjustment_verification',None);h.pop('verification',None)
            h['numeric_status']='UNVERIFIED';h['verification_status']='SOURCE_ROW_UNREVIEWED'
            for c in h.get('source_cells',[]):c['verification']='NUMERIC_EVIDENCE_UNVERIFIED'
            doc_id=h['document_id'];doc=w.document(doc_id)
            if doc['sha256']!=h['source_sha256']:raise ValueError('PDF_SOURCE_HASH_MISMATCH')
            if doc_id not in pdfs:pdfs[doc_id]=pymupdf.open(w.source_file(doc_id))
            pdf=pdfs[doc_id];page=pdf[h['page']-1]
            if page.rotation:continue
            context_page=h.get('scope_provenance',{}).get('page')
            if context_page not in {h['page'],h['page']-1}:continue
            context=pdf[context_page-1].get_text();cf=folded(context)
            scope='CONSOLIDATED' if 'hop nhat' in cf[:1600] else 'SEPARATE' if re.search(r'\brieng\b|cong ty me',cf[:1600]) else None
            dates=re.findall(r'\b(\d{1,2}/\d{1,2}/20\d{2})\b',context)
            if scope!=h.get('statement_scope') or 'trieu dong' not in cf or not dates:continue
            if len(set(dates))!=1 or not dates[0].endswith('/'+str(h.get('report_period'))):continue
            row_rect=pymupdf.Rect(h['box']);row_rect.y0-=.5;row_rect.y1+=.5
            source_label=folded(' '.join(page.get_text(clip=row_rect).split()))
            if folded(' '.join(h['row_label'].split())) not in source_label:continue
            y=h['box'][1];header=[v for v in page.get_text('words') if v[3]<min(y-4,150)]
            # These three distinct original header words anchor semantics to x.
            markers=[]
            for term in ('đã','chỉnh','trình'):
                matches=[v for v in header if v[4].casefold().strip('().:')==term]
                if len(matches)!=1:break
                markers.append((matches[0][0]+matches[0][2])/2)
            if len(markers)!=3 or markers!=sorted(markers):continue
            native_header=folded(' '.join(v[4] for v in header))
            if not all(t in native_header for t in ('cong bo','dieu chinh','trinh bay lai')):continue
            cells=sorted(h['source_cells'],key=lambda c:c['column_index'])
            if len(cells)!=3 or [c['column_index'] for c in cells]!=[0,1,2]:continue
            boundaries=[(markers[i]+markers[i+1])/2 for i in range(2)]
            values=[];proof=[]
            for i,c in enumerate(cells):
                box=c.get('box');raw=c['text'].strip()
                if not box or not re.fullmatch(r'\(?-?\d[\d,]*\)?',raw):break
                x=(box[0]+box[2])/2
                if (i>0 and x<=boundaries[i-1]) or (i<2 and x>=boundaries[i]):break
                rect=pymupdf.Rect(box);rect.x0-=.5;rect.y0-=.5;rect.x1+=.5;rect.y1+=.5
                actual=''.join(page.get_text(clip=rect).split())
                if actual!=raw:break
                try:value=parse_number(raw,'en_US')
                except ValueError:break
                values.append(value);proof.append({'raw':raw,'value':str(value),'box':box,'basis':('ORIGINAL','ADJUSTMENT','RESTATED')[i]})
            if len(values)!=3 or values[0]+values[1]!=values[2]:continue
            for c in h['source_cells']:c['verification']='NATIVE_CELL_VERIFIED'
            h.update(verification_status='NATIVE_CELL_VERIFIED',adjustment_verification={'version':VERSION,'status':'VERIFIED','cells':proof,
                'period_end':dates[0],'scope_source_page':context_page,'unit_source_page':context_page,
                'header_marker_centers':markers,'checks':['ORIGINAL_NATIVE_CELL_BYTES','SEMANTIC_COLUMN_ORDER','SOURCE_SCOPE_DATE_UNIT','RESTATEMENT_IDENTITY']},
                numeric_status='CELL_VERIFIED',verification='VERIFIED_NATIVE_ADJUSTMENT_ROW',unit='TRIEU_VND')
        return hits
    finally:
        for pdf in pdfs.values():pdf.close()

def comparison_answer(question,hits):
    if not re.search(r'khac nhau bao nhieu|chenh lech.*dieu chinh|difference.*adjust',folded(question)):return None
    rows=[h for h in hits if h.get('adjustment_verification',{}).get('status')=='VERIFIED']
    separate=[h for h in rows if h['statement_scope']=='SEPARATE'];consolidated=[h for h in rows if h['statement_scope']=='CONSOLIDATED']
    if len(separate)!=1 or len(consolidated)!=1:return None
    a,b=separate[0],consolidated[0]
    from app.product.financial_understanding import understand
    slots=understand(question)
    if slots.requested_unit and slots.requested_unit!=a['unit']:return None
    if slots.years and set(slots.years)!={a['report_period']}:return None
    if not a.get('metric') or (a['metric'],a['report_period'],a['unit'])!=(b.get('metric'),b['report_period'],b['unit']):return None
    av=a['adjustment_verification']['cells'][1];bv=b['adjustment_verification']['cells'][1]
    difference=Decimal(bv['value'])-Decimal(av['value'])
    return {'status':'SUPPORTED','answer':f"Mức điều chỉnh hợp nhất là {bv['raw']} triệu đồng [2]; riêng ngân hàng là {av['raw']} triệu đồng [1]. Chênh lệch (hợp nhất − riêng): {difference:,.0f} triệu đồng.",
        'values':[str(difference)],'unit':'TRIEU_VND','formula':f"{bv['value']} - {av['value']} = {difference}",
        'citations':[a,b],'verification_status':VERSION,'search_profile':'faith_r_product_v1',
        'operands':[{'value_raw':v['raw'],'normalized_value':str(Decimal(v['value'])*1000000),'normalized_unit':'VND',
            'row_label':h['row_label'],'currency':'VND','scale':'1000000','period':h['report_period'],'basis':'ADJUSTMENT',
            'statement_scope':h['statement_scope']} for h,v in ((b,bv),(a,av))]}

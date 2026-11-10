"""A source-bound page map over the immutable extraction checkpoints."""
from hashlib import sha256
import re

from app.product.pdf_extract import folded
from app.product.pdf_ocr_financial_v3 import statement_type

TITLES={'BALANCE_SHEET':'Bảng cân đối kế toán','INCOME_STATEMENT':'Báo cáo kết quả kinh doanh',
        'CASH_FLOW':'Báo cáo lưu chuyển tiền tệ','NOTES':'Thuyết minh báo cáo tài chính',
        'POLICY':'Chính sách kế toán','EXPLANATION':'Giải trình biến động kết quả kinh doanh',
        'COVER':'Bìa báo cáo tài chính','UNKNOWN':'Nội dung trích xuất chưa phân loại'}

TOPICS={
 'dac diem hoat dong':'Đặc điểm hoạt động','hinh thuc so huu von':'Hình thức sở hữu vốn', 'ky ke toan':'Kỳ kế toán và đơn vị tiền tệ',
 'cac chinh sach ke toan':'Chính sách kế toán', 'trich lap cho nhung khoan phai thu':'Dự phòng phải thu',
 'nguyen tac ghi nhan von':'Nguyên tắc ghi nhận vốn chủ sở hữu', 'tien gui ngan hang':'Tiền và tiền gửi ngân hàng',
 'dau tu vao cong ty':'Đầu tư vào công ty con','phai thu khac':'Phải thu khác',
 'tai san co dinh huu hinh':'Tài sản cố định hữu hình','tai san co dinh vo hinh':'Tài sản cố định vô hình',
 'bat dong san dau tu':'Bất động sản đầu tư','thue gia tri gia tang':'Thuế và các khoản phải nộp',
 'phai tra khac':'Phải trả khác','bang doi chieu bien dong':'Bảng đối chiếu biến động vốn chủ sở hữu',
 'co phieu dang luu hanh':'Cổ phiếu đang lưu hành','gia von hang ban':'Giá vốn hàng bán',
 'chi phi tai chinh':'Chi phí tài chính','chi phi quan ly doanh nghiep':'Chi phí quản lý doanh nghiệp',
 'giai trinh bien dong':'Giải trình biến động kết quả kinh doanh',
}


def source_ref(doc, number, text, *, box=None, identity='', **fields):
    key=sha256(f"{doc['sha256']}:{number}:{identity}:{box}".encode()).hexdigest()[:24]
    return {'document_id':doc['id'],'filename':doc['filename'],'issuer':doc.get('issuer',''),
            'source_sha256':doc['sha256'],'page':number,'source_kind':'PDF','text':text,
            'box':box,'citation_id':key,'evidence_id':key,**fields}


def printed_folio(page):
    height=page['width'] if page['engine'].get('correction_clockwise') in {90,270} else page['height']
    width=page['height'] if page['engine'].get('correction_clockwise') in {90,270} else page['width']
    matches=[]
    for line in page['lines']:
        for word in line['words']:
            if re.fullmatch(r'[1-9]\d{0,2}',word['text']) and (word.get('confidence') is None or word['confidence']>=75) and word['ry']>height*.88 and word['rx']>width*.67:
                matches.append((int(word['text']),word['box']))
    return matches[0] if len(matches)==1 else (None,None)


def page_entry(doc,number,page,error=None):
    if page is None:
        text='Chưa có bằng chứng đọc được'
        return {'page':number,'title':text,'kind':'UNKNOWN','printed_page':None,'reading_status':text,
                'extraction_error':error,'sample':'—','citation':source_ref(doc,number,text)}
    body=folded(page['text'])
    kind=statement_type(page['text'])
    if 'giai trinh bien dong ket qua' in body:
        kind='EXPLANATION'
    elif 'thuyet' in body[:900] and 'minh' in body[:900] and kind=='UNKNOWN':
        kind='NOTES'
    elif re.search(r'bao cao tai chinh (?:rieng|hop nhat)',body) and kind=='UNKNOWN' and len(body)<700:
        kind='COVER'
    topics=[label for key,label in TOPICS.items() if key in body]
    if kind=='NOTES' and 'tien te su dung trong ke toan' in body and 'Kỳ kế toán và đơn vị tiền tệ' not in topics:
        topics.insert(0,'Kỳ kế toán và đơn vị tiền tệ')
    if kind=='NOTES' and any(t in topics for t in ('Kỳ kế toán và đơn vị tiền tệ','Chính sách kế toán','Dự phòng phải thu','Nguyên tắc ghi nhận vốn chủ sở hữu')):
        kind='POLICY'
    title=TITLES[kind]
    if kind in {'NOTES','POLICY','EXPLANATION'} and topics:
        title+=' · '+', '.join(topics[:3])
    row=next((r for r in page['tables'] if r.get('metric')),None)
    if not row and kind in {'BALANCE_SHEET','CASH_FLOW','INCOME_STATEMENT'}:
        row=next((r for r in page['tables'] if len(folded(r['row_label']).split())>=3
                  and any(c.get('period') and c.get('text') for c in r['cells'])),None)
    sample=(row.get('row_label_normalized') or row['row_label']) if row else (
        topics[0] if topics else next((l['text'] for l in page['lines'] if len(l['text'])>30), '—'))
    weak=[]
    for line in page['lines']:
        scores=[w['confidence'] for w in line['words'] if w.get('confidence') is not None]
        if len(scores)>=3 and sum(score<60 for score in scores)*2>=len(scores):
            weak.append({'box':line['box'],'status':'LOW_OCR_CONFIDENCE'})
        if len(weak)==4:
            break
    if kind=='COVER':
        cover=[line['text'] for line in page['lines'] if re.search(r'bao cao tai chinh|quy [ivx]+/',folded(line['text']))]
        if cover:
            sample=' · '.join(cover)
    rotation=page['engine'].get('correction_clockwise',0)
    quality=page.get('quality',{})
    state='Lớp chữ PDF' if page['method']=='NATIVE' else 'OCR · chưa chứng nhận'
    if not page['text'].strip() or page.get('status')=='FAILED':
        state='Chưa đọc được nội dung'
    if rotation:
        state+=f' · hiệu chỉnh {rotation}°'
    folio,folio_box=printed_folio(page)
    return {'page':number,'printed_page':folio,'printed_page_box':folio_box,'title':title,'kind':kind,
            'sample':sample[:160],'reading_status':state,'rotation':rotation,'method':page['method'],
            'extraction_status':page.get('status'),'ocr_quality':quality,
            'tables':len({r.get('table_id') for r in page['tables']}),
            'metrics':sorted({r['metric'] for r in page['tables'] if r.get('metric')}),
            'reading_warnings':page.get('ocr_warnings',[]),'weak_ocr_regions':weak,
            'citation':source_ref(doc,number,title,identity='page-map',extraction_method=page['method'])}


def document_map(workspace,doc):
    pages=[page_entry(doc,n,page,error) for n,page,error in workspace.iter_document_evidence(doc['id'],doc['pages'])]
    return {'document_id':doc['id'],'source_sha256':doc['sha256'],'page_count':doc['pages'],'pages':pages}

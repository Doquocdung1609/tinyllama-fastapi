"""Grounded OCR explanations and tentative reads, separate from the review ledger."""
from hashlib import sha256
import re
from decimal import Decimal, InvalidOperation

from app.product.analysis import METRICS, parse_number
from app.product.financial_understanding import requested_unit
from app.product.ocr_reviewed_answer import SCOPE_LABELS, UNIT_LABELS, period_label, requested_note_column, requested_periods
from app.product.pdf_extract import folded
from app.product.pdf_ocr_financial_v3 import AUTOMATED, CROSSCHECKED, VERSION

DEFINITIONS = {
    'assets':'Tổng tài sản là tổng giá trị tài sản doanh nghiệp ghi nhận tại một ngày, gồm tài sản ngắn hạn và dài hạn.',
    'liabilities':'Nợ phải trả là các nghĩa vụ doanh nghiệp còn phải thanh toán hoặc thực hiện tại ngày báo cáo.',
    'equity':'Vốn chủ sở hữu là phần tài sản còn lại sau khi trừ nợ phải trả.',
    'net_revenue':'Doanh thu thuần là doanh thu bán hàng và cung cấp dịch vụ sau khi trừ các khoản giảm trừ doanh thu.',
    'net_income':'Lợi nhuận sau thuế là phần lãi hoặc lỗ còn lại sau khi tính chi phí và thuế thu nhập doanh nghiệp.',
    'operating_cashflow':'Lưu chuyển tiền thuần từ hoạt động kinh doanh là tiền thực thu trừ tiền thực chi từ hoạt động kinh doanh trong kỳ. Số âm cho biết tiền chi ra lớn hơn tiền thu vào.',
}
MATH = re.compile(r'\b(?:tinh|chenh lech|so voi|ty le|ty trong|phan tram|tang truong|doi sang)\b')


def locator(doc, page, row, cell=None):
    number=page['page']
    base=sha256(f"{doc['sha256']}:{number}:{row['id']}:{page['evidence_sha256']}".encode()).hexdigest()[:24]
    box=cell['box'] if cell else row['box']
    identity=sha256(f"{base}:{cell['cell_id']}".encode()).hexdigest()[:24] if cell else base
    label=row.get('row_label_normalized') or row['row_label']
    text=label+' | '+cell['text'] if cell and cell.get('text') else label
    evidence={'citation_id':identity,'evidence_id':identity,'document_id':doc['id'],'source_sha256':doc['sha256'],
              'source_kind':'PDF','page':number,'row_id':row['id'],'row_label':label,'box':box,
              'filename':doc['filename'],'issuer':doc['issuer'],'text':text,'extraction_method':'OCR',
              'numeric_status':'UNVERIFIED','statement_scope':row.get('statement_scope')}
    if cell:
        evidence.update(column_id=cell['cell_id'],period=cell.get('period'),unit=cell.get('unit'),
                        ocr_provenance={k:cell.get(k) for k in ('raw_value','text','observations','ocr_engine',
                            'ocr_warning','review_status','printed_marker','period_type','period_start','period_end')})
    return evidence


def response(text,citations,level='OCR_SOURCE_EXPLANATION'):
    return {'status':'SOURCE_EXCERPTS','answer_status':level,'answer':text,'citations':citations,
            'values':[],'verification_status':level}


def eligible_candidate(row,cell):
    if (not cell.get('box') or cell.get('binding_status')!='GEOMETRIC_CANDIDATE'
            or not cell.get('period_end') or not cell.get('period_type') or cell.get('unit') not in UNIT_LABELS
            or cell.get('statement_scope') not in SCOPE_LABELS or cell.get('review_status') not in {AUTOMATED,CROSSCHECKED}
            or cell.get('ocr_warning')=='OCR_ENGINE_DISAGREEMENT'
            or any((cell.get('period') or '') in warning for warning in row.get('warnings',[]))):
        return False
    try:
        return cell.get('numeric_value') is not None and parse_number(cell['text'],'vi_VN')==Decimal(cell['numeric_value'])
    except (ValueError,InvalidOperation):
        return False


def describe_reread(cell):
    rereads=[o for o in cell.get('observations',[]) if o['raw']==cell['text']]
    if not rereads or not cell.get('raw_value') or cell.get('unit') not in UNIT_LABELS:
        return None
    original=cell['raw_value']
    unit=UNIT_LABELS[cell['unit']]
    engines=', '.join(dict.fromkeys(o['engine'].replace('PP-OCRv6_small','PaddleOCR PP-OCRv6 Small') for o in rereads))
    digits=[f'{a} → {b}' for a,b in zip(original,cell['text']) if a.isdigit() and b.isdigit() and a!=b]
    change=f" Chữ số thay đổi: {', '.join(digits)}." if digits and len(original)==len(cell['text']) else ''
    if original==cell['text']:
        return f"Tesseract ban đầu và {engines} ở lượt đọc lại cùng đọc {original} {unit}. Giá trị OCR ứng viên chưa được người dùng xác nhận."
    return (f"Tesseract ban đầu đọc {original} {unit}. {engines} đọc lại thành {cell['text']} {unit}.{change} "
            "Bản đọc lại là giá trị OCR ứng viên, chưa được người duyệt xác nhận.")


def answer(workspace,request,hits):
    if len(request.document_ids)!=1:
        return None
    doc_id=request.document_ids[0]
    doc=workspace.document(doc_id)
    q=folded(request.question)
    metrics=[m for m,aliases in METRICS.items() if any(a in q for a in aliases)]
    dash='du phong' in q and ('dau gach' in q or 'o trong' in q)
    note='tien gui ngan hang' in q
    discrepancy=bool(re.search(r'ocr ban dau|ocr goc|doc lai|lan doc',q))
    definition=bool(re.search(r'la gi\b|y nghia|giai thich',q)) and not re.search(r'bao nhieu|nguyen nhan|vi sao|tai sao',q)
    value=bool(re.search(r'bao nhieu|gia tri|kiem duyet|xac minh|o trang nao|vi tri|nam o dau',q))
    if not (dash or note or len(metrics)==1 or len(metrics)>1 and MATH.search(q)):
        return None
    if re.search(r'\b(?:chua phan phoi|ngan han|dai han)\b',q) or ('hop nhat' in q and 'cong ty me' in q):
        return None
    if not discrepancy and not dash and MATH.search(q):
        from app.product.analysis import eligible_facts
        from app.product.pdf_ocr_financial_v3 import HUMAN, METRIC_LABELS
        missing=[];refs=[]
        facts=eligible_facts(workspace,[doc_id])
        for metric in metrics:
            periods=requested_periods(request.question,metric)
            reviewed=[f for f in facts if f['metric']==metric and (f['period'],f.get('period_type')) in periods
                      and f.get('review_status')==HUMAN]
            if len(reviewed)==1:
                fact=reviewed[0]
                refs.append({**fact,'citation_id':fact['id'],'column_id':fact.get('cell_id'),'source_kind':'PDF',
                             'text':fact['row_label']+' | '+fact['source_display']})
                continue
            missing.append(METRIC_LABELS[metric])
            for hit in hits:
                if not hit.get('row_id'):
                    continue
                page=workspace.page_evidence(doc_id,hit['page'])
                row=next((r for r in page['tables'] if r['id']==hit['row_id'] and r.get('metric')==metric),None)
                if row is not None:
                    cells=[c for c in row['cells'] if c.get('box') and (c.get('period_end'),c.get('period_type')) in periods]
                    refs.append(locator(doc,page,row,cells[0] if len(cells)==1 else None))
                    break
        reason=f" Cần đối chiếu thêm: {', '.join(missing)}." if missing else " Cần xác định phép tính và các ô cùng kỳ, cùng phạm vi."
        return response('Chưa đủ căn cứ để tính kết quả đã xác minh.'+reason+
                        ''.join(f' [{i}]' for i in range(1,len(refs)+1)), refs)
    if not (value or discrepancy or definition or dash):
        return None
    metric=metrics[0] if len(metrics)==1 else None
    if not (metric or note or dash):
        return None
    explicit=re.search(r'\btrang\s+(\d{1,3})\b',q)
    if explicit and not 1<=int(explicit[1])<=doc['pages']:
        return response('Số trang bạn nêu nằm ngoài PDF đã chọn.',[])
    pages=[int(explicit[1])] if explicit else list(dict.fromkeys(h['page'] for h in hits if h.get('document_id')==doc_id))
    # The original note may rank below page-level results when a question
    # combines the financial label with OCR terminology.
    if note and not explicit:
        pages=list(dict.fromkeys([*pages,*range(1,doc['pages']+1)]))
    requested_scope='CONSOLIDATED' if 'hop nhat' in q else 'SEPARATE' if 'cong ty me' in q or 'bao cao rieng' in q else None
    found=[]
    for number in pages:
        page=workspace.page_evidence(doc_id,number)
        if page.get('version')!=VERSION or page['method']!='OCR':
            continue
        for row in page['tables']:
            if requested_scope and row.get('statement_scope')!=requested_scope:
                continue
            label=folded(row['row_label'])
            if dash or (note and 'tien gui ngan hang' in label) or (metric and row.get('metric')==metric):
                found.append((page,row))
    if dash:
        for page,row in found:
            for cell in row['cells']:
                if (cell.get('printed_marker')=='PRINTED_DASH' and cell.get('box')
                        and 'du phong' in folded(cell.get('column_label') or '')):
                    c=locator(doc,page,row,cell)
                    return response(f"Không thể mặc định dấu gạch bằng số 0. Ô “{c['row_label']}” ở cột {cell['period']} "
                                    f"hiển thị dấu gạch in trên PDF, trang {page['page']}. [1] "
                                    "Số 0 là giá trị được in bằng chữ số. Ô trống và ô OCR chưa đọc được cũng là các trường hợp riêng. "
                                    "Chỉ diễn giải dấu gạch theo quy ước nêu trong báo cáo.",[c])
        return response('Chưa định vị được một dấu gạch có tọa độ trong cột dự phòng đã hỏi. Hãy mở bảng để kiểm tra ký hiệu in trên ảnh.',hits[:1])
    if definition and metric:
        cites=[locator(doc,*found[0])] if found else []
        return response(DEFINITIONS[metric]+(f" Báo cáo trình bày chỉ tiêu này tại trang {cites[0]['page']}. [1]" if cites else ''),cites)
    wanted=requested_periods(request.question,metric)
    if note:
        end,_=requested_note_column(request.question)
        wanted=[(end,'INSTANT')] if end else []
    if not wanted:
        return response('Bạn muốn đối chiếu cột nào? Hãy ghi ngày đối với chỉ tiêu tại một thời điểm, hoặc ghi rõ quý và năm tài chính đối với chỉ tiêu theo kỳ.',
                        [locator(doc,*found[0])] if found else hits[:1])
    chosen=[]; citations=[]
    for end,kind in wanted:
        matches=[(p,r,c) for p,r in found for c in r['cells']
                 if c.get('period_end')==end and c.get('period_type')==kind and c.get('box')]
        if len(matches)!=1:
            return response('Chưa định vị được một ô duy nhất cho kỳ và phạm vi bạn hỏi. Hãy mở bảng nguồn để đối chiếu cột hoặc ghi rõ trang.',
                            [locator(doc,*item) for item in found[:2]] or hits[:1])
        page,row,cell=matches[0]
        c=locator(doc,page,row,cell)
        citations.append(c)
        number=len(citations)
        period=period_label(kind,end,cell.get('column_label'))
        if note:
            c['row_label']='Tiền gửi ngân hàng'
        location=f"{c['row_label']} tại {period}, {SCOPE_LABELS.get(c['statement_scope'],'phạm vi chưa xác định')}, trang {page['page']}"
        unit=requested_unit(request.question)
        if re.search(r'o trang nao|vi tri|nam o dau',q) and not re.search(r'bao nhieu|gia tri',q):
            chosen.append(f"Ô {location}. Mở trích dẫn để xem đúng hàng và cột. [{number}]")
        elif not eligible_candidate(row,cell) or (unit and unit!=cell['unit']):
            chosen.append(f"Đã tìm thấy ô {location}, nhưng cách đọc, kỳ, đơn vị hoặc liên kết cột chưa đủ nhất quán để nêu số. Hãy đối chiếu ô trên PDF. [{number}]")
        elif discrepancy:
            comparison=describe_reread(cell)
            if comparison:
                chosen.append(f"Ô {location}. {comparison} [{number}]")
            else:
                chosen.append(f"Ô {location} có bản đọc OCR ban đầu, nhưng chưa có quan sát đọc lại tương ứng để so sánh. [{number}]")
        else:
            detail='đã đọc đối chiếu tự động' if cell['review_status']==CROSSCHECKED else 'đọc từ ảnh quét'
            chosen.append(f"{location}, có giá trị OCR ứng viên {cell['text']} {UNIT_LABELS[cell['unit']]} ({detail}). [{number}]")
    if not discrepancy and not re.search(r'o trang nao|vi tri|nam o dau',q) and any('OCR ứng viên' in t for t in chosen):
        chosen.append('Các giá trị ứng viên chưa được người dùng xác nhận. Mở từng ô để đối chiếu chữ số, dấu và cột trên ảnh gốc.')
    return response('\n\n'.join(chosen),citations,'OCR_CANDIDATE_ANSWER' if any('OCR ứng viên' in t for t in chosen) else 'OCR_SOURCE_EXPLANATION')

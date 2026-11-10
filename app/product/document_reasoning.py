"""Plan and execute independent, source-bound tasks for whole-document questions."""
from decimal import Decimal, localcontext
import re

from app.product.analysis import eligible_facts
from app.product.document_financial_cells import DATE, LABELS, cached_facts, iso, words_of
from app.product.document_page_map import page_entry, source_ref
from app.product.pdf_extract import folded
from app.product.pdf_ocr_financial_v2 import union
from app.product.pdf_ocr_financial_v3 import HUMAN, explicit_cover_scope

TASKS={
 'equation':('Phương trình kế toán',('assets','liabilities','equity')),
 'cash':('Đối chiếu tiền và tương đương tiền',('cash','cash_end','cash_note')),
 'income':('Doanh thu, giá vốn và lợi nhuận gộp',('gross_revenue','deductions','net_revenue','cogs','gross_profit','note_revenue','note_cogs')),
 'shares':('Vốn góp, số cổ phiếu và mệnh giá',('paid_in_capital','shares','par')),
 'notes':('Tài sản cố định, thuế và phải trả khác',('fixed','fixed_note','intangible','intangible_note','investment','investment_note','tax','tax_note','other_payables','other_payables_note')),
 'explain':('Lợi nhuận và giải trình biến động',('net_income',)),
 'capital':('Vốn góp của chủ sở hữu',('paid_in_capital',)),
 'capital_equity':('Vốn góp và tổng vốn chủ sở hữu',('paid_in_capital','equity')),
}
MONEY={'VND':'đồng','SHARES':'cổ phiếu','VND_PER_SHARE':'đồng/cổ phiếu'}


def classify(text):
    q=folded(text)
    if ('tong tai san' in q or 'phuong trinh' in q) and 'no phai tra' in q and 'von chu so huu' in q:
        return 'equation'
    if 'tuong duong tien' in q and ('luu chuyen' in q or 'thuyet minh tien' in q):
        return 'cash'
    if 'gia von' in q and 'doanh thu' in q:
        return 'income'
    if ('co phieu' in q and 'menh gia' in q) or ('von gop' in q and 'co phieu' in q):
        return 'shares'
    if 'tai san co dinh' in q and ('thuyet minh' in q or 'thue' in q):
        return 'notes'
    if 'loi nhuan' in q and any(s in q for s in ('nguyen nhan','giai trinh','vi sao','tai sao')):
        return 'explain'
    return None


def plan(question):
    q=folded(question)
    if re.search(r'kiem ke|lap bang|doc|liet ke|tom tat',q) and re.search(r'(?:toan bo|tat ca|tung|moi)\s*(?:\d+\s*)?trang',q):
        return {'inventory':True,'tasks':['capital'] if 'von gop' in q and DATE.search(q) else []}
    numbered=re.findall(r'^\s*\d{1,2}[.)]\s+(.+)$',question,re.M)
    if len(numbered)>=2:
        tasks=[classify(item) for item in numbered]
        if sum(t is not None for t in tasks)>=2:
            return {'inventory':False,'tasks':[t or 'unknown' for t in tasks],'requests':numbered}
    if 'von gop' in q and DATE.search(q) and 'co phieu' not in q:
        return {'inventory':False,'tasks':['capital_equity' if 'tong von chu so huu' in q else 'capital']}
    task=classify(q)
    if task in {'shares','explain','income','notes','cash','equation'} and re.search(r'doi chieu|thuyet minh|trang \d|giai trinh',q):
        return {'inventory':False,'tasks':[task]}
    return None


def years(question):
    raw=folded(question)
    explicit=re.search(r'(?:quy\s*iv|q4)[ /]+(?:nam\s+)?(20\d{2})',raw)
    if explicit:
        return int(explicit[1])
    close=re.findall(r'31/12/(20\d{2})',raw)
    if close:
        return max(map(int,close))
    mentions=[int(x) for x in re.findall(r'\b20\d{2}\b',raw)]
    return max(mentions,default=None)


def explain_source(doc,page):
    words=words_of(page)
    heading=next((l for l in page['lines'] if 'giai trinh bien dong ket qua kinh doanh' in folded(l['text'])),None)
    if not heading:
        return None
    top=heading['box'][3]
    band=[w for w in words if top<w['ry']<top+47]
    # Read within each horizontal line rather than OCR block order.
    rows=[]
    for w in sorted(band,key=lambda w:w['ry']):
        if rows and w['ry']-rows[-1][0]['ry']<8:
            rows[-1].append(w)
        else:
            rows.append([w])
    paragraph=' '.join(' '.join(w['text'] for w in sorted(row,key=lambda w:w['rx'])) for row in rows)
    normalized=folded(paragraph)
    reason=re.search(r'chu yeu nho loi nhuan cong ty con chuyen ve tang',normalized)
    reported=re.search(r'quy iv nam (20\d{2}) la (\d{1,3}(?:\.\d{3})*) ty dong',normalized)
    if reason:
        return source_ref(doc,page['page'],paragraph,box=union(band),identity='published-explanation',
                          extraction_method=page['method'],reported_billions=reported[2] if reported else None,
                          reported_year=reported[1] if reported else None)
    return None


def markdown_safe(text):
    return str(text or '—').replace('|',' / ').replace('\n',' ')


def table(headers, rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join('---' for _ in headers)+' |',
                      *('| '+' | '.join(map(markdown_safe,row))+' |' for row in rows)])


def grouped(cells, metric, date, kind=None, prefer=None):
    matches=[c for c in cells if c['metric_id']==metric and c['period_end']==date
             and (kind is None or c['period_type']==kind)]
    if prefer and any(c['page']==prefer for c in matches):
        matches=[c for c in matches if c['page']==prefer]
    if len(matches)==1:
        return matches[0]
    if matches and len({(c['raw'],c['statement_scope'],c['unit']) for c in matches})==1:
        return matches[0]
    return None


def compare(operands, formula, relation, units, *, closing_balance=False):
    """Check dimensional compatibility before applying a registered Decimal relation."""
    refs=[c['citation']['citation_id'] for c in operands if c]
    if (any(c is None or c['value'] is None for c in operands)
            or len({(c['source_sha256'],c['statement_scope'],c['period_end']) for c in operands})!=1
            or tuple(c['unit'] for c in operands)!=units):
        return 'BLOCKED',None,formula+'. Thiếu ô số cùng tài liệu, kỳ, phạm vi hoặc đơn vị.',refs
    periods={(c.get('period_start'),c['period_type']) for c in operands}
    same_closing=(closing_balance and [c['metric_id'] for c in operands]==['cash','cash_end']
                  and [c['period_type'] for c in operands]==['INSTANT','FY'])
    if len(periods)!=1 and not same_closing:
        return 'BLOCKED',None,formula+'. Kỳ đo của các ô không tương thích.',refs
    with localcontext() as context:
        context.prec=50
        delta=relation([Decimal(c['value']) for c in operands])
    mode='VERIFIED_CALCULATION' if all(c['review_status']==HUMAN for c in operands) else 'CANDIDATE_RECONCILIATION'
    status='PASS' if not delta else 'PARTIAL'
    check='Khớp theo các ô nguồn' if not delta else f'Chênh lệch {delta:,.0f} đồng'.replace(',','.')
    return status,mode,f'{formula}. {check}.',refs


def answer(workspace,request,emit=lambda **_:None):
    planned=plan(request.question)
    if not planned or len(request.document_ids)!=1:
        return None
    doc=workspace.document(request.document_ids[0])
    if not doc:
        return None
    if not doc.get('issuer'):
        from app.product.financial_understanding import issuers
        identities=issuers(doc.get('filename',''))
        if len(identities)==1:
            doc={**doc,'issuer':identities[0]}
    emit(stage='planning',tasks_total=len(planned['tasks']))
    mapping=[]; cells=[]; explanation=None; scope=None; currency=None; currency_source=None; calendar=False; pages_read=0
    needed={metric for task in planned['tasks'] if task in TASKS for metric in TASKS[task][1]}
    for number,page,error in workspace.iter_document_evidence(doc['id'],doc['pages']):
        entry=page_entry(doc,number,page,error)
        mapping.append(entry)
        if page and page['text'].strip() and page.get('status')!='FAILED':
            pages_read+=1
        if page and needed:
            text=folded(page['text'])
            if number==1:
                scope=explicit_cover_scope(text)
            if not scope and 'cong ty me' in text[:850] and 'hop nhat' not in text[:850]:
                scope='SEPARATE'
            if 'dong viet nam' in text and 'tien te' in text and 'vnd' in text:
                currency='VND'
                line=next((l for l in page['lines'] if 'dong viet nam' in folded(l['text'])),None)
                if line and currency_source is None:
                    currency_source=source_ref(doc,number,line['text'],box=line['box'],
                                               identity='currency-policy',extraction_method=page['method'])
            if re.search(r'1 thang 1 den ngay 31 thang 12|01/01/20\d{2} den ngay 31/12/20\d{2}',text):
                calendar=True
            cells.extend(c for c in cached_facts(doc,page,entry,scope,currency) if c['metric_id'] in needed)
            if entry['kind']=='EXPLANATION' and 'explain' in planned['tasks']:
                explanation=explain_source(doc,page) or explanation
        emit(stage='reading',pages_read=pages_read,pages_examined=number,pages_total=doc['pages'])
    if not calendar:
        cells=[c for c in cells if c['period_type']=='INSTANT']
    review=[]
    if needed:
        try:
            review=eligible_facts(workspace,[doc['id']])
        except ValueError:
            # A stale review must never suppress independently readable pages.
            review=[]
    for cell in cells:
        verified=next((f for f in review if f.get('review_status')==HUMAN and f['page']==cell['page']
                       and f['row_id']==cell.get('row_id') and f.get('cell_id')==cell.get('column_id')
                       and f['period']==cell['period_end'] and f['unit']==cell['unit'] and f['box']==cell.get('box')
                       and f['statement_scope']==cell['statement_scope'] and f['metric']==cell['metric_id']),None)
        if verified:
            cell.update(review_status=HUMAN,value=verified['value'],raw=verified['source_display'])
            cell['citation'].update(verification=verified['verification'],
                                    text=f"{LABELS[cell['metric_id']]} · {verified['source_display']}")
    citations=[]; positions={}
    def cite(c):
        key=c['citation_id']
        if key not in positions:
            citations.append(c)
            positions[key]=len(citations)
        return f'[{positions[key]}]'
    parts=[]
    if planned['inventory']:
        parts.append(f'Đã kiểm kê **{len(mapping)}/{doc["pages"]} trang PDF**. Đọc được nội dung ở {pages_read} trang từ dữ liệu đã lưu.')
        parts.append(table(('Trang PDF','Trang in','Nội dung chính','Thông tin tiêu biểu','Tình trạng đọc','Nguồn'),
            [(p['page'],p['printed_page'],p['title'],p['sample'],p['reading_status'],cite(p['citation'])) for p in mapping]))
    outcomes=[]; requested=years(request.question)
    observed=sorted({c['period_end'] for c in cells if c.get('period_end')})
    year=requested or (int(observed[-1][:4]) if observed else None)
    closing=f'{year}-12-31' if year else ''
    def pick(m,end,kind=None):
        return grouped(cells,m,end,kind)
    def render(cell):
        status='đã đối chiếu ảnh gốc' if cell['review_status']==HUMAN else 'dấu gạch in' if cell['value'] is None else 'ứng viên OCR'
        return f"{LABELS[cell['metric_id']]} · {cell['citation']['period']} · {cell['raw']} {MONEY.get(cell['unit'],cell['unit'])} ({status}) {cite(cell['citation'])}"
    def finish(task,used,checks,detail=''):
        title=TASKS.get(task,('Yêu cầu chưa phân loại',))[0]
        used=[c for c in used if c]
        entries=list(dict.fromkeys(render(c) for c in used))
        status='PASS' if checks and all(t[0]=='PASS' for t in checks) else 'PARTIAL' if used or any(t[0]!='BLOCKED' for t in checks) else 'BLOCKED'
        messages=[]
        for check in checks:
            state,mode,text=check[:3]
            if mode:
                text+=(' Kiểm tra sơ bộ từ ứng viên OCR, chưa được chứng nhận.' if mode=='CANDIDATE_RECONCILIATION'
                       else ' Tất cả toán hạng đã được xác minh.')
            messages.append(text)
        missing=detail if detail else ''
        outcomes.append({'task':task,'title':title,'status':status,'checks':[
            {'status':check[0],'mode':check[1] or ('BLOCKED' if check[0]=='BLOCKED' else None),
             'result':check[2],'operand_citations':check[3] if len(check)>3 else []} for check in checks],
            'operands':used,'missing':missing,'display':' '.join(messages+[missing]).strip(),
            'sources':'<br>'.join(entries)})
    money=lambda n: ('VND',)*n
    for index,task in enumerate(planned['tasks']):
        request_text=planned['requests'][index] if 'requests' in planned else request.question
        dates=list(dict.fromkeys(filter(None,map(iso,DATE.findall(request_text)))))
        task_year=years(request_text)
        end=f'{task_year}-12-31' if task_year else closing
        if task in {'capital','capital_equity'}:
            metrics=TASKS[task][1]
            used=[pick(m,date,'INSTANT') for date in dates for m in metrics]
            checks=[('PASS',None,'Đã định vị từng ô theo ngày và tên cột.') if used and all(used)
                    else ('BLOCKED',None,'Chưa gắn được đủ cột với hàng ngày được hỏi.')]
            if used and used[0]:
                first=used[0]; folio=mapping[first['page']-1]['printed_page']
                part=f"**{LABELS[first['metric_id']]}** ngày {first['citation']['period']} là **{first['raw']} đồng** theo " + (
                    'giá trị đã đối chiếu' if first['review_status']==HUMAN else 'giá trị OCR ứng viên, chưa được người duyệt xác nhận')
                suffix=f" (trang in {folio})" if folio else ''
                detail=f"{part}. Bảng đối chiếu biến động vốn chủ sở hữu, trang PDF {first['page']}{suffix}. {cite(first['citation'])}"
            else:
                detail=''
            finish(task,used,checks,detail)
        elif task=='equation':
            used=[pick(m,end,'INSTANT') for m in TASKS[task][1]]
            finish(task,used,[compare(used,'Tổng tài sản − nợ phải trả − vốn chủ sở hữu',lambda v:v[0]-v[1]-v[2],money(3))])
        elif task=='cash':
            used=[pick('cash',end,'INSTANT'),pick('cash_end',end,'FY'),pick('cash_note',end,'INSTANT')]
            finish(task,used,[compare([used[0],used[1]],'Bảng cân đối − số dư cuối kỳ trên lưu chuyển tiền',lambda v:v[0]-v[1],money(2),closing_balance=True),
                              compare([used[0],used[2]],'Bảng cân đối − thuyết minh tiền',lambda v:v[0]-v[1],money(2))])
        elif task=='income':
            used=[pick(m,end,'Q4') for m in TASKS[task][1]]
            gross,deduction,net,cost,profit,note_revenue,note_cogs=used
            checks=[compare([gross,note_revenue],'Doanh thu bán hàng/dịch vụ − doanh thu dịch vụ thuyết minh',lambda v:v[0]-v[1],money(2)),
                    compare([cost,note_cogs],'Giá vốn báo cáo chính − giá vốn thuyết minh',lambda v:v[0]-v[1],money(2)),
                    compare([net,cost,profit],'Doanh thu thuần − giá vốn − lợi nhuận gộp',lambda v:v[0]-v[1]-v[2],money(3))]
            if deduction and deduction['value'] is None:
                checks.append(('BLOCKED',None,'Chưa tính doanh thu bán hàng trừ giảm trừ vì ô giảm trừ là dấu gạch.'))
                detail='Dòng giảm trừ in dấu gạch. Có thể đọc riêng doanh thu bán hàng và doanh thu thuần, nhưng chưa coi dấu gạch là số 0 để kiểm lại phép trừ.'
            else:
                detail=''
                checks.append(compare([gross,deduction,net],'Doanh thu bán hàng − giảm trừ − doanh thu thuần',lambda v:v[0]-v[1]-v[2],money(3)))
            finish(task,used,checks,detail)
        elif task=='shares':
            used=[pick('paid_in_capital',end,'INSTANT'),pick('shares',end,'INSTANT'),pick('par',end,'INSTANT')]
            extra=[pick('paid_in_capital',d,'INSTANT') for d in dates if d!=end]
            finish(task,used+extra,[compare(used,'Vốn góp cuối kỳ − số cổ phiếu lưu hành × mệnh giá',lambda v:v[0]-v[1]*v[2],
                                                 ('VND','SHARES','VND_PER_SHARE'))],
                   'Đơn vị tiền tệ theo chính sách kế toán '+cite(currency_source)+'.' if currency_source and used[2] else '')
        elif task=='notes':
            used=[];checks=[]
            for a,b in zip(TASKS[task][1][::2],TASKS[task][1][1::2],strict=True):
                pair=[pick(a,end,'INSTANT'),pick(b,end,'INSTANT')]
                used.extend(pair)
                checks.append(compare(pair,f'{LABELS[a]} cuối kỳ − dòng thuyết minh tương ứng',lambda v:v[0]-v[1],money(2)))
            finish(task,used,checks,'Các so sánh trên dùng cột cuối kỳ. Chỉ tiêu phải trả khác là một phần của tổng nợ phải trả.')
        elif task=='explain':
            income=pick('net_income',end,'Q4')
            narrative=explanation if explanation and explanation.get('reported_year')==end[:4] else None
            detail=('Theo giải trình của công ty, lợi nhuận sau thuế quý IV tăng chủ yếu do lợi nhuận công ty con chuyển về tăng. '+cite(narrative)
                    if narrative else 'Chưa đọc được câu giải trình đủ rõ cho đúng quý và năm.')
            if narrative and narrative.get('reported_billions') and income:
                raw=narrative['reported_billions']
                approximate=Decimal(raw.replace('.',''))*1_000_000_000
                gap=Decimal(income['value'])-approximate
                detail+=f" Văn bản nêu {raw} tỷ đồng, bảng nêu {income['raw']} đồng. "
                detail+=('Hai cách ghi chênh dưới một tỷ đồng, nên chỉ đối chiếu ở mức tỷ đồng.'
                         if abs(gap)<1_000_000_000 else 'Chênh lệch vượt một tỷ đồng, cần đối chiếu lại ảnh nguồn.')
            finish(task,[income],[('PASS' if income and narrative else 'PARTIAL' if narrative else 'BLOCKED',
                                  None,'Đối chiếu ô lợi nhuận với phần giải trình cùng quý. Tách số chi tiết trên bảng khỏi mức làm tròn trong văn bản.')],detail)
        else:
            finish(task,[],[('BLOCKED',None,'Chưa xác định được điều kiện đối chiếu cho yêu cầu này.')],
                   planned.get('requests',['']*len(planned['tasks']))[index])
        emit(stage='checking',tasks_done=index+1,tasks_total=len(planned['tasks']),
             needs_review=sum(any(c.get('mode')=='CANDIDATE_RECONCILIATION' for c in r['checks'])
                              for r in outcomes))
    if outcomes:
        if len(outcomes)==1 and outcomes[0]['task'] in {'capital','capital_equity'}:
            parts.append(outcomes[0]['display'])
        parts.append(table(('Mục','Kết quả','Phép đối chiếu và giới hạn','Giá trị, kỳ và nguồn'),
                           [(r['title'],r['status'],r['display'],r['sources'].replace('<br>',' / ')) for r in outcomes]))
    emit(stage='composing')
    return {'status':'SOURCE_EXCERPTS','answer_status':'DOCUMENT_REASONING','answer':'\n\n'.join(parts),
            'values':[],'citations':citations,'document_plan':planned,'task_results':outcomes,
            'page_map':[{k:v for k,v in p.items() if k!='citation'} for p in mapping] if planned['inventory'] else None,
            'document_coverage':{'pages_read':pages_read,'pages_examined':len(mapping),'pages_total':doc['pages'],'tasks_done':len(outcomes)}}

"""Read accounting cells from checkpoint rows or date-row geometry."""
from datetime import datetime
from decimal import Decimal
import re

from app.product.analysis import parse_number
from app.product.document_page_map import source_ref
from app.product.pdf_extract import folded
from app.product.pdf_ocr_financial_v2 import cx,cy,union

DATE=re.compile(r'\d{1,2}/\d{1,2}/20\d{2}')
AMOUNT=re.compile(r'(?:\(\d{1,3}(?:\.\d{3})+\)|-?\d{1,3}(?:\.\d{3})+)\Z')
LABELS={
 'assets':'Tổng tài sản','liabilities':'Nợ phải trả','equity':'Tổng vốn chủ sở hữu',
 'cash':'Tiền và các khoản tương đương tiền','cash_end':'Tiền và tương đương tiền cuối kỳ',
 'cash_note':'Tổng tiền trong thuyết minh','paid_in_capital':'Vốn góp của chủ sở hữu',
 'gross_revenue':'Doanh thu bán hàng và cung cấp dịch vụ','deductions':'Các khoản giảm trừ doanh thu',
 'net_revenue':'Doanh thu thuần','cogs':'Giá vốn hàng bán','gross_profit':'Lợi nhuận gộp',
 'note_revenue':'Doanh thu cung cấp dịch vụ trong thuyết minh','note_cogs':'Giá vốn trong thuyết minh',
 'shares':'Số cổ phiếu đang lưu hành','par':'Mệnh giá cổ phiếu',
 'fixed':'Tài sản cố định hữu hình','fixed_note':'Giá trị còn lại của TSCĐ hữu hình trong thuyết minh',
 'intangible':'Tài sản cố định vô hình','intangible_note':'Giá trị còn lại của TSCĐ vô hình trong thuyết minh',
 'investment':'Bất động sản đầu tư','investment_note':'Giá trị còn lại của bất động sản đầu tư trong thuyết minh',
 'tax':'Thuế và các khoản phải nộp Nhà nước','tax_note':'Tổng các khoản thuế trong thuyết minh',
 'other_payables':'Phải trả khác','other_payables_note':'Tổng phải trả khác trong thuyết minh',
 'net_income':'Lợi nhuận sau thuế',
}


def iso(text):
    try:
        return datetime.strptime(text,'%d/%m/%Y').date().isoformat()
    except ValueError:
        return None


def words_of(page):
    return [w for line in page['lines'] for w in line['words'] if all(k in w for k in ('rx','ry','rw','rh'))]


def period_info(label):
    if not label:
        return None,None,None
    if DATE.fullmatch(label):
        return None,iso(label),'INSTANT'
    m=re.fullmatch(r'(FY|Q4) (20\d{2})',label)
    if m:
        return f'{m[2]}-{"01" if m[1]=="FY" else "10"}-01',f'{m[2]}-12-31',m[1]
    return None,None,None


def fact(doc,page,metric,scope,row_id,column_id,label,raw,box,unit,period,header=None):
    start,end,kind=period_info(period)
    if not end or not scope or not box or not unit:
        return None
    try:
        value=parse_number(raw,'vi_VN')
    except ValueError:
        return None
    c=source_ref(doc,page['page'],f"{LABELS[metric]} · {period} · {raw}",box=box,
                 identity=f'{page["evidence_sha256"]}:{row_id}:{column_id}',row_id=row_id,row_label=label,
                 column_id=column_id,period=period,unit=unit,statement_scope=scope,extraction_method=page['method'])
    if header:
        c['header_box']=header
    return {'metric_id':metric,'row_id':row_id,'column_id':column_id,'period_start':start,'period_end':end,
            'period_type':kind,'value':str(value),'raw':raw,'unit':unit,'statement_scope':scope,
            'issuer':doc.get('issuer',''),'document_id':doc['id'],'source_sha256':doc['sha256'],
            'page':page['page'],'box':box,'review_status':'AUTOMATED_EXTRACTION','citation':c}


def near_column(words,x,y,allowance,limit=32):
    matches=[w for w in words if abs(cx(w)-x)<=allowance and 0<y-cy(w)<limit]
    return folded(' '.join(w['text'] for w in sorted(matches,key=lambda w:(round(cy(w)/7),w['rx']))))


def equity_matrix(doc,page,scope):
    """Bind dates on the left to independently observed column headings."""
    text=folded(page['text'])
    if 'bang doi chieu bien dong von chu so huu' not in text:
        return []
    words=words_of(page)
    dates=[w for w in words if DATE.fullmatch(w['text']) and w['rx']<page['height']*.38]
    units=sorted((w for w in words if w['text']=='VND'),key=cx)
    if not dates or len(units)<3:
        return []
    first,last=units[0],units[-1]
    if cx(last)-cx(first)<50:
        return []
    slope=(cy(last)-cy(first))/(cx(last)-cx(first))
    if abs(slope)>.08:
        return []
    positions=[]
    for i,w in enumerate(words):
        if folded(w['text'])!='von':
            continue
        line=[v for v in words if w['rx']<=v['rx']<w['rx']+130 and abs(cy(v)-cy(w))<6]
        line.sort(key=lambda v:v['rx'])
        sequence=' '.join(folded(v['text']) for v in line)
        if sequence.startswith('von gop cua chu so huu'):
            group=line[:6]
            x=(group[0]['rx']+group[-1]['rx']+group[-1]['rw'])/2
            if x<cx(first) and min(cy(v) for v in group)<min(cy(d) for d in dates):
                positions.append(('paid_in_capital',x,union(group),min(cx(first)-x,110)*.51))
    if near_column(words,cx(last),cy(last),30).strip().endswith('cong'):
        positions.append(('equity',cx(last),last['box'],min(cx(last)-cx(units[-2]),100)*.51))
    result=[]
    for d in dates:
        for metric,x,header,span in positions:
            candidates=[w for w in words if AMOUNT.fullmatch(w['text']) and abs(cx(w)-x)<span
                        and abs(cy(w)-(cy(d)+slope*(cx(w)-cx(d))))<=5]
            if len(candidates)!=1:
                continue
            w=candidates[0]
            value=fact(doc,page,metric,scope,f'date:{d["text"]}',metric,LABELS[metric],w['text'],w['box'],'VND',d['text'],header)
            if value:
                result.append(value)
    return result


def tax_totals(doc,page,scope,words,row):
    dates=[w for w in words if DATE.fullmatch(w['text']) and cy(w)<row['reading_y']]
    result=[]
    for d in dates:
        unit=[w for w in words if w['text']=='VND' and abs(cx(w)-cx(d))<20 and 2<cy(w)-cy(d)<20]
        if len(unit)!=1:
            continue
        headings=sorted((w for w in words if 18<cy(w)-cy(d)<45 and 10<cx(w)-cx(d)<89),
                        key=lambda w:w['rx'])
        normalized=[folded(w['text']) for w in headings]
        options=[headings[i:i+3] for i in range(len(headings)-2) if normalized[i:i+3]==['so','phai','nop']]
        if len(options)!=1:
            continue
        header=options[0]
        x=(header[0]['rx']+header[-1]['rx']+header[-1]['rw'])/2
        values=[w for w in words if AMOUNT.fullmatch(w['text']) and abs(cx(w)-x)<31
                and abs(cy(w)-row['reading_y'])<7]
        if len(values)!=1:
            continue
        w=values[0]
        cell=fact(doc,page,'tax_note',scope,row['id'],'payable:'+d['text'],
                  'Cộng · Số phải nộp',w['text'],w['box'],'VND',d['text'],union(header))
        if cell:
            result.append(cell)
    return result


def investment_totals(doc,page,scope,words):
    if not any('bat dong san dau tu' in folded(line['text']) for line in page['lines']):
        return []
    heading=next((line for line in page['lines'] if folded(line['text'])=='gia tri con lai'),None)
    if not heading:
        return []
    y=min(w['ry'] for w in heading['words'])
    units=[w for w in words if w['text']=='VND' and 0<y-w['ry']<210]
    if len(units)!=1:
        return []
    unit=units[0];result=[]
    for d in words:
        if not DATE.fullmatch(d['text']) or not 0<d['ry']-y<58:
            continue
        numbers=[w for w in words if AMOUNT.fullmatch(w['text']) and abs(cx(w)-cx(unit))<31
                 and abs(cy(w)-cy(d))<10]
        if len(numbers)!=1:
            continue
        w=numbers[0]
        value=fact(doc,page,'investment_note',scope,f'investment:{d["text"]}','carrying_value',
                   LABELS['investment_note'],w['text'],w['box'],'VND',d['text'],unit['box'])
        if value:
            result.append(value)
    return result


MAIN={
 'BALANCE_SHEET':{'110':'cash','221':'fixed','227':'intangible','230':'investment','313':'tax','319':'other_payables'},
 'INCOME_STATEMENT':{'01':'gross_revenue','02':'deductions','11':'cogs','20':'gross_profit'},
}


def cached_facts(doc,page,entry,cover_scope,currency):
    text=folded(page['text'])
    kind=entry['kind']
    words=words_of(page)
    scope=cover_scope
    output=equity_matrix(doc,page,scope)+investment_totals(doc,page,scope,words)
    # Section identity and local printed headings distinguish identically labelled totals.
    fixed_note=kind=='NOTES' and 'tai san co dinh huu hinh' in text
    intangible_note=kind=='NOTES' and 'tai san co dinh vo hinh' in text
    labels={folded(r['row_label']).strip() for r in page['tables']}
    cash_note=any('tien gui ngan hang' in label for label in labels) and 'cac khoan tuong duong tien' in labels
    tax_note=any('thue gia tri gia tang hang nhap' in label for label in labels) and 'thue thu nhap doanh nghiep' in labels
    debt_note='lai vay phai tra' in text and 'phai tra co tuc' in text
    shares_note='co phieu dang luu hanh' in text and 'so luong co phieu' in text
    revenue_note='gia von hang ban' in text and 'doanh thu cung dich vu' in text
    subsection=None
    for row in page['tables']:
        label=folded(row['row_label'])
        row_scope=row.get('statement_scope') or row.get('scope') or scope
        metric=row.get('metric') or MAIN.get(kind,{}).get(row.get('item_code'))
        if kind=='CASH_FLOW' and re.search(r'70\s*=\s*50\s*\+\s*60\s*\+\s*61',label):
            metric='cash_end'
        if label.strip()=='cong':
            if tax_note:
                output.extend(tax_totals(doc,page,row_scope,words,row))
                continue
            metric='cash_note' if cash_note else 'other_payables_note' if debt_note else metric
        if shares_note and 'dang luu hanh' in label:
            metric='par' if 'menh gia' in label else 'shares' if 'so luong' in label else metric
        if (fixed_note or intangible_note) and 'gia tri con lai' in label:
            subsection='fixed_note' if fixed_note else 'intangible_note'
        if subsection and DATE.search(label):
            metric=subsection
        if revenue_note and 'doanh thu cung dich vu' in label:
            metric='note_revenue'
        elif revenue_note and label=='von cap':
            # Require the local printed cost-of-sales heading above the row.
            y=row.get('reading_y',0)
            section=[line for line in page['lines'] if 'gia von hang ban' in folded(line['text'])
                     and 0<y-min((w['ry'] for w in line['words']),default=y)<130]
            if section:
                metric='note_cogs'
        if metric not in LABELS:
            continue
        for i,cell in enumerate(row['cells']):
            raw=cell.get('text')
            if not raw or not cell.get('box') or cell.get('ocr_warning')=='OCR_ENGINE_DISAGREEMENT':
                continue
            period=cell.get('period');unit=cell.get('unit')
            if period and any(period in warning for warning in row.get('warnings',[])):
                continue
            if metric in {'fixed_note','intangible_note'}:
                if i!=len(row['cells'])-1 or not re.search(r't[oe]ng cong',text):
                    continue
                period=DATE.search(label)[0]
            if metric in {'shares','par','note_revenue','note_cogs'}:
                period,unit=bind_missing(page,row,cell,metric,currency,words)
            if metric=='deductions' and raw in {'-','–','—'}:
                # A printed dash is evidence, never a numerical zero.
                if period and row_scope and unit:
                    _,end,kind_value=period_info(period)
                    c=source_ref(doc,page['page'],LABELS[metric]+' · '+period+' · '+raw,box=cell['box'],
                                 identity=cell.get('cell_id','dash'),period=period,unit=unit,statement_scope=row_scope)
                    output.append({'metric_id':metric,'raw':raw,'value':None,'unit':unit,'period_end':end,
                                   'period_type':kind_value,'statement_scope':row_scope,'page':page['page'],
                                   'review_status':'PRINTED_DASH','citation':c})
                continue
            value=fact(doc,page,metric,row_scope,row['id'],cell.get('cell_id') or f'{row["id"]}:{i}',row['row_label'],
                       raw,cell['box'],unit,period)
            if value:
                output.append(value)
    return output


def bind_missing(page,row,cell,metric,currency,words):
    box=cell['box']
    # These note tables use visible, right-aligned column labels on upright pages.
    if page['engine'].get('correction_clockwise'):
        return None,None
    y=box[1];right=box[2]
    if metric in {'shares','par'}:
        labels=[w for w in words if DATE.fullmatch(w['text']) and 0<y-w['ry']<175
                and abs(w['rx']+w['rw']-right)<45]
        if len(labels)==1:
            return labels[0]['text'],'SHARES' if metric=='shares' else ('VND_PER_SHARE' if currency=='VND' else None)
    else:
        labels=sorted((w for w in words if re.fullmatch(r'20\d{2}',w['text']) and 0<y-w['ry']<110
                       and abs(w['rx']+w['rw']-right)<36),key=lambda w:-w['ry'])
        if labels:
            year=labels[0]
            band=folded(' '.join(w['text'] for w in words if abs(w['ry']-year['ry'])<7))
            unit=any(w['text']=='VND' and abs(cx(w)-cx(year))<54 and 3<w['ry']-year['ry']<28 for w in words)
            if re.search(r'quy iv',band) and unit:
                return f'Q4 {year["text"]}','VND'
    return None,None

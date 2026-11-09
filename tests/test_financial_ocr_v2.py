from app.product.ocr_candidate_answer import eligible_candidate
from app.product.pdf_document_comparison import _legacy_statement_page
from app.product.pdf_ocr_financial_v2 import arithmetic_warnings, reconstruct


def word(text, x, y, width=23):
    return {'text':text,'rx':x,'ry':y,'rw':width,'rh':8,'box':[x,y,x+width,y+8],'confidence':90}


def test_financial_layout_preserves_period_sign_and_coordinate():
    words=[word('31/12/2025',285,100,47),word('01/01/2025',385,100,47),
           word('VND',300,116),word('VND',400,116),
           word('Tài sản',45,148,40),word('100',230,150),word('20.000',305,149,34),word('19.000',405,150,34),
           word('Điều chỉnh',45,172,50),word('200',230,172),word('(5.000)',302,172,36),word('6.000',405,172,34),
           word('Điện thoại',45,480,55),word('024-222-5555',305,480,80)]
    rows=reconstruct(words,3,'SEPARATE')
    assert [r['item_code'] for r in rows]==['100','200']
    assert [c['period'] for c in rows[1]['cells']]==['31/12/2025','01/01/2025']
    assert rows[1]['cells'][0]['text']=='(5.000)'
    assert rows[1]['cells'][0]['box']==[302,172,338,180]
    assert rows[1]['cells'][0]['verification']=='OCR_UNVERIFIED'


def test_printed_formula_only_creates_warning():
    def row(code,label,text):
        return {'item_code':code,'row_label':label,'cells':[{'text':text,'period':'FY 2025','unit':'VND'}]}
    rows=[row('01','Doanh thu','8.000'),row('02','Giảm trừ','1.000'),
          row('10','Doanh thu thuần (10 = 01 - 02)','6.000')]
    marked=arithmetic_warnings(rows)
    assert marked[2]['warnings']
    assert marked[2]['cells'][0]['text']=='6.000'
    assert 'warnings' not in rows[2]


def test_comparison_recovers_rotated_legacy_quarter_with_joined_year():
    words = [
        word('Quý', 267, 100, 16), word('IV', 286, 100, 10), word('năm2023', 299, 100, 42),
        word('Năm', 367, 100, 23), word('2023', 393, 100, 24),
        word('VND', 300, 116), word('VND', 400, 116),
        word('Doanh thu', 45, 149, 55), word('01', 230, 149),
        word('19.000', 305, 149, 34), word('57.000', 405, 149, 34),
        word('Lợi nhuận sau thuế', 45, 172, 112), word('60', 230, 172),
        word('5.000', 305, 172, 34), word('15.000', 405, 172, 34),
    ]
    for token in words:
        width = token.pop('rw')
        token['box'] = [token['ry'], 800 - token['rx'] - width, token['ry'] + 8, 800 - token['rx']]
    page = {'page': 8, 'method': 'OCR', 'engine': {'correction_clockwise': 90},
            'text': 'Báo cáo kết quả hoạt động kinh doanh',
            'lines': [{'words': words}], 'tables': []}
    view = _legacy_statement_page(page, 'SEPARATE')
    profit = next(row for row in view['tables'] if row['metric'] == 'net_income')
    current, annual = profit['cells']
    assert (current['period_type'], current['numeric_value']) == ('3M_Q4', '5000')
    assert (annual['period_type'], annual['numeric_value']) == ('FY', '15000')
    assert eligible_candidate(profit, current)
    assert current['review_status'] == 'AUTOMATED_EXTRACTION'
    assert current['box'] == words[-2]['box']
    assert not page['tables']

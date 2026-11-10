from types import SimpleNamespace

from app.product.document_financial_cells import period_info
from app.product.document_page_map import printed_folio
from app.product.document_reasoning import compare, plan
from app.product.document_progress import get, update


def test_inventory_keeps_capital_followup_and_plans_six_separate_tasks():
    assert plan('Kiểm kê toàn bộ 24 trang. Tìm vốn góp tại 01/01/2024.')=={
        'inventory':True,'tasks':['capital']}
    q=('1. Tổng tài sản với nợ phải trả và vốn chủ sở hữu.\n'
       '2. Tiền và tương đương tiền ở báo cáo lưu chuyển.\n'
       '3. Doanh thu thuần và giá vốn.\n'
       '4. Vốn góp, số cổ phiếu và mệnh giá.\n'
       '5. Đối chiếu tài sản cố định trong thuyết minh.\n'
       '6. Giải trình nguyên nhân lợi nhuận tăng.')
    assert plan(q)['tasks']==['equation','cash','income','shares','notes','explain']


def test_candidate_reconciliation_never_uses_dash_or_incompatible_period():
    common={'value':'10','source_sha256':'sha','statement_scope':'SEPARATE','period_end':'2025-12-31',
            'period_start':None,'period_type':'INSTANT','unit':'VND','review_status':'AUTOMATED_EXTRACTION',
            'citation':{'citation_id':'a'}}
    result=compare([common,{**common,'citation':{'citation_id':'b'}}],'difference',lambda v:v[0]-v[1],('VND','VND'))
    assert result[:2]==('PASS','CANDIDATE_RECONCILIATION')
    assert result[3]==['a','b']
    for invalid in ({**common,'value':None},{**common,'period_type':'FY'},{**common,'statement_scope':'CONSOLIDATED'}):
        assert compare([common,invalid],'difference',lambda v:v[0]-v[1],('VND','VND'))[0]=='BLOCKED'


def test_missing_checkpoint_gets_its_own_page_map_row():
    from app.product.document_page_map import document_map
    doc={'id':'doc','sha256':'sha','filename':'x.pdf','pages':2}
    w=SimpleNamespace(iter_document_evidence=lambda *_:iter([(1,None,'missing'),(2,None,'missing')]))
    result=document_map(w,doc)
    assert [p['citation']['page'] for p in result['pages']]==[1,2]
    assert all(p['printed_page'] is None for p in result['pages'])


def test_folio_comes_from_visible_high_confidence_number_not_page_offset():
    word={'text':'19','ry':545,'rx':740,'confidence':97,'box':[1,2,3,4]}
    page={'page':25,'width':595,'height':842,'engine':{'correction_clockwise':90},'lines':[{'words':[word]}]}
    assert printed_folio(page)==(19,word['box'])
    assert printed_folio({**page,'lines':[{'words':[{**word,'confidence':40}]}]})==(None,None)


def test_dates_are_not_derived_from_report_year():
    assert period_info('01/01/2024')==(None,'2024-01-01','INSTANT')
    assert period_info('Q4 2025')==('2025-10-01','2025-12-31','Q4')


def test_progress_is_isolated_and_reports_observed_counts_only():
    update('one','id',stage='reading',pages_read=4,pages_total=24)
    update('one','id',stage='checking',tasks_done=1)
    assert get('one','id')['pages_read']==4
    assert get('one','id')['tasks_done']==1
    assert get('two','id')=={}

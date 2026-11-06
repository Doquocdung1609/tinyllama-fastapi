from types import SimpleNamespace

import pytest
from PIL import Image, ImageDraw

from app.product import ocr_reviewed_answer as dialogue, pdf_ocr_financial_v3 as ocr
from app.product.analysis import FactReview, review_fact


def test_statement_total_uses_printed_relationship_without_assuming_row_code():
    row={'item_code':'299','row_label':'TỒN SANG EALSAN (299 = 100 + 200)'}
    assert ocr.metric_for(row,'BALANCE_SHEET')=='assets'
    assert ocr.metric_for(row,'NOTES') is None
    assert ocr.metric_for({**row,'item_code':'270'},'BALANCE_SHEET') is None


def test_crop_does_not_replace_a_digit_on_lone_paddle_vote():
    one=[{'engine':'PP-OCRv6_small','raw':'18.700'}]
    assert ocr.select_candidate('18.100',one)==('18.100',ocr.AUTOMATED,'OCR_ENGINE_DISAGREEMENT')
    reads=[*one,{'engine':'Tesseract','raw':'18.700'}]
    assert ocr.select_candidate('18.100',reads)==('18.700',ocr.CROSSCHECKED,'REREAD_DIFFERS_FROM_BASELINE')


@pytest.mark.parametrize('shape,state',[('dash','PRINTED_DASH'),('empty','EMPTY_CELL'),('unresolved','OCR_NOT_DETECTED')])
def test_image_marker_distinguishes_a_stroke_from_no_content(monkeypatch,shape,state):
    image=Image.new('L',(116,70),255)
    draw=ImageDraw.Draw(image)
    if shape=='dash':draw.rectangle((50,30,62,34),fill=50)
    if shape=='unresolved':draw.rectangle((50,30,62,50),fill=50)
    monkeypatch.setattr(ocr,'crop',lambda *_:image)
    marker,box=ocr.detect_marker(None,{'period':'31/12/2025 Dự phòng','column_right_anchor':380},
                                {'reading_y':200},0,600,800)
    assert marker==state
    if shape=='dash':
        assert box[2]-box[0] < 3


@pytest.mark.parametrize('year',('2025','2024'))
def test_quarter_and_full_year_have_distinct_source_durations(year):
    assert ocr.periods(f'Q4 {year}','INCOME_STATEMENT')==(f'{year}-10-01',f'{year}-12-31','3M_Q4')
    assert ocr.periods(f'FY {year}','INCOME_STATEMENT')==(f'{year}-01-01',f'{year}-12-31','FY')
    assert ocr.periods(f'FY {year}','BALANCE_SHEET')==(None,None,None)


def test_review_rejects_a_different_metric_and_period_start():
    row={'id':'row','metric':'net_revenue','cells':[{'review_status':ocr.AUTOMATED,
        'period_start':'2025-10-01','period_end':'2025-12-31','column_label':'Quý IV năm 2025'}]}
    workspace=SimpleNamespace(page_evidence=lambda *_:{'tables':[row]})
    review=FactReview(page=5,row_id='row',column_index=0,metric='assets',period='2025-12-31',
        column_label='Quý IV năm 2025',statement_scope='SEPARATE',unit='VND',convention='vi_VN',
        source_image_reviewed=True)
    with pytest.raises(ValueError,match='SOURCE_METRIC_MISMATCH'):
        review_fact(workspace,'doc',review)
    with pytest.raises(ValueError,match='SOURCE_PERIOD_MISMATCH'):
        review_fact(workspace,'doc',review.model_copy(update={'metric':'net_revenue','period_start':'2025-01-01'}))


def test_dual_period_chat_requires_both_separately_reviewed_cells(monkeypatch):
    from app.product import analysis
    base={'id':'base','period':'2025-12-31','metric':'net_revenue','statement_scope':'SEPARATE','basis':'AS_REPORTED',
          'value':'1500','source_display':'1.500','unit':'VND','row_label':'Doanh thu thuần',
          'page':5,'document_id':'doc','source_sha256':'sha','column_label':'Năm 2025','box':[0,0,4,5]}
    facts=[{**base,'review_status':ocr.HUMAN,'period_type':'FY'},
           {**base,'id':'quarter','review_status':ocr.CROSSCHECKED,'period_type':'3M_Q4','value':'400'}]
    monkeypatch.setattr(analysis,'eligible_facts',lambda *_:facts)
    workspace=SimpleNamespace(document=lambda _:{'sha256':'sha','pages':5},source_file=lambda _:None)
    request=analysis.AnalysisRequest(question='Doanh thu thuần quý IV/2025 và cả năm 2025 là bao nhiêu?',document_ids=['doc'])
    assert dialogue.answer(workspace,request) is None
    facts[1]['review_status']=ocr.HUMAN
    result=dialogue.answer(workspace,request)
    assert result['values']==['400','1500']
    assert [c['id'] for c in result['citations']]==['quarter','base']


def test_ocr_locator_verification_accepts_source_box_and_rejects_tampering():
    from hashlib import sha256
    from app.product.independent_verifier_v2 import verify_plan

    parent=sha256(b'sha:3:row:checkpoint').hexdigest()[:24]
    locator=sha256(f'{parent}:cell'.encode()).hexdigest()[:24]
    box=[1,2,3,4]
    evidence={'version':ocr.VERSION,'evidence_sha256':'checkpoint','tables':[{'id':'row','cells':[
        {'cell_id':'cell','box':box,'source_sha256':'sha'}]}]}
    workspace=SimpleNamespace(document=lambda _:{'sha256':'sha','pages':3},
                              page_evidence=lambda *_:evidence,source_file=lambda _:None)
    citation={'citation_id':locator,'document_id':'doc','source_sha256':'sha','page':3,
              'row_id':'row','column_id':'cell','box':box,'numeric_status':'UNVERIFIED'}
    plan=SimpleNamespace(citations=[citation],operands=[],claims=[],calculations=[])
    assert verify_plan(workspace,plan)['status']=='SOURCE_SUPPORTED_NON_NUMERIC'
    citation['box']=[0,0,3,4]
    assert verify_plan(workspace,plan)['reason']=='OCR_CANDIDATE_LOCATOR_FORGED'


def test_zero_requires_a_source_token_in_the_bound_column():
    word={'text':'0','rx':364,'ry':196,'rw':5,'rh':8,'box':[364,196,369,204]}
    cell={'binding_status':'GEOMETRIC_CANDIDATE','column_right_anchor':371}
    assert ocr.recognized_zero([word],cell,200)==word
    assert ocr.recognized_zero([word],cell,225) is None
    assert ocr.recognized_zero([word],{**cell,'binding_status':'AMBIGUOUS'},200) is None


def test_year_end_from_printed_accounting_interval():
    from app.product.analysis import source_calendar

    pages={5:{'text':'Quý IV năm 2025 · Năm 2025', 'evidence_sha256':'5'},
           6:{'text':'Giai đoạn từ ngày 01/01/2025 đến ngày 31/12/2025', 'evidence_sha256':'6'}}
    workspace=SimpleNamespace(document=lambda _:{'pages':6},
                              page_evidence=lambda _,p:pages.get(p,{'text':''}))
    assert source_calendar(workspace,'doc',5,'2025')=={'page':6,'evidence_sha256':'6'}
    assert source_calendar(workspace,'doc',5,'2024') is None

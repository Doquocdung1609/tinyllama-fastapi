"""Independent original-byte verification and adversarial claim binding."""
from copy import deepcopy
from decimal import Decimal
from hashlib import sha256
import pymupdf
import pytest
from app.product.source_cells_v2 import native_catalog,cell_id
from app.product.independent_verifier_v2 import verify_operand,recompute,verify_plan,verify_rendered_numerals,AnswerPlan,Claim
from app.product.answer_planner_v2 import plan_question,resolve_followup

@pytest.fixture
def cells(tmp_path):
    pdf=pymupdf.open();page=pdf.new_page()
    page.insert_text((40,40),'Net sales and gross margins as expressed in U.S. dollars')
    page.insert_text((40,65),'CONSOLIDATED STATEMENTS OF OPERATIONS')
    page.insert_text((40,85),'USD in millions')
    page.insert_text((280,105),'September 27, 2025')
    page.insert_text((410,105),'September 28, 2024')
    page.insert_text((300,125),'2025');page.insert_text((430,125),'2024')
    for y,label,a,b in [(155,'Total net sales','125','100'),(180,'Net income','(12)','10')]:
        page.insert_text((40,y),label);page.insert_text((300,y),a);page.insert_text((430,y),b)
    path=tmp_path/'native.pdf';pdf.save(path);pdf.close();digest=sha256(path.read_bytes()).hexdigest()
    class W:
        def document(self,_):return {'id':'d','sha256':digest,'filename':'native.pdf','pages':1}
        def source_file(self,_):return path
    w=W();records=native_catalog(w,['d'])
    for c in records:c['operand_id']=c['citation_id']
    return w,records

def select(records,year='2025',metric='net_revenue'):
    return deepcopy(next(c for c in records if c['period']==year and c['metric']==metric))

def test_actual_original_native_negative_and_growth(cells):
    w,records=cells;a=verify_operand(w,select(records));b=verify_operand(w,select(records,'2024'))
    assert recompute('PERCENT_CHANGE',[a,b])=='25.00'
    assert verify_operand(w,select(records,metric='net_income'))['value']=='-12'

@pytest.mark.parametrize('change',[{'value_raw':'(125)'},{'value_raw':'126'},{'metric':'net_income'},{'period':'2024'},{'statement_scope':'SEPARATE'},
    {'currency':'VND'},{'scale':'1'},{'unit':'VND'},{'extraction_method':'OCR'},{'period_end':'2025-12-31'},
    {'period_type':'3M_Q4'},{'source_sha256':'0'*64},{'row_label':'Net income'},{'value':'999'},
    {'box':[0,0,1,1]},{'header_box':[0,0,1,1]}])
def test_tampered_operand_rejected_even_with_rehashed_citation(cells,change):
    w,records=cells;c=select(records);c.update(change);c['citation_id']=cell_id(c)
    with pytest.raises(ValueError):verify_operand(w,c)

def bundle(w,records):
    a=select(records);b=select(records,'2024')
    return AnswerPlan(plan_question('total net sales growth fiscal 2024 to 2025?').public(),
        [Claim('c','NUMERIC',[a['citation_id'],b['citation_id']],'CONSOLIDATED',['2024','2025'],'PENDING',value='25.00',calculation_id='calc',operand_ids=[a['operand_id'],b['operand_id']])],
        [a,b],[a,b],[{'calculation_id':'calc','operation':'PERCENT_CHANGE','operand_ids':[a['operand_id'],b['operand_id']],'proposed_result':'25.00','result_unit':'%'}])

def test_independent_claim_gate_and_rendered_numerals(cells):
    w,records=cells;p=bundle(w,records);assert verify_plan(w,p)['status']=='VERIFIED'
    assert verify_rendered_numerals('FY2025 growth 25.00% [1][2]',p)
    assert not verify_rendered_numerals('Growth 99.99% [1]',p)

@pytest.mark.parametrize('kind',['result','claim_operands','claim_scope','question_year','question_scope','question_currency','question_quarter','direction','citation'])
def test_forged_claim_graph_rejected(cells,kind):
    w,records=cells;p=bundle(w,records)
    if kind=='result':p.calculations[0]['proposed_result']='999';p.claims[0].value='999'
    elif kind=='claim_operands':p.claims[0].operand_ids.reverse();p.claims[0].source_refs.reverse()
    elif kind=='claim_scope':p.claims[0].source_scope='SEPARATE'
    elif kind=='question_year':p.question_plan['years']=['2023']
    elif kind=='question_scope':p.question_plan['scope']='SEPARATE'
    elif kind=='question_currency':p.question_plan['requested_unit']='VND'
    elif kind=='question_quarter':p.question_plan['period_type']='3M_Q4'
    elif kind=='direction':
        p.calculations[0]['operand_ids'].reverse();p.claims[0].operand_ids.reverse();p.calculations[0]['proposed_result']='-20.00';p.claims[0].value='-20.00'
    elif kind=='citation':p.citations[0]['citation_id']='forged'
    assert verify_plan(w,p)['status']=='REJECTED'

def test_followup_only_uses_supplied_scope_history():
    h=[{'question':'Apple total net sales FY2025?','response':{'conversation_slots':plan_question('Apple total net sales FY2025?').public()}}]
    resolved,p=resolve_followup('And in FY2024? How much did it grow in dollars and percent?',h)
    assert p.metric=='net_revenue' and p.years==['2024','2025'] and p.operation=='CHANGE_AND_GROWTH'
    assert resolve_followup('And in FY2024?',[])[1].metric is None
    assert plan_question('Lợi nhuận sau thuế chưa phân phối riêng năm 2024?').period_type=='INSTANT'


def test_requested_currency_scale_is_bound_to_claim(cells):
    w,records=cells;a=select(records)
    p=AnswerPlan(plan_question('total net sales FY2025 in USD?').public(),
        [Claim('c','NUMERIC',[a['citation_id']],'CONSOLIDATED',['2025'],'PENDING',value='125',calculation_id='calc',operand_ids=[a['operand_id']])],
        [a],[a],[{'calculation_id':'calc','operation':'EXTRACT','operand_ids':[a['operand_id']],'proposed_result':'125','result_unit':'MILLION_USD'}])
    assert verify_plan(w,p)['status']=='REJECTED'


def test_restatement_identity_planner_and_zero_guard(cells):
    assert plan_question('Kiểm tra lợi nhuận sau thuế chưa phân phối riêng năm 2024: đã công bố cộng điều chỉnh bằng trình bày lại?').operation=='RESTATEMENT_IDENTITY'
    w,records=cells;a=verify_operand(w,select(records));b=verify_operand(w,select(records,'2024'));b['value']='0'
    with pytest.raises(ValueError,match='ZERO_DENOMINATOR'):recompute('PERCENT_CHANGE',[a,b])

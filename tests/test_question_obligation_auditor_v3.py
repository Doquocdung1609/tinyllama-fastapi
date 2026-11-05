"""Adversarial under-planning tests: raw utterance is a separate audit input."""
from decimal import Decimal
import pytest
from app.product.question_obligation_auditor import audit
from app.product.answer_planner_v2 import plan_question
from app.product.independent_verifier_v2 import recompute

def test_underplanned_relative_comparison_cannot_be_complete():
    raw='Services FY2025 cao hơn Products bao nhiêu điểm phần trăm và phần trăm tương đối?'
    outputs=[{'status':'VERIFIED','numeric_verification':'VERIFIED','calculation_operations':['PERCENTAGE_POINT_DIFFERENCE']}]
    assert audit(raw,outputs)['MISSING']==['RELATIVE_COMPARISON']

def test_per100_extraction_does_not_satisfy_question():
    outputs=[{'status':'VERIFIED','numeric_verification':'VERIFIED','calculation_operations':['EXTRACT']}]
    assert audit('Trong 100 USD doanh thu có bao nhiêu USD từ Services?',outputs)['MISSING']==['PER_100']

def test_verified_confirmation_not_rendered_is_missing():
    outputs=[{'status':'VERIFIED','numeric_verification':'VERIFIED','calculation_operations':['EXTRACT']}]
    assert audit('Doanh thu là 69.377 triệu USD, đúng không?',outputs,'Doanh thu 64.377 triệu USD')['MISSING']==['EXPLICIT_CONFIRMATION']

@pytest.mark.parametrize('raw',[
 'Trong 100 USD doanh thu Apple năm 2025 thì khoảng bao nhiêu USD đến từ Services?',
 'Cứ 100 đồng doanh thu Apple năm 2025 thì mấy đồng thuộc dịch vụ?',
 'Trong mỗi 100 USD doanh thu FY2025 có bao nhiêu USD từ Services?',
])
def test_per100_paraphrase_contract(raw):
    p=plan_question(raw)
    assert p.operation=='PER_100'
    assert p.metrics==['services_net_sales','net_revenue']
    assert p.requested_unit is None

def cell(value,metric,unit='%'):
    return {'value':value,'value_raw':value,'metric':metric,'unit':unit,'scale':'1','currency':'USD','document_id':'doc','period_type':'FY','statement_scope':'CONSOLIDATED','period':'2025','basis':'AS_REPORTED'}

def test_relative_difference_decimal_and_wrong_denominator_direction():
    inputs=[cell('75.4','services_gross_margin_percentage'),cell('36.8','products_gross_margin_percentage')]
    # Independent recompute parses source raw values; no producer calculator.
    assert Decimal(recompute('RELATIVE_DIFFERENCE',inputs))==Decimal('104.89')
    with pytest.raises(ValueError,match='MARGIN_DIRECTION_MISMATCH'):recompute('RELATIVE_DIFFERENCE',inputs[::-1])

def test_relative_zero_denominator_refused():
    with pytest.raises(ValueError,match='ZERO_DENOMINATOR'):recompute('RELATIVE_DIFFERENCE',[cell('75.4','services_gross_margin_percentage'),cell('0','products_gross_margin_percentage')])

def test_fiscal_year_is_not_an_issuer_and_unknown_company_still_binds():
    from app.product.query_source_context import company_mentions
    assert company_mentions('Services FY2031 revenue?')==[]
    assert company_mentions('Acme FY2031 revenue?')==['Acme']

def test_growth_followup_uses_most_recent_two_periods_not_highest_years_ever_seen():
    from app.product.answer_planner_v2 import resolve_followup
    history=[{'question':f'Services FY{year}', 'response':{'conversation_slots':{'metric':'services_net_sales','years':[year]}}} for year in ['2025','2024','2023']]
    _,plan=resolve_followup('So how much did Services grow in absolute terms and percentage?',history)
    assert plan.years==['2023','2024']

def test_word_relative_without_its_verified_result_does_not_cover_question():
    output={'status':'VERIFIED','numeric_verification':'VERIFIED','calculation_operations':['RELATIVE_DIFFERENCE'],
        'calculation_results':[{'operation':'RELATIVE_DIFFERENCE','recomputed_result':'104.89','operand_metrics':['services_gross_margin_percentage','products_gross_margin_percentage']}]}
    raw='Services gross margin compared with Products: relative percent?'
    assert audit(raw,[output],'Relative comparison: consult the source')['MISSING']==['RELATIVE_COMPARISON']
    assert audit(raw,[output],'Relative difference is 104.89%')['MISSING']==[]

def test_confirmation_polarity_is_checked_in_rendered_answer():
    output={'status':'VERIFIED','numeric_verification':'VERIFIED','confirmation':False,'calculation_operations':['EXTRACT'],
        'calculation_results':[{'operation':'EXTRACT','recomputed_result':'64377'}]}
    raw='Doanh thu 69.377 triệu USD, đúng không?'
    assert audit(raw,[output],'Đúng. Doanh thu 64.377 triệu USD')['MISSING']==['EXPLICIT_CONFIRMATION']
    assert audit(raw,[output],'Không đúng. Doanh thu 64.377 triệu USD')['MISSING']==[]

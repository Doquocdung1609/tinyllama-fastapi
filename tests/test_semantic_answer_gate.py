from copy import deepcopy
import pytest
from app.product.answer_planner_v2 import plan_question,resolve_followup
from app.product.semantic_answer_gate import verify_coverage

def test_region_and_tax_are_not_total_revenue():
    p=plan_question("I believe Apple's FY2025 Greater China net sales were $69,377 million. Can you confirm?")
    assert p.metric=='greater_china_net_sales' and p.proposed_amount=='69377'
    p=plan_question('What were effective tax rates FY2025 and FY2024? Explain the drivers stated in the filing.')
    assert len(p.requested_claims)==4 and all(s['metric']=='effective_tax_rate' for s in p.requested_claims)

def test_all_requested_outputs_are_planned():
    p=plan_question('How much did Services grow in absolute terms and percentage FY2024 to FY2025?')
    assert p.operation=='CHANGE_AND_GROWTH'
    assert {'absolute_change','percentage_change'}<=set(p.requested_claims[0]['outputs'])
    p=plan_question('What are FY2026 total net sales according to the FY2025 filing selected?')
    assert p.years==['2026']
    p=plan_question('Compare total net sales and net income FY2024 to FY2025.')
    assert {s['metric'] for s in p.requested_claims}=={'net_revenue','net_income'}

@pytest.mark.parametrize('change',[{'metric':'net_revenue'},{'years':['2024']},{'operation':'EXTRACT'}, {'outputs':['amount']},{'status':'UNANSWERED'},{'numeric_verification':'REJECTED'}])
def test_correct_number_for_wrong_or_incomplete_question_is_rejected(change):
    p=plan_question('How much did Services grow in absolute terms and percentage FY2024 to FY2025?').public();slot=p['requested_claims'][0]
    o={**slot,'status':'VERIFIED','numeric_verification':'VERIFIED'};o.update(change)
    assert verify_coverage(p,[o])['status']=='UNANSWERED'

def test_partial_explanation_does_not_discard_verified_values():
    p=plan_question('What were effective tax rates FY2025 and FY2024? Explain drivers.').public()
    outputs=[{**s,'status':'VERIFIED','numeric_verification':'VERIFIED'} for s in p['requested_claims'] if s['kind']=='numeric']
    result=verify_coverage(p,outputs)
    assert result['status']=='PARTIAL' and result['answered_count']==3
    assert result['unanswered_subquestions'][0]['kind']=='explanation'

def test_services_three_turn_followup_preserves_metric_and_years():
    p=plan_question('What were Services net sales FY2025?')
    h=[{'question':p.raw_text,'response':{'conversation_slots':p.public()}}]
    q,p=resolve_followup('And in FY2024?',h)
    h.append({'question':'And in FY2024?','response':{'conversation_slots':p.public()}})
    q,p=resolve_followup('So how much did Services grow in absolute terms and percentage?',h)
    assert p.metric=='services_net_sales' and p.operation=='CHANGE_AND_GROWTH' and p.years==['2024','2025']


def test_user_amount_confirmation_is_checked_against_recomputed_source_value():
    p=plan_question("I believe Greater China net sales FY2025 were $69,377 million. Can you confirm?").public();slot=p['requested_claims'][0]
    output={**slot,'status':'VERIFIED','numeric_verification':'VERIFIED','confirmation':True,
        'calculation_results':[{'operation':'EXTRACT','recomputed_result':'64377'}]}
    assert verify_coverage(p,[output])['status']=='UNANSWERED'
    output['confirmation']=False
    assert verify_coverage(p,[output])['status']=='COMPLETE'


def test_margin_followup_retains_both_categories_and_point_difference():
    previous=plan_question('Compare Services and Products gross margin percentages FY2025.')
    q,p=resolve_followup('And in FY2024?',[{'question':previous.raw_text,'response':{'conversation_slots':previous.public()}}])
    assert p.operation=='PERCENTAGE_POINT_DIFFERENCE' and p.years==['2024']
    assert len(p.metrics)==2


def test_explanation_question_does_not_pass_as_generic_document_navigation():
    p=plan_question('Why did Services net sales increase in FY2025?')
    assert p.requested_claims and all(s['kind']=='explanation' for s in p.requested_claims)
    assert p.requested_claims[0]['metric']=='services_net_sales'

import pytest
from app.product.query_source_context import company_mentions,source_company_conflict
from test_v7p_verified_operands import setup_source


@pytest.mark.parametrize('question',[
    "What was othercorp's net income in 2025?",'OtherCorp Inc. net income 2025?',
    'Doanh thu OtherCorp năm 2025?','Net income of OtherCorp in fiscal 2025?'])
def test_wrong_company_language_variants_refuse(tmp_path,question):
    w,_,_=setup_source(tmp_path)
    result=source_company_conflict(w,['d'],question)
    assert result['status']=='QUERY_CONTEXT_CONFLICT' and result['values']==[]


def test_user_display_name_never_authenticates_another_issuer(tmp_path):
    w,_,_=setup_source(tmp_path)
    original=w.document
    w.document=lambda i:{**original(i),'issuer':'OtherCorp'}
    assert source_company_conflict(w,['d'],"OtherCorp's net income 2025?")['values']==[]
    assert source_company_conflict(w,['d'],"Example's net income 2025?") is None


def test_financial_adjectives_do_not_become_company_names():
    assert company_mentions('Which geographic segment generated the highest net sales in fiscal year 2025?')==[]
    assert company_mentions('How much net income in fiscal year 2025?')==[]
    assert company_mentions("Calculate Example's year-over-year total net sales growth rate 2024 to 2025")==['Example']

from app.product import frontend_api
from app.product.analysis import AnalysisRequest
from app.product.assistant_answer import contract, needs_number


def test_segment_maximum_is_numeric_and_cannot_be_answered_by_excerpt():
    question='Which geographic segment generated the highest net sales in fiscal year 2025, and how much did it generate?'
    assert needs_number(question)
    answer=contract(question,{'results':[{'text':'Americas 178,353','chunk_id':'source'}]},'baseline')
    assert answer['values']==[]
    assert answer['verification_status']=='NUMERIC_UNVERIFIED'


def test_explicit_filter_conflict_never_silently_overridden(monkeypatch):
    class Workspace:
        def search(self,*args):return {'results':[{'text':'source','chunk_id':'c'}]}
    monkeypatch.setattr(frontend_api,'workspace',lambda:Workspace())
    monkeypatch.setattr(frontend_api,'eligible_facts',lambda *_:[])
    from app.product import assistant_answer
    monkeypatch.setattr(assistant_answer,'reviewed_plan',lambda *_:{
        'metric':'net_revenue','operation':'PERCENT_CHANGE','current_period':'2025-09-27',
        'previous_period':'2024-09-28','statement_scope':'CONSOLIDATED','basis':'AS_REPORTED'})
    monkeypatch.setattr(frontend_api,'numeric_answer',lambda *_: (_ for _ in ()).throw(AssertionError('must refuse before calculation')))
    request=AnalysisRequest(question='Calculate net sales growth rate 2024 to 2025',
        document_ids=['d'],metric='assets',operation='EXTRACT',statement_scope='SEPARATE')
    result=frontend_api.analysis(request)
    assert result['status']=='QUERY_CONTEXT_CONFLICT'
    assert set(result['conflicting_fields'])=={'metric','operation','statement_scope'}
    assert result['values']==[]


def test_omitted_ui_defaults_do_not_block_verified_plan(monkeypatch):
    class Workspace:
        def search(self,*args):return {'results':[{'text':'source','chunk_id':'c'}]}
    monkeypatch.setattr(frontend_api,'workspace',lambda:Workspace())
    monkeypatch.setattr(frontend_api,'eligible_facts',lambda *_:[])
    from app.product import assistant_answer
    plan={'metric':'net_income','operation':'EXTRACT','current_period':'2025-09-27',
          'previous_period':'','statement_scope':'CONSOLIDATED','basis':'AS_REPORTED'}
    monkeypatch.setattr(assistant_answer,'reviewed_plan',lambda *_:plan)
    monkeypatch.setattr(frontend_api,'numeric_answer',lambda _,request:{
        'status':'SUPPORTED','values':['1'],'verification':'TEST_FIXTURE','citations':[]})
    result=frontend_api.analysis(AnalysisRequest(question='What was net income in 2025?',document_ids=['d']))
    assert result['status']=='SUPPORTED'

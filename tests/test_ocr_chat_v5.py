from types import SimpleNamespace

from app.product.chat_source_focus import selected_source
from app.product.ocr_candidate_answer import eligible_candidate
from app.product.ocr_reviewed_answer import period_label
from app.product.pdf_ocr_financial_v3 import AUTOMATED


def test_passively_opened_page_never_becomes_source_focus():
    workspace=SimpleNamespace()
    request=SimpleNamespace(document_ids=['doc'],evidence_context={'document_id':'doc','page':1})
    assert selected_source(workspace,request) is None


def test_candidate_is_fail_closed_when_source_conflicts():
    row={}
    cell={'box':[1,2,3,4],'binding_status':'GEOMETRIC_CANDIDATE','period_end':'2025-12-31',
          'period_type':'FY','period':'FY 2025','unit':'VND','statement_scope':'SEPARATE',
          'review_status':AUTOMATED,'numeric_value':'-1700','text':'(1.700)'}
    assert eligible_candidate(row,cell)
    assert not eligible_candidate(row,{**cell,'ocr_warning':'OCR_ENGINE_DISAGREEMENT'})
    assert not eligible_candidate(row,{**cell,'text':'1.700'})
    assert not eligible_candidate({'warnings':['OCR_ARITHMETIC_MISMATCH · FY 2025']},cell)


def test_period_label_returns_one_string():
    assert period_label('INSTANT','2025-12-31','31/12/2025')=='ngày 31/12/2025'
    assert period_label('3M_Q4','2025-12-31')=='quý IV/2025'
    assert period_label('FY','2025-12-31')=='cả năm 2025'


def test_debt_ratio_uses_only_reviewed_operands_and_recomputes(monkeypatch):
    from app.product import analysis
    from app.product.ocr_reviewed_answer import calculation
    from app.product.pdf_ocr_financial_v3 import HUMAN

    doc={'id':'doc','issuer':'Issuer','sha256':'source','pages':4}
    common={'document_id':'doc','issuer':'Issuer','source_sha256':'source','statement_scope':'SEPARATE',
            'period':'2025-12-31','period_type':'INSTANT','unit':'VND','currency':'VND','basis':'AS_REPORTED',
            'page':3,'box':[1,2,3,4]}
    facts=[{**common,'id':'a','metric':'liabilities','review_status':HUMAN,'row_label':'Nợ phải trả',
            'value':'40','base_value':'40','source_display':'40'},
           {**common,'id':'b','metric':'assets','review_status':AUTOMATED,'row_label':'Tổng tài sản',
            'value':'160','base_value':'160','source_display':'160'}]
    monkeypatch.setattr(analysis,'eligible_facts',lambda *_:facts)
    workspace=SimpleNamespace(document=lambda _:doc,list_documents=lambda:[doc],source_file=lambda _:None)
    request=analysis.AnalysisRequest(question='Tính tỷ lệ nợ phải trả trên tổng tài sản tại 31/12/2025.',
                                     document_ids=['doc'])
    assert calculation(workspace,request) is None
    facts[1]['review_status']=HUMAN
    result=calculation(workspace,request)
    assert '25,00%' in result['answer']
    assert [ref['id'] for ref in result['citations']]==['a','b']


def test_saved_legacy_reply_is_formatted_on_read_without_rewriting_history():
    import json
    from app.product.chat_store import public
    from app.product.pdf_ocr_financial_v3 import HUMAN

    original="Nợ phải trả · {'INSTANT': '31/12/2025', 'FY': 'Cả năm 2025'}: 1.234 VND"
    turn={'question':'Nợ phải trả?', 'response':{'answer':original,'verification_status':HUMAN,
          'values':['1234'],'citations':[{'period':'2025-12-31','page':4,'unit':'VND','row_label':'Nợ phải trả'}]},
          'messages':[{'role':'assistant','text':original}]}
    row={'id':'id','title':'T','created_at':'','updated_at':'','document_ids':'[]','payload':json.dumps([turn])}
    result=public(row,detail=True)
    assert '1.234 đồng' in result['turns'][0]['response']['answer']
    assert 'INSTANT' not in result['messages'][0]['text']
    assert json.loads(row['payload'])[0]['response']['answer']==original

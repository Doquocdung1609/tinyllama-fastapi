from types import SimpleNamespace

from app.product.pdf_extract import folded
from app.product.sec_multi_qa import requested_metrics, resolve_followup
from app.product.sec_question import MARGIN, answer, margin, requested_topics
from app.product.sec_task_plan import plan_sec_question


def catalog():
    return {symbol: [({'ticker': symbol, 'issuer': name, 'filing_id': symbol,
                       'report_period': '2026-08-02'}, None)]
            for symbol, name in [('COST', 'Costco Wholesale Corporation'),
                                 ('HD', 'The Home Depot, Inc.'),
                                 ('PG', 'The Procter & Gamble Company'),
                                 ('MSFT', 'Microsoft Corporation')]}


def plan(text, selected=None):
    q = folded(text)
    margin = MARGIN.search(q)
    scope = catalog()
    if selected is not None:
        scope = {k: v for k, v in scope.items() if k in selected}
    return plan_sec_question(text, scope, None, requested_metrics(q),
                             margin.group(0) if margin else None, requested_topics(q))


def test_focus_overrides_contextual_company_mentions():
    p = plan('Tôi chọn COST, HD và PG. Hãy chỉ sử dụng Home Depot để tính tỷ suất lợi nhuận hoạt động kỳ 13 tuần.')
    assert p.focused_entities == ['HD']
    assert p.context_only_entities == ['COST', 'PG']
    assert [(t.issuer, t.operation) for t in p.tasks] == [('HD', 'MARGIN_PERCENT')]
    assert plan('Among PG, COST and HD, focus on Home Depot operating margin').eligible_entities == ['HD']


def test_multi_metric_and_two_topic_obligations():
    p = plan('Microsoft 10-Q: so sánh doanh thu, lợi nhuận hoạt động và lợi nhuận ròng với cùng kỳ năm trước.')
    assert {t.metric for t in p.tasks} == {'revenue', 'operating_income', 'income'}
    assert all(t.operation == 'YEAR_OVER_YEAR' for t in p.tasks)
    n = plan('Microsoft có rủi ro cạnh tranh và an ninh mạng nào?')
    assert {t.metric for t in n.tasks} == {'COMPETITION', 'CYBERSECURITY'}


def test_missing_company_cannot_redirect_to_selected_issuers():
    for text, expected in [('Amazon FY2024 AWS chiếm bao nhiêu phần trăm doanh thu?', 'AMZN'),
                           ('Chỉ chọn PepsiCo 10-Q, so sánh doanh thu kỳ 12 và 24 tuần.', 'PEP')]:
        p = plan(text)
        assert p.unselected_entities == [expected]
        assert p.eligible_entities == [] and p.tasks == []
        assert p.error == 'SEC_ISSUER_NOT_SELECTED'


def test_partial_comparison_keeps_available_issuers_and_missing_slot():
    p = plan('So sánh tỷ suất lợi nhuận hoạt động của COST, HD và PG theo kỳ ngắn nhất.', {'HD', 'PG'})
    assert p.eligible_entities == ['HD', 'PG']
    assert p.unselected_entities == ['COST']
    assert len(p.tasks) == 2


def test_short_followup_fills_only_pending_slot():
    prior = {'pending_clarification': {'original_task': 'So sánh doanh thu của các nguồn đang chọn',
                                       'missing_slot': 'issuer'}}
    assert resolve_followup('Chỉ HD.', prior).endswith('chỉ sử dụng HD')
    assert resolve_followup('Cả ba.', prior).endswith('so sánh từng doanh nghiệp')
    prior['pending_clarification']['missing_slot'] = 'duration'
    assert resolve_followup('Kỳ 13 tuần.', prior).endswith('Kỳ 13 tuần.')
    assert resolve_followup('Đúng rồi.', prior) == 'Đúng rồi.'


def test_short_followup_keeps_prior_metric_and_explicit_duration():
    previous = {'sec_question_plan': {'intent': 'MARGIN', 'named_entities': ['HD'],
                 'original_question': 'Tính biên lợi nhuận hoạt động của HD trong kỳ 13 tuần.'}}
    assert resolve_followup('Còn PG thì sao?', previous) == 'Tính biên lợi nhuận hoạt động của PG trong kỳ 13 tuần.'


def test_narrative_paraphrases_create_both_topics():
    q = folded('Microsoft công bố gì về sức ép đối thủ và rủi ro tấn công mạng?')
    assert requested_topics(q) == ['COMPETITION', 'CYBERSECURITY']
    assert set(requested_metrics(folded('doanh thu và thu nhập ròng'))) == {'revenue','income'}
    assert set(requested_metrics(folded('lãi hoạt động và doanh thu'))) == {'operating_income','revenue'}
    assert MARGIN.search(folded('biên hoạt động của PG'))
    assert MARGIN.search(folded('phần trăm lợi nhuận từ hoạt động trên tổng doanh thu'))


def test_margin_rejects_unselected_future_year_before_cell_lookup():
    filing = {'ticker':'HD','report_period':'2026-08-02','fiscal_year':2026}
    result = margin([(filing, None)], 'HD báo cáo tỷ suất lợi nhuận hoạt động năm 2037?', 'HD', 'f'*64)
    assert result['reason'] == 'SEC_FISCAL_PERIOD_ABSENT'


def test_orchestrator_keeps_all_metric_tasks(monkeypatch):
    from app.product import sec_question
    class Index:
        catalog_rows = [entry[0] for entry in catalog()['MSFT']]
    index = Index()
    calls = []
    def numeric(_scope, _question, ticker, _key, *, metric_override, **_):
        calls.append((ticker, metric_override))
        return {'status': 'SUPPORTED', 'answer': metric_override, 'values': ['1'],
                'citations': [], 'source_cells': []}
    monkeypatch.setattr(sec_question, 'numeric_answer', numeric)
    result = answer(index, 'Microsoft: so sánh doanh thu, lợi nhuận hoạt động và lợi nhuận ròng cùng kỳ năm trước', None, 'f' * 64)
    assert {metric for _, metric in calls} == {'revenue', 'operating_income', 'income'}
    assert result['answer_completeness'] == {'completed': 3, 'required': 3}


def test_orchestrator_does_not_calculate_unselected_pepsi(monkeypatch):
    from app.product import sec_question
    index = SimpleNamespace(catalog_rows=[entry[0] for symbol in ('COST', 'HD', 'PG', 'MSFT')
                                          for entry in catalog()[symbol]])
    monkeypatch.setattr(sec_question, 'numeric_answer', lambda *_a, **_k: (_ for _ in ()).throw(AssertionError('wrong source')))
    result = answer(index, 'Chỉ chọn PepsiCo. Tính thay đổi doanh thu của kỳ 12 và 24 tuần.', None, 'f' * 64)
    assert result['reason'] == 'SEC_ISSUER_NOT_SELECTED'
    assert result['sec_question_plan']['unselected_entities'] == ['PEP']

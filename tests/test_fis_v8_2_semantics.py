from decimal import Decimal
from types import SimpleNamespace

from app.product.pdf_extract import folded
from app.product.sec_question import MARGIN, requested_topics
from app.product.sec_ratio import _prior_end, ratio_variants
from app.product.sec_task_plan import plan_sec_question, resolve_typed_followup


def filing(symbol,name,end):
    return {'ticker':symbol,'issuer':name,'filing_id':symbol+end,'report_period':end,'form':'10-Q'}


def cell(end, start, label, value):
    return SimpleNamespace(period_end=end,period_start=start,period_kind='DURATION',period_months=3,unit='USD',
                           filing_id='sample-filing',cik='sample-cik',raw_sha256='sample-hash',generation='sample-gen',
                           row_label=label,effective_value=Decimal(value),warnings=(),structural_path=label)


def test_period_relation_checks_actual_previous_year_cells():
    current=cell('2025-10-03','2025-07-05','Operating income','64')
    last_quarter=cell('2025-07-04','2025-04-05','Operating income','45')
    last_year=cell('2024-10-04','2024-07-06','Operating income','57')
    recent_sales=cell('2025-07-04','2025-04-05','Total revenue','140')
    old_sales=cell('2024-10-04','2024-07-06','Total revenue','155')
    assert _prior_end(current,[last_quarter],[recent_sales],3,'REPORTED_REVENUE') is None
    assert _prior_end(current,[last_quarter,last_year],[recent_sales,old_sales],3,'REPORTED_REVENUE')=='2024-10-04'


def test_formula_variants_become_distinct_task_obligations():
    q='For Orchid Works, compute operating margin on total revenue and net sales.'
    catalog={'OW':[ (filing('OW','Orchid Works, Inc.','2025-10-03'),None) ]}
    match=MARGIN.search(folded(q))
    plan=plan_sec_question(q,catalog,margin=match[0])
    assert [(t.issuer,t.denominator) for t in plan.tasks]==[('OW','TOTAL_REVENUE'),('OW','NET_SALES')]
    assert ratio_variants(folded('trên doanh thu thuần bán hàng'))==['PRODUCT_NET_SALES']


def test_followup_rebinds_catalog_alias_and_explicit_shortest_duration():
    index=SimpleNamespace(catalog_rows=[filing('OW','Orchid Works, Inc.','2025-10-03'),
                                        filing('NL','North Lantern Corporation','2026-04-02')])
    old={'sec_question_plan':{'intent':'MARGIN'},'sec_task_context':{'kind':'MARGIN','issuer':'OW',
         'metric':'operating_income','duration':[13],'report_end':'2025-10-03','denominators':['NET_SALES']}}
    got=resolve_typed_followup(index,'What about North Lantern, use its shortest available period?',old)
    assert got['overrides']=={'issuer':'NL','duration':'SHORTEST_REPORTED'}
    assert 'NL' in got['question'] and 'doanh thu thuần' in got['question']
    assert '13' not in got['question'] and '2025-10-03' not in got['question']


def test_narrative_topics_preserve_distinct_and_unknown_obligations():
    topics=requested_topics(folded('Phân tích riêng rủi ro pháp lý, bảo mật dữ liệu, an ninh mạng và orbital debris.'))
    assert set(topics)=={'LEGAL','DATA_SECURITY','CYBERSECURITY','LOCAL:orbital debris'}

def test_comparison_word_dong_nhat_does_not_bind_vnd(monkeypatch):
    from app.product import sec_ratio
    monkeypatch.setattr(sec_ratio,'observations',lambda *_:[])
    source=filing('OW','Orchid Works, Inc.','2025-10-03')
    result=sec_ratio.margin([(source,None)],'Biên lợi nhuận hoạt động kỳ ngắn nhất. Các kỳ không hoàn toàn đồng nhất.',
                            'OW','key','operating_income')
    assert result['reason']=='SEC_MARGIN_SOURCE_UNAVAILABLE'
    refused=sec_ratio.margin([(source,None)],'Biên lợi nhuận hoạt động, trình bày bằng VND.',
                             'OW','key','operating_income')
    assert refused['reason']=='SEC_UNSUPPORTED_DIMENSION'

"""Synthetic native source contracts; real Apple acceptance is separate HTTP."""
from hashlib import sha256
import pymupdf
import pytest
from app.product.analysis import AnalysisRequest,table_bound_scope
from app.product.verified_financial import automatic_answer,verified_bundle


def setup_source(tmp_path,unit='USD in millions',previous='100',missing_header=False,duplicate=False):
    pdf=pymupdf.open();cover=pdf.new_page()
    cover.insert_text((40,50),'Example Inc. (Exact name of Registrant as specified in its charter)')
    cover.insert_text((40,75),'FORM 10-K. For the fiscal year ended September 27, 2025.')
    cover.insert_text((40,95),'The fiscal years 2025 and 2024 are annual reporting periods.')
    page=pdf.new_page();page.insert_text((40,50),'CONSOLIDATED STATEMENTS OF OPERATIONS')
    page.insert_text((40,70),unit)
    page.insert_text((40,85),'Years ended')
    if not missing_header:
        page.insert_text((285,90),'September 27,');page.insert_text((405,90),'September 28,')
        page.insert_text((300,102),'2025');page.insert_text((420,102),'2024')
    for y,label,a,b in [(125,'Total net sales','125',previous),(145,'Net income','(12)','10')]:
        page.insert_text((40,y),label);page.insert_text((300,y),a);page.insert_text((420,y),b)
    if duplicate:
        page.insert_text((40,165),'Net income');page.insert_text((300,165),'99');page.insert_text((420,165),'88')
    path=tmp_path/'source.pdf';path.write_bytes(pdf.tobytes());pdf.close();digest=sha256(path.read_bytes()).hexdigest()
    class Workspace:
        def document(self,_):return {'id':'d','sha256':digest,'status':'READY','issuer':'Example Inc.'}
        def source_file(self,_):
            if sha256(path.read_bytes()).hexdigest()!=digest:raise ValueError('PDF_SOURCE_HASH_MISMATCH')
            return path
    hits={'results':[{'chunk_id':'synthetic-original-chunk','document_id':'d','page':2,'source_sha256':digest,'text':'Total net sales and Net income'}]}
    return Workspace(),hits,path


def test_typed_cells_and_decimal_growth(tmp_path):
    w,r,_=setup_source(tmp_path)
    result=automatic_answer(w,AnalysisRequest(question='Total net sales growth rate fiscal 2024 to 2025?',document_ids=['d']),r)
    assert result['status']=='SUPPORTED' and result['values']==['25.00']
    assert len(result['citations'])==2
    for c in result['citations']:
        assert c['verification_status']=='CELL_VERIFIED'
        assert c['cell_bbox'] and c['header_bbox'] and c['row_bbox']
        assert c['issuer']=='Example Inc.' and c['normalized_unit']=='USD'
        assert c['retrieved_chunk_ids']==['synthetic-original-chunk']


@pytest.mark.parametrize('updates',[{'metric':'assets'},{'operation':'ABS_CHANGE'},{'statement_scope':'SEPARATE'},{'current_period':'2025-12-31'}])
def test_explicit_conflicts_fail_closed(tmp_path,updates):
    w,r,_=setup_source(tmp_path)
    req=AnalysisRequest(question='Total net sales growth rate fiscal 2024 to 2025?',document_ids=['d'],**updates)
    assert automatic_answer(w,req,r)['status']=='QUERY_CONTEXT_CONFLICT'


def test_equivalent_year_and_fiscal_end_are_accepted(tmp_path):
    w,r,_=setup_source(tmp_path)
    for period in ['2025','2025-09-27']:
        req=AnalysisRequest(question='Net income fiscal 2025?',document_ids=['d'],current_period=period)
        result=automatic_answer(w,req,r)
        assert result['status']=='SUPPORTED' and result['values']==['-12']


@pytest.mark.parametrize('period',['2025junk','2025-09','FY2025Q2'])
def test_malformed_period_constraint_never_broadens(tmp_path,period):
    w,r,_=setup_source(tmp_path)
    req=AnalysisRequest(question='Net income fiscal 2025?',document_ids=['d'],current_period=period)
    result=automatic_answer(w,req,r)
    assert result['status']=='QUERY_CONTEXT_CONFLICT' and not result['values']


def test_reverse_comparison_not_silently_reordered(tmp_path):
    w,r,_=setup_source(tmp_path)
    result=automatic_answer(w,AnalysisRequest(question='Total net sales growth from fiscal 2025 to fiscal 2024?',document_ids=['d']),r)
    assert result['values']==[] and result['reason']=='REVERSE_COMPARISON_REQUIRES_EXPLICIT_OPERAND_ORDER'


@pytest.mark.parametrize('question',['Net income fiscal 2037?','Net income attributable to common shareholders 2025?','Net income Q2 2025?','Total assets 2025?'])
def test_unsupported_period_definition_and_duration(tmp_path,question):
    w,r,_=setup_source(tmp_path)
    assert automatic_answer(w,AnalysisRequest(question=question,document_ids=['d']),r)['values']==[]


def test_unit_missing_header_zero_and_tamper(tmp_path):
    w,r,p=setup_source(tmp_path,unit='Amounts shown below')
    assert verified_bundle(w,['d'],r['results'])['cells']==[]
    p.write_bytes(p.read_bytes()+b'changed')
    with pytest.raises(ValueError,match='HASH_MISMATCH'):verified_bundle(w,['d'],r['results'])


def test_zero_denominator(tmp_path):
    w,r,_=setup_source(tmp_path,previous='0')
    result=automatic_answer(w,AnalysisRequest(question='Total net sales growth fiscal 2024 to 2025?',document_ids=['d']),r)
    assert result['reason']=='ZERO_DENOMINATOR'


def test_thousand_scale_not_mislabeled_as_unscaled_usd(tmp_path):
    from app.product.verified_financial import _source_unit
    assert _source_unit({'scale':'1000','currency':'USD'})=='THOUSAND_USD'
    w,r,_=setup_source(tmp_path,unit='USD in thousands')
    result=automatic_answer(w,AnalysisRequest(question='Net income fiscal 2025?',document_ids=['d']),r)
    # The current native table adapter supports only locally declared millions.
    assert result['status']!='SUPPORTED' and result['values']==[]


@pytest.mark.parametrize('unit',['$ in millions','CAD in millions','USD in millions; all amounts in thousands'])
def test_ambiguous_currency_and_conflicting_scale(tmp_path,unit):
    w,r,_=setup_source(tmp_path,unit=unit)
    result=automatic_answer(w,AnalysisRequest(question='Net income fiscal 2025?',document_ids=['d']),r)
    assert result['status']!='SUPPORTED' and result['values']==[]


def test_duplicate_metric_values_conflict(tmp_path):
    w,r,_=setup_source(tmp_path,duplicate=True)
    result=automatic_answer(w,AnalysisRequest(question='Net income fiscal 2025?',document_ids=['d']),r)
    assert result['reason']=='CONFLICTING_EVIDENCE' and result['values']==[]


def test_missing_years_never_become_cells(tmp_path):
    w,r,_=setup_source(tmp_path,missing_header=True)
    assert verified_bundle(w,['d'],r['results'])['cells']==[]


def test_unrelated_page_scope_not_proof_of_current_statement():
    def line(y,text):return {'text':text,'box':[0,y,300,y+10],'words':[{'ry':y,'box':[0,y,300,y+10]}]}
    page={'lines':[line(10,'CONSOLIDATED STATEMENTS OF OPERATIONS'),line(100,'SEPARATE FINANCIAL STATEMENTS')]}
    assert table_bound_scope(page,{'reading_y':140})=='SEPARATE'


@pytest.mark.parametrize('complete',[True,False])
def test_segment_set_must_match_source_declaration(tmp_path,complete):
    _,_,original=setup_source(tmp_path)
    pdf=pymupdf.open(original)
    pdf[0].insert_text((40,110),'The reportable segments consist of North and South.')
    pg=pdf.new_page();pg.insert_text((40,50),'Segment Operating Performance')
    pg.insert_text((40,70),'Net sales by reportable segment (USD in millions)')
    pg.insert_text((300,100),'2025');pg.insert_text((420,100),'2024')
    entries=[('North','20','15')]+([('South','10','5')] if complete else [])
    entries+=[('Total net sales','30' if complete else '20','20' if complete else '15')]
    for i,(label,a,b) in enumerate(entries):
        y=125+i*20;pg.insert_text((40,y),label);pg.insert_text((300,y),a);pg.insert_text((420,y),b)
    path=tmp_path/'segments.pdf';path.write_bytes(pdf.tobytes());pdf.close()
    digest=sha256(path.read_bytes()).hexdigest()
    class Workspace:
        def document(self,_):return {'id':'d','status':'READY','sha256':digest,'issuer':'Example Inc.'}
        def source_file(self,_):return path
    hits={'results':[{'document_id':'d','page':3,'source_sha256':digest,'chunk_id':'synthetic-segment-source','text':'net sales reportable segments'}]}
    r=automatic_answer(Workspace(),AnalysisRequest(question='Which segment had highest net sales fiscal 2025?',document_ids=['d']),hits)
    if complete:assert r['status']=='SUPPORTED' and r['winner']=='North' and len(r['citations'])==2
    else:assert r['reason']=='INCOMPLETE_OR_AMBIGUOUS_SEGMENT_SET' and r['values']==[]

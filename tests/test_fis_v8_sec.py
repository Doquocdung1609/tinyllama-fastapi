import json
import subprocess
from types import SimpleNamespace

from app.product import sec_library
from app.product.sec_answer_contract import verify_comparison
from app.product.sec_question import resolve_sources, _readable
from app.product.sec_multi_qa import requested_metrics


def test_issuer_resolution_uses_actual_selected_catalog():
    index=SimpleNamespace(catalog_rows=[
        {'ticker':'EX','issuer':'Example Retail, Inc.','filing_id':'retail'},
        {'ticker':'EF','issuer':'Example Finance Corporation','filing_id':'finance'},
    ])
    _,eligible,missing,conflict=resolve_sources(index,'Example Retail: doanh thu quý này?')
    assert (eligible,missing,conflict)==(['EX'],[],None)
    _,eligible,missing,_=resolve_sources(index,'Doanh thu của Microsoft quý này?')
    assert eligible==[] and missing==['MSFT']


def test_overlapping_accounting_terms_are_distinct():
    assert requested_metrics('deferred revenue and total revenue')==['deferred_revenue','revenue']
    assert requested_metrics('cost of revenue and operating income')==['cost_of_revenue','operating_income']
    assert not _readable(SimpleNamespace(kind='text',text='http://fasb.org/us-gaap/2026#OtherAssets ' * 4))
    assert not _readable(SimpleNamespace(kind='table',text='Business address '*10))


def test_decimal_period_values_from_multiple_printed_scales():
    def cell(raw,value,scale,effective):
        return {'raw_value':raw,'value':value,'unit':'USD','multiplier':scale,
                'effective_value':effective,'source_status':'VERIFIED_SOURCE_CELL'}
    proofs=verify_comparison([cell('45,030','45030','1000','45030000'),
                              cell('85','85','1000000','85000000')],[('PERIOD_VALUES',['45.03','85'])])
    assert proofs['stage_b'][0]['recomputed_results']==['45.03','85']


def test_watchdog_timeout_keeps_published_lexical_state(tmp_path,monkeypatch):
    monkeypatch.setenv('STUDIO_WORKSPACE_DIR',str(tmp_path))
    key='a'*24
    with sec_library.db() as db:
        db.execute('INSERT INTO filings VALUES (?, ?, ?, ?, ?)',(key,'{}','LEXICAL_READY','BUILDING_DENSE',1))
    source,_=sec_library.paths(key)
    (source/'frozen_v1').mkdir(parents=True)
    identity={'generation':'test-gen','manifest_hash':'test-manifest'}
    (source/'frozen_v1/freeze.json').write_text(json.dumps(identity))
    (source/'lexical-publication.json').write_text(json.dumps({**identity,'state':'LEXICAL_READY','parent_count':12}))

    class HungWorker:
        killed=False
        def __enter__(self):
            return self
        def __exit__(self,*_):
            pass
        def wait(self,timeout=None):
            if not self.killed:
                raise subprocess.TimeoutExpired('worker',timeout)
            return 1
        def kill(self):
            self.killed=True

    monkeypatch.setattr(sec_library,'JOB_LIMIT_SECONDS',0)
    monkeypatch.setattr(sec_library.subprocess,'Popen',lambda *args,**kwargs: HungWorker())
    sec_library.process(key)
    row=sec_library.rows()[0]
    assert row['status']=='LEXICAL_READY' and row['reason']=='WORKER_PROGRESS_TIMEOUT_RETRY'
    assert sec_library.job_progress(row)['published_chunks']==12
    assert not sec_library.import_running(row)

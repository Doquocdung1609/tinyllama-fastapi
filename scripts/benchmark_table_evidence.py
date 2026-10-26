"""D2 synthetic representation audit, not retrieval/held-out evaluation.

Run from repository root: python -m scripts.benchmark_table_evidence
Writes only stdout. Redirect explicitly to a NEW D2 report if desired.
"""
import json
import math
import platform
import statistics
import time
import tracemalloc
from decimal import Decimal
from hashlib import sha256
from pathlib import Path

from app.financial_ingestion import PARSER_VERSION, CHUNKER_VERSION, INGESTION_VERSION
from app.financial_ingestion.schemas import FilingMetadata
from app.financial_ingestion.html_parser import parse_sec_html, normalized_filing_text
from app.financial_ingestion.chunker import chunk_filing
from app.table_evidence import context_from_snapshot, build_table_evidence, build_evidence_bundle
from app.table_evidence.compact import compact_view
from app.table_evidence.contracts import SourceBindingV1
from app.table_evidence.identity import digest, canonical

CASES_PATH=Path(__file__).resolve().parents[1]/'tests/fixtures/table_evidence/cases.json'


def fixture(case,rows=1):
    # Explicitly synthetic; no owner corpus, files, registry or indexes opened.
    html=('<html><body><h1>'+case['title']+'</h1><p>'+case['unit']+'</p><table>'
          '<tr><th>Metric</th>'+''.join('<th>'+h+'</th>' for h in case['headers'])+'</tr>'+''.join(
              '<tr><td>'+case['row']+'</td>'+''.join('<td>'+v+'</td>' for v in case['values'])+'</tr>' for _ in range(rows))+
          '</table></body></html>')
    raw=html.encode()
    meta=FilingMetadata(filing_id='sec:0000000202:0000000202-25-000001',cik='0000000202',
        accession_number='0000000202-25-000001',company_name='Synthetic D2',form_type='10-K',
        filing_date='2026-03-01',report_date='2025-01-31',primary_document='synthetic.htm',
        source_url='https://example.invalid/synthetic',raw_content_hash=sha256(raw).hexdigest(),
        parser_version=PARSER_VERSION,chunker_version=CHUNKER_VERSION,ingestion_version=INGESTION_VERSION,
        document_status='READY')
    filing=parse_sec_html(raw,meta.model_copy(deep=True)); chunks=chunk_filing(filing)
    binding=SourceBindingV1(dataset_id='synthetic-d2',manifest_hash='a'*64,generation_id='b'*64,
        filing_id=meta.filing_id,raw_hash=sha256(raw).hexdigest(),
        normalized_hash=sha256(normalized_filing_text(filing).encode()).hexdigest(),metadata_hash=digest(meta.model_dump(mode='json')),
        parent_hashes=tuple(sorted((c.chunk_id,digest(c.model_dump(mode='json'))) for c in chunks)))
    return [c for c in chunks if c.kind=='table'],raw,meta,binding


def distribution(values):
    return {'p50_ms':statistics.median(values),'p95_ms':sorted(values)[max(0,math.ceil(.95*len(values))-1)],'samples':len(values)}


def main():
    cases=json.loads(CASES_PATH.read_text()); totals={k:0 for k in ['cells','coordinates_correct','periods_correct','typed_periods','units_correct','raw_correct','locators_complete','parent_correspondence','partial_cells','verified_cells']}
    rows=[]; timings=[]; context_timings=[]; first_calls=[]
    for case in cases:
        parents,raw,meta,binding=fixture(case)
        start=time.perf_counter(); ctx=context_from_snapshot(raw,meta,binding); context_timings.append((time.perf_counter()-start)*1000)
        p=parents[0]; start=time.perf_counter(); result=build_table_evidence(p,ctx); first_calls.append((time.perf_counter()-start)*1000)
        assert result.evidence is not None
        e=result.evidence
        totals['parent_correspondence']+=int(e.parent_payload_hash==digest(p.model_dump(mode='json')))
        for index,c in enumerate(e.cells[1:]):
            totals['cells']+=1
            totals['coordinates_correct']+=int(c.row==1 and c.column==index+1)
            totals['raw_correct']+=int(c.original_text==case['values'][index])
            totals['locators_complete']+=int(c.locator.structural_path.endswith(f'/tr[2]/td[{index+2}]'))
            if 'ends' in case:
                expected=case['ends'][index]; correct=c.period is not None and c.period.end==expected and c.period.kind==case['kind']
            else:
                expected=case['years'][index]; correct=(c.period.year if c.period else None)==expected
            totals['periods_correct']+=int(correct); totals['typed_periods']+=int(c.period is not None)
            unit='PERCENT' if case['id']=='segment' and index==2 else case['expected_unit']
            scale=Decimal(1) if unit=='PERCENT' else Decimal(case['scale'])
            totals['units_correct']+=int(c.unit==unit and c.multiplier==scale)
            totals['partial_cells']+=int(c.status=='PARTIAL_CONTEXT'); totals['verified_cells']+=int(c.status=='VERIFIED_CONTEXT')
        for _ in range(5):
            build_table_evidence(p,ctx)
        for _ in range(100):
            start=time.perf_counter(); build_table_evidence(p,ctx); timings.append((time.perf_counter()-start)*1000)
        rows.append({'id':case['id'],'family':case['family'],'parent_id':p.chunk_id,'parent_hash':e.parent_payload_hash,
            'status':result.status,'input_parent_bytes':len(p.model_dump_json().encode()),'parent_text_bytes':len(p.text.encode()),
            'full_evidence_bytes':len(result.model_dump_json().encode()),'compact_bytes':len(canonical(compact_view(e)).encode())})
    # Bounded larger fixture: 100 rows/303 physical cells, five selected parents.
    parents,raw,meta,binding=fixture(cases[0],rows=100)
    tracemalloc.start(); start=time.perf_counter(); context=context_from_snapshot(raw,meta,binding)
    preparation_ms=(time.perf_counter()-start)*1000
    large_times=[]
    for _ in range(20):
        start=time.perf_counter(); bundle=build_evidence_bundle(parents[-5:],context); large_times.append((time.perf_counter()-start)*1000)
    _,peak=tracemalloc.get_traced_memory(); tracemalloc.stop()
    output={'environment':{'python':platform.python_version(),'os':platform.platform(),'cpu':platform.processor()},
        'fixture_sha256':sha256(CASES_PATH.read_bytes()).hexdigest(),'fixture_canonical_hash':digest(cases),
        'implementation_files_sha256':{str(p.relative_to(CASES_PATH.parents[3])).replace('\\','/'):sha256(p.read_bytes()).hexdigest()
            for p in sorted((CASES_PATH.parents[3]/'app/table_evidence').glob('*.py'))},
        'denominators':{'financial_value_cells':totals['cells'],'parents':len(cases),'synthetic_table_families':6},
        'correctness':totals,'cases':rows,'warm_build':distribution(timings),'first_call_after_imports':distribution(first_calls),
        'context_reconstruction_first_call':distribution(context_timings),
        'larger_fixture':{'source_bytes':len(raw),'rows':100,'physical_cells':303,'selected_parents':5,
            'context_reconstruction_ms':preparation_ms,'bundle_build_with_tracemalloc':distribution(large_times),
            'python_peak_traced_bytes':peak,'last_bundle_bytes':len(bundle.model_dump_json().encode())},
        'limits':['Synthetic development oracles, not SEC/held-out evidence.','No cold-process/disk-cache or end-to-end retrieval measurement.',
                  'Context parsing is separate from candidate build.','Tracemalloc is Python allocation peak, not process RSS.',
                  'Unsupported change-column periods remain unresolved and included in denominator.']}
    print(json.dumps(output,indent=2,ensure_ascii=False))


if __name__=='__main__':
    main()

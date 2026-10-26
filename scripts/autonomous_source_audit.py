"""Read-only D2 retained-source diagnostic; never opens a Qdrant/index engine.

Usage: python -m scripts.autonomous_source_audit --index <accepted SQLite path>
Output is JSON stdout. Child verification is bounded to one source at a time.
"""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import time

from app.financial_index.corpus import digest_file, canonical

CASES={
 'income':'fin_19d2cfc014d0fa3de5de7388f8fc10a4',
 'balance':'fin_5bfa952d62635c58a11a200e85a0e38e',
 'cashflow':'fin_109254de42ad309951696ba81ea6dc04',
 'eps':'fin_cb5fd1b6ac172b0d600dd27213b06cfa',
 'segment':'fin_16dad97ca625b02269e2de09fbd6b28c',
 'fair_value':'fin_5effdf056e993e8bf68080bb9742de49',
}


def worker():
    import app.financial_index.corpus as corpus
    from app.financial_index.corpus import verified_source
    from app.financial_ingestion.pipeline import validate_metadata_identity
    from app.financial_ingestion.schemas import StructuredFiling
    spec=json.load(sys.stdin); source=spec['source']
    saved=StructuredFiling.model_validate_json(Path(source['structured_path']).read_bytes())
    validate_metadata_identity(saved.metadata)
    timings={}
    for name in ['_verified_bytes','digest_file','parse_sec_html','chunk_filing','normalized_filing_text']:
        original=getattr(corpus,name)
        def measured(*args,_name=name,_original=original,**kwargs):
            start=time.perf_counter()
            try:return _original(*args,**kwargs)
            finally:timings[_name]=timings.get(_name,0)+(time.perf_counter()-start)*1000
        setattr(corpus,name,measured)
    start=time.perf_counter(); parents=verified_source(source,generation=spec['generation'])
    elapsed=(time.perf_counter()-start)*1000
    result={'c_verification':'VERIFIED','c_verify_ms':elapsed,'stage_ms':timings,'parent_count':len(parents),'parents':{}}
    for cid in spec['ids']:
        p=parents[cid]
        result['parents'][cid]={'payload_hash':sha256(canonical(p.model_dump(mode='json')).encode()).hexdigest(),
          'row':p.metadata.get('row_index'),'table_id':p.metadata.get('table_id'),
          'source_locator':p.source_location.model_dump(mode='json'),
          'raw_cells':p.metadata.get('cells'),'column_labels':p.metadata.get('column_labels'),
          'unit_context':p.metadata.get('unit_context'),'row_label':p.metadata.get('row_label'),
          'cik':p.metadata.get('cik'),'accession':p.metadata.get('accession_number')}
    print(json.dumps(result))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--index',type=Path)
    parser.add_argument('--worker',action='store_true');args=parser.parse_args()
    if args.worker:
        worker();return
    path=args.index.resolve(); before=digest_file(path); groups={}; cases=[]
    with sqlite3.connect(path.as_uri()+'?mode=ro&immutable=1',uri=True) as c:
        for family,cid in CASES.items():
            row=c.execute('SELECT d.payload,d.payload_hash,m.source,m.generation,g.metadata '
                'FROM documents d JOIN members m ON d.cid=m.cid JOIN generations g ON m.generation=g.generation '
                'WHERE d.cid=? AND g.state=?',(cid,'READY')).fetchone()
            if row is None:
                cases.append({'family':family,'parent_id':cid,'status':'NOT_TESTED_SOURCE_ABSENT'});continue
            payload=json.loads(row[0]); source=json.loads(row[2]); generation=row[3]
            from app.financial_ingestion.schemas import DatasetManifest
            manifests=[DatasetManifest.model_validate(s['manifest']) for s in json.loads(row[4])['sources']]
            if not any(m.manifest_hash==source['manifest_hash'] and m.content_hash()==m.manifest_hash and source['filing_id'] in m.filing_ids for m in manifests):
                raise ValueError('UPSTREAM_MANIFEST_LINEAGE_MISMATCH')
            assert sha256(canonical(payload).encode()).hexdigest()==row[1]
            group=groups.setdefault(source['raw_hash'],{'source':source,'generation':generation,'ids':[]})
            group['ids'].append(cid)
            cases.append({'family':family,'parent_id':cid,'payload_hash':row[1],'filing_id':source['filing_id'],
                          'raw_sha256':source['raw_hash'],'manifest_hash':source['manifest_hash'],'generation':generation})
    outputs={}
    for key,spec in groups.items():
        s=spec['source']; hashes={k:digest_file(Path(s[k+'_path'])) for k in ['raw','structured','chunks']}
        assert all(hashes[k]==s[k+'_hash'] for k in hashes)
        # No large unbounded subprocess/experiment: two known sources only.
        start=time.perf_counter()
        p=subprocess.run([sys.executable,'-m','scripts.autonomous_source_audit','--worker'],
            input=json.dumps(spec),capture_output=True,text=True,timeout=90)
        verified=json.loads(p.stdout) if p.returncode==0 else {'c_verification':'FAILED','error_type':'SOURCE_VERIFICATION_WORKER_FAILED'}
        verified['child_total_ms']=(time.perf_counter()-start)*1000
        verified['raw_bytes']=Path(s['raw_path']).stat().st_size
        verified['d2_context_status']='UNSUPPORTED_SOURCE_SIZE' if verified['raw_bytes']>250000 else 'ELIGIBLE_FOR_D2_CONTEXT'
        verified['hashes_unchanged_after']=all(digest_file(Path(s[k+'_path']))==v for k,v in hashes.items())
        outputs[key]=verified
    for case in cases:
        if 'raw_sha256' in case:
            result=outputs[case['raw_sha256']]; parent=result.get('parents',{}).get(case['parent_id'])
            if parent:assert parent['payload_hash']==case['payload_hash']
            case['observed']=parent;case['c_verification']=result['c_verification'];case['d2_status']=result['d2_context_status']
            case['d2_observed_value']=None;case['d2_header_path']=None
    print(json.dumps({'cases':cases,'source_verifications':outputs,'index_bytes_unchanged':digest_file(path)==before,
        'limits':['Consumed sources are development diagnostics only.','Full D2 source context NOT built above250KB.',
                  'No source window/limit bypass; no real D2 VERIFIED_CONTEXT claim.']},indent=2))


if __name__=='__main__':main()

"""Read-only SEC source diagnostics on the isolated owned research snapshot."""
import argparse
from collections import Counter
from contextlib import closing
import json
from pathlib import Path
from app.research_qa.backend import ResearchBackend
import app.table_evidence.real_source as real


LABELS={'net sales','revenue','total revenue','total assets','cash and cash equivalents',
        'net cash provided by operating activities','basic earnings per share',
        'diluted earnings per share','carrying amount','fair value'}


def run(root):
    backend=ResearchBackend(root);snapshot=backend.adapter
    with closing(snapshot.lexical.connect()) as db:
        rows=db.execute('SELECT cid,cik,payload FROM documents ORDER BY cik,cid').fetchall()
    selected=[]
    for cid,cik,raw in rows:
        p=json.loads(raw);label=p['metadata'].get('row_label','').strip().casefold()
        if label in LABELS and p['kind']=='table':selected.append((cid,cik,label,p))
    findings=[];original=real.derive_cell
    try:
        for cid,cik,label,p in selected:
            failures=[]
            def capture(parent,table,cell,resources,**kwargs):
                try:return original(parent,table,cell,resources,**kwargs)
                except ValueError as exc:
                    failures.append({'row':cell.row,'column':cell.column,'text':cell.text[:100],
                                     'facts':[{'name':f.get('name'),'scale':f.get('scale'),'contextref':f.get('contextref')}
                                              for f in cell.numeric_facts[:2]],'reason':str(exc)})
                    raise
            real.derive_cell=capture
            try:
                cells=real.verified_real_cells(snapshot,cid)
                status='VERIFIED_CELLS' if cells else 'NO_SUPPORTED_CELL'
                reason=None
            except (ValueError,RuntimeError) as exc:
                cells=();status='SOURCE_REJECTED';reason=str(exc)
            findings.append({'cik':cik,'parent_id':cid,'row_label':label,
                             'filing_id':p['filing_id'],'table_id':p['source_location'].get('table_id'),
                             'source_url':p['metadata'].get('source_url'),'status':status,'source_error':reason,
                             'cells':[c.model_dump(mode='json') for c in cells],
                             'attempted_cells':len(failures),'failures':failures[:12],
                             'failure_counts':dict(Counter(f['reason'] for f in failures))})
    finally:real.derive_cell=original
    return {'schema_version':'topic3-p8-source-diagnostics/v1','read_only':True,
            'manifest_hash':snapshot.freeze['manifest_hash'],'generation':snapshot.freeze['generation'],
            'source_cases':findings}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    result=run(args.root);args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'cases':len(result['source_cases']),
        'supported':sum(x['status']=='VERIFIED_CELLS' for x in result['source_cases'])}))

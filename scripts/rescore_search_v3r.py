"""Recompute explicit locator metrics from saved raw hits;does not rerun or tune search."""
import argparse,json,sys,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.benchmark_search_v3r import scores,summarize
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',required=True);p.add_argument('--qrels',required=True);p.add_argument('--output',required=True);a=p.parse_args();output=Path(a.output)
    if output.exists():raise ValueError('NEW_RESULT_REQUIRED')
    report=json.loads(Path(a.input).read_text(encoding='utf-8'));qs={q['id']:q for q in map(json.loads,Path(a.qrels).read_text(encoding='utf-8').splitlines())}
    for r in report['records']:r['metrics']=scores(qs[r['id']],{'results':r['results'],'evidence_status':r.get('evidence_status')})
    report['summaries']=summarize(report['records']);report['stratified']={str(v):summarize([r for r in report['records'] if r['strata'].get('pdf_type')==v]) for v in {q.get('strata',{}).get('pdf_type') for q in qs.values()}}
    report['rescored_from_raw_sha256']=hashlib.sha256(Path(a.input).read_bytes()).hexdigest();output.write_text(json.dumps(report,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')

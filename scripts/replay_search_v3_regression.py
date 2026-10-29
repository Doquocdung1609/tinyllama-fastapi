"""Replay immutable V2's70 exposed questions against V3; never independent test data."""
import argparse,json,sys,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.product.workspace import PdfWorkspace
from app.product.search_v3 import FinancialSearchV3,search_sec_v3
from app.product.sec_search import SecResearchIndex
from scripts.benchmark_search_v2 import score_query
from scripts.benchmark_search_v3 import policy_hash


def replay(root,sec_root,sec_vectors,output):
    root=Path(root);output=Path(output)
    if output.exists() or not (root/'search-v2-experiment.json').exists():raise ValueError('NEW_RESULT_AND_OWNED_CLONE_REQUIRED')
    repo=Path(__file__).resolve().parents[1];qrels=repo/'docs/search_v2/SEARCH_BENCHMARK_QRELS.jsonl'
    w=PdfWorkspace(root);sec=SecResearchIndex(Path(sec_root),Path(sec_vectors));v=FinancialSearchV3(w,root/'v3-regression-sidecar');records=[];frozen=policy_hash()
    try:
        for line in qrels.read_text(encoding='utf-8').splitlines():
            q=json.loads(line)
            result=search_sec_v3(sec,q['query'],'hybrid',10,q['ticker']) if q['source']=='SEC' else v.search(q['query'],'hybrid',10,q['document_ids'])
            records.append({'id':q['id'],'family':q['family'],'metrics':score_query(q,result),'results':[{k:h.get(k) for k in ['page','row_id','chunk_id','evidence_match','numeric_answer_eligible','conflicts']} for h in result['results'][:10]],'reason':result.get('reason')})
            print(q['id'],flush=True)
        if policy_hash()!=frozen:raise ValueError('POLICY_CHANGED_DURING_REPLAY')
        data={'scope':'70 exposed V2 queries,regression only','policy_sha256':frozen,'qrels_sha256':hashlib.sha256(qrels.read_bytes()).hexdigest(),'harness_sha256':hashlib.sha256(Path(__file__).read_text(encoding='utf-8').encode()).hexdigest(),'records':records}
        output.write_text(json.dumps(data,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
    finally:w.close();sec.close()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',required=True);p.add_argument('--sec-root',required=True);p.add_argument('--sec-vectors',required=True);p.add_argument('--output',required=True);a=p.parse_args();replay(a.root,a.sec_root,a.sec_vectors,a.output)

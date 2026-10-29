"""Eight-arm, source-scoped V3 evaluation. Freeze before reserved-source annotation."""
import argparse,hashlib,json,statistics,sys,time
from datetime import datetime,timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import psutil
from app.product.workspace import PdfWorkspace
from app.product.search_v2 import FinancialSearchV2,EXPERIMENTS
from app.product.search_v3 import FinancialSearchV3,search_sec_v3
from app.product.sec_search import SecResearchIndex
from scripts.benchmark_search_v2 import score_query,percentile

REPO=Path(__file__).resolve().parents[1]
POLICY_FILES=['app/product/search_v3.py','app/product/search_v2.py','app/product/query_intent.py','app/product/pdf_extract.py','app/product/workspace.py','app/product/sec_search.py','app/product/frontend_api.py','app/product/analysis.py','frontend/src/Studio.tsx','frontend/src/api.ts','scripts/benchmark_search_v3.py']
ARMS=(*EXPERIMENTS,'V3')


def policy_hash():
    # Canonical text preserves reproducibility across Windows CRLF and Linux LF.
    return hashlib.sha256(json.dumps({p:hashlib.sha256((REPO/p).read_text(encoding='utf-8').encode()).hexdigest() for p in POLICY_FILES},sort_keys=True).encode()).hexdigest()


def summaries(records):
    result={}
    for arm in ARMS:
        rows=[r for r in records if r['arm']==arm and r['status']=='PASS_EXECUTION']
        keys=set(k for r in rows for k,v in r['metrics'].items() if isinstance(v,(int,float)) or v is None)
        metrics={};denominators={}
        for k in sorted(keys):
            values=[r['metrics'][k] for r in rows if isinstance(r['metrics'].get(k),(int,float))]
            metrics[k]=statistics.mean(values) if values else None;denominators[k]=len(values)
        result[arm]={'queries':len(rows),'metrics':metrics,'metric_denominators':denominators,
            'p50_ms':percentile([r['latency_ms'] for r in rows],.5),'p95_ms':percentile([r['latency_ms'] for r in rows],.95)}
    return result


def run(args):
    folder=REPO/'docs/search_v3';lock_path=folder/'POLICY_LOCK.json'
    if args.freeze_policy:
        if lock_path.exists():raise ValueError('POLICY_ALREADY_FROZEN')
        data={'policy_sha256':policy_hash(),'frozen_at_utc':datetime.now(timezone.utc).isoformat(),
            'files':{p:hashlib.sha256((REPO/p).read_text(encoding='utf-8').encode()).hexdigest() for p in POLICY_FILES},
            'hash_convention':'UTF8 canonical text with universal newline normalization',
            'protocol':'Reserved source contents and queries not inspected before this freeze; single Codex annotator, no independent human reviewer.'}
        lock_path.write_text(json.dumps(data,indent=2)+'\n');print('POLICY_FROZEN',data['policy_sha256']);return
    output=Path(args.output)
    if output.exists():raise ValueError('RESULT_EXISTS')
    root=Path(args.root)
    if not (root/'search-v2-experiment.json').exists():raise ValueError('OWNED_CLONE_REQUIRED')
    qrels=Path(args.qrels);questions=[json.loads(s) for s in qrels.read_text(encoding='utf-8').splitlines()]
    selected=[q for q in questions if q['split']==args.split]
    if not selected:raise ValueError('EMPTY_SPLIT')
    frozen=policy_hash()
    if args.split=='locked_test':
        lock=json.loads(lock_path.read_text());manifest=json.loads((folder/'SPLIT_MANIFEST.json').read_text())
        if lock['policy_sha256']!=frozen or manifest['qrels_sha256']!=hashlib.sha256(qrels.read_bytes()).hexdigest():raise ValueError('POLICY_OR_QRELS_CHANGED')
    w=PdfWorkspace(root);sec=None;records=[];peaks=[];started=time.perf_counter()
    try:
        old=FinancialSearchV2(w,root/'v3-comparator-sidecar');v=FinancialSearchV3(w,root/'v3-comparator-sidecar');v.base=old
        t=time.perf_counter();snapshot=old.prepare();prepare_ms=(time.perf_counter()-t)*1000
        if any(q['source']=='SEC' for q in selected):sec=SecResearchIndex(Path(args.sec_root),Path(args.sec_vectors))
        warm=next((q for q in selected if q['source']=='PDF'),None)
        if warm:
            for arm in ARMS:(v.search(warm['query'],'hybrid',10,warm['document_ids']) if arm=='V3' else old.search(warm['query'],'hybrid',10,warm['document_ids'],arm))
        for i,q in enumerate(selected):
            for arm in ARMS:
                t=time.perf_counter()
                if q['source']=='SEC':
                    mode={'B0':'bm25','B1':'dense','B2':'hybrid','C1':'bm25','C2':'hybrid','C3':'hybrid','C4':'hybrid','V3':'hybrid'}[arm]
                    result=search_sec_v3(sec,q['query'],mode,10,q['ticker']) if arm=='V3' else sec.search(q['query'],mode,10,q['ticker'])
                else:result=v.search(q['query'],'hybrid',10,q['document_ids']) if arm=='V3' else old.search(q['query'],'hybrid',10,q['document_ids'],arm)
                elapsed=(time.perf_counter()-t)*1000;peaks.append(psutil.Process().memory_info().rss)
                scores=score_query(q,result);matched=scores['matched_reference_indices'];positive=bool(q['relevant']);hits=result['results'][:10]
                scores['recall_at_1']=len(set(matched[0]))/len(q['relevant']) if positive and matched else 0. if positive else None
                scores['retrieval_false_abstention']=int(not hits) if positive else None
                supports_contract=arm not in {'B0','B1','B2'} and q['source']=='PDF' or arm=='V3'
                eligible=[h for h in hits if h.get('numeric_answer_eligible')]
                scores['correct_numeric_abstention']=int(not eligible) if q['expected_abstention'] and supports_contract else None
                expected=q.get('numeric_eligibility_expected')
                scores['answer_eligibility_correctness']=int(bool(eligible)==expected) if expected is not None and supports_contract else None
                scores['answer_false_abstention']=int(not eligible) if expected is True and supports_contract else None
                scores['wrong_document_at_1']=int(hits[0].get('document_id') not in q['document_ids']) if hits and q['source']=='PDF' else None
                scores['wrong_period_rate']=None;scores['wrong_basis_rate']=None;scores['exact_cell_hit_rate']=None
                records.append({'id':q['id'],'family':q['family'],'arm':arm,'status':'PASS_EXECUTION','latency_ms':elapsed,
                    'source':q['source'],'strata':q.get('strata',{}),'metrics':scores,'reason':result.get('reason'),'evidence_status':result.get('evidence_status'),
                    'hits':[{k:h.get(k) for k in ['rank','document_id','chunk_id','evidence_id','page','row_id','box','source_sha256','numeric_answer_eligible','evidence_match','conflicts']} for h in hits]})
            print(args.split,i+1,'/',len(selected),q['id'],flush=True)
        by_stratum={}
        for dimension in sorted({k for q in selected for k in q.get('strata',{})}):
            for value in sorted({q['strata'][dimension] for q in selected if dimension in q.get('strata',{})}):
                by_stratum[dimension+':'+str(value)]=summaries([r for r in records if r['strata'].get(dimension)==value])
        assert frozen==policy_hash(),'POLICY_CHANGED_DURING_RUN'
        report={'split':args.split,'policy_sha256':frozen,'qrels_sha256':hashlib.sha256(qrels.read_bytes()).hexdigest(),'queries':len(selected),
            'annotation':'PROVISIONAL_CODEX_SOURCE_ANNOTATION; ZERO_INDEPENDENT_HUMAN_REVIEW',
            'summaries':summaries(records),'stratified':by_stratum,'records':records,
            'resources':{'elapsed_s':time.perf_counter()-started,'prepare_ms':prepare_ms,'active_index_bytes':snapshot['path'].stat().st_size,
                'benchmark_process_peak_rss_bytes':max(peaks),'free_disk_bytes':psutil.disk_usage(str(root)).free},
            'limits':['Row/source-hit metrics do not certify requested numeric columns. Exact cell,wrong period,basis unjudged are null.',
                'No independent human labels. SEC comparator C arms retain V2 passthrough; V3 adds parent reranking without generation mutation.',
                'Warm query timing includes source integrity checks; external Ollama/browser memory excluded.',
                'Expected numeric eligibility is null when a gold source has no product-reviewed fact; this is not automatic safety perfection.']}
        output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(report,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
    finally:
        w.close()
        if sec:sec.close()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--freeze-policy',action='store_true');p.add_argument('--root');p.add_argument('--qrels');p.add_argument('--split',choices=['development','locked_test','regression']);p.add_argument('--output');p.add_argument('--sec-root');p.add_argument('--sec-vectors');run(p.parse_args())

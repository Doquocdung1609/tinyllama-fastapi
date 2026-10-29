"""Four source-scoped arms;all old V3 questions are exposed regression only."""
import argparse,json,sys,time,statistics,hashlib,re,math
from pathlib import Path
from contextlib import ExitStack
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.product.workspace import PdfWorkspace
from app.product.derived_workspace import DerivedPdfWorkspace
from app.product.search_v3 import FinancialSearchV3,search_sec_v3
from app.product.search_v3r import FinancialSearchV3R
from app.product.sec_search import SecResearchIndex
from scripts.benchmark_search_v2 import score_query,exact_hit,percentile
import psutil

ARMS=('A0_OLD_V3','A1_NEW_V3','A2_REGION','A3_REGION_LABELS')

def signed_digits(value):
    sign='-' if re.search(r'[-−]',value) or ('(' in value and ')' in value) else ''
    return sign+re.sub(r'\D','',value)

def locator(hit,ref):
    if exact_hit(hit,ref):return True
    if (hit.get('document_id'),hit.get('page'))!=(ref.get('document_id'),ref.get('page')):return False
    # Evaluation only:identical ordered digits locate OCR punctuation errors,never repair data.
    return any(signed_digits(c['text'])==signed_digits(v) and len(re.sub(r'\D','',v))>=6
        for c in hit.get('source_cells',hit.get('_evaluation_cells',[])) for v in ref.get('source_values',[]))

def scores(q,r):
    s=score_query(q,r);refs=q['relevant'];hits=r['results'][:10]
    matches=[{i for i,ref in enumerate(refs) if locator(h,ref)} for h in hits]
    for k in (1,5,10):s[f'digit_locator_recall_at_{k}']=len(set().union(*matches[:k]))/len(refs) if refs else None
    s['digit_locator_mrr_at_5']=next((1/(i+1) for i,m in enumerate(matches[:5]) if m),0.) if refs else None
    s['correct_numeric_abstention']=int(not any(h.get('numeric_answer_eligible') for h in hits)) if q['expected_abstention'] else None
    expected=q.get('numeric_eligibility_expected');s['eligibility_correct']=int(any(h.get('numeric_answer_eligible') for h in hits)==expected) if expected is not None else None
    s['wrong_document_at_1']=int(hits[0].get('document_id') not in q['document_ids']) if hits and q['source']=='PDF' else None
    expected_metrics={ref.get('metric') for ref in refs}-{None}
    top_metrics=set(hits[0].get('metric_ids',[])) if hits else set()
    s['wrong_classified_metric_at_1']=int(not bool(top_metrics&expected_metrics)) if expected_metrics and top_metrics else None
    s['unclassified_metric_at_1']=int(not top_metrics) if expected_metrics and hits else None
    s['wrong_period_rate']=None;s['wrong_basis_rate']=None
    s['exact_cell_hit_at_5']=None
    boxed=[ref for ref in refs if ref.get('independently_located_cell_box')]
    if boxed:
        def cell_match(h,ref):
            if (h.get('document_id'),h.get('page'))!=(ref['document_id'],ref['page']):return False
            window=ref['independently_located_cell_box']
            for c in h.get('source_cells',h.get('_evaluation_cells',[])):
                box=c.get('box')
                if not box or not any(signed_digits(c['text'])==signed_digits(v) for v in ref.get('source_values',[])):continue
                x=(box[0]+box[2])/2;y=(box[1]+box[3])/2
                if window[0]<=x<=window[2] and window[1]<=y<=window[3]:return True
            return False
        s['exact_cell_hit_at_5']=sum(any(cell_match(h,ref) for h in hits[:5]) for ref in boxed)/len(boxed)
    return s

def summarize(records):
    out={}
    for arm in sorted({r['arm'] for r in records}):
        rows=[r for r in records if r['arm']==arm];keys={k for r in rows for k,v in r['metrics'].items() if isinstance(v,(int,float)) or v is None}
        out[arm]={'queries':len(rows),'metrics':{},'denominators':{},'p50_ms':percentile([r['elapsed_ms'] for r in rows],.5),'p95_ms':percentile([r['elapsed_ms'] for r in rows],.95)}
        for k in keys:
            vs=[r['metrics'][k] for r in rows if isinstance(r['metrics'].get(k),(int,float))]
            out[arm]['metrics'][k]=statistics.mean(vs) if vs else None;out[arm]['denominators'][k]=len(vs)
    return out

def run(a):
    output=Path(a.output)
    if output.exists():raise ValueError('RESULT_EXISTS')
    qs=[json.loads(l) for l in Path(a.qrels).read_text(encoding='utf-8').splitlines()]
    new=DerivedPdfWorkspace(Path(a.root));old=[];sec=None;records=[];preparations=[];started=time.perf_counter();peak=0
    try:
        engines={'A1_NEW_V3':FinancialSearchV3(new,new.root/'ablation-v3'),
            'A2_REGION':FinancialSearchV3R(new,new.root/'ablation-region',aliases=False),
            'A3_REGION_LABELS':FinancialSearchV3R(new,new.root/'ablation-labels',aliases=True)}
        for root in a.old_root or []:
            root=Path(root)
            if not (root/'search-v2-experiment.json').exists():raise ValueError('OLD_CLONE_REQUIRED')
            w=PdfWorkspace(root);old.append((w,FinancialSearchV3(w,root/'v3r-old-sidecar')))
        if any(q['source']=='SEC' for q in qs):sec=SecResearchIndex(Path(a.sec_root),Path(a.sec_vectors))
        for name,e in engines.items():
            t=time.perf_counter();e.base.prepare();e._source_entries(e.base.prepare(),{d['id']:d for d in new.list_documents()});preparations.append({'arm':name,'ms':(time.perf_counter()-t)*1000})
        for q in qs:
            for arm in ARMS if old else ('A3_REGION_LABELS',):
                w=new
                if q['source']=='SEC':engine=None
                elif arm=='A0_OLD_V3':
                    w,engine=next((w,e) for w,e in old if set(q['document_ids'])<={d['id'] for d in w.list_documents()})
                else:engine=engines[arm]
                t=time.perf_counter();r=search_sec_v3(sec,q['query'],'hybrid',10,q['ticker']) if engine is None else engine.search(q['query'],'hybrid',10,q['document_ids']);elapsed=(time.perf_counter()-t)*1000
                for h in r['results']:
                    if h.get('row_id') and 'source_cells' not in h:
                        row=next((row for row in w.page_evidence(h['document_id'],h['page'])['tables'] if row['id']==h['row_id']),None)
                        if row:h['_evaluation_cells']=row['cells']
                record={'id':q['id'],'arm':arm,'source':q['source'],'strata':q.get('strata',{}),'status':'PASS_EXECUTION','elapsed_ms':elapsed,'generation':r.get('generation'),'metrics':scores(q,r),'reason':r.get('reason'),'evidence_status':r.get('evidence_status'),'results':r['results']}
                records.append(record);peak=max(peak,psutil.Process().memory_info().rss)
            print(q['id'],flush=True)
        report={'annotation':'PROVISIONAL_AGENT_ANNOTATED','qrels_sha256':hashlib.sha256(Path(a.qrels).read_bytes()).hexdigest(),'scope':a.scope,'summaries':summarize(records),'records':records,'prepare':preparations,
            'resources':{'elapsed_s':time.perf_counter()-started,'sampled_python_peak_rss':peak,'free_disk_bytes':psutil.disk_usage(str(new.root)).free},
            'stratified':{str(v):summarize([r for r in records if r['strata'].get('pdf_type')==v]) for v in {q.get('strata',{}).get('pdf_type') for q in qs}},
            'limits':['Original exact source-span metrics retained alongside evaluation-only digit locator metrics;no runtime value repair.','Unjudged period/basis/full-column accuracy remains null. No independent human reviewer.']}
        output.write_text(json.dumps(report,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
    finally:
        new.close()
        for w,e in old:w.close()
        if sec:sec.close()

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',required=True);p.add_argument('--old-root',action='append');p.add_argument('--qrels',required=True);p.add_argument('--output',required=True);p.add_argument('--scope',default='EXPOSED_REGRESSION');p.add_argument('--sec-root');p.add_argument('--sec-vectors');run(p.parse_args())

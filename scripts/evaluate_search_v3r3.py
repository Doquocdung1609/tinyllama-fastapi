"""Paired, exposed-set precision accounting; does not edit labels or raw runs."""
import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before',type=Path,required=True)
    parser.add_argument('--after',type=Path,required=True)
    parser.add_argument('--qrels',type=Path,action='append',required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    before=json.loads(args.before.read_text(encoding='utf-8'))
    after=json.loads(args.after.read_text(encoding='utf-8'))
    labels={q['id']:q for path in args.qrels for q in map(json.loads,path.read_text(encoding='utf-8').splitlines())}
    old={r['id']:r for r in before['records']}
    new={r['id']:r for r in after['records']}
    if set(old)!=set(new) or set(old)!=set(labels):raise ValueError('PAIRED_QUERY_IDS_DIFFER')

    def metrics(records,ids):
        counts=Counter();values=defaultdict(list)
        for id in ids:
            r=records[id];q=labels[id];hit=r['results'][0] if r['results'] else None
            counts['queries']+=1
            if q.get('expected_abstention') is False:
                counts['source_positive']+=1
                for name in ['digit_locator_recall_at_5','digit_locator_mrr_at_5','exact_evidence_hit_at_1','exact_cell_hit_at_5','ndcg_at_5']:
                    v=r['metrics'].get(name)
                    if v is not None:values[name].append(v)
                expected=set(r['intent'].get('metrics') or [])
                if expected:
                    counts['metric_labeled_positive']+=1
                    actual=set(hit.get('metric_ids') or []) if hit else set()
                    if expected&actual:counts['correct_metric_top1']+=1
                    elif actual:counts['known_wrong_metric_top1']+=1
                    else:counts['unclassified_metric_top1']+=1
                else:counts['intent_metric_unjudged']+=1
            if q.get('expected_abstention') is True:
                counts['numeric_negative']+=1
                counts['numeric_negative_abstained']+=int(not any(h.get('numeric_answer_eligible') for h in r['results']))
            if q.get('numeric_eligibility_expected') is True:
                counts['positive_numeric_eligible']+=1
                counts['positive_false_abstention']+=int(not any(h.get('numeric_answer_eligible') for h in r['results']))
        return {'counts':dict(counts),'averages':{name:{'value':sum(v)/len(v),'denominator':len(v)} for name,v in values.items()}}

    all_ids=sorted(labels)
    strata={}
    for dimension in ['pdf_type','content','language','form','pages','answerability']:
        groups=defaultdict(list)
        for id,q in labels.items():groups[str(q.get('strata',{}).get(dimension,'UNSPECIFIED'))].append(id)
        strata[dimension]={name:{'before':metrics(old,ids),'after':metrics(new,ids)} for name,ids in sorted(groups.items())}
    changes=[]
    for id in all_ids:
        o=old[id]['metrics'];n=new[id]['metrics'];before_hit=old[id]['results'][0] if old[id]['results'] else None;after_hit=new[id]['results'][0] if new[id]['results'] else None
        if (o.get('digit_locator_recall_at_5'),o.get('exact_evidence_hit_at_1'),(before_hit or {}).get('metric_ids')) != (n.get('digit_locator_recall_at_5'),n.get('exact_evidence_hit_at_1'),(after_hit or {}).get('metric_ids')):
            changes.append({'id':id,'query':labels[id]['query'],'before_source_r5':o.get('digit_locator_recall_at_5'),'after_source_r5':n.get('digit_locator_recall_at_5'),'before_exact_evidence_top1':o.get('exact_evidence_hit_at_1'),'after_exact_evidence_top1':n.get('exact_evidence_hit_at_1'),'before_top1':{k:(before_hit or {}).get(k) for k in ['page','row_label','metric_ids','evidence_match','numeric_answer_eligible']},'after_top1':{k:(after_hit or {}).get(k) for k in ['page','row_label','metric_ids','evidence_match','numeric_answer_eligible']}})
    result={'status':'EXPOSED_REGRESSION_ONLY','query_count':len(all_ids),'new_independent_eval':'NEW_INDEPENDENT_EVAL_NOT_AVAILABLE','before':metrics(old,all_ids),'after':metrics(new,all_ids),'strata':strata,'changed_top1_or_source':changes,'unmeasured':['wrong_period_rate','wrong_basis_rate','wrong_unit_rate'],'limits':['Agent-prepared references are not human review.','Unclassified Top-1 is counted separately from correct and known-wrong.','Source retrieval metrics do not establish financial numeric correctness.']}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'queries':len(all_ids),'before_metric':result['before']['counts'],'after_metric':result['after']['counts'],'top1_or_source_changes':len(changes)},ensure_ascii=False))


if __name__=='__main__':main()

"""Frozen metric definitions. No retrieval/model calls or ground-truth invention."""
from math import log2
import statistics


def retrieval_metrics(ids,relevance,groups):
    if len(ids)!=len(set(ids)):raise ValueError('DUPLICATE_RANKED_IDS')
    if any(type(v) is not int or v not in {0,1,2} for v in relevance.values()):raise ValueError('INVALID_RELEVANCE')
    gold={k for k,v in relevance.items() if v>=1};direct={k for k,v in relevance.items() if v>=2}
    result={}
    for k in [5,10]:
        top=ids[:k];result[f'recall@{k}']=len(set(top)&gold)/len(gold) if gold else None
        result[f'group_coverage@{k}']=sum(bool(set(g)&set(top)) for g in groups)/len(groups) if groups else None
    result['precision@5']=sum(cid in gold for cid in ids[:5])/5
    result['mrr@5']=next((1/(i+1) for i,cid in enumerate(ids[:5]) if cid in direct),0) if direct else None
    dcg=sum((2**relevance.get(cid,0)-1)/log2(i+2) for i,cid in enumerate(ids[:5]))
    ideal=sum((2**v-1)/log2(i+2) for i,v in enumerate(sorted(relevance.values(),reverse=True)[:5]))
    result['ndcg@5']=dcg/ideal if ideal else None
    return result


def means(records):
    if not records:return {}
    return {k:statistics.mean([r[k] for r in records if r[k] is not None]) if any(r[k] is not None for r in records) else None for k in records[0]}


def paired(left,right):
    if set(left)!=set(right):raise ValueError('UNPAIRED_QUERIES')
    return {k:{m:right[k][m]-left[k][m] if left[k][m] is not None and right[k][m] is not None else None for m in left[k]} for k in sorted(left)}

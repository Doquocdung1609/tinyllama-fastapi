"""Read-only D1 scope inspection for candidate real instant balance queries."""
import argparse,json
from pathlib import Path
from app.research_qa.backend import ResearchBackend
from app.research_qa.source_alias import verified_alias_catalog
from app.financial_query import resolve_financial_query

QUERIES=("What were P&G's total assets as of September 30, 2026?",
         "What were HD total assets as of August 2, 2026?",
         "What were P&G's total assets as of June 30, 2026?")

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args()
    b=ResearchBackend(a.root);catalog=verified_alias_catalog(b.adapter)
    for q in QUERIES:
        r=resolve_financial_query(q,{},catalog);s=r.resolved_scope
        print(json.dumps({'query':q,'status':r.status.value,
                          'metrics':[m.model_dump(mode='json') for m in r.query_intent.metric_mentions],
                          'periods':[p.model_dump(mode='json') for p in s.requested_periods] if s else [],
                          'filings':list(s.eligible_filing_ids) if s else [],
                          'reasons':list(s.resolution_reasons) if s else []}))

"""Read-only development QA probes; source values are never retrieval hints."""
import argparse,json
from pathlib import Path
from app.research_qa.backend import ResearchBackend

CASES=(
 ('pg_assets_2026',"What were P&G's total assets as of September 30, 2026?",{}),
 ('pg_assets_2026_prior',"What were P&G's total assets as of June 30, 2026?",{}),
 ('hd_assets_2026',"What were HD total assets as of August 2, 2026?",{}),
 ('hd_assets_2026_prior',"What were HD total assets as of February 1, 2026?",{}),
 ('hd_assets_compare',"Compare HD total assets as of February 1, 2026 and as of August 2, 2026.",{}),
 ('pg_assets_compare',"Compare P&G total assets as of June 30, 2026 and as of September 30, 2026.",{}),
 ('pg_net_sales_control',"What were P&G's net sales for the three months ended September 30, 2026?",{}),
 ('hd_net_sales_unsupported',"What were HD net sales for the quarter ended August 2, 2026?",{}),
 ('cost_assets_unsupported',"What were COST total assets as of May 10, 2026?",{}),
 ('wrong_period',"What were HD total assets as of August 2, 2024?",{}),
 ('conflicting_cik',"What were HD total assets as of August 2, 2026?",{'cik':'0000080424'}),
 ('wrong_unit',"What were HD total assets in thousands as of August 2, 2026?",{}),
 ('fair_value_refusal',"What were HD total assets fair value as of August 2, 2026?",{}),
)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
 p.add_argument('--output',type=Path,required=True);a=p.parse_args();backend=ResearchBackend(a.root)
 rows=[]
 for name,q,filters in CASES:
  try:
   response=backend.query(q,filters,'B','EXTRACT',5,False,'automatic_real')
   rows.append({'case_id':name,'question':q,'filters':filters,'response':response})
  except (ValueError,RuntimeError) as exc:
   rows.append({'case_id':name,'question':q,'filters':filters,'error':str(exc)[:150]})
 result={'schema_version':'topic3-p8-real-qa-development/v1','heldout_used':False,
         'manifest_hash':backend.adapter.freeze['manifest_hash'],'generation':backend.adapter.freeze['generation'],
         'cases':rows}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps([(r['case_id'],r.get('response',{}).get('answer',{}).get('status'),
                    r.get('response',{}).get('answer',{}).get('result_values'),
                    r.get('response',{}).get('failure_code')) for r in rows]))

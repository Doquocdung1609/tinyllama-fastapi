"""Bounded official SEC acquisition into a NEW explicitly owned research root.

No existing corpus is ingested or changed. A403 stops the affected acquisition
chain; do not evade with another identity/source. Contact identity is not logged.
"""
import argparse
from datetime import datetime,timezone
from hashlib import sha256
import json
import os
from pathlib import Path

from dotenv import dotenv_values
from app.financial_ingestion.sec_client import SECClient,SECRequestError

PLAN=(('JPM','0000019617','dev'),('PG','0000080424','dev'),('COST','0000909832','validation'),('HD','0000354950','heldout'))
OWNER='TOPIC3_AUTONOMOUS_D2_TO_D5_GATED_EXECUTION_AUTHORIZED'


def owned_root(path):
    root=path.resolve(); marker=root/'ownership.json'
    if root.exists():
        if not marker.is_file() or json.loads(marker.read_text()).get('owner')!=OWNER:
            raise ValueError('RESEARCH_STORAGE_OWNERSHIP_REQUIRED')
    else:
        root.mkdir(parents=True)
        marker.write_text(json.dumps({'owner':OWNER,'namespace':'topic3-autonomous-v1','accepted_owner_data':False}))
    return root


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True);p.add_argument('--env-file',type=Path)
    args=p.parse_args();root=owned_root(args.root)
    env=dotenv_values(args.env_file) if args.env_file else {}
    identity=os.getenv('SEC_USER_AGENT') or env.get('SEC_USER_AGENT','')
    result={'schema_version':'topic3-sec-probe/v1','plan_fixed_before_acquisition':PLAN,'records':[],
        'limits':{'requests_per_second':1,'retries':0,'request_timeout_seconds':10,'documents_max':4,'bytes_per_document_max':4*1024*1024},
        'no_ranking_executed':True,'timestamp_utc':datetime.now(timezone.utc).isoformat()}
    try:client=SECClient(identity,requests_per_second=1,timeout_seconds=10,max_retries=0)
    except ValueError:
        result['status']='BLOCKED_SEC_IDENTITY';print(json.dumps(result,indent=2));return
    except RuntimeError:
        result['status']='BLOCKED_SEC_IDENTITY';print(json.dumps(result,indent=2));return
    blocked=None
    for ticker,cik,split in PLAN:
        record={'ticker':ticker,'cik':cik,'partition':split}
        if blocked:
            record['status']='BLOCKED_AFTER_PUBLIC_SOURCE_FAILURE';record['reason']=blocked
        else:
            try:
                filings=client.discover(cik,ticker=ticker,forms=['10-Q'],date_to='2026-10-26',limit=1)
                if not filings:
                    record['status']='NO_OFFICIAL_FILING_AVAILABLE'
                else:
                    m=filings[0];record['metadata']=m.model_dump(mode='json')
                    target=root/'raw'/cik/m.accession_number/m.primary_document
                    if target.exists():
                        record['status']='EXISTING_ISOLATED_BYTES_NOT_REPLACED'
                    else:
                        download=client.download(m.source_url,target,max_bytes=4*1024*1024)
                        record['status']='ACQUIRED_OFFICIAL_SOURCE';record['retrieved_at']=download.retrieved_at
                    record['source_sha256']=sha256(target.read_bytes()).hexdigest();record['source_bytes']=target.stat().st_size
                    record['relative_path']=target.relative_to(root).as_posix()
            except SECRequestError as exc:
                record['status']='PUBLIC_SOURCE_REQUEST_FAILED';record['http_status']=exc.status_code
                record['error_type']=type(exc).__name__
                if 'exceeds configured' in str(exc):
                    record['reason']='SOURCE_BYTES_BUDGET_EXCEEDED'
                    # A per-document budget is not a network-wide denial. Keep
                    # the source excluded and inspect only the fixed remaining plan.
                else:
                    record['reason']='OFFICIAL_REQUEST_FAILED';blocked=f'SEC_HTTP_{exc.status_code}'
            except Exception as exc:
                record['status']='PUBLIC_SOURCE_PROBE_FAILED';record['error_type']=type(exc).__name__;blocked=type(exc).__name__
        result['records'].append(record)
    result['status']='BLOCKED_PUBLIC_SOURCE' if blocked else 'SOURCE_AUDIT_REQUIRED'
    client.session.close()
    print(json.dumps(result,indent=2,ensure_ascii=False))


if __name__=='__main__':main()

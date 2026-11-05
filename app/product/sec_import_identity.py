"""Fail-closed identity check on original official inline-XBRL bytes."""
from app.financial_ingestion.html_parser import TreeParser,_walk
from datetime import datetime

def validate(raw,metadata):
    parser=TreeParser();parser.feed(raw.decode('utf-8',errors='strict'))
    found={}
    for node,_ in _walk(parser.root):
        name=(node.attrs.get('name') or '').split(':')[-1].casefold()
        if name in {'entitycentralindexkey','documenttype','documentperiodenddate'}:
            found.setdefault(name,set()).add(node.text().strip())
    expected={'entitycentralindexkey':metadata.cik,'documenttype':metadata.form_type.removesuffix('/A'),'documentperiodenddate':metadata.report_date}
    for name,value in expected.items():
        values=found.get(name,set())
        if name=='entitycentralindexkey':values={v.zfill(10) for v in values}
        if name=='documentperiodenddate':
            normalized=set()
            for v in values:
                for pattern in ('%Y-%m-%d','%B %d, %Y','%b %d, %Y'):
                    try:normalized.add(datetime.strptime(v,pattern).date().isoformat());break
                    except ValueError:continue
            values=normalized
        if not value or values!={value}:raise ValueError('SEC_SOURCE_IDENTITY_REQUIRES_REVIEW_'+name.upper())
    return {'identity':'VERIFIED_FROM_ORIGINAL_DEI','cik':metadata.cik,'form':metadata.form_type,'report_end':metadata.report_date}

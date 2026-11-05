"""Fail-closed identity check on original official inline-XBRL bytes."""
from app.financial_ingestion.html_parser import TreeParser,_walk
from datetime import datetime
import re

def validate(raw,metadata):
    parser=TreeParser();parser.feed(raw.decode('utf-8',errors='strict'))
    found={}
    end_by_context={}
    period_facts=[]
    for node,_ in _walk(parser.root):
        if node.tag=='xbrli:context':
            ends={child.text().strip() for child,_ in _walk(node) if child.tag in {'xbrli:enddate','xbrli:instant'}}
            if len(ends)==1:
                end_by_context[node.attrs.get('id')]=next(iter(ends))
        name=(node.attrs.get('name') or '').split(':')[-1].casefold()
        if name in {'entitycentralindexkey','documenttype','entityregistrantname','documentfiscalyearfocus','documentfiscalperiodfocus'}:
            found.setdefault(name,set()).add(' '.join(node.text().split()))
        if name=='documentperiodenddate':
            period_facts.append((' '.join(node.text().split()),node.attrs.get('contextref')))
    expected={'entitycentralindexkey':metadata.cik,'documenttype':metadata.form_type.removesuffix('/A'),'documentperiodenddate':metadata.report_date}
    for name,value in expected.items():
        values=found.get(name,set())
        if name=='entitycentralindexkey':values={v.zfill(10) for v in values}
        if name=='documentperiodenddate':
            normalized=set()
            for raw_date,context_ref in period_facts:
                raw_date=re.sub(r'\s*,\s*',', ',raw_date)
                parsed=None
                for pattern in ('%Y-%m-%d','%B %d, %Y','%b %d, %Y','%B %d,%Y','%b %d,%Y','%m/%d/%Y'):
                    try:
                        parsed=datetime.strptime(raw_date,pattern).date().isoformat()
                        break
                    except ValueError:
                        continue
                if parsed is None and context_ref in end_by_context:
                    # Some displayed DEI dates omit the year. Require the
                    # associated iXBRL context to prove the entire end date.
                    end=end_by_context[context_ref]
                    try:
                        context_end=datetime.fromisoformat(end).date()
                        for pattern in ('%B %d','%b %d','%m/%d'):
                            try:
                                day=datetime.strptime(raw_date+' '+str(context_end.year),pattern+' %Y').date()
                            except ValueError:
                                continue
                            if day==context_end:
                                parsed=context_end.isoformat()
                                break
                    except ValueError:
                        pass
                normalized.add(parsed or 'UNVERIFIED')
            values=normalized
        if not value or values!={value}:raise ValueError('SEC_SOURCE_IDENTITY_REQUIRES_REVIEW_'+name.upper())
    def unique(key):
        values=found.get(key,set())
        return next(iter(values)) if len(values)==1 else None
    year=unique('documentfiscalyearfocus')
    return {'company_name':unique('entityregistrantname'),'fiscal_year':int(year) if year and year.isdecimal() else None,
            'fiscal_period':unique('documentfiscalperiodfocus'),'identity':'VERIFIED_FROM_ORIGINAL_DEI','cik':metadata.cik,'form':metadata.form_type,'report_end':metadata.report_date}

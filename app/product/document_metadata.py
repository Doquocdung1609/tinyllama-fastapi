"""Source-first metadata and a separate auditable user correction layer."""
import re
from datetime import datetime, timezone
from contextlib import closing
import json
import pymupdf

VERSION='source-document-metadata/v1'


def extract_metadata(path):
    fields={};texts=[];issuer_candidates=[];period_candidates=[]
    # An invalid file opened by pathname can retain a Windows file handle in
    # MuPDF's exception traceback. Bounded uploads are parsed from bytes so a
    # rejected upload can always be removed without exposing a server error.
    from pathlib import Path
    with pymupdf.open(stream=Path(path).read_bytes(),filetype='pdf') as pdf:
        for i in range(min(3,len(pdf))):texts.append((i+1,pdf[i].get_text()))
    def put(key,value,page,text,status='AUTO_CONFIRMED'):
        fields[key]={'value':value,'status':status,'source_page':page,'source_snippet':text[:350],
                     'method':VERSION,'review_required':status!='AUTO_CONFIRMED'}
    for page,text in texts:
        flat=' '.join(text.split())
        for m in re.finditer(r'([A-Z][\w &.,()-]{2,90})\s*\(Exact name of Registrant',flat):
            issuer_candidates.append((re.sub(r'^.*?\d{3}-\d+\s+','',m[1]).strip(),page,m[0]))
        for m in re.finditer(r'fiscal year ended\s+([A-Za-z]+\s+\d{1,2},\s*20\d{2})',flat,re.I):
            period_candidates.append((m[1],page,m[0]))
        if 'issuer' not in fields:
            match=re.search(r'([A-Z][\w &.,()-]{2,90})\s*\(Exact name of Registrant',flat)
            if match:
                name=re.sub(r'^.*?\d{3}-\d+\s+','',match[1]);put('issuer',name,page,match[0])
            else:
                lines=[s.strip() for s in text.splitlines() if s.strip()]
                names=[s for s in lines[:25] if re.search(r'công ty|tập đoàn|ngân hàng',s,re.I)]
                if len(names)==1:put('issuer',names[0],page,names[0],'NEEDS_REVIEW')
        if 'document_type' not in fields:
            m=re.search(r'FORM\s+(10-[KQ](?:/A)?)',text,re.I)
            if m:put('document_type',m[1].upper(),page,m[0])
            elif re.search(r'báo cáo tài chính',text,re.I):put('document_type','Báo cáo tài chính',page,'Báo cáo tài chính')
        if 'report_period' not in fields:
            m=re.search(r'fiscal year ended\s+([A-Za-z]+\s+\d{1,2},\s*20\d{2})',flat,re.I)
            if m:
                try:
                    end=datetime.strptime(m[1],'%B %d, %Y').date().isoformat()
                    put('report_period',end,page,m[0]);put('period_kind','FISCAL_YEAR',page,m[0])
                except ValueError:pass
        if re.search(r'\bCONSOLIDATED\s+(?:FINANCIAL\s+)?STATEMENTS',text,re.I):
            put('reporting_scope','CONSOLIDATED',page,'CONSOLIDATED STATEMENTS')
    for key in ('issuer','document_type','report_period','ticker','currency','reporting_scope'):
        fields.setdefault(key,{'value':None,'status':'UNKNOWN','source_page':None,'source_snippet':'',
                               'method':VERSION,'review_required':True})
    if len({v.casefold() for v,_,_ in issuer_candidates})>1:
        fields['issuer'].update(value=None,status='CONFLICTING_METADATA',review_required=True,candidates=[v for v,_,_ in issuer_candidates])
    # Multiple fiscal dates on cover pages are not collapsed into a guessed year.
    if len({v for v,_,_ in period_candidates})>1:
        fields['report_period'].update(value=None,status='NEEDS_REVIEW',review_required=True,candidates=[v for v,_,_ in period_candidates])
    sample=' '.join(text for _,text in texts)
    language='vi' if re.search('[ăâđêôơưĂÂĐÊÔƠƯ]',sample) else 'en' if len(re.findall(r'\b(?:the|and|for|form)\b',sample,re.I))>=3 else None
    fields['language']={'value':language,'status':'NEEDS_REVIEW' if language else 'UNKNOWN','source_page':1,
        'source_snippet':sample[:150],'method':'SOURCE_LANGUAGE_RULE','review_required':True}
    return {'version':VERSION,'fields':fields,'corrections':[]}


def save_metadata(workspace,document_id,metadata):
    with closing(workspace._connect()) as db,db:
        db.execute('CREATE TABLE IF NOT EXISTS document_metadata(document_id TEXT PRIMARY KEY,payload TEXT NOT NULL)')
        db.execute('INSERT OR REPLACE INTO document_metadata VALUES(?,?)',(document_id,json.dumps(metadata,ensure_ascii=False)))


def read_metadata(workspace,document_id):
    with closing(workspace._connect()) as db:
        db.execute('CREATE TABLE IF NOT EXISTS document_metadata(document_id TEXT PRIMARY KEY,payload TEXT NOT NULL)')
        row=db.execute('SELECT payload FROM document_metadata WHERE document_id=?',(document_id,)).fetchone()
    return json.loads(row['payload']) if row else {'version':VERSION,'fields':{},'corrections':[]}


def correct_metadata(workspace,document_id,changes):
    workspace.source_file(document_id)
    if not changes:raise ValueError('NO_METADATA_CORRECTION')
    if set(changes)-{'issuer','document_type','report_period'}:raise ValueError('UNSUPPORTED_METADATA_FIELD')
    if any(not isinstance(v,str) or len(v)>160 for v in changes.values()):raise ValueError('INVALID_METADATA_VALUE')
    metadata=read_metadata(workspace,document_id)
    if len(metadata['corrections'])>=100:raise ValueError('METADATA_REVISION_LIMIT')
    if not metadata['fields']:metadata=extract_metadata(workspace.source_file(document_id))
    metadata['corrections'].append({'timestamp':datetime.now(timezone.utc).isoformat(),'changes':changes,
                                    'status':'USER_CORRECTED','revision':len(metadata['corrections'])+1})
    with closing(workspace._connect()) as db,db:
        db.execute('INSERT OR REPLACE INTO document_metadata VALUES(?,?)',(document_id,json.dumps(metadata,ensure_ascii=False)))
        for key,value in changes.items():db.execute('UPDATE documents SET '+key+'=? WHERE id=?',(value,document_id))
    return metadata

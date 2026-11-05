"""Read-only navigation into registered SEC bytes, never an HTML/URL proxy."""
import base64
from contextlib import closing
from hashlib import sha256
import hmac
import json
import os
from pathlib import Path
import re
import secrets
from threading import Lock
from urllib.parse import urlsplit

from app.financial_index.corpus import verified_source, _verified_bytes
from app.financial_ingestion.html_parser import parse_sec_html, normalized_filing_text
from app.financial_ingestion.schemas import StructuredFiling
from app.table_evidence.identity import digest
from app.table_evidence.real_source import derive_cell, parse_resources, MAX_SOURCE_BYTES

VERSION='registered-sec-viewer/v1'
_key_lock=Lock()


def server_key(root):
    """Separate local signing secret; the browser's bearer token is not a key."""
    path=Path(root)/'sec-source-viewer.key'
    with _key_lock:
        if not path.exists():
            try:
                fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
                with os.fdopen(fd,'w') as stream:stream.write(secrets.token_hex(32))
            except FileExistsError:pass
        key=path.read_text().strip()
    if not re.fullmatch(r'[a-f0-9]{64}',key):raise SourceViewError('SOURCE_REFERENCE_UNAVAILABLE')
    return key


class SourceViewError(ValueError):
    pass


def reference(index,parent_id,secret,cell=None):
    if len(secret)<16:raise SourceViewError('SOURCE_REFERENCE_UNAVAILABLE')
    item=index.by_id.get(parent_id)
    if item is None:raise SourceViewError('UNREGISTERED_SOURCE_ID')
    p=item['chunk'];loc=p.source_location
    identity={k:index.identity[k] for k in ('dataset_id','generation','manifest_hash')}
    target=None
    if cell is not None:
        if cell['parent_id']!=parent_id or cell['raw_sha256']!=item['frozen']['raw_hash'] or cell['filing_id']!=p.filing_id:
            raise SourceViewError('SOURCE_IDENTITY_MISMATCH')
        target={k:cell[k] for k in ('table_id','row','column','raw_value','period_end','unit','multiplier','structural_path')}
    value={'version':VERSION,**identity,'parent_id':parent_id,'raw_hash':item['frozen']['raw_hash'],'target':target}
    raw=json.dumps(value,sort_keys=True,separators=(',',':')).encode()
    encoded=base64.urlsafe_b64encode(raw).decode().rstrip('=')
    return encoded+'.'+hmac.new(secret.encode(),encoded.encode(),sha256).hexdigest()


def decode_reference(value,secret):
    try:
        if not isinstance(value,str) or len(value)>4096:raise ValueError()
        encoded,signature=value.split('.')
        expected=hmac.new(secret.encode(),encoded.encode(),sha256).hexdigest()
        if len(secret)<16 or not hmac.compare_digest(signature,expected):raise ValueError()
        data=json.loads(base64.urlsafe_b64decode(encoded+'='*(-len(encoded)%4)))
        if set(data)!={'version','dataset_id','generation','manifest_hash','parent_id','raw_hash','target'} or data['version']!=VERSION:raise ValueError()
        return data
    except (ValueError,TypeError,KeyError,UnicodeError):raise SourceViewError('UNREGISTERED_SOURCE_REFERENCE') from None


def _official_url(parent):
    m=parent.metadata;value=m['source_url'];u=urlsplit(value)
    expected=f"/Archives/edgar/data/{int(m['cik'])}/{m['accession_number'].replace('-','')}/{m['primary_document']}"
    if u.scheme!='https' or u.netloc!='www.sec.gov' or u.path!=expected or u.query or u.fragment:
        raise SourceViewError('SOURCE_IDENTITY_MISMATCH')
    return value


def resolve(index,value,secret):
    """Every read rehashes raw/structured/chunks and validates live membership.

    `index` is constructed by SecResearchIndex/source_records against committed
    anchors. Client values are only signed navigation claims, never trust roots.
    """
    data=decode_reference(value,secret)
    for key in ('dataset_id','generation','manifest_hash'):
        if data[key]!=index.identity[key]:raise SourceViewError('SOURCE_GENERATION_MISMATCH')
    fresh=json.loads((index.root/'frozen_v1/freeze.json').read_bytes())
    vectors=json.loads((index.vector_root/'generation_manifest.json').read_bytes())
    if vectors.get('state')!='READY' or any(fresh.get(k)!=data[k] or vectors.get(k)!=data[k] for k in ('generation','manifest_hash')):
        raise SourceViewError('SOURCE_GENERATION_MISMATCH')
    record=index.lexical.generation(data['dataset_id'],data['generation'])
    if record is None or record['state']!='READY' or record['n']!=len(index.by_id):raise SourceViewError('SOURCE_GENERATION_MISMATCH')
    item=index.by_id.get(data['parent_id'])
    if item is None or data['raw_hash']!=item['frozen']['raw_hash']:raise SourceViewError('UNREGISTERED_SOURCE_ID')
    frozen=item['frozen']
    for key in ('raw_path','structured_path','chunks_path'):
        path=Path(frozen[key]).resolve()
        if not path.is_relative_to(index.root):raise SourceViewError('SOURCE_IDENTITY_MISMATCH')
        if not path.is_file():raise SourceViewError('SOURCE_BYTES_NOT_AVAILABLE')
        if path.stat().st_size>(MAX_SOURCE_BYTES if key=='raw_path' else 32_000_000):raise SourceViewError('SOURCE_EVIDENCE_BUDGET')
    # Reject replacement of lexical identity even when this index object is cached.
    with closing(index.lexical.connect()) as db:
        row=db.execute('SELECT d.payload,d.payload_hash,m.source FROM documents d JOIN members m ON m.cid=d.cid WHERE d.cid=? AND m.generation=?',(data['parent_id'],data['generation'])).fetchone()
    if row is None or json.loads(row['source'])!=frozen or digest(json.loads(row['payload']))!=row['payload_hash']:
        raise SourceViewError('SOURCE_IDENTITY_MISMATCH')
    try:
        canonical=verified_source(frozen,cache=index._cache,generation=data['generation'])
        parent=canonical.get(data['parent_id'])
        if parent is None or parent.model_dump(mode='json')!=json.loads(row['payload']) or parent.model_dump()!=item['chunk'].model_dump():
            raise SourceViewError('SOURCE_IDENTITY_MISMATCH')
        raw=_verified_bytes(Path(frozen['raw_path']),frozen['raw_hash'])
        saved=StructuredFiling.model_validate_json(_verified_bytes(Path(frozen['structured_path']),frozen['structured_hash']))
        parsed=parse_sec_html(raw,saved.metadata.model_copy(deep=True))
        if sha256(normalized_filing_text(parsed).encode()).hexdigest()!=frozen['normalized_hash']:raise SourceViewError('SOURCE_HASH_MISMATCH')
    except FileNotFoundError:raise SourceViewError('SOURCE_BYTES_NOT_AVAILABLE') from None
    except ValueError as exc:
        if isinstance(exc,SourceViewError):raise
        raise SourceViewError('SOURCE_HASH_MISMATCH') from None
    if parent.filing_id!=frozen['filing_id'] or parent.metadata.get('raw_content_hash') not in (None,frozen['raw_hash']):raise SourceViewError('SOURCE_IDENTITY_MISMATCH')
    result={'version':VERSION,'status':'VERIFIED_LOCAL_SEC_SNAPSHOT',
        'dataset_id':data['dataset_id'],'generation':data['generation'],'manifest_hash':data['manifest_hash'],
        'source_sha256':frozen['raw_hash'],'normalized_sha256':frozen['normalized_hash'],
        'parent_id':parent.chunk_id,'filing_id':parent.filing_id,'issuer':saved.metadata.company_name,
        'cik':saved.metadata.cik,'accession':saved.metadata.accession_number,'form':saved.metadata.form_type,
        'report_period':saved.metadata.report_date,'filing_date':saved.metadata.filing_date,
        'fiscal_year':saved.metadata.fiscal_year,'official_url':_official_url(parent),
        'rendering':'DERIVED_TEXT_TABLE_FROM_VERIFIED_ORIGINAL_BYTES_NOT_ORIGINAL_HTML',
        'external_access':'NOT_CHECKED_BY_LOCAL_VIEWER','warnings':parsed.parser_warnings[:8],
        'locator':parent.source_location.model_dump(mode='json'),'selected_cell':None,'table':None,
        'excerpt':parent.text[:4000]}
    target=data['target'];table_id=target['table_id'] if target else parent.source_location.table_id
    if not table_id:
        if target:raise SourceViewError('SOURCE_LOCATOR_UNRESOLVED')
        result.update(status='SOURCE_EVIDENCE_PARTIAL',locator_limitation='SOURCE_PARAGRAPH_VERIFIED_NO_FINANCIAL_CELL_SELECTED')
        return result
    tables=[t for t in parsed.tables if t.table_id==table_id]
    if len(tables)!=1 or parent.source_location.table_id!=table_id:raise SourceViewError('SOURCE_LOCATOR_UNRESOLVED')
    table=tables[0];selected_row=parent.source_location.row_index
    if target:
        if selected_row!=target['row']:raise SourceViewError('SOURCE_LOCATOR_UNRESOLVED')
        cells=[c for c in table.cells if (c.row,c.column)==(target['row'],target['column'])]
        if len(cells)!=1:raise SourceViewError('SOURCE_LOCATOR_UNRESOLVED')
        try:observation=derive_cell(parent,table,cells[0],parse_resources(raw),raw_hash=frozen['raw_hash'],generation=data['generation'],manifest_hash=data['manifest_hash'],dataset_id=data['dataset_id'],product_mode=True).model_dump(mode='json')
        except ValueError:raise SourceViewError('SOURCE_LOCATOR_UNRESOLVED') from None
        if any(observation[k]!=target[k] for k in target):raise SourceViewError('SOURCE_LOCATOR_UNRESOLVED')
        result['selected_cell']=observation
        result['locator']={'structural_path':observation['structural_path'],'table_id':table_id,
            'row_index':observation['row'],'column_index':observation['column'],
            'parent_location':parent.source_location.model_dump(mode='json')}
    selected_row=selected_row if selected_row is not None else 0
    first=min(table.row_indices) if table.row_indices else 0
    wanted=set(range(min(first,10)))|set(range(max(0,selected_row-5),selected_row+6))
    if len(table.cells)>2000 or len(table.columns)>32:raise SourceViewError('SOURCE_EVIDENCE_BUDGET')
    rows=[]
    for row_index in sorted(wanted):
        cells=[{'column':c.column,'text':c.text,'colspan':c.colspan,'rowspan':c.rowspan} for c in table.cells if c.row==row_index]
        if cells:rows.append({'index':row_index,'cells':cells})
    result['table']={'id':table.table_id,'caption':table.caption,'statement':table.statement_title,'section':table.section,
        'columns':table.columns,'rows':rows,'selected_row':selected_row,'header_row_count':first,
        'total_source_rows':max((c.row for c in table.cells),default=-1)+1,'context_is_bounded':True,
        'warnings':table.extraction_warnings,'footnotes':table.footnotes[:8]}
    if len(json.dumps(result,ensure_ascii=False).encode())>250000:raise SourceViewError('SOURCE_EVIDENCE_BUDGET')
    return result

"""Versioned, narrowly scoped iXBRL cell observations from C-authenticated SEC bytes.

This module does not reinterpret an arbitrary document as a trusted source. The
public entrypoint authenticates against a committed raw-source registry, C's
full-source reconstruction, and exact parent membership before deriving a cell.
"""
import calendar
from datetime import date
from decimal import Decimal,localcontext
from hashlib import sha256
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from contextlib import closing
from typing import Literal
from pydantic import BaseModel,ConfigDict
from app.financial_index.corpus import verified_source
from app.financial_ingestion.html_parser import parse_sec_html,normalized_filing_text
from app.financial_ingestion.schemas import FinancialChunk,FinancialTable,TableCell,StructuredFiling
from app.table_evidence.identity import digest

MAX_SOURCE_BYTES=4_000_000
PRODUCT_SOURCE_BYTES=16_000_000
CONCEPTS={'net sales':{'us-gaap:revenues'},
          'total assets':{'us-gaap:assets'}}
MONTHS={name.casefold():n for n,name in enumerate(calendar.month_name) if name}


class RealCellObservationV1(BaseModel):
    model_config=ConfigDict(extra='forbid',frozen=True)
    contract_version:Literal['real-sec-cell-observation/v1']='real-sec-cell-observation/v1'
    source_status:Literal['VERIFIED_SOURCE_CELL']='VERIFIED_SOURCE_CELL'
    dataset_id:str
    generation:str
    manifest_hash:str
    filing_id:str
    cik:str
    accession:str
    raw_sha256:str
    parent_id:str
    parent_payload_hash:str
    table_id:str
    row:int
    column:int
    row_label:str
    raw_value:str
    value:Decimal
    unit:str
    display_unit_header:str
    multiplier:Decimal
    effective_value:Decimal
    period_kind:str
    period_start:str|None
    period_end:str
    period_months:int|None
    header_path:tuple[str,...]
    fact_name:str
    fact_context_ref:str
    fact_unit_ref:str
    source_url:str
    structural_path:str
    footnotes:tuple[str,...]
    warnings:tuple[str,...]
    authentication:Literal['COMMITTED_RAW_HASH_AND_C_RECONSTRUCTION']='COMMITTED_RAW_HASH_AND_C_RECONSTRUCTION'


class _Resources(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.contexts={};self.units={};self.current=None;self.capture=None;self.parts=[]

    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs);tag=tag.casefold()
        if tag in {'xbrli:context','xbrli:unit'}:
            if self.current is not None:raise ValueError('NESTED_XBRL_RESOURCE')
            key=attrs.get('id','')
            if not key or len(key)>100:raise ValueError('INVALID_XBRL_RESOURCE_ID')
            collection=self.contexts if tag=='xbrli:context' else self.units
            if key in collection or len(collection)>=5000:raise ValueError('DUPLICATE_OR_EXCESSIVE_XBRL_RESOURCE')
            self.current={'type':tag,'id':key,'measures':[],'segment':False,'dimensions':[]}
        elif self.current is not None and tag in {'xbrli:segment','xbrldi:explicitmember','xbrldi:typedmember'}:
            self.current['segment']=True
            if tag=='xbrldi:typedmember':
                self.current['dimensions'].append(('typed',''))
            elif tag=='xbrldi:explicitmember':
                self.capture=tag;self.parts=[]
                self.dimension=attrs.get('dimension','')
        if self.current is not None and tag in {'xbrli:identifier','xbrli:startdate','xbrli:enddate','xbrli:instant','xbrli:measure'}:
            self.capture=tag;self.parts=[]

    def handle_data(self,data):
        if self.capture:self.parts.append(data)

    def handle_endtag(self,tag):
        tag=tag.casefold()
        if self.current is not None and tag==self.capture:
            value=''.join(self.parts).strip()
            if tag=='xbrldi:explicitmember':self.current['dimensions'].append((self.dimension,value))
            elif tag=='xbrli:measure':self.current['measures'].append(value)
            elif tag in self.current:raise ValueError('DUPLICATE_XBRL_FIELD')
            else:self.current[tag]=value
            self.capture=None;self.parts=[]
        if self.current is not None and tag==self.current['type']:
            collection=self.contexts if tag=='xbrli:context' else self.units
            collection[self.current['id']]=self.current;self.current=None


def parse_resources(raw:bytes, *, product_mode=False):
    if not isinstance(raw,bytes) or len(raw)>(PRODUCT_SOURCE_BYTES if product_mode else MAX_SOURCE_BYTES):raise ValueError('SOURCE_SIZE_BUDGET')
    try:text=raw.decode('utf-8')
    except UnicodeDecodeError:text=raw.decode('latin-1')
    parser=_Resources();parser.feed(text);parser.close()
    if parser.current is not None:raise ValueError('UNTERMINATED_XBRL_RESOURCE')
    return {'contexts':parser.contexts,'units':parser.units}


def _source_period(context,headers, *, product_mode=False):
    if context.get('segment'):raise ValueError('XBRL_SEGMENT_CONTEXT_UNSUPPORTED')
    start=context.get('xbrli:startdate');end=context.get('xbrli:enddate');instant=context.get('xbrli:instant')
    if instant and (start or end) or not instant and not (start and end):raise ValueError('XBRL_PERIOD_INCOMPLETE')
    text=' / '.join(headers)
    if instant:period_end=date.fromisoformat(instant);months=None;kind='INSTANT'
    else:
        first=date.fromisoformat(start);period_end=date.fromisoformat(end)
        months=(period_end.year-first.year)*12+period_end.month-first.month+1
        if product_mode:
            days = (period_end-first).days+1
            week_labels = {int(n) for n in re.findall(r'\b(12|13|14|24|25|26|27|36|37|39|40|52|53)[ -]weeks?\b', text, re.I)}
            week_labels.update(n for term,n in [('twelve',12),('thirteen',13),('twenty-four',24),('twenty-six',26),
                                                ('thirty-six',36),('thirty-nine',39),('fifty-two',52),('fifty-three',53)]
                               if re.search(rf'\b{term}[ -]weeks?\b',text,re.I))
            month_labels = {n for term, n in [('three',3),('six',6),('nine',9),('twelve',12)]
                            if re.search(rf'\b{term}[ -]months?\b', text, re.I)}
            if re.search(r'\b(?:fiscal )?years? ended\b', text, re.I):
                month_labels.add(12)
            quarter_months = {12:3,13:3,14:3,24:6,25:6,26:6,27:6,36:9,37:9,39:9,40:9,52:12,53:12}
            if week_labels:
                if len(week_labels)!=1 or days!=next(iter(week_labels))*7:
                    raise ValueError('HEADER_XBRL_WEEK_CONFLICT')
                months = quarter_months[next(iter(week_labels))]
                if month_labels and month_labels!={months}:
                    raise ValueError('HEADER_XBRL_DURATION_CONFLICT')
            elif len(month_labels)==1:
                months = next(iter(month_labels))
                bounds = {3:(80,98),6:(160,190),9:(245,282),12:(350,378)}
                if not bounds[months][0]<=days<=bounds[months][1]:
                    raise ValueError('HEADER_XBRL_DURATION_CONFLICT')
            elif month_labels or first.day!=1 or period_end.day!=calendar.monthrange(period_end.year,period_end.month)[1] or months not in {3,6,9,12}:
                raise ValueError('XBRL_DURATION_NOT_SUPPORTED')
        elif first.day!=1 or period_end.day!=calendar.monthrange(period_end.year,period_end.month)[1] or months not in {3,6,9,12}:
            raise ValueError('XBRL_DURATION_NOT_SUPPORTED')
        kind='DURATION'
    years={int(y) for y in re.findall(r'\b(?:19|20)\d{2}\b',text)}
    if years!={period_end.year}:raise ValueError('HEADER_XBRL_YEAR_CONFLICT_OR_ABSENT')
    mentions=[]
    for name,number in MONTHS.items():
        for match in re.finditer(r'\b'+name+r'\s+(\d{1,2})\b',text.casefold()):
            mentions.append((number,int(match.group(1))))
    if mentions and (period_end.month,period_end.day) not in mentions:raise ValueError('HEADER_XBRL_DATE_CONFLICT')
    if kind=='DURATION' and re.search(r'\bthree\s+months\s+ended\b',text,re.I) and months!=3:
        raise ValueError('HEADER_XBRL_DURATION_CONFLICT')
    return kind,start,period_end.isoformat(),months


def _physical_product_headers(table, cell):
    """Bind a styled TD header omitted by the legacy table-header detector."""
    if table.header_rows:
        return (), ()
    contexts={re.sub(r'\s+','',value).casefold() for value in table.context_text}
    if not contexts & {'incomestatements','consolidatedincomestatements',
                       'balancesheets','consolidatedbalancesheets'}:
        return (), ()
    period_rows=[]
    for header in table.cells:
        if header.row>=cell.row or header.column!=0:
            continue
        if not re.search(r'\b(?:years? ended|as of)\b|(?:June|December|September|March)\s+\d{1,2}',header.text,re.I):
            continue
        years=[candidate.text for candidate in table.cells
               if candidate.row==header.row and candidate.column<=cell.column<candidate.column+candidate.colspan
               and not candidate.numeric_facts and re.fullmatch(r'(?:19|20)\d{2}',candidate.text)]
        if len(years)==1:
            period_rows.append((header.row,header.text,years[0]))
    if len(period_rows)!=1:
        return (), ()
    row, label, year=period_rows[0]
    units=tuple(sorted({header.text.strip() for header in table.cells
                        if header.row<row and header.column==0 and not header.numeric_facts
                        and re.match(r'^\(?in millions\b',header.text,re.I)}))
    return (label,year),units


def derive_cell(parent:FinancialChunk,table:FinancialTable,cell:TableCell,resources:dict,*,raw_hash:str,generation:str,manifest_hash:str,dataset_id:str='research-sec-v1',product_mode:bool=False):
    """Derive one physical fact; caller must authenticate all inputs first."""
    if parent.kind!='table' or parent.extraction_status!='OK' or table.extraction_status!='OK' or table.extraction_warnings:
        raise ValueError('SELECTED_TABLE_EXTRACTION_INCOMPLETE')
    m=parent.metadata
    if parent.source_location.table_id!=table.table_id or m.get('table_id')!=table.table_id or parent.source_location.row_index!=cell.row:
        raise ValueError('SOURCE_TABLE_ROW_IDENTITY_MISMATCH')
    source_row=[c for c in table.cells if c.row==cell.row]
    if [c.model_dump(mode='json') for c in source_row]!=[TableCell.model_validate(c).model_dump(mode='json') for c in m.get('cells',[])]:
        raise ValueError('SOURCE_PARENT_PHYSICAL_ROW_MISMATCH')
    if not any(c.model_dump(mode='json')==cell.model_dump(mode='json') for c in source_row):
        raise ValueError('SOURCE_CELL_NOT_IN_ROW')
    if m.get('header_rows')!=table.header_rows or m.get('column_labels')!=table.columns:
        raise ValueError('SOURCE_PARENT_HEADER_MISMATCH')
    span_matches = cell.colspan==1 or product_mode and all(
        len(set(grid[cell.column:cell.column+cell.colspan]))==1
        and len(grid[cell.column:cell.column+cell.colspan])==cell.colspan for grid in table.header_rows)
    if cell.rowspan!=1 or not span_matches or len(cell.numeric_facts)!=1:
        raise ValueError('AMBIGUOUS_PHYSICAL_VALUE_CELL')
    row_label=m.get('row_label','').strip().casefold()
    fact=cell.numeric_facts[0];name=fact.get('name','').casefold()
    concepts=CONCEPTS.get(row_label,set())
    if product_mode:
        revenue = {'us-gaap:revenues','us-gaap:salesrevenuenet','us-gaap:revenuefromcontractwithcustomerexcludingassessedtax'}
        aliases = {'net sales':revenue, 'total net sales':revenue, 'revenue':revenue, 'total revenue':revenue,
                   'net revenue':revenue, 'net income':{'us-gaap:netincomeloss'},
                   'net income (loss)':{'us-gaap:netincomeloss'}}
        concepts = concepts | aliases.get(row_label,set())
    if name not in concepts:raise ValueError('CONCEPT_ROW_CORRESPONDENCE_UNSUPPORTED')
    if fact.get('source_text','').strip()!=cell.text.strip() or fact.get('format','').casefold().split(':')[-1] not in {'num-dot-decimal','numdotdecimal'}:
        raise ValueError('INLINE_DISPLAY_OR_FORMAT_UNSUPPORTED')
    from app.table_evidence.interpretation import parse_number
    value,sign,missing,reason=parse_number(cell.text)
    if missing!='NUMBER' or reason or value is None:raise ValueError('SOURCE_NUMBER_UNSUPPORTED')
    ixsign=fact.get('sign','')
    if ixsign not in {'','-','+'} or ixsign=='+' and value<0 or ixsign=='-' and sign=='PLUS':raise ValueError('SOURCE_SIGN_CONFLICT')
    if ixsign=='-' and value>0:value=-value
    context=resources['contexts'].get(fact.get('contextref',''))
    unit=resources['units'].get(fact.get('unitref',''))
    if context is None or unit is None:raise ValueError('XBRL_RESOURCE_MISSING')
    if context.get('xbrli:identifier')!=m.get('cik'):raise ValueError('XBRL_ISSUER_CONFLICT')
    if unit.get('segment') or unit.get('measures')!=['iso4217:USD']:
        raise ValueError('XBRL_UNIT_UNSUPPORTED')
    first_row=min(table.row_indices) if table.row_indices else 0
    headers=[]
    for h in sorted(table.cells,key=lambda x:(x.row,x.column)):
        if h.row<first_row and h.column<=cell.column<h.column+h.colspan and h.text.strip():
            if not any(h.column<len(grid) and grid[h.column]==h.text for grid in table.header_rows):
                raise ValueError('SOURCE_HEADER_GRID_CONFLICT')
            headers.append(h.text)
    physical_units=()
    if not headers and product_mode:
        headers,physical_units=_physical_product_headers(table,cell)
    if not headers:raise ValueError('SOURCE_HEADER_PATH_MISSING')
    product_sales_scope = (product_mode and row_label=='net sales'
        and context.get('dimensions')==[('srt:ProductOrServiceAxis','us-gaap:ProductMember')]
        and re.search(r'\bconsolidated statements? of (?:income|operations|earnings)\b',table.statement_title or '',re.I))
    period_context={**context,'segment':False} if product_sales_scope else context
    kind,start,end,months=_source_period(period_context,headers,product_mode=product_mode)
    try:exp=int(fact.get('scale','0'))
    except (TypeError,ValueError):raise ValueError('XBRL_SCALE_UNSUPPORTED') from None
    if not -12<=exp<=12:raise ValueError('XBRL_SCALE_UNSUPPORTED')
    unit_headers=sorted({h.strip() for grid in table.header_rows for h in grid
                         if re.search(r'\b(?:thousands|millions|billions)\b',h,re.I)})
    if physical_units:
        unit_headers=list(physical_units)
    if product_mode and table.unit_context and table.unit_context==m.get('unit_context') and table.unit_context in table.context_text and table.context_locations:
        context_units=set(re.findall(r'\b(?:thousands|millions|billions)\b',table.unit_context.casefold()))
        header_units={u for h in unit_headers for u in re.findall(r'\b(?:thousands|millions|billions)\b',h.casefold())}
        if context_units and header_units and context_units!=header_units:raise ValueError('CONFLICTING_DISPLAY_UNIT_CAPTIONS')
        if context_units and not unit_headers:unit_headers=[table.unit_context.strip()]
    if len(unit_headers)!=1 or 'millions' not in unit_headers[0].casefold() or exp!=6:
        raise ValueError('DISPLAY_UNIT_XBRL_SCALE_CONFLICT_OR_ABSENT')
    multiplier=Decimal(10)**exp
    with localcontext() as dec:
        dec.prec=100;effective=value*multiplier
    return RealCellObservationV1(dataset_id=dataset_id,generation=generation,manifest_hash=manifest_hash,
        filing_id=parent.filing_id,cik=m['cik'],accession=m['accession_number'],raw_sha256=raw_hash,
        parent_id=parent.chunk_id,parent_payload_hash=digest(parent.model_dump(mode='json')),
        table_id=table.table_id,row=cell.row,column=cell.column,row_label=m['row_label'],raw_value=cell.text,
        value=value,unit='USD',display_unit_header=unit_headers[0],multiplier=multiplier,effective_value=effective,
        period_kind=kind,period_start=start,period_end=end,period_months=months,header_path=tuple(headers),
        fact_name=fact['name'],fact_context_ref=fact['contextref'],fact_unit_ref=fact['unitref'],
        source_url=m['source_url'],structural_path=cell.source_location.structural_path,
        footnotes=tuple(table.footnotes),warnings=(('FILING_PARTIAL_EXTRACTION_OUTSIDE_SELECTED_TABLE',) if m.get('document_status')=='PARTIAL_EXTRACTION' else ())
        + (('PRODUCT_SALES_DIMENSION_EXCLUDES_MEMBERSHIPS',) if product_sales_scope else ()))


def validate_frozen_parent_membership(frozen:dict,payload:dict):
    """A member cannot borrow a verified parent from a different filing."""
    if frozen.get('filing_id')!=payload.get('filing_id'):
        raise ValueError('FROZEN_PARENT_FILING_ID_MISMATCH')


def verified_real_cells(snapshot,parent_id:str):
    """Authenticate complete owned SEC source and derive supported cells in one parent.

    The committed D3 raw-source registry is the independent trust anchor. C's
    verified_source checks bytes, structured/chunk hashes and full rechunking.
    A second accepted parse yields exact table coordinates without changing C.
    """
    root=snapshot.root;freeze=snapshot.freeze
    registry_path=Path(__file__).resolve().parents[2]/'docs/topic3/milestone_d/d3/D3_FRESH_EXACT_ROW_FREEZE_v1.json'
    registry=json.loads(registry_path.read_text(encoding='utf-8'))
    from app.table_evidence.product_registry import product_registry
    registry=product_registry(freeze) or registry
    from app.product.sec_product_snapshot import ProductSecSnapshot
    if isinstance(snapshot,ProductSecSnapshot):registry=snapshot.product_source_registry
    if registry['manifest_hash']!=freeze['manifest_hash'] or registry['generation']!=freeze['generation']:
        raise ValueError('COMMITTED_RESEARCH_REGISTRY_MISMATCH')
    with closing(snapshot.lexical.connect()) as db:
        row=db.execute('SELECT d.payload,d.payload_hash,m.source FROM documents d JOIN members m ON m.cid=d.cid WHERE d.cid=? AND m.generation=?',
                       (parent_id,freeze['generation'])).fetchone()
    if row is None:raise ValueError('PARENT_NOT_IN_PINNED_GENERATION')
    frozen=json.loads(row['source']);payload=json.loads(row['payload'])
    validate_frozen_parent_membership(frozen,payload)
    if frozen.get('manifest_hash')!=freeze['manifest_hash'] or digest(payload)!=row['payload_hash']:
        raise ValueError('PINNED_PARENT_OR_MANIFEST_MISMATCH')
    for key in ('raw_path','structured_path','chunks_path'):
        if not Path(frozen[key]).resolve().is_relative_to(root):raise ValueError('RESEARCH_SOURCE_PATH_ESCAPE')
    group=[g for g in registry['source_groups'] if g['raw_hash']==frozen.get('raw_hash')]
    if len(group)!=1:raise ValueError('SOURCE_NOT_IN_COMMITTED_REGISTRY')
    anchor=group[0]
    raw_path=Path(frozen['raw_path'])
    product_mode = getattr(snapshot,'product_verification',False)
    if raw_path.stat().st_size>(PRODUCT_SOURCE_BYTES if product_mode else MAX_SOURCE_BYTES):raise ValueError('SOURCE_SIZE_BUDGET')
    raw=raw_path.read_bytes()
    if sha256(raw).hexdigest()!=anchor['raw_hash']:raise ValueError('COMMITTED_RAW_BYTES_MISMATCH')
    expected=verified_source(frozen,generation=freeze['generation'],cache=snapshot.cache)
    parent=expected.get(parent_id)
    if parent is None or parent.model_dump(mode='json')!=payload or parent.metadata.get('accession_number')!=anchor['accession'] or parent.metadata.get('source_url')!=anchor['url'] or parent.metadata.get('cik')!=anchor['cik']:
        raise ValueError('COMMITTED_PARENT_IDENTITY_MISMATCH')
    saved=StructuredFiling.model_validate_json(Path(frozen['structured_path']).read_bytes())
    parsed=parse_sec_html(raw,saved.metadata.model_copy(deep=True))
    if sha256(normalized_filing_text(parsed).encode()).hexdigest()!=frozen['normalized_hash']:
        raise ValueError('REPARSED_NORMALIZED_SOURCE_MISMATCH')
    if sha256(raw_path.read_bytes()).hexdigest()!=anchor['raw_hash']:raise ValueError('SOURCE_CHANGED_DURING_CELL_DERIVATION')
    tables=[t for t in parsed.tables if t.table_id==parent.source_location.table_id]
    if len(tables)!=1:raise ValueError('SELECTED_TABLE_NOT_UNIQUE')
    table=tables[0]
    if len(table.cells)>2000 or len(table.model_dump_json())>250000:raise ValueError('SELECTED_TABLE_BUDGET')
    resources=parse_resources(raw,product_mode=product_mode)
    cells=[]
    for cell in table.cells:
        if cell.row!=parent.source_location.row_index or not cell.numeric_facts:continue
        try:cells.append(derive_cell(parent,table,cell,resources,raw_hash=anchor['raw_hash'],generation=freeze['generation'],manifest_hash=freeze['manifest_hash'],dataset_id=snapshot.catalog.dataset_id,product_mode=getattr(snapshot,'product_verification',False)))
        except ValueError:continue
    return tuple(cells)

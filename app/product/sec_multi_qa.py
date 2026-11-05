"""Product financial observations over selected, separately authenticated SEC filings."""
from datetime import date
from decimal import Decimal, ROUND_HALF_UP, localcontext
from functools import lru_cache
from hashlib import sha256
from pathlib import Path
import re
from time import perf_counter

from app.financial_index.corpus import _verified_bytes, verified_source
from app.financial_ingestion.html_parser import normalized_filing_text, parse_sec_html
from app.financial_ingestion.schemas import StructuredFiling
from app.product.answer_composer_v2 import display
from app.product.pdf_extract import folded
from app.product.sec_library import partitions
from app.product.sec_viewer import reference
from app.table_evidence.real_source import PRODUCT_SOURCE_BYTES, derive_cell, parse_resources

METRICS = {
    'revenue': ('Doanh thu', {'net sales','total net sales','revenue','total revenue','net revenue'}),
    'income': ('Lợi nhuận ròng', {'net income','net income (loss)'}),
    'assets': ('Tổng tài sản', {'total assets'}),
}
WEEK_WORDS = {'twelve':12,'thirteen':13,'twenty-four':24,'twenty-six':26,'thirty-six':36,'thirty-nine':39}
COMPARISON = r'\b(?:so voi|so sanh|compared|compare|versus|vs|thay doi|tang bao nhieu|giam bao nhieu|chenh lech|year.over.year|yoy)\b'


def metric_for(q):
    requested = []
    for name, pattern in [('revenue',r'\b(?:net sales|revenue|doanh thu)\b'),
                          ('income',r'\b(?:net income|loi nhuan rong|loi nhuan sau thue)\b'),
                          ('assets',r'\b(?:total assets|tong tai san)\b')]:
        if re.search(pattern,q):
            requested.append(name)
    return requested[0] if len(requested)==1 else None


def period_for(q, sources, metric):
    if metric=='assets':
        return 'INSTANT'
    labels = re.findall(r'\b(12|13|14|24|26|36|39|52|53)\s*(?:tuan|weeks?)\b',q)
    labels.extend(str(count) for word,count in WEEK_WORDS.items() if re.search(rf'\b{word}[ -]weeks?\b',q))
    if labels:
        return tuple(sorted(set(map(int,labels))))
    if re.search(r'\b(?:luy ke|ytd|year.to.date)\b',q):
        return 'YTD'
    if re.search(r'\b(?:three months|ba thang|3 thang|quarter|quarterly|quy|q[1-4])\b',q):
        return 3
    if re.search(r'\b(?:six months|6 thang|sau thang)\b',q):
        return 6
    if re.search(r'\b(?:nine months|9 thang|chin thang)\b',q):
        return 9
    if re.search(r'\bfy\s*20\d{2}|\b(?:fiscal year|nam tai chinh|ca nam|annual|full.year)\b',q):
        return 12
    if all(row['form'] in {'10-K','20-F'} for row,_ in sources):
        return 12
    return None


@lru_cache(maxsize=2)
def parsed_source(generation, raw_hash, normalized_hash, raw, metadata_json):
    from app.financial_ingestion.schemas import FilingMetadata
    parsed = parse_sec_html(raw,FilingMetadata.model_validate_json(metadata_json))
    if sha256(normalized_filing_text(parsed).encode()).hexdigest()!=normalized_hash:
        raise ValueError('SEC_NORMALIZED_SOURCE_MISMATCH')
    return {table.table_id:table for table in parsed.tables}, parse_resources(raw,product_mode=True)


def observations(part, filing, metric, labels=None):
    labels = labels or METRICS[metric][1]
    candidates = [p for p in part.parents if p['chunk'].filing_id==filing['filing_id']
                  and p['chunk'].metadata.get('row_label','').strip().casefold() in labels]
    if not candidates or len(candidates)>36:
        return []
    source = candidates[0]['frozen']
    if Path(source['raw_path']).stat().st_size > PRODUCT_SOURCE_BYTES:
        raise ValueError('SEC_SOURCE_SIZE_LIMIT')
    generation = part.identity['generation']
    canonical = verified_source(source,cache=part._cache,generation=generation)
    raw = _verified_bytes(Path(source['raw_path']),source['raw_hash'])
    saved = StructuredFiling.model_validate_json(_verified_bytes(Path(source['structured_path']),source['structured_hash']))
    tables, resources = parsed_source(generation,source['raw_hash'],source['normalized_hash'],raw,saved.metadata.model_dump_json())
    result = []
    for item in candidates:
        parent = item['chunk']
        if item['frozen']!=source or parent!=canonical.get(parent.chunk_id):
            raise ValueError('SEC_CANONICAL_PARENT_MISMATCH')
        table = tables.get(parent.source_location.table_id)
        if not table or len(table.cells)>2000:
            continue
        for cell in table.cells:
            if cell.row!=parent.source_location.row_index or not cell.numeric_facts:
                continue
            try:
                value = derive_cell(parent,table,cell,resources,raw_hash=source['raw_hash'],generation=generation,
                                    manifest_hash=part.identity['manifest_hash'],dataset_id=part.identity['dataset_id'],product_mode=True)
            except ValueError:
                continue
            result.append(value)
    return result


def period_matches(cell, period):
    if period=='INSTANT':
        return cell.period_kind=='INSTANT'
    if cell.period_kind!='DURATION':
        return False
    if isinstance(period,tuple):
        days = (date.fromisoformat(cell.period_end)-date.fromisoformat(cell.period_start)).days+1
        return days%7==0 and days//7 in period
    if period=='YTD':
        return cell.period_months in {6,9}
    return period is None or cell.period_months==period


def abstain(reason, text, *, timings=None):
    return {'status':'NEEDS_CLARIFICATION','answer_status':'REQUIRES_SOURCE_REVIEW','answer':text,
            'reason':reason,'values':[],'citations':[],'timings_ms':timings or {}}


def resolve_followup(question, previous):
    context = previous.get('sec_context') or {}
    if not context:
        return question
    q = folded(question)
    if re.search(r'^\b(?:the |con |vay )?nam truoc\b',q) and context['period']==12:
        return f"{context['ticker']} {context['metric_phrase']} FY{int(context['targets'][-1][:4])-1}"
    if re.search(r'^(?:hai |cac )?(?:so|gia tri).*(?:filing|nguon|bao cao)|(?:xem|mo).*so goc',q):
        return context['question']
    return question


def answer(index, question, ticker, key, operation='EXTRACT'):
    q = folded(question)
    metric = metric_for(q)
    if not metric:
        return None
    if re.search(r'\b(?:vi sao|tai sao|nguyen nhan|why|explain|services|products|segment|geographic|mang|khu vuc|phan khuc|gross|ty trong|margin|adjusted|dieu chinh|restat\w*|trinh bay lai)\b',q):
        return None
    from app.product.sec_a5 import plan_query
    plan = plan_query(question)
    if plan.scope=='PARENT' or plan.currency not in {None,'USD'} or plan.unit=='BILLION':
        return abstain('SEC_UNSUPPORTED_DIMENSION','Tôi chưa có ô nguồn SEC đã đối chiếu cho phạm vi hoặc đơn vị bạn yêu cầu.')
    started = perf_counter()
    sources = [(row,part) for part in partitions(index) for row in part.catalog_rows
               if not (ticker or plan.issuer) or row['ticker']==(ticker or plan.issuer).upper()]
    if ticker and plan.issuer and ticker.upper()!=plan.issuer:
        return abstain('SEC_COMPANY_SCOPE_CONFLICT','Doanh nghiệp trong câu hỏi khác với doanh nghiệp đã chọn.')
    if len({row['cik'] for row,_ in sources})!=1:
        return abstain('SEC_COMPANY_SCOPE_AMBIGUOUS','Hãy nêu tên doanh nghiệp trong câu hỏi hoặc chọn các filing của cùng một doanh nghiệp.')
    if any(row['form'] not in {'10-K','10-Q','20-F'} for row,_ in sources):
        return abstain('SEC_REPORTING_BASIS_UNSUPPORTED','Các filing đang chọn cần đối chiếu riêng về loại báo cáo hoặc trạng thái sửa đổi.')
    dates = tuple(sorted(set(re.findall(r'\b20\d{2}-\d{2}-\d{2}\b',q))))
    years = tuple(sorted(set(re.findall(r'\b(?:fy\s*)?(20\d{2})\b',re.sub(r'\b20\d{2}-\d{2}-\d{2}\b','',q)))))
    if not dates and plan.period_end:
        dates = (plan.period_end,)
        years = ()
    period = period_for(q,sources,metric)
    compare = bool(re.search(COMPARISON,q) or operation!='EXTRACT' or len(years)>1 or len(dates)>1)
    if plan.quarter and not dates:
        return abstain('SEC_QUARTER_END_REQUIRED','Hãy cho biết ngày kết thúc quý để tôi kiểm tra đúng ngữ cảnh iXBRL của kỳ.')
    if not period and len(sources)==1:
        return abstain('SEC_PERIOD_DURATION_REQUIRED','Bạn muốn số riêng của quý, số lũy kế hay số cả năm? Hãy nêu độ dài kỳ hoặc chọn báo cáo năm.')
    timings = {'scope_and_intent':(perf_counter()-started)*1000}
    begin = perf_counter()
    collected = []
    for filing, part in sources:
        labels=None
        if metric=='revenue':
            if re.search(r'\b(?:net sales|doanh thu thuan)\b',q):
                labels={'net sales','total net sales','net revenue'}
            elif re.search(r'\b(?:total revenue|tong doanh thu)\b',q):
                labels={'total revenue','revenue','total net sales'}
        cells = observations(part,filing,metric,labels)
        collected.extend((cell,filing,part) for cell in cells if period_matches(cell,period))
    timings['source_and_cells'] = (perf_counter()-begin)*1000
    if dates:
        targets = list(dates)
    elif years:
        targets = list(years)
    else:
        targets = sorted({filing['report_period'] for filing,_ in sources})
    if not compare and not years and not dates and len(targets)>1:
        return abstain('SEC_PERIOD_REQUIRED','Các filing đã chọn thuộc nhiều kỳ. Hãy nêu kỳ cần xem hoặc yêu cầu so sánh các kỳ.')
    if len(targets) not in {1,2} or compare and len(targets)!=2:
        return abstain('SEC_COMPARISON_PERIODS_REQUIRED','Hãy chỉ rõ hai năm tài chính hoặc hai ngày kết thúc kỳ cần so sánh.')
    chosen = []
    for target in targets:
        options = [(cell,filing,part) for cell,filing,part in collected if cell.period_end.startswith(target)]
        if not options:
            return abstain('SEC_VERIFIED_PERIOD_CELL_UNAVAILABLE','Chưa đối chiếu được ô nguồn cho kỳ '+target+'. Hãy kiểm tra chỉ tiêu, loại kỳ và filing đang chọn.',timings=timings)
        facts = {(cell.period_start,cell.period_end,cell.period_months,cell.unit,cell.multiplier,cell.effective_value)
                 for cell,_,_ in options}
        if len(facts)!=1:
            return abstain('SEC_PERIOD_OR_REPORTING_BASIS_CONFLICT','Có nhiều ô khác nhau cho kỳ '+target+'. Hãy chỉ rõ số quý hay lũy kế và filing cần dùng.',timings=timings)
        options.sort(key=lambda item:(item[0].period_end!=item[1]['report_period'],item[1]['report_period'],item[0].parent_id))
        chosen.append(options[0])
    cells = [cell for cell,_,_ in chosen]
    dimensions = {(c.cik,c.unit,c.multiplier,c.period_kind,c.period_months,c.fact_name.casefold(),
                   'PRODUCT_SALES_DIMENSION_EXCLUDES_MEMBERSHIPS' in c.warnings) for c in cells}
    if len(dimensions)!=1:
        return abstain('SEC_COMPARISON_DIMENSION_CONFLICT','Hai ô khác loại kỳ, khái niệm iXBRL hoặc đơn vị. Tôi có thể đối chiếu từng kỳ riêng.',timings=timings)
    if len(cells)==2 and cells[0].period_start and cells[1].period_start:
        lengths=[(date.fromisoformat(c.period_end)-date.fromisoformat(c.period_start)).days+1 for c in cells]
        if abs(lengths[1]-lengths[0])>3:
            return abstain('SEC_COMPARISON_DURATION_CONFLICT','Hai kỳ có độ dài khác nhau. Hãy xem từng giá trị riêng để tránh so sánh trực tiếp.',timings=timings)
    begin = perf_counter()
    citations = []
    for cell,filing,part in chosen:
        citations.append({'source_kind':'SEC','chunk_id':cell.parent_id,'issuer':filing['issuer'],
            'source_reference':reference(part,cell.parent_id,key,cell.model_dump(mode='json')),
            'filing_id':cell.filing_id,'accession':cell.accession,'form':filing['form'],'generation':cell.generation,
            'report_period':cell.period_end,'source_url':cell.source_url,'source_sha256':cell.raw_sha256,
            'text':f'{cell.row_label}: {cell.raw_value} · {cell.period_end}','row_label':cell.row_label,
            'column_label':' / '.join(cell.header_path),'verification':'VERIFIED_SOURCE_CELL','unit':cell.unit})
    values = [c.value for c in cells]
    label = METRICS[metric][0]
    lines = [f'{label} của {chosen[0][1]["ticker"]} được đối chiếu từ bảng trong filing SEC.',
             '| Kỳ nguồn | Triệu USD | Filing |\n| --- | ---: | --- |\n'+'\n'.join(
                 f'| {c.period_start+" → " if c.period_start else ""}{c.period_end} | {display(str(c.value))} | {c.accession} [{i}] |'
                 for i,c in enumerate(cells,1))]
    result = list(values)
    formula = None
    if len(values)==2 and operation!='COMPARE':
        old,new = values
        with localcontext() as ctx:
            ctx.prec = 50
            delta = new-old
            lines.append(f'Chênh lệch = {display(str(new))} − {display(str(old))} = **{display(str(delta))} triệu USD**. [1][2]')
            result = [delta]
            formula = 'current - previous'
            if old and operation!='ABS_CHANGE':
                change = (delta/old*100).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
                lines.append(f'Mức thay đổi = chênh lệch ÷ {display(str(old))} × 100 = **{display(str(change))}%**. [1][2]')
                if operation=='PERCENT_CHANGE':
                    result = [change]
                    formula = '(current - previous) / previous * 100'
            elif operation=='PERCENT_CHANGE':
                return abstain('SEC_ZERO_BASE','Kỳ gốc bằng 0 nên không xác định được phần trăm thay đổi.',timings=timings)
    timings['compute_and_citations'] = (perf_counter()-begin)*1000
    timings['total'] = (perf_counter()-started)*1000
    return {'status':'SUPPORTED','answer_status':'VERIFIED_ANSWER','answer':'\n\n'.join(lines),
            'values':[str(value) for value in result],'unit':'%' if operation=='PERCENT_CHANGE' else 'MILLION_USD',
            'citations':citations,'source_cells':[cell.model_dump(mode='json') for cell in cells],
            'verification_status':'VERIFIED_IXBRL_SOURCE_CELLS_AND_DECIMAL','timings_ms':timings,'formula':formula,
            'operation':operation,'sec_context':{'metric':metric,'period':period,'targets':targets,
                'ticker':chosen[0][1]['ticker'],'metric_phrase':{'revenue':'net sales','income':'net income','assets':'total assets'}[metric],
                'question':question}}

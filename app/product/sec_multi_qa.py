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

from app.table_evidence.product_concepts import PRODUCT_ROWS

METRICS = {
    **{code: (label, rows) for code,(label,rows,_) in PRODUCT_ROWS.items()},
    'revenue': ('Doanh thu', {'net sales','total net sales','revenue','total revenue','net revenue'}),
    'income': ('Lợi nhuận ròng', {'net income','net income (loss)'}),
    'assets': ('Tổng tài sản', {'total assets'}),
}
WEEK_WORDS = {'twelve':12,'thirteen':13,'twenty-four':24,'twenty-six':26,'thirty-six':36,'thirty-nine':39}
COMPARISON = r'\b(?:so voi|so sanh|compared|compare|versus|vs|thay doi|tang bao nhieu|giam bao nhieu|chenh lech|year.over.year|yoy)\b'


METRIC_PATTERNS = {
    'deferred_revenue': r'deferred revenue|unearned revenue|doanh thu chua thuc hien|doanh thu tra truoc',
    'cost_of_revenue': r'cost of (?:sales|revenue|goods sold)|gia von(?: hang ban)?',
    'operating_cash': r'net cash from operations|(?:net )?cash (?:flow|from|provided by) operating activities|operating cash flow|(?:luu chuyen |dong )tien (?:thuan )?tu hoat dong kinh doanh|dong tien hoat dong',
    'investing_cash': r'cash (?:flow|from|used in) investing activities|luu chuyen tien (?:thuan )?tu hoat dong dau tu',
    'financing_cash': r'cash (?:flow|from|used in) financing activities|luu chuyen tien (?:thuan )?tu hoat dong tai chinh',
    'comprehensive_income': r'(?:total )?comprehensive income|thu nhap toan dien',
    'operating_income': r'operating (?:income|profit)|loi nhuan (?:tu )?hoat dong kinh doanh',
    'gross_profit': r'gross profit|loi nhuan gop',
    'current_assets': r'(?:total )?current assets|tai san ngan han',
    'current_liabilities': r'(?:total )?current liabilities|no ngan han',
    'liabilities': r'total liabilities|tong no phai tra',
    'income': r'net income|loi nhuan rong|loi nhuan sau thue',
    'assets': r'total assets|tong tai san',
    'revenue': r'(?:total )?(?:net sales|revenue|net revenue)|(?:tong )?doanh thu(?: thuan)?',
}
INSTANT_METRICS = {'assets','current_assets','liabilities','current_liabilities','deferred_revenue'}


def requested_metrics(q):
    matches = []
    for metric, pattern in METRIC_PATTERNS.items():
        regex = rf'\b(?:{pattern})\b'
        if re.search(regex,q):
            matches.append(metric)
            q = re.sub(regex,' ',q)
    return matches


def metric_for(q):
    metrics = requested_metrics(q)
    return metrics[0] if len(metrics)==1 else None


def period_for(q, sources, metric):
    if metric in INSTANT_METRICS:
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


def duration_days(cell):
    return ((date.fromisoformat(cell.period_end)-date.fromisoformat(cell.period_start)).days+1
            if cell.period_start else None)


def period_matches(cell, period):
    if period=='INSTANT':
        return cell.period_kind=='INSTANT'
    if cell.period_kind!='DURATION':
        return False
    if isinstance(period,tuple):
        days = duration_days(cell)
        return days%7==0 and days//7 in period
    if period=='YTD':
        return cell.period_months in {6,9}
    return period is None or cell.period_months==period


def target_matches(cell, filing, target, fiscal):
    if len(target)!=4 or not fiscal:
        return cell.period_end.startswith(target)
    focused_year=filing.get('fiscal_year')
    report_end=filing['report_period']
    if focused_year is None or not report_end:
        return False
    if cell.period_end==report_end:
        return str(focused_year)==target
    if filing['form'] in {'10-K','20-F'} and cell.period_end[5:7]==report_end[5:7]:
        observed_year=focused_year-int(report_end[:4])+int(cell.period_end[:4])
        return str(observed_year)==target
    return False


def abstain(reason, text, *, timings=None):
    return {'status':'NEEDS_CLARIFICATION','answer_status':'REQUIRES_SOURCE_REVIEW','answer':text,
            'reason':reason,'values':[],'citations':[],'timings_ms':timings or {}}


def resolve_followup(question, previous):
    context = previous.get('sec_context') or {}
    if not context:
        return question
    q = folded(question)
    if re.fullmatch(r'(?:the |con |vay )?(?:cung ky nam truoc|same period last year)[?!. ]*',q):
        period=context['period']
        if isinstance(period,list):
            if len(period)!=1:
                return question
            duration=f'{period[0]} weeks'
        else:
            duration={3:'three months',6:'six months',9:'nine months',12:'full year','YTD':'year to date'}.get(period,'')
        if duration:
            target=context['targets'][-1]
            return f"{context['ticker']} {context['metric_phrase']} {duration} {target} cùng kỳ năm trước, chỉ lấy kỳ trước"
    if re.search(r'^\b(?:the |con |vay )?nam truoc\b',q) and context['period']==12:
        return f"{context['ticker']} {context['metric_phrase']} FY{int(context['targets'][-1][:4])-1}"
    if re.search(r'^(?:hai |cac )?(?:so|gia tri).*(?:filing|nguon|bao cao)|(?:xem|mo).*so goc',q):
        return context['question']
    return question


def answer(index, question, ticker, key, operation='EXTRACT', *, metric_override=None, default_quarter=False, single_observation=False):
    q = folded(question)
    metric = metric_override or metric_for(q)
    if not metric:
        return None
    explanation = re.search(r'\b(?:vi sao|tai sao|nguyen nhan|why|explain)\b',q)
    if re.search(r'\b(?:services|products|segment|geographic|mang|khu vuc|phan khuc|ty trong|margin|adjusted|dieu chinh|restat\w*|trinh bay lai)\b',q):
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
    if not sources:
        return abstain('SEC_ISSUER_NOT_SELECTED','Filing của doanh nghiệp được hỏi chưa nằm trong bộ nguồn đang chọn.')
    if len({row['cik'] for row,_ in sources})!=1:
        return abstain('SEC_COMPANY_SCOPE_AMBIGUOUS','Hãy nêu tên doanh nghiệp trong câu hỏi hoặc chọn các filing của cùng một doanh nghiệp.')
    if any(row['form'] not in {'10-K','10-Q','20-F'} for row,_ in sources):
        return abstain('SEC_REPORTING_BASIS_UNSUPPORTED','Các filing đang chọn cần đối chiếu riêng về loại báo cáo hoặc trạng thái sửa đổi.')
    fiscal = bool(re.search(r'\bfy\s*20\d{2}|\b(?:fiscal year|nam tai chinh)\b',q))
    dates = tuple(sorted(set(re.findall(r'\b20\d{2}-\d{2}-\d{2}\b',q))))
    years = tuple(sorted(set(re.findall(r'\b(?:fy\s*)?(20\d{2})\b',re.sub(r'\b20\d{2}-\d{2}-\d{2}\b','',q)))))
    if not dates and plan.period_end:
        dates = (plan.period_end,)
        years = tuple(y for y in years if y!=plan.period_end[:4])
    period = period_for(q,sources,metric)
    if default_quarter and period is None and len(sources)==1 and sources[0][0]['form']=='10-Q':
        period=3
    same_period = bool(re.search(r'\b(?:cung ky|same period|prior.year|comparative period)\b',q))
    different_durations = isinstance(period,tuple) and len(period)>1
    if different_durations and len(period)>4:
        return abstain('SEC_TOO_MANY_DURATIONS','Hãy chọn tối đa bốn độ dài kỳ để đối chiếu.')
    if dates and fiscal and years and all(str(row.get('fiscal_year')) not in years for row,_ in sources):
        return abstain('SEC_FISCAL_PERIOD_ABSENT','Filing kết thúc '+dates[-1]+' không có kỳ tài chính '+', '.join(years)+' được yêu cầu.')
    ordinal = re.search(r'\b(?:quy|q|quarter)\s*(iv|iii|ii|i|[1-4])\b',q)
    if ordinal and fiscal:
        number={'i':'1','ii':'2','iii':'3','iv':'4'}.get(ordinal[1],ordinal[1])
        matching=[row for row,_ in sources if row.get('fiscal_period')==f'Q{number}'
                  and (not years or str(row.get('fiscal_year')) in years)
                  and (not dates or row['report_period'] in dates)]
        if not matching:
            available=', '.join(sorted({f"{row.get('fiscal_period') or row['form']} FY{row['fiscal_year']} kết thúc {row['report_period']}"
                                        if row.get('fiscal_year') else f"{row['form']} kết thúc {row['report_period']}" for row,_ in sources}))
            return abstain('SEC_FISCAL_PERIOD_ABSENT',f'Filing đang chọn có {available}. Không tìm thấy quý tài chính {number} được yêu cầu.')
    if explanation and not different_durations:
        return None
    compare = bool((not single_observation and re.search(COMPARISON,q)) or operation!='EXTRACT' or len(years)>1 or len(dates)>1)
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
    if same_period and len(targets)==1:
        if not period:
            return abstain('SEC_PERIOD_DURATION_REQUIRED','Hãy cho biết bạn muốn so sánh quý hay kỳ lũy kế.')
        current=targets[0]
        prior=str(int(current[:4])-1)
        matching_dates={c.period_end for c,_,_ in collected if c.period_end.startswith(prior)
                        and (len(current)==4 or c.period_end[5:7]==current[5:7])}
        if len(matching_dates)!=1:
            return abstain('SEC_PRIOR_PERIOD_UNBOUND','Không gắn được một kỳ so sánh duy nhất trong filing đang chọn.')
        prior_only='chi lay ky truoc' in q
        targets=[next(iter(matching_dates))] if prior_only else [next(iter(matching_dates)),current]
        compare=not prior_only
    if len(targets) not in {1,2} or (compare and len(targets)!=2 and not different_durations):
        return abstain('SEC_COMPARISON_PERIODS_REQUIRED','Hãy chỉ rõ hai năm tài chính hoặc hai ngày kết thúc kỳ cần so sánh.')
    chosen = []
    if different_durations and len(targets)!=1:
        return abstain('SEC_DURATION_END_REQUIRED','Hãy nêu một ngày kết thúc để đối chiếu nhiều độ dài kỳ.')
    requests=[(targets[0],(weeks,)) for weeks in period] if different_durations else [(target,period) for target in targets]
    for target, duration in requests:
        options = [(cell,filing,part) for cell,filing,part in collected if target_matches(cell,filing,target,fiscal)
                   and period_matches(cell,duration)]
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
    if different_durations:
        dimensions={(c.cik,c.unit,c.multiplier,c.period_kind,c.fact_name.casefold()) for c in cells}
    if len(dimensions)!=1:
        return abstain('SEC_COMPARISON_DIMENSION_CONFLICT','Hai ô khác loại kỳ, khái niệm iXBRL hoặc đơn vị. Tôi có thể đối chiếu từng kỳ riêng.',timings=timings)
    if not different_durations and len(cells)==2 and cells[0].period_start and cells[1].period_start:
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
    with localcontext() as ctx:
        ctx.prec = 50
        values = [c.effective_value/Decimal(1_000_000) for c in cells]
    def describe_duration(cell):
        days=duration_days(cell)
        if not days:
            return 'Tại ngày báo cáo'
        if isinstance(period,tuple):
            return f'{days//7} tuần'
        return f'{cell.period_months} tháng ({days} ngày)'
    label = METRICS[metric][0]
    lines = [f'{label} của {chosen[0][1]["ticker"]} được đối chiếu từ bảng trong filing SEC.',
             '| Kỳ nguồn | Độ dài | Triệu USD | Filing |\n| --- | --- | ---: | --- |\n'+'\n'.join(
                 f'| {c.period_start+" → " if c.period_start else ""}{c.period_end} | {describe_duration(c)} | {display(str(value))} | {c.accession} [{i}] |'
                 for i,(c,value) in enumerate(zip(cells,values),1))]
    result = list(values)
    checks = [('EXTRACT',values[0])] if len(values)==1 else []
    formula = None
    if any('PRODUCT_SALES_DIMENSION_EXCLUDES_MEMBERSHIPS' in cell.warnings for cell in cells):
        lines.append('Dòng doanh thu bán hàng này không bao gồm phí thành viên theo phạm vi iXBRL của ô nguồn.')
    if different_durations:
        lines.append('Các giá trị có cùng ngày kết thúc nhưng bắt đầu ở những ngày khác nhau. '
                     'Kỳ dài hơn bao gồm phần hoạt động trước kỳ ngắn hơn, vì vậy hai giá trị đo các khoảng thời gian khác nhau.')
        checks=[('PERIOD_VALUES', values)]
    if not different_durations and len(values)==2 and operation!='COMPARE':
        old,new = values
        with localcontext() as ctx:
            ctx.prec = 50
            delta = new-old
            lines.append(f'Chênh lệch = {display(str(new))} − {display(str(old))} = **{display(str(delta))} triệu USD**. [1][2]')
            result = [delta]
            checks.append(('ABS_CHANGE',delta))
            formula = 'current - previous'
            if old and operation!='ABS_CHANGE':
                change = (delta/old*100).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
                checks.append(('PERCENT_CHANGE',change))
                lines.append(f'Mức thay đổi = chênh lệch ÷ {display(str(old))} × 100 = **{display(str(change))}%**. [1][2]')
                if operation=='PERCENT_CHANGE':
                    result = [change]
                    formula = '(current - previous) / previous * 100'
            elif operation=='PERCENT_CHANGE':
                return abstain('SEC_ZERO_BASE','Kỳ gốc bằng 0 nên không xác định được phần trăm thay đổi.',timings=timings)
    source_cells = [{**cell.model_dump(mode='json'),'duration_days':duration_days(cell),
                     'scope':'CONSOLIDATED_PRODUCTS' if 'PRODUCT_SALES_DIMENSION_EXCLUDES_MEMBERSHIPS' in cell.warnings else 'CONSOLIDATED',
                     'dimensions':[{'axis':'ProductOrServiceAxis','member':'ProductMember'}]
                       if 'PRODUCT_SALES_DIMENSION_EXCLUDES_MEMBERSHIPS' in cell.warnings else []}
                    for cell in cells]
    from app.product.sec_answer_contract import verify_comparison
    try:
        independent = verify_comparison(source_cells,checks)
    except (ValueError,ArithmeticError):
        return {**abstain('SEC_INDEPENDENT_ARITHMETIC_MISMATCH','Các ô nguồn được giữ lại để đối chiếu; phép tính chưa vượt qua kiểm tra độc lập.',timings=timings),
                'citations':citations}
    timings['compute_and_citations'] = (perf_counter()-begin)*1000
    timings['total'] = (perf_counter()-started)*1000
    return {'status':'SUPPORTED','answer_status':'VERIFIED_ANSWER','answer':'\n\n'.join(lines),
            'values':[str(value) for value in result],'unit':'%' if operation=='PERCENT_CHANGE' else 'MILLION_USD',
            'citations':citations,'source_cells':source_cells,'independent_verification':independent,
            'verification_status':'VERIFIED_IXBRL_SOURCE_CELLS_AND_DECIMAL','timings_ms':timings,'formula':formula,
            'operation':'COMPARE' if different_durations else 'ABS_CHANGE' if len(values)==2 and operation=='EXTRACT' else operation,'sec_context':{'metric':metric,'period':period,'targets':targets,
                'ticker':chosen[0][1]['ticker'],'metric_phrase':('net sales' if metric=='revenue' and re.search(r'net sales|doanh thu thuan',q) else
                                 {'operating_cash':'operating cash flow','revenue':'revenue','income':'net income',
                                  'assets':'total assets'}.get(metric,metric.replace('_',' '))),
                'question':question}}

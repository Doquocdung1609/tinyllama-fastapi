"""Bind and compose financial ratios from authenticated SEC cell pairs."""
from datetime import date
from decimal import Decimal, ROUND_HALF_UP, localcontext
import re

from app.product.answer_composer_v2 import display
from app.product.pdf_extract import folded
from app.product.sec_a5 import plan_query
from app.product.sec_answer_contract import verify_comparison
from app.product.sec_multi_qa import abstain, duration_days, observations, period_for, period_matches
from app.product.sec_viewer import reference

PRIOR = re.compile(r'\b(?:cung ky(?: truoc| nam truoc)?|cung quy nam (?:truoc|ngoai)|same (?:quarter|period)(?: last year| a year earlier)?|prior.year|year.over.year|yoy)\b')
MOVEMENT = re.compile(r'\b(?:diem phan tram|percentage points?|subtract|tru|chenh lech|thay doi|change)\b')
CURRENT = re.compile(r'\b(?:hien tai|moi nhat|current|latest)\b')
SHORTEST = re.compile(r'\b(?:ky ngan nhat|shortest (?:available |reported )?period)\b')
TOTAL = re.compile(r'\b(?:tong doanh thu|total revenue)\b')
SALES = re.compile(r'\b(?:doanh thu thuan(?: ban hang)?|net sales|net revenue)\b')
PRODUCTS = re.compile(r'\b(?:doanh thu thuan ban hang|net (?:product|merchandise) sales)\b')
DENOMINATORS = {
    'TOTAL_REVENUE': ('Tổng doanh thu', {'total revenue','revenue','total revenues'}),
    'NET_SALES': ('Doanh thu thuần', {'net sales','total net sales','net revenue'}),
    'PRODUCT_NET_SALES': ('Doanh thu thuần bán hàng', {'net sales','net product sales'}),
}
TITLES={'operating_income':'Biên lợi nhuận hoạt động','gross_profit':'Biên lợi nhuận gộp','income':'Biên lợi nhuận ròng'}


def ratio_variants(q):
    labels=[]
    if total:=TOTAL.search(q):
        labels.append((total.start(),'TOTAL_REVENUE'))
    product=PRODUCTS.search(q)
    if sales:=product or SALES.search(q):
        labels.append((sales.start(),'PRODUCT_NET_SALES' if product else 'NET_SALES'))
    return [variant for _,variant in sorted(labels)] or ['REPORTED_REVENUE']


def _scope(cell):
    return 'CONSOLIDATED_PRODUCTS' if 'PRODUCT_SALES_DIMENSION_EXCLUDES_MEMBERSHIPS' in cell.warnings else 'CONSOLIDATED'


def _record(cell):
    scope=_scope(cell)
    return {**cell.model_dump(mode='json'),'duration_days':duration_days(cell),'scope':scope,
            'dimensions':[{'axis':'ProductOrServiceAxis','member':'ProductMember'}] if scope=='CONSOLIDATED_PRODUCTS' else []}


def _citation(cell, filing, part, key):
    return {'source_kind':'SEC','issuer':filing['issuer'],'filing_id':cell.filing_id,'accession':cell.accession,
            'generation':cell.generation,'source_sha256':cell.raw_sha256,'chunk_id':cell.parent_id,
            'report_period':cell.period_end,'form':filing['form'],'source_url':cell.source_url,
            'text':f'{cell.row_label}: {cell.raw_value} · {cell.period_end}','row_label':cell.row_label,
            'column_label':' / '.join(cell.header_path),'unit':cell.unit,'verification':'VERIFIED_SOURCE_CELL',
            'source_reference':reference(part,cell.parent_id,key,cell.model_dump(mode='json'))}


def _choose(cells, labels):
    matches=[c for c in cells if c.row_label.strip().casefold() in labels]
    if len({c.effective_value for c in matches})!=1:
        return None
    return min(matches,key=lambda c:(c.row_label.strip().casefold() not in {'total revenue','total net sales'},
                                     c.structural_path))


def _eligible(cells, end, duration):
    return [c for c in cells if c.period_end==end and period_matches(c,duration)]


def _denominator(profit, cells, variant):
    compatible=[c for c in cells if (c.period_start,c.period_end,c.unit,c.filing_id,c.cik,c.raw_sha256,c.generation)==
                (profit.period_start,profit.period_end,profit.unit,profit.filing_id,profit.cik,profit.raw_sha256,profit.generation)]
    plain=[c for c in compatible if _scope(c)==_scope(profit)]
    if variant=='REPORTED_REVENUE':
        # Prefer a stated total. A consolidated net sales line can be the
        # reported revenue when the statement has no distinct total.
        for labels in ({'total revenue','total revenues'},{'net sales','total net sales','net revenue','revenue'}):
            if any(c.row_label.strip().casefold() in labels for c in plain):
                return _choose(plain,labels)
        return None
    pool=plain
    if variant=='PRODUCT_NET_SALES':
        pool=[c for c in compatible if _scope(c)=='CONSOLIDATED_PRODUCTS' or
              c.row_label.strip().casefold()=='net product sales']
    return _choose(pool,DENOMINATORS[variant][1])


def _prior_end(current, profits, revenues, duration, variant):
    """Use actual year-earlier columns with the same reporting duration."""
    end=date.fromisoformat(current.period_end)
    candidates=set()
    for cell in profits:
        if not period_matches(cell,duration):
            continue
        prev=date.fromisoformat(cell.period_end)
        if prev.year==end.year-1 and abs((end-prev).days-365)<=8 and abs(duration_days(current)-duration_days(cell))<=7:
            if _denominator(cell,revenues,variant):
                candidates.add(cell.period_end)
    return next(iter(candidates)) if len(candidates)==1 else None


def _failure(reason,text,expected):
    reply=abstain(reason,text)
    reply['answer_completeness']={'completed':0,'required':expected}
    return reply


def margin(sources, question, ticker, key, metric):
    q=folded(question)
    variants=ratio_variants(q)
    explicit_dates=sorted(set(re.findall(r'\b20\d{2}-\d{2}-\d{2}\b',q)) | {
        f'{year}-{int(month):02d}-{int(day):02d}' for day,month,year in
        re.findall(r'\b(\d{1,2})/(\d{1,2})/(20\d{2})\b',q)})
    year_prior=bool(PRIOR.search(q))
    compare=year_prior or len(explicit_dates)==2
    relative=bool(re.search(r'\b(?:relative (?:change|growth)|tang truong tuong doi|thay doi tuong doi)\b',q))
    explicit_relative_only=relative and not re.search(r'\b(?:diem phan tram|percentage points?)\b',q)
    targets=1+int(compare)+int(compare and not explicit_relative_only)+int(compare and relative)
    variant_delta=not compare and len(variants)==2 and bool(MOVEMENT.search(q)) and not relative
    expected=len(variants)*targets+int(variant_delta)
    if len(explicit_dates)>2 or (MOVEMENT.search(q) and not compare and not variant_delta):
        return _failure('SEC_MARGIN_COMPARISON_PERIOD_REQUIRED',
                        'Bạn muốn đối chiếu với cùng kỳ năm trước hay kỳ cụ thể nào?',max(expected,3))
    # These Vietnamese expressions use “đồng” in a non-currency sense.
    plan=plan_query(re.sub(r'\bđồng\s+(?:nhất|thời|ý)\b',' ',question,flags=re.I))
    if plan.scope=='PARENT' or plan.currency not in {None,'USD'}:
        return _failure('SEC_UNSUPPORTED_DIMENSION','Chưa hỗ trợ phép tính biên lợi nhuận cho phạm vi hoặc tiền tệ đã hỏi.',expected)
    if not sources:
        return _failure('SEC_ISSUER_NOT_SELECTED','Hãy chọn filing của doanh nghiệp được hỏi.',expected)
    quarter=plan.quarter
    roman=re.search(r'\bquy\s+(iv|iii|ii|i)\b',q)
    if roman:
        quarter={'i':1,'ii':2,'iii':3,'iv':4}[roman[1]]
    if quarter:
        sources=[(row,part) for row,part in sources if row.get('fiscal_period')==f'Q{quarter}']
    if plan.form:
        sources=[(row,part) for row,part in sources if row.get('form')==plan.form]
    accession=re.search(r'\b\d{10}-\d{2}-\d{6}\b',q)
    if accession:
        sources=[(row,part) for row,part in sources if row.get('accession')==accession[0]]
    if plan.period_end:
        anchor=explicit_dates[-1] if len(explicit_dates)==2 else plan.period_end
        sources=[(row,part) for row,part in sources if row['report_period']==anchor]
    else:
        years=set(re.findall(r'\b20\d{2}\b',q))
        if years:
            fiscal=bool(re.search(r'\bfy\s*20\d{2}|fiscal year|nam tai chinh',q))
            sources=[(row,part) for row,part in sources if
                     (str(row.get('fiscal_year')) if fiscal else row['report_period'][:4]) in years]
    if not sources:
        return _failure('SEC_FISCAL_PERIOD_ABSENT','Bộ filing đang chọn thiếu kỳ hoặc loại báo cáo bạn yêu cầu cho '+ticker+'.',expected)
    if len({row['report_period'] for row,_ in sources})>1 and (CURRENT.search(q) or compare) and not plan.period_end:
        # Current is the latest selected report of the requested issuer.
        # Earlier selected filings never become the comparison period.
        if re.search(r'\b(?:quy|quarter|quarterly)\b',q):
            sources=[(row,part) for row,part in sources if row.get('form')=='10-Q']
        if sources:
            latest=max(row['report_period'] for row,_ in sources)
            sources=[(row,part) for row,part in sources if row['report_period']==latest]
    if len(sources)!=1:
        return _failure('SEC_FILING_PERIOD_AMBIGUOUS','Bạn muốn dùng filing nào của '+ticker+'? Hãy nêu ngày kết thúc hoặc accession.',expected)
    filing,part=sources[0]
    end=filing['report_period']
    explicit_weeks=tuple(sorted({int(w) for w in re.findall(r'\b(\d{1,2})[ -]*(?:tuan|weeks?)\b',q)}))
    explicit_months={int(m) for m in re.findall(r'\b(\d{1,2})[ -]*(?:thang|months?)\b',q)}
    if not SHORTEST.search(q) and (len(explicit_months)>1 or explicit_months and explicit_weeks):
        return _failure('SEC_MARGIN_DURATION_AMBIGUOUS','Hãy nêu một độ dài kỳ cho mỗi phép tính biên lợi nhuận.',expected)
    duration=(None if SHORTEST.search(q) else explicit_weeks or
              (next(iter(explicit_months)) if explicit_months else period_for(q,sources,metric)))
    if isinstance(duration,tuple) and len(duration)>1:
        return _failure('SEC_MARGIN_DURATION_AMBIGUOUS','Hãy nêu một độ dài kỳ cho mỗi phép tính biên lợi nhuận.',expected)
    profits=observations(part,filing,metric)
    sales=observations(part,filing,'revenue',{'net sales','total net sales','net revenue','revenue','total revenue',
                                            'total revenues','net product sales'})
    current=_eligible(profits,end,duration)
    if current and duration is None:
        shortest=min(duration_days(c) for c in current)
        current=[c for c in current if duration_days(c)==shortest]
        duration=current[0].period_months
    current=_choose(current,{c.row_label.strip().casefold() for c in current})
    if not current or _scope(current)!='CONSOLIDATED':
        return _failure('SEC_MARGIN_SOURCE_UNAVAILABLE','Chưa gắn được ô '+TITLES[metric].lower()+' cho kỳ '+end+'.',expected)

    refs,records,steps,lines,values,proofs=[],[],[],[],[],[]
    def compute(profit,revenue,variant,role):
        operands=[_record(c) for c in (profit,revenue)]
        if revenue.effective_value<=0:
            return None
        with localcontext() as ctx:
            ctx.prec=50
            exact=profit.effective_value/revenue.effective_value*100
            result=exact.quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
        proof=verify_comparison(operands,[('MARGIN_PERCENT',result)])
        proofs.extend(proof['stage_b'])
        numbers=[]
        for cell,record in zip((profit,revenue),operands):
            position=next((i for i,r in enumerate(records,1) if r==record),None)
            if position is None:
                refs.append(_citation(cell,filing,part,key))
                records.append(record)
                position=len(refs)
            numbers.append(position)
        values.append(str(result))
        steps.append({'operation':'MARGIN_PERCENT','denominator':variant,'role':role,'unit':'%',
                      'period_start':profit.period_start,'period_end':profit.period_end,
                      'duration_days':duration_days(profit),'citations':numbers,'result':str(result)})
        days=duration_days(profit)
        length=f'{days//7} tuần' if days%7==0 else f'{profit.period_months} tháng ({days} ngày)'
        lines.append(f'**{role} · {profit.period_start} đến {profit.period_end} ({length}): {display(result)}%**. '
                     f'{profit.row_label} {display(profit.effective_value/1000000)} triệu USD [{numbers[0]}] ÷ '
                     f'{revenue.row_label} {display(revenue.effective_value/1000000)} triệu USD [{numbers[1]}] × 100.')
        return exact,operands,numbers

    available=[]
    computed=[]
    for variant in variants:
        name=DENOMINATORS.get(variant,('Doanh thu trên báo cáo',None))[0]
        lines.append(f'### {name}')
        revenue=_denominator(current,sales,variant)
        present=compute(current,revenue,variant,'Kỳ hiện tại' if compare else 'Kỳ báo cáo') if revenue else None
        if present is None:
            lines.append(f'Chưa xác minh được mẫu số {name.lower()} cùng kỳ và phạm vi.')
            continue
        available.append((variant,revenue))
        computed.append(present)
        if _scope(revenue)=='CONSOLIDATED_PRODUCTS':
            lines.append('Mẫu số là doanh thu bán hàng, không gồm phí thành viên. Tử số là lợi nhuận hoạt động hợp nhất.')
        if not compare:
            continue
        prior_end=(_prior_end(current,profits,sales,duration,variant) if year_prior else explicit_dates[0])
        if year_prior and len(explicit_dates)==2 and prior_end!=explicit_dates[0]:
            prior_end=None
        prior=_choose(_eligible(profits,prior_end,duration),{current.row_label.strip().casefold()})
        prior_revenue=_denominator(prior,sales,variant) if prior else None
        if (not prior_revenue or _scope(prior_revenue)!=_scope(revenue)
                or prior_revenue.fact_name.casefold()!=revenue.fact_name.casefold()
                or abs(duration_days(prior)-duration_days(current))>7
                or prior.fact_name.casefold()!=current.fact_name.casefold()
                or prior_revenue.row_label.strip().casefold()!=revenue.row_label.strip().casefold()):
            lines.append('Chưa tìm thấy cột kỳ so sánh có cùng định nghĩa và độ dài trong filing này.')
            continue
        previous=compute(prior,prior_revenue,variant,'Cùng kỳ năm trước' if year_prior else 'Kỳ so sánh')
        if previous is None:
            lines.append('Chưa tính được biên của cùng kỳ năm trước vì doanh thu không dương.')
            continue
        operations=[]
        with localcontext() as ctx:
            ctx.prec=50
            if not explicit_relative_only:
                operations.append(('MARGIN_DELTA_PP',(present[0]-previous[0]).quantize(Decimal('.01'),rounding=ROUND_HALF_UP),'điểm phần trăm'))
            if relative and previous[0]!=0:
                operations.append(('MARGIN_RELATIVE_CHANGE',((present[0]/previous[0]-1)*100).quantize(Decimal('.01'),rounding=ROUND_HALF_UP),'%'))
        numbers=present[2]+previous[2]
        proofs.extend(verify_comparison(present[1]+previous[1],[(op,result) for op,result,_ in operations])['stage_b'])
        for op,result,unit in operations:
            values.append(str(result))
            steps.append({'operation':op,'denominator':variant,'unit':unit,'citations':numbers,'result':str(result)})
            signed=('+' if result>0 else '')+display(result)
            lines.append(f'**Thay đổi {"tương đối" if unit=="%" else "của biên"}: {signed} {unit}**. '
                         + ('Lấy tỷ số giữa hai biên, trừ 1 rồi nhân 100.' if unit=='%' else
                            'Lấy biên kỳ hiện tại trừ biên kỳ so sánh, rồi làm tròn kết quả.'))
    if len(variants)>1:
        if len(available)==len(variants):
            if len({c.effective_value for _,c in available})==1:
                lines.append('Hai dòng nguồn có cùng giá trị ở kỳ này, nên dùng cùng tử số cho ra hai tỷ lệ bằng nhau.')
            else:
                largest=max(available,key=lambda item:item[1].effective_value)
                lines.append(f'Cùng tử số, mẫu số “{largest[1].row_label}” lớn hơn nên cho tỷ lệ thấp hơn. '
                             'Mỗi tỷ lệ dùng đúng dòng doanh thu ghi trong bảng.')
        else:
            lines.append('Chưa thể đối chiếu hai tỷ lệ vì còn thiếu mẫu số đã xác minh.')
    if variant_delta and len(computed)==2:
        first,second=computed
        with localcontext() as ctx:
            ctx.prec=50
            delta=(first[0]-second[0]).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
        proofs.extend(verify_comparison(first[1]+second[1],[('MARGIN_DELTA_PP',delta)])['stage_b'])
        values.append(str(delta))
        steps.append({'operation':'MARGIN_DELTA_PP','denominators':variants,'unit':'điểm phần trăm',
                      'citations':first[2]+second[2],'result':str(delta),'basis':'FIRST_VARIANT_MINUS_SECOND'})
        lines.append(f'**Chênh lệch: {display(delta)} điểm phần trăm** theo thứ tự tỷ lệ thứ nhất trừ tỷ lệ thứ hai.')
    completed=len(steps)
    return {'status':'SUPPORTED' if completed==expected else 'SOURCE_EXCERPTS',
            'answer_status':'VERIFIED_ANSWER' if completed==expected else 'PARTIAL_VERIFIED' if completed else 'REQUIRES_SOURCE_REVIEW',
            'answer':f'{TITLES[metric]} của **{ticker}** · {filing["form"]} kết thúc {end}.\n\n'+'\n\n'.join(lines),
            'citations':refs,'source_cells':records,'values':values,'unit':'%' if not (compare or variant_delta) else None,
            'ratio_steps':steps,'answer_completeness':{'completed':completed,'required':expected},
            'independent_verification':{'status':'VERIFIED','stage_b':proofs} if proofs else None,
            'sec_task_context':{'kind':'MARGIN','metric':metric,'issuer':ticker,'denominators':variants,
                                'duration':duration,'report_end':end,'relation':'PRIOR_YEAR' if year_prior else None}}

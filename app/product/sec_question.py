"""Resolve SEC tasks against the selected, authenticated filing set."""
from collections import defaultdict
from datetime import date
from decimal import Decimal, ROUND_HALF_UP, localcontext
from time import perf_counter
import re

from app.financial_index.corpus import verified_source
from app.product.pdf_extract import folded
from app.product.sec_a5 import plan_query
from app.product.sec_library import FederatedIndex, ScopedIndex, partitions
from app.product.sec_multi_qa import abstain, answer as numeric_answer, observations, requested_metrics
from app.product.sec_ontology_v8 import ISSUERS
from app.product.sec_task_plan import plan_sec_question
from app.product.sec_viewer import reference

RISK = re.compile(r'\b(?:rui ro|nguy co|bat dinh|risks?|risk factors?|uncertaint\w*)\b')
MANAGEMENT = re.compile(r'\b(?:thao luan cua ban quan ly|management.s discussion|md&a|liquidity|thanh khoan)\b')
MARGIN = re.compile(r'\b(?P<gross>gross (?:profit )?margin|bien loi nhuan gop|ty suat loi nhuan gop)\b|'
                    r'\b(?:operating margin|bien loi nhuan hoat dong|bien hoat dong|ty suat loi nhuan hoat dong|'
                    r'phan tram loi nhuan (?:tu )?hoat dong tren (?:tong )?doanh thu)\b')
PROFILE = re.compile(r'\b(?:do dai ky|don vi tien te|pham vi bao cao|reporting duration|reporting scope|filing profile)\b')
NO_CHANGE = re.compile(r'\bno (?:material|significant) changes?\b.{0,250}\brisk factors?\b|\brisk factors?\b.{0,240}\b(?:no material changes?|have not materially changed)\b', re.I)
RISK_TOPIC = re.compile(r'\b(?:tariffs?|inflation|competition|foreign exchange|currency|cybersecurity|supply chain|'
                        r'interest rates?|economic conditions?|regulation|geopolitical|security risks?)\b',re.I)
DISCLOSURE = re.compile(r'\b(?:competit\w*|uncertain\w*|could|may|risk|adversely|impact|volatil\w*|challeng\w*|fluctuat\w*)\b',re.I)


def _matches(q, name):
    return bool(name and re.search(r'(?<!\w)'+re.escape(folded(name))+r'(?!\w)',q))


def resolve_sources(index, question, ticker=None):
    groups = defaultdict(list)
    for part in partitions(index):
        for filing in part.catalog_rows:
            groups[filing['ticker']].append((filing,part))
    plan = plan_sec_question(question, groups, ticker)
    return groups, plan.eligible_entities, plan.unselected_entities, plan.error


def _scoped(sources):
    groups = defaultdict(list)
    for filing,part in sources:
        groups[part].append(filing['filing_id'])
    narrowed=[ScopedIndex(part,ids) for part,ids in groups.items()]
    return narrowed[0] if len(narrowed)==1 else FederatedIndex(narrowed)


def _citation(part, filing, chunk, key, text):
    item=part.by_id[chunk.chunk_id]
    canonical=verified_source(item['frozen'],cache=part._cache,generation=part.identity['generation'])
    if canonical.get(chunk.chunk_id)!=chunk:
        raise ValueError('SEC_CANONICAL_PARENT_MISMATCH')
    return {'source_kind':'SEC','issuer':filing['issuer'],'filing_id':filing['filing_id'],
            'accession':filing['accession'],'report_period':filing['report_period'],
            'generation':part.identity['generation'],'source_sha256':item['frozen']['raw_hash'],
            'source_reference':reference(part,chunk.chunk_id,key),'chunk_id':chunk.chunk_id,
            'source_url':filing['source_url'],'text':text,'section':chunk.source_location.section,
            'verification':'VERIFIED_SOURCE_EXCERPT'}


def _readable(chunk):
    if chunk.kind!='text':
        return False
    text=chunk.text
    return (len(text)>65 and not re.search(
        r'https?://(?:www\.)?(?:xbrl\.org|fasb\.org)|\b(?:us-gaap|xbrli|ix):\w+|\b(?:zip code|commission file number|registrant.s telephone)\b',
        text,re.I) and len(re.findall(r'\b20\d\d-\d\d-\d\d\b',text))<4)


def narrative(sources, q, key):
    risk=bool(RISK.search(q))
    scored=[]
    for filing,part in sources:
        for item in part.parents:
            c=item['chunk']
            if c.filing_id!=filing['filing_id'] or not _readable(c):
                continue
            section=c.source_location.section or ''
            direct=bool(re.search(r'\brisk factors?\b|^we (?:face|depend|may|are subject to)\b|'
                                  r'\b(?:could adversely|industry risks?|intense competition)\b',section,re.I))
            management=bool(re.search(r'management.s discussion|liquidity|results of operations|executive overview|forward.looking',section,re.I))
            explicit=NO_CHANGE.search(c.text) if risk else None
            score=(12 if explicit else 0)+(6 if direct and risk else 0)+(3 if management else 0)
            if risk and RISK_TOPIC.search(section):
                score+=2
            if (risk and not explicit and not (direct or management and RISK_TOPIC.search(c.text))
                    or not DISCLOSURE.search(c.text)):
                continue
            if score:
                scored.append((score,filing,part,c,explicit,direct))
    scored.sort(key=lambda x:(-x[0],x[3].source_location.structural_path))
    lines,refs,seen=[],[],set()
    explicit_filings={filing['filing_id'] for _,filing,_,_,explicit,_ in scored if explicit}
    for _,filing,part,chunk,explicit,direct in scored:
        if risk and filing['filing_id'] in explicit_filings and not explicit:
            continue
        # Show a complete sentence from the authenticated narrative, rather
        # than synthesizing causal claims from metadata or nearby tables.
        candidates=re.split(r'(?<=[.!?])\s+(?=[A-Z])',chunk.text)
        sentence=next((s.strip() for s in candidates if explicit and NO_CHANGE.search(s)),None)
        if not sentence:
            sentence=next((s.strip() for s in candidates if 70<=len(s)<=560 and DISCLOSURE.search(s) and (not risk or
                           direct or RISK_TOPIC.search(s))),None)
        if not sentence or sentence in seen:
            continue
        seen.add(sentence)
        refs.append(_citation(part,filing,chunk,key,sentence))
        heading=chunk.source_location.section or ('Risk Factors' if explicit else 'Thảo luận của ban quản lý')
        if explicit:
            lines.append(f'- **{filing["ticker"]}** cho biết không có thay đổi trọng yếu đối với các yếu tố rủi ro đã công bố. [{len(refs)}]')
        else:
            lines.append(f'- **{filing["ticker"]} · {heading}**: “{sentence}” [{len(refs)}]')
        if len(refs)==3:
            break
    if not refs:
        return abstain('SEC_NARRATIVE_SECTION_NOT_BOUND',
                       'Chưa gắn được đoạn thuyết minh phù hợp với mục được hỏi trong filing đang chọn.')
    return {'status':'SOURCE_EXCERPTS','answer_status':'SEC_NARRATIVE_EVIDENCE',
            'answer':('Các công bố về rủi ro và bất định trong filing:\n\n' if risk else
                      'Các đoạn thảo luận trong filing:\n\n')+'\n'.join(lines),
            'values':[],'citations':refs}


TOPIC_TERMS={
    'COMPETITION':re.compile(r'\b(?:canh tranh|suc ep doi thu|doi thu canh tranh|competition|competit\w*)\b',re.I),
    'CYBERSECURITY':re.compile(r'\b(?:an ninh mang|tan cong mang|cybersecurity|cyber.?security|cyber.?attacks?|data breaches?)\b',re.I),
}
TOPIC_LABELS={'COMPETITION':'Cạnh tranh','CYBERSECURITY':'An ninh mạng'}


def requested_topics(q):
    return [name for name,pattern in TOPIC_TERMS.items() if pattern.search(q)]


def narrative_obligations(sources, topics, key):
    """One authenticated disclosure per requested topic, with visible gaps."""
    lines,refs,results=[],[],[]
    for topic in topics:
        pattern=TOPIC_TERMS[topic]
        candidates=[]
        for filing,part in sources:
            for item in part.parents:
                chunk=item['chunk']
                if chunk.filing_id!=filing['filing_id'] or not _readable(chunk):
                    continue
                section=chunk.source_location.section or ''
                if not (pattern.search(section) or pattern.search(chunk.text)):
                    continue
                sentences=re.split(r'(?<=[.!?])\s+(?=[A-Z])',chunk.text)
                sentence=next((s.strip() for s in sentences if pattern.search(s) and 45<=len(s)<=700),None)
                if sentence:
                    score=(3 if pattern.search(section) else 0)+(2 if DISCLOSURE.search(sentence) else 0)
                    if re.search(r'\b(?:risk|could adversely|may not|could lead to|vulnerabilit\w*)\b',sentence,re.I):
                        score+=6
                    if re.search(r'\b(?:risk|adversely)\b',section,re.I):
                        score+=3
                    candidates.append((score,filing,part,chunk,sentence))
        candidates.sort(key=lambda x:(-x[0],x[3].source_location.structural_path))
        if not candidates:
            lines.append(f'- **{TOPIC_LABELS[topic]}**: chưa gắn được đoạn công bố phù hợp trong filing đã chọn.')
            results.append({'topic':topic,'status':'SOURCE_UNAVAILABLE'})
            continue
        _,filing,part,chunk,sentence=candidates[0]
        refs.append(_citation(part,filing,chunk,key,sentence))
        if topic=='COMPETITION' and re.search(r'\b(?:competit\w*|compete)\b',sentence,re.I) and re.search(r'\badversely affect\b',sentence,re.I):
            disclosed='Công ty nêu áp lực cạnh tranh có thể ảnh hưởng bất lợi đến hoạt động hoặc kết quả kinh doanh.'
        elif topic=='CYBERSECURITY' and re.search(r'\bcyberattacks?\b',sentence,re.I) and re.search(r'\breduced revenue\b',sentence,re.I):
            disclosed='Công ty nêu tấn công mạng hoặc lỗ hổng bảo mật có thể làm giảm doanh thu, tăng chi phí, phát sinh yêu cầu bồi thường hoặc ảnh hưởng danh tiếng.'
        else:
            disclosed='Báo cáo có công bố về chủ đề này; cần đọc đoạn nguồn để xác định nội dung và mức độ ảnh hưởng cụ thể.'
        lines.append(f'- **{TOPIC_LABELS[topic]} — công bố của {filing["ticker"]}:** {disclosed} [{len(refs)}]')
        results.append({'topic':topic,'status':'SOURCE_EXCERPTS','citation':len(refs)})
    return {'status':'SOURCE_EXCERPTS','answer_status':'SEC_NARRATIVE_EVIDENCE',
            'answer':'Các công bố liên quan trong filing:\n\n'+'\n'.join(lines)+
                     '\n\n**Nhận định của trợ lý:** Chỉ có thể kết luận về các chủ đề có đoạn nguồn nêu trên; các chủ đề thiếu nguồn cần kiểm tra thêm.',
            'values':[],'citations':refs,'topic_results':results,
            'answer_completeness':{'completed':sum(x['status']=='SOURCE_EXCERPTS' for x in results),
                                   'required':len(results)}}


def profile(sources,key):
    rows,refs=[],[]
    for filing,part in sources:
        found=[c for c in observations(part,filing,'revenue') if c.period_end==filing['report_period']]
        groups={}
        for cell in found:
            groups.setdefault((cell.period_start,cell.period_end),[]).append(cell)
        valid=[]
        for cells in groups.values():
            consolidated=[c for c in cells if 'PRODUCT_SALES_DIMENSION_EXCLUDES_MEMBERSHIPS' not in c.warnings]
            group=consolidated or cells
            if len({c.effective_value for c in group})==1:
                valid.append(min(group,key=lambda c:c.table_id))
        valid.sort(key=lambda c:c.period_start or '')
        indexes=[]
        durations=[]
        for cell in valid[:4]:
            days=(date.fromisoformat(cell.period_end)-date.fromisoformat(cell.period_start)).days+1
            durations.append(f'{days//7} tuần' if days%7==0 else f'{cell.period_months} tháng ({days} ngày)')
            cite=_citation(part,filing,part.by_id[cell.parent_id]['chunk'],key,cell.row_label)
            cite['source_reference']=reference(part,cell.parent_id,key,cell.model_dump(mode='json'))
            refs.append(cite)
            indexes.append(f'[{len(refs)}]')
        scale=', '.join(sorted({{1000:'Nghìn USD',1000000:'Triệu USD',1000000000:'Tỷ USD'}[int(c.multiplier)]
                               for c in valid})) if valid else 'Chưa gắn được ô nguồn'
        scope=('Hợp nhất · dòng doanh thu bán hàng' if any('PRODUCT_SALES_DIMENSION_EXCLUDES_MEMBERSHIPS' in c.warnings for c in valid)
               else 'Hợp nhất' if valid else 'Chưa xác định')
        rows.append(f'| {filing["ticker"]} | {filing["form"]} | {filing["report_period"]} | {", ".join(durations) or "Chưa xác định"} | {scale} | {scope} | {filing["accession"]} {" ".join(indexes)} |')
    return {'status':'SOURCE_EXCERPTS','answer_status':'SEC_FILING_PROFILE','values':[],'citations':refs,
            'answer':'| Doanh nghiệp | Form | Ngày kết thúc | Kỳ doanh thu | Đơn vị nguồn | Phạm vi | Accession |\n'
                     '| --- | --- | --- | --- | --- | --- | --- |\n'+'\n'.join(rows)}


def margin(sources, question, ticker, key):
    match=MARGIN.search(folded(question))
    metric='gross_profit' if match['gross'] else 'operating_income'
    raw_question=folded(question)
    years=set(re.findall(r'\b20\d{2}\b',re.sub(r'\b20\d{2}-\d{2}-\d{2}\b',' ',raw_question)))
    available={str(filing['report_period'][:4]) for filing,_ in sources}
    available.update(str(filing['fiscal_year']) for filing,_ in sources if filing.get('fiscal_year'))
    if years and not years <= available:
        return abstain('SEC_FISCAL_PERIOD_ABSENT',
                       'Bộ filing đang chọn không có kỳ '+', '.join(sorted(years-available))+' cho '+ticker+'.')
    # Build an issuer-local request: contextual names may never enter the
    # source-cell binder, and an unspecified 10-Q uses its shortest quarter.
    filing_dates={filing['report_period'] for filing,_ in sources}
    if len(filing_dates)!=1:
        return abstain('SEC_FILING_PERIOD_AMBIGUOUS','Hãy chọn một filing hoặc nêu ngày kết thúc kỳ cho '+ticker+'.')
    report_end=next(iter(filing_dates))
    original=[] if re.search(r'\b(?:ky ngan nhat|shortest period)\b',folded(question)) else re.findall(
        r'\b(12|13|14|24|26|36|39|52|53)\s*(?:tuan|weeks?)\b',folded(question))
    if len(set(original))>1:
        return abstain('SEC_MARGIN_DURATION_AMBIGUOUS','Hãy nêu một độ dài kỳ cho phép tính biên lợi nhuận.')
    duration=(original[0]+' weeks') if original else 'three months'
    request=f'{ticker} {duration} {report_end}'
    scoped=_scoped(sources)
    profit_result=numeric_answer(scoped,request,ticker,key,metric_override=metric,default_quarter=True)
    denominators=[numeric_answer(scoped,request+' '+phrase,ticker,key,metric_override='revenue',default_quarter=True)
                  for phrase in ('net sales','total revenue')]
    same=('cik','filing_id','period_start','period_end','scope','unit')
    profit_cell=profit_result['source_cells'][0] if profit_result and profit_result.get('status')=='SUPPORTED' and len(profit_result.get('source_cells',[]))==1 else None
    compatible=[a for a in denominators if a and a.get('status')=='SUPPORTED'
                and len(a.get('source_cells',[]))==1 and profit_cell
                and all(a['source_cells'][0][k]==profit_cell[k] for k in same)]
    distinct={a['source_cells'][0]['effective_value'] for a in compatible}
    revenue_result=compatible[0] if len(distinct)==1 else None
    results=[profit_result,revenue_result]
    if not profit_cell or not revenue_result:
        unavailable=[m for m,a in zip((metric,'revenue'),results) if not a or a.get('status')!='SUPPORTED']
        reply=abstain('SEC_MARGIN_SOURCE_UNAVAILABLE','Chưa gắn được ô nguồn '+', '.join(unavailable)+' cùng kỳ cho '+ticker+'.')
        reply['operand_results']=[{'metric':m,'status':a.get('status') if a else 'UNSUPPORTED',
                                  'reason':a.get('reason') if a else 'SEC_SOURCE_CELL_UNAVAILABLE'}
                                 for m,a in zip((metric,'revenue'),results)]
        reply['denominator_candidates']=[{'status':a.get('status') if a else 'UNSUPPORTED',
                                         'reason':a.get('reason') if a else None} for a in denominators]
        return reply
    operands=[r['source_cells'][0] for r in results]
    dimensions=('cik','filing_id','period_start','period_end','scope','unit')
    if any(operands[0][k]!=operands[1][k] for k in dimensions):
        return abstain('SEC_MARGIN_DIMENSION_CONFLICT','Ô doanh thu và lợi nhuận thuộc phạm vi hoặc kỳ khác nhau.')
    profit,revenue=[Decimal(c['effective_value']) for c in operands]
    if revenue<=0:
        return abstain('SEC_ZERO_BASE','Không có doanh thu dương để tính biên lợi nhuận cho kỳ này.')
    with localcontext() as ctx:
        ctx.prec=50
        result=(profit/revenue*100).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
        from app.product.sec_answer_contract import verify_comparison
        proof=verify_comparison(operands,[('MARGIN_PERCENT',result)])
    refs=[r['citations'][0] for r in results]
    label='Biên lợi nhuận gộp' if match['gross'] else 'Biên lợi nhuận hoạt động'
    start,end=operands[0]['period_start'],operands[0]['period_end']
    days=(date.fromisoformat(end)-date.fromisoformat(start)).days+1
    duration_label=f'{days//7} tuần' if days%7==0 else f'{operands[0]["period_months"]} tháng ({days} ngày)'
    return {'status':'SUPPORTED','answer_status':'VERIFIED_ANSWER','values':[str(result)],'unit':'%',
            'answer':f'{label} của {ticker} cho kỳ {start}–{end} ({duration_label}): **{result}%**. '
                     f'{operands[0]["row_label"]}: {profit:,} USD [1] ÷ '
                     f'{operands[1]["row_label"]}: {revenue:,} USD [2] × 100.',
            'citations':refs,'source_cells':operands,'independent_verification':proof}


def _combine(tasks,missing):
    blocks,refs=[],[]
    for label,reply in tasks:
        start=len(refs)
        refs.extend(reply.get('citations',[]))
        answer=re.sub(r'\[(\d+)\]',lambda m:f'[{start+int(m[1])}]',reply['answer'])
        blocks.append(f'### {label}\n{answer}')
    if missing:
        blocks.append('Bộ nguồn đang chọn thiếu filing của '+', '.join(missing)+'.')
    statuses=[a.get('status') for _,a in tasks]
    return {'status':'SUPPORTED' if statuses and all(x=='SUPPORTED' for x in statuses) and not missing else 'SOURCE_EXCERPTS',
            'answer_status':'SEC_TASK_RESULTS','answer':'\n\n'.join(blocks),'values':[],
            'citations':refs,'task_results':[{'label':label,'status':a['status'],'values':a.get('values',[]),
                         'reason':a.get('reason'),'source_cells':a.get('source_cells',[])} for label,a in tasks],
            'answer_completeness':{'completed':sum(x=='SUPPORTED' for x in statuses),
                                   'required':len(tasks)+len(missing)}}


def answer(index,question,ticker,key):
    started=perf_counter()
    q=folded(question)
    groups=defaultdict(list)
    for part in partitions(index):
        for filing in part.catalog_rows:
            groups[filing['ticker']].append((filing,part))
    metrics=requested_metrics(q)
    is_profile=bool(PROFILE.search(q) and re.search(r'\b(?:bang|so sanh|filing|metadata)\b',q))
    margin_match=MARGIN.search(q)
    topics=requested_topics(q) if RISK.search(q) or MANAGEMENT.search(q) else []
    qualitative=bool(RISK.search(q) or MANAGEMENT.search(q)) and not metrics and not margin_match
    plan=plan_sec_question(question,groups,ticker,metrics,margin_match.group(0) if margin_match else None,
                           topics if qualitative else ())
    selected,missing,conflict=plan.eligible_entities,plan.unselected_entities,plan.error
    mismatched=[task for task in plan.tasks if not any(
        (not task.filing_form or row['form']==task.filing_form)
        and (not task.accession or row['accession']==task.accession)
        and (not task.period or row['report_period']==task.period)
        for row,_ in groups[task.issuer])]
    if mismatched:
        reply=abstain('SEC_REQUESTED_FILING_NOT_SELECTED',
                      'Filing, accession hoặc ngày kết thúc kỳ được hỏi không thuộc nguồn SEC đang chọn.')
    elif conflict or not selected:
        label=', '.join(missing) if missing else ', '.join(plan.named_entities) or 'doanh nghiệp được hỏi'
        reply=abstain(conflict or 'SEC_ISSUER_NOT_SELECTED','Bộ nguồn đang chọn thiếu filing của '+label+
                      '. Hãy chọn hoặc nhập đúng filing rồi hỏi lại.' if conflict=='SEC_ISSUER_NOT_SELECTED' else
                      'Hãy nêu rõ doanh nghiệp cần phân tích trong bộ nguồn đang chọn.')
    elif is_profile:
        reply=profile([source for issuer in selected for source in groups[issuer]],key)
    elif qualitative:
        sources=[source for issuer in selected for source in groups[issuer]]
        reply=narrative_obligations(sources,topics,key) if topics else narrative(sources,q,key)
    elif margin_match:
        tasks=[(issuer+' · biên lợi nhuận hoạt động',margin(groups[issuer],question,issuer,key)) for issuer in selected]
        reply=tasks[0][1] if len(tasks)==1 and not missing else _combine(tasks,missing)
        if len(tasks)>1:
            reply['answer']+='\n\nCác kỳ ngắn nhất được báo cáo có thể là 12 tuần, 13 tuần hoặc ba tháng; '
            reply['answer']+='không coi chúng là các khoảng thời gian hoàn toàn đồng nhất.'
    elif metrics:
        tasks=[]
        for issuer in selected:
            scope=_scoped(groups[issuer])
            for metric in metrics:
                if len(tasks)>=12:
                    tasks.append((issuer+' · '+metric,abstain('SEC_TASK_BUDGET_REACHED',
                                  'Chưa chạy tác vụ này vì giới hạn 12 tác vụ mỗi câu hỏi.')))
                    continue
                response=numeric_answer(scope,question,issuer,key,metric_override=metric,default_quarter=True,
                                        single_observation=len(selected)>1)
                if response is None:
                    response=abstain('SEC_NUMERIC_TASK_UNSUPPORTED','Chưa gắn được chỉ tiêu hoặc phép tính này với ô nguồn có thể xác minh.')
                tasks.append((issuer+' · '+metric.replace('_',' '),response))
        reply=tasks[0][1] if len(tasks)==1 and not missing else _combine(tasks,missing)
    else:
        if re.search(r'\b(?:bao nhieu|tinh|ty le|phan tram|doanh thu|loi nhuan|net sales|revenue|income|margin|percent)\b',q):
            reply=abstain('SEC_NUMERIC_INTENT_NOT_PLANNED','Chưa xác định đủ chỉ tiêu hoặc phép tính tài chính từ câu hỏi. Hãy nêu chỉ tiêu và kỳ cần xem.')
        else:
            return None
    if reply.get('reason')=='SEC_FISCAL_PERIOD_ABSENT' and len(selected)==1 and not margin_match:
        evidence=profile(groups[selected[0]],key)
        reply['answer']+='\n\n'+evidence['answer']
        reply['citations']=evidence['citations']
    if missing and (is_profile or qualitative):
        reply['answer']+='\n\nBộ nguồn đang chọn thiếu filing của '+', '.join(missing)+'.'
    eligible=[f['filing_id'] for t in selected for f,_ in groups[t]]
    reply['sec_source_selection']={'eligible_filing_ids':eligible,'excluded_filing_ids':
        [f['filing_id'] for t in groups if t not in selected for f,_ in groups[t]],'unselected_issuers':missing}
    reply['sec_question_plan']=plan.public()
    if 'answer_completeness' not in reply:
        complete=bool(reply.get('status')=='SUPPORTED' and reply.get('citations'))
        reply['answer_completeness']={'completed':int(complete),'required':max(1,len(plan.tasks)+len(missing))}
    if reply.get('status')=='NEEDS_CLARIFICATION' and reply.get('reason') in {
            'SEC_COMPANY_SCOPE_AMBIGUOUS','SEC_PERIOD_DURATION_REQUIRED','SEC_COMPARISON_PERIODS_REQUIRED'}:
        slot='issuer' if reply['reason']=='SEC_COMPANY_SCOPE_AMBIGUOUS' else 'duration' if reply['reason']=='SEC_PERIOD_DURATION_REQUIRED' else 'period'
        reply['pending_clarification']={'original_task':question,'missing_slot':slot,
            'acceptable_type':'selected issuer or comparison set' if slot=='issuer' else 'reporting period or duration',
            'chosen_issuers':selected,'selected_filing_ids':plan.selected_filing_ids,
            'metric_constraints':metrics,'time_constraints':re.findall(r'\b20\d{2}(?:-\d{2}-\d{2})?\b',q)}
    reply.setdefault('timings_ms',{})['orchestration_total']=(perf_counter()-started)*1000
    return reply

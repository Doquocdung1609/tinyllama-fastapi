"""Resolve SEC tasks against the selected, authenticated filing set."""
from collections import defaultdict
from datetime import date
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
MARGIN = re.compile(r'\b(?P<net>net (?:profit )?margin|bien loi nhuan rong|ty suat loi nhuan rong)\b|'
                    r'\b(?P<gross>gross (?:profit )?margin|bien loi nhuan gop|ty suat loi nhuan gop)\b|'
                    r'\b(?:operating margin|bien loi nhuan hoat dong|bien hoat dong|ty suat loi nhuan hoat dong|'
                    r'phan tram loi nhuan (?:tu )?hoat dong tren (?:tong )?doanh thu|'
                    r'loi nhuan (?:tu )?hoat dong.{0,80}chiem.{0,45}phan tram.{0,25}doanh thu|'
                    r'what percent(?:age)? of revenue is operating (?:income|profit)|'
                    r'operating (?:income|profit) as a percent(?:age)? of revenue)\b')
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
    'LEGAL':re.compile(r'\b(?:phap ly|legal (?:risks?|proceedings?|matters?|exposure|liability)|litigation|lawsuits?|regulatory (?:risks?|scrutiny|actions?))\b',re.I),
    'REGULATION':re.compile(r'\b(?:quy dinh|giam sat phap ly|regulations?|regulatory (?:risks?|scrutiny|actions?)|compliance)\b',re.I),
    'LITIGATION':re.compile(r'\b(?:kien tung|tranh chap|to tung|litigation|lawsuits?|legal proceedings?)\b',re.I),
    'DATA_SECURITY':re.compile(r'\b(?:bao mat du lieu|quyen rieng tu|data (?:security|breaches?|privacy)|privacy breaches?)\b',re.I),
    'SECURITY':re.compile(r'\b(?:bao mat|security breaches?|security vulnerabilit\w*|unauthori[sz]ed access)\b',re.I),
    'COMPETITION':re.compile(r'\b(?:canh tranh|suc ep doi thu|doi thu canh tranh|competition|competit\w*)\b',re.I),
    'CYBERSECURITY':re.compile(r'\b(?:an ninh mang|tan cong mang|cybersecurity|cyber.?security|cyber.?attacks?|data breaches?)\b',re.I),
    'CURRENCY':re.compile(r'\b(?:ty gia|ngoai hoi|foreign exchange|currency fluctuations?)\b',re.I),
    'SUPPLY_CHAIN':re.compile(r'\b(?:chuoi cung ung|supply chain|supplier disruptions?)\b',re.I),
    'LIQUIDITY':re.compile(r'\b(?:thanh khoan|liquidity|cash constraints?)\b',re.I),
}
TOPIC_LABELS={'LEGAL':'Pháp lý','REGULATION':'Quy định','LITIGATION':'Kiện tụng','DATA_SECURITY':'Bảo mật dữ liệu',
              'SECURITY':'Bảo mật','COMPETITION':'Cạnh tranh','CYBERSECURITY':'An ninh mạng',
              'CURRENCY':'Tỷ giá','SUPPLY_CHAIN':'Chuỗi cung ứng','LIQUIDITY':'Thanh khoản'}


def requested_topics(q):
    # Specific concepts consume only their own text. A separately requested
    # broader topic stays visible, and an unfamiliar enumerated item survives.
    topics=[]
    remainder=q
    for topic in ('DATA_SECURITY','COMPETITION','CYBERSECURITY','SECURITY','LITIGATION','REGULATION',
                  'LEGAL','CURRENCY','SUPPLY_CHAIN','LIQUIDITY'):
        p=TOPIC_TERMS[topic]
        ask=p
        if topic=='LEGAL':
            ask=re.compile(r'\b(?:phap ly|legal(?: risks?)?)\b')
        elif topic=='SECURITY':
            ask=re.compile(r'\b(?:bao mat|security)\b')
        elif topic=='CYBERSECURITY':
            ask=re.compile(r'\b(?:an ninh mang|tan cong mang|cybersecurity|cyber.?security|cyber.?attacks?)\b')
        if ask.search(remainder):
            topics.append(topic)
            remainder=ask.sub(' ',remainder)
    explicit=re.search(r'\b(?:phan tich rieng|tach rieng|separately analy[sz]e)\s+(?:cac\s+)?(?:rui ro|risks?)\s+([^.!?;]+)',q)
    if explicit and re.search(r',|\b(?:va|and)\b',explicit[1]):
        for name in re.split(r'\s*,\s*|\s+(?:va|and)\s+',explicit[1]):
            name=name.strip()
            if not 1<=len(name.split())<=6 or any(p.search(name) for p in TOPIC_TERMS.values()):
                continue
            if not re.fullmatch(r'[a-z][a-z -]{2,60}',name) or 'chu de' in name or 'chung cu' in name:
                continue
            topics.append('LOCAL:'+name)
    return topics


def narrative_obligations(sources, topics, key):
    """One authenticated disclosure per requested topic, with visible gaps."""
    lines,refs,results=[],[],[]
    for topic in topics:
        label=TOPIC_LABELS.get(topic,topic.removeprefix('LOCAL:').capitalize())
        pattern=TOPIC_TERMS.get(topic) or re.compile(r'(?<!\w)'+re.escape(topic.removeprefix('LOCAL:'))+r'(?!\w)',re.I)
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
                    if topic=='LEGAL':
                        if re.search(r'\b(?:litigation|legal proceedings?|lawsuits?|claims?|contingencies)\b',section+' '+sentence,re.I):
                            score+=7
                        if TOPIC_TERMS['SECURITY'].search(section) or TOPIC_TERMS['CYBERSECURITY'].search(sentence):
                            score-=5
                    if topic in {'SECURITY','DATA_SECURITY'} and re.search(r'\b(?:unauthori[sz]ed access|breaches?|compromis\w*)\b',sentence,re.I):
                        score+=3
                    if re.search(r'\b(?:risk|adversely)\b',section,re.I):
                        score+=3
                    candidates.append((score,filing,part,chunk,sentence))
        candidates.sort(key=lambda x:(-x[0],x[3].source_location.structural_path))
        if not candidates:
            lines.append(f'- **{label}**: chưa gắn được đoạn công bố phù hợp trong filing đã chọn.')
            results.append({'topic':topic,'status':'SOURCE_UNAVAILABLE'})
            continue
        _,filing,part,chunk,sentence=candidates[0]
        refs.append(_citation(part,filing,chunk,key,sentence))
        if topic=='COMPETITION' and re.search(r'\b(?:competit\w*|compete)\b',sentence,re.I) and re.search(r'\badversely affect\b',sentence,re.I):
            disclosed='Công ty nêu áp lực cạnh tranh có thể ảnh hưởng bất lợi đến hoạt động hoặc kết quả kinh doanh.'
        elif topic in {'CYBERSECURITY','SECURITY','DATA_SECURITY'} and re.search(r'\bcyberattacks?\b',sentence,re.I) and re.search(r'\breduced revenue\b',sentence,re.I):
            disclosed='Công ty nêu tấn công mạng hoặc lỗ hổng bảo mật có thể làm giảm doanh thu, tăng chi phí, phát sinh yêu cầu bồi thường hoặc ảnh hưởng danh tiếng.'
        elif topic in {'LEGAL','LITIGATION'} and re.search(r'\b(?:litigation|proceedings?|claims?|lawsuits?)\b',sentence,re.I):
            disclosed=('Công ty cho biết kết quả các thủ tục pháp lý và khiếu kiện còn bất định.'
                       if 'uncertainty' in sentence.casefold() else
                       'Công ty cho biết các khiếu kiện có thể dẫn đến kết quả bất lợi.'
                       if 'adverse outcomes' in sentence.casefold() else
                       'Báo cáo đề cập các vụ việc hoặc thủ tục pháp lý.')
        elif topic=='LEGAL' and re.search(r'\b(?:regulat\w*|laws?|compliance)\b',sentence,re.I):
            disclosed='Báo cáo đề cập nghĩa vụ tuân thủ hoặc rủi ro từ quy định.'
        elif topic in {'SECURITY','DATA_SECURITY'}:
            disclosed='Đoạn công bố liên quan đến bảo mật. Phạm vi sự cố và ảnh hưởng cụ thể nằm trong trích đoạn.'
        else:
            disclosed='Đoạn công bố dưới đây nêu căn cứ trực tiếp cho chủ đề.'
        if topic not in {'COMPETITION','CYBERSECURITY','SECURITY','DATA_SECURITY'} or disclosed.startswith('Đoạn'):
            disclosed+=f' Trích đoạn: “{sentence}”'
        lines.append(f'- **{label} — công bố của {filing["ticker"]}:** {disclosed} [{len(refs)}]')
        item=part.by_id[chunk.chunk_id]
        warnings=['FILING_PARTIAL_EXTRACTION'] if filing.get('extraction_status')=='PARTIAL_EXTRACTION' or (
            item['chunk'].metadata.get('document_status')=='PARTIAL_EXTRACTION') else []
        if warnings:
            lines.append('  *Nguồn có cảnh báo trích xuất một phần. Mục này chỉ phản ánh đoạn đã đối chiếu.*')
        results.append({'topic':topic,'status':'SOURCE_EXCERPTS','citation':len(refs),'warnings':warnings})
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
    from app.product.sec_ratio import margin as execute_margin
    match=MARGIN.search(folded(question))
    return execute_margin(sources,question,ticker,key,
                          'gross_profit' if match['gross'] else 'income' if match['net'] else 'operating_income')


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
    if mismatched and not margin_match:
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
        sources=[]
        for issuer in selected:
            local=groups[issuer]
            hint=next((t for t in plan.tasks if t.issuer==issuer),None)
            if hint:
                local=[(row,part) for row,part in local if (not hint.filing_form or row['form']==hint.filing_form)
                       and (not hint.period or row['report_period']==hint.period)
                       and (not hint.accession or row['accession']==hint.accession)]
            if local:
                latest=max(row['report_period'] for row,_ in local)
                sources.extend((row,part) for row,part in local if row['report_period']==latest)
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
    if missing and qualitative and 'answer_completeness' in reply:
        reply['answer_completeness']['required']+=len(topics)*len(missing)
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
            'SEC_COMPANY_SCOPE_AMBIGUOUS','SEC_PERIOD_DURATION_REQUIRED','SEC_COMPARISON_PERIODS_REQUIRED',
            'SEC_MARGIN_COMPARISON_PERIOD_REQUIRED','SEC_FILING_PERIOD_AMBIGUOUS','SEC_MARGIN_DURATION_AMBIGUOUS'}:
        slot='issuer' if reply['reason']=='SEC_COMPANY_SCOPE_AMBIGUOUS' else 'duration' if reply['reason']=='SEC_PERIOD_DURATION_REQUIRED' else 'period'
        reply['pending_clarification']={'original_task':question,'missing_slot':slot,
            'acceptable_type':'selected issuer or comparison set' if slot=='issuer' else 'reporting period or duration',
            'chosen_issuers':selected,'selected_filing_ids':plan.selected_filing_ids,
            'metric_constraints':metrics,'time_constraints':re.findall(r'\b20\d{2}(?:-\d{2}-\d{2})?\b',q)}
    reply.setdefault('timings_ms',{})['orchestration_total']=(perf_counter()-started)*1000
    return reply

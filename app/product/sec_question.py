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
from app.product.sec_viewer import reference

RISK = re.compile(r'\b(?:rui ro|bat dinh|risks?|risk factors?|uncertaint\w*)\b')
MANAGEMENT = re.compile(r'\b(?:thao luan cua ban quan ly|management.s discussion|md&a|liquidity|thanh khoan)\b')
MARGIN = re.compile(r'\b(?P<gross>gross (?:profit )?margin|bien loi nhuan gop)\b|'
                    r'\b(?:operating margin|bien loi nhuan hoat dong)\b')
PROFILE = re.compile(r'\b(?:do dai ky|don vi tien te|pham vi bao cao|reporting duration|reporting scope|filing profile)\b')
NO_CHANGE = re.compile(r'\bno (?:material|significant) changes?\b.{0,250}\brisk factors?\b|\brisk factors?\b.{0,240}\b(?:no material changes?|have not materially changed)\b', re.I)
RISK_TOPIC = re.compile(r'\b(?:tariffs?|inflation|competition|foreign exchange|currency|cybersecurity|supply chain|'
                        r'interest rates?|economic conditions?|regulation|geopolitical|security risks?)\b',re.I)
DISCLOSURE = re.compile(r'\b(?:competit\w*|uncertain\w*|could|may|risk|adversely|impact|volatil\w*|challeng\w*|fluctuat\w*)\b',re.I)


def _matches(q, name):
    return bool(name and re.search(r'(?<!\w)'+re.escape(folded(name))+r'(?!\w)',q))


def resolve_sources(index, question, ticker=None):
    q = folded(question)
    groups = defaultdict(list)
    for part in partitions(index):
        for filing in part.catalog_rows:
            groups[filing['ticker']].append((filing,part))
    named = {symbol for symbol,names in ISSUERS.items() if any(_matches(q,n) for n in names)}
    for symbol, sources in groups.items():
        issuer = sources[0][0]['issuer']
        company = re.sub(r'\s+(?:(?:inc|corp|co|company|corporation|ltd|plc|limited)\.?\s*)+$','',issuer.replace(',',''),flags=re.I).strip()
        if _matches(q,symbol) or _matches(q,issuer) or (len(company)>=4 and _matches(q,company)):
            named.add(symbol)
    named.update(x.upper() for x in re.findall(r'\b(?:ticker|ma chung khoan)\s+([a-z]{1,5})\b',q))
    if ticker and named and ticker.upper() not in named:
        return groups, [], sorted(named), 'SEC_COMPANY_SCOPE_CONFLICT'
    missing=sorted(named-groups.keys())
    chosen=sorted(named & groups.keys()) if named else ([ticker.upper()] if ticker and ticker.upper() in groups else list(groups))
    return groups,chosen,missing,None


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
    # All other qualifiers remain in the request passed to the source gate.
    request=re.sub(r'gross (?:profit )?margin|operating margin|biên lợi nhuận (?:gộp|hoạt động)|bien loi nhuan (?:gop|hoat dong)',
                   ' ',question,count=1,flags=re.I).replace('%',' ')
    scoped=_scoped(sources)
    results=[numeric_answer(scoped,request,ticker,key,metric_override=m,default_quarter=True)
             for m in (metric,'revenue')]
    if not all(a and a.get('status')=='SUPPORTED' and len(a.get('source_cells',[]))==1 for a in results):
        return _combine([(m,a) for m,a in zip((metric,'revenue'),results) if a],[]) if any(results) else abstain(
            'SEC_MARGIN_SOURCE_UNAVAILABLE','Chưa gắn được lợi nhuận và doanh thu của cùng kỳ.')
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
    return {'status':'SUPPORTED','answer_status':'VERIFIED_ANSWER','values':[str(result)],'unit':'%',
            'answer':f'{label} của {ticker} cho kỳ {operands[0]["period_end"]}: **{result}%**. '
                     f'Lợi nhuận {profit:,} USD [1] ÷ doanh thu {revenue:,} USD [2] × 100.',
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
    return {'status':'SOURCE_EXCERPTS','answer_status':'SEC_TASK_RESULTS','answer':'\n\n'.join(blocks),'values':[],
            'citations':refs,'task_results':[{'label':label,'status':a['status'],'values':a.get('values',[]),
                         'reason':a.get('reason'),'source_cells':a.get('source_cells',[])} for label,a in tasks]}


def answer(index,question,ticker,key):
    started=perf_counter()
    q=folded(question)
    groups,selected,missing,conflict=resolve_sources(index,question,ticker)
    metrics=requested_metrics(q)
    is_profile=bool(PROFILE.search(q) and re.search(r'\b(?:bang|so sanh|filing|metadata)\b',q))
    qualitative=bool(RISK.search(q) or MANAGEMENT.search(q)) and not metrics
    if conflict or not selected:
        reply=abstain(conflict or 'SEC_ISSUER_NOT_SELECTED','Bộ nguồn đang chọn thiếu filing của '+(', '.join(missing) or 'doanh nghiệp được hỏi')+'.')
    elif len(selected)>1 and not is_profile and not re.search(r'\b(?:so sanh|ca ba|ca hai|compare|each|tung)\b',q):
        reply=abstain('SEC_COMPANY_SCOPE_AMBIGUOUS','Bạn muốn hỏi '+', '.join(selected)+'? Hãy nêu doanh nghiệp hoặc yêu cầu đối chiếu từng filing.')
    elif is_profile:
        reply=profile([source for issuer in selected for source in groups[issuer]],key)
    elif qualitative:
        reply=narrative([source for issuer in selected for source in groups[issuer]],q,key)
    elif MARGIN.search(q) and len(selected)==1:
        reply=margin(groups[selected[0]],question,selected[0],key)
    elif metrics:
        tasks=[]
        if len(selected)>1 and len(metrics)>1:
            # A shared cross-company query can safely compare a single metric.
            # Separate clauses are needed to assign disjoint metric obligations.
            return abstain('SEC_ENTITY_METRIC_BINDING_AMBIGUOUS','Hãy ghi chỉ tiêu và kỳ cạnh tên từng doanh nghiệp để tôi gắn đúng ô nguồn.')
        for issuer in selected:
            scope=_scoped(groups[issuer])
            for metric in metrics[:4]:
                response=numeric_answer(scope,question,issuer,key,metric_override=metric,default_quarter=True,
                                        single_observation=len(selected)>1)
                if response is None:
                    response=abstain('SEC_NUMERIC_TASK_UNSUPPORTED','Chưa gắn được chỉ tiêu hoặc phép tính này với ô nguồn có thể xác minh.')
                tasks.append((issuer+' · '+metric.replace('_',' '),response))
        reply=tasks[0][1] if len(tasks)==1 and not missing else _combine(tasks,missing)
    else:
        return None
    if reply.get('reason')=='SEC_FISCAL_PERIOD_ABSENT' and len(selected)==1:
        evidence=profile(groups[selected[0]],key)
        reply['answer']+='\n\n'+evidence['answer']
        reply['citations']=evidence['citations']
    if missing and (is_profile or qualitative):
        reply['answer']+='\n\nBộ nguồn đang chọn thiếu filing của '+', '.join(missing)+'.'
    eligible=[f['filing_id'] for t in selected for f,_ in groups[t]]
    reply['sec_source_selection']={'eligible_filing_ids':eligible,'excluded_filing_ids':
        [f['filing_id'] for t in groups if t not in selected for f,_ in groups[t]],'unselected_issuers':missing}
    reply.setdefault('timings_ms',{})['orchestration_total']=(perf_counter()-started)*1000
    return reply

"""FAITH-R product adapter: immutable PDF rows + source-first financial ranking.

No corpus changes, inferred OCR corrections or certification from arithmetic alone.
SEC retains its separate HTML adapter and source-cell verifier.
"""
from contextlib import closing
from hashlib import sha256
import json
import re
from time import perf_counter
from app.product.pdf_extract import folded
from app.product.financial_understanding import understand, issuers

VERSION = 'FAITH_R_PRODUCT_V1'

def sec_search(index, question, mode, top_k, ticker='', period=''):
    """A5 feature ordering over a compatible product SEC pool, not the A5 index.

    Fiscal dates come from the pinned source manifest; numerical certification
    remains the existing HTML/iXBRL verifier. We never transplant research data.
    """
    from app.product.sec_a5 import plan_query, feature_audit, _ordering
    from app.product.sec_multi_qa import METRICS, metric_for
    from app.product.sec_question import RISK, _readable
    started=perf_counter();plan=plan_query(question)
    if ticker and plan.issuer and ticker.upper()!=plan.issuer:raise ValueError('SEC_COMPANY_SCOPE_CONFLICT')
    selected=ticker or plan.issuer or ''
    metric=metric_for(folded(question))
    labels=METRICS[metric][1] if metric else set()
    expansion=' '.join(sorted(labels)) if labels else plan.search_query
    risk=bool(RISK.search(folded(question)) and not metric)
    base=index.search(question,mode,20,selected,period)
    expanded=(index.search('risk factors uncertainty material changes' if risk else expansion,'bm25',20,selected,period)
              if labels or risk or plan.metric else {'results':[]})
    pool={h['chunk_id']:h for h in base['results']}
    for h in expanded['results']:pool.setdefault(h['chunk_id'],h)
    dates={f['accession']:f['report_period'] for f in index.catalog()['filings']}
    audited=[]
    registered=index.by_id
    for rank,h in enumerate(pool.values(),1):
        chunk=registered[h['chunk_id']]['chunk']
        row_label=chunk.metadata.get('row_label','').strip()
        if chunk.kind=='table' and (not row_label or not any(c.get('numeric_facts') for c in chunk.metadata.get('cells',[]))
                                    or metric and row_label.casefold() not in labels):
            continue
        if chunk.kind!='table' and not _readable(chunk):
            continue
        if risk and (chunk.kind!='text' or not re.search(r'risk|uncertaint',chunk.text,re.I)):
            continue
        h={**h,'row_label':row_label or None}
        if chunk.kind=='table' and row_label:
            # The signed source opens the full table. Show readable row text,
            # without embedded namespaces and context records.
            h['text']=' · '.join(c.get('text','') for c in chunk.metadata.get('cells',[]) if c.get('text')) or row_label
        features=feature_audit({**h,'document_type':h.get('form'),'fiscal_period':h.get('report_period'),
            'accession_number':h.get('accession'),'section':json.dumps(h.get('source_location',{}))},plan,dates)
        features['exact_source_row']=bool(labels and row_label.casefold() in labels)
        audited.append((h,features,rank))
    audited.sort(key=lambda v:(-int(v[1]['exact_source_row']),_ordering(v[1],v[2])))
    hits=[{**h,'rank':rank,'rank_reasons':features,'algorithm_executed':'A5_FEATURE_RERANK_PRODUCT_SEC_V1',
        'engine_version':VERSION,'numeric_status':'CANDIDATE_ONLY','citation_id':h['chunk_id'],'text_quote':h['text']}
        for rank,(h,features,_) in enumerate(audited[:top_k],1)]
    return {**base,'results':hits,'latency_ms':round((perf_counter()-started)*1000,2),'intent':understand(question).public(),
        'evidence_status':'RELATED_UNVERIFIED_EVIDENCE' if hits else 'NO_SUFFICIENT_EVIDENCE',
        'algorithm_executed':'A5_FEATURE_RERANK_PRODUCT_SEC_V1','candidate_count':len(pool),'engine_version':VERSION}

def _scope(text):
    q = folded(text)
    if re.search(r'hop nhat|consolidated', q): return 'CONSOLIDATED'
    if re.search(r'\brieng\b|cong ty me|parent company|separate', q): return 'SEPARATE'
    return None

def _tokens(text):
    stop = set('tim dong trong tai lieu dang chon cho biet cac doan nguon lien quan va trang pdf bang bao cao tai chinh nam cua the in of for this selected document find show please'.split())
    return {t for t in re.findall(r'\w+', folded(text)) if len(t)>2 and t not in stop}

def pdf_search(w, question, mode, top_k, document_ids):
    started = perf_counter(); slots = understand(question)
    docs=w._eligible(document_ids)
    requested_issuers=issuers(question)
    if requested_issuers:
        from app.product.financial_understanding import document_profile
        docs=[d for d in docs if set(document_profile(w,d)['identities'])&set(requested_issuers)]
    if not docs:
        return {'results':[],'latency_ms':0,'mode':mode,'generation':sha256(b'NO_MATCHING_SOURCE').hexdigest(),'intent':slots.public(),'candidate_count':0,'search_profile':'faith_r_product_v1','engine_version':VERSION,'evidence_status':'NO_SUFFICIENT_EVIDENCE','filter_reason':'ISSUER_SOURCE_FILTER','dedup_count':0}
    document_ids=[d['id'] for d in docs]
    # Original BM25/dense/RRF contributes candidates; page-row sidecar fills the
    # bounded row coverage gap. RRF itself remains k=60 in workspace.search.
    fallback = None
    try: base = w.search(question, mode, 20, document_ids)
    except (ValueError, OSError, __import__('requests').RequestException) as exc:
        if mode == 'bm25' or (isinstance(exc, ValueError) and str(exc) != 'EMBEDDING_MODEL_DIGEST_MISMATCH'): raise
        base = w.search(question, 'bm25', 20, document_ids); fallback = 'DENSE_UNAVAILABLE_BM25_PLUS_ROW_SIDECAR'
    from app.product.ocr_financial_workspace import AdaptiveFinancialOcrWorkspace, FinancialOcrWorkspace
    explicit_pages = re.findall(r'\b(?:trang|page)\s+(\d{1,3})\b', folded(question))
    financial_ocr = isinstance(w, FinancialOcrWorkspace)
    adaptive = isinstance(w, AdaptiveFinancialOcrWorkspace)
    target_page = int(explicit_pages[0]) if financial_ocr and len(explicit_pages) == 1 else None
    from app.product.ocr_reviewed_answer import requested_note_column, requested_periods
    target_periods = requested_periods(question, slots.metric) if adaptive else []
    note_end,note_basis=requested_note_column(question) if target_page and not slots.metric else (None,None)
    pool = []; terms = _tokens(question);page_context={};observed_scopes=set()
    if slots.intent=='SUMMARIZE':
        vietnamese=False
        if docs:
            cover=folded(w.page_evidence(docs[0]['id'],1).get('text',''))
            vietnamese=bool(re.search(r'bao cao|tai san|ngan hang|cong ty',cover))
        seeds=[('Hoạt động','hoạt động kinh doanh' if vietnamese else 'business operations products services'),
            ('Tài chính','kết quả kinh doanh doanh thu lợi nhuận' if vietnamese else 'financial condition net sales net income'),
            ('Rủi ro','rủi ro' if vietnamese else 'risk factors')]
        summary_hits=[]
        for label,query in seeds:
            extra=w.search(query,'bm25',2,document_ids)
            summary_hits.extend({**h,'summary_section':label} for h in extra.get('results',[]))
        base={**base,'results':summary_hits+base.get('results',[])}
    for d in docs:
        w.source_file(d['id'])  # immutable source check, including cached rows
        with closing(w._connect()) as db:
            chunks = [dict(r) for r in db.execute('SELECT * FROM chunks WHERE document_id=? ORDER BY page,id', (d['id'],))]
        parent_by_page = {}
        for c in chunks: parent_by_page.setdefault(c['page'], []).append(c)
        scope = None; unit = None; period = None; context_page = None
        identity = issuers(d['filename'] + ' ' + d.get('issuer',''))
        for page in range(1, d['pages']+1):
            e = w.page_evidence(d['id'], page); text = e.get('text',''); f = folded(text)
            # Carry headings only through a genuine continued table, not across
            # unrelated narrative pages. Mixed-scope documents stay mixed.
            local_scope = _scope(text[:1600])
            if local_scope: scope = local_scope; context_page = page
            elif not re.search(r'so trinh bay lai|chi tieu|\(1\).*\(2\)', f): scope = None; unit = None; period = None
            if 'trieu dong' in f: unit = 'TRIEU_VND'
            elif re.search(r'\bin millions\b', f): unit = 'MILLION_USD' if re.search(r'\$|dollars', text, re.I) else None
            years = re.findall(r'(?:nam|ngay|year ended|september|december)[^\n]{0,50}?\b(20\d{2})\b', f)
            if years: period = years[0] if len(set(years))==1 else None
            if not identity: identity = issuers(text[:1200])
            page_context[(d['id'],page)]={'statement_scope':scope or 'UNKNOWN','report_period':period or '', 'unit':unit}
            if scope:observed_scopes.add(scope)
            if target_page is not None and page != target_page: continue
            if slots.scope and scope and slots.scope != scope: continue
            parents = parent_by_page.get(page, [])
            if not parents: continue
            for row in e.get('tables', []):
                label = row.get('row_label',''); cells = row.get('cells',[])
                quote = label + ' | ' + ' | '.join(c['text'] for c in cells)
                overlap = len(terms & _tokens(label))
                label_key = folded(label)
                exact = any(a in label_key for a in slots.metric_phrases)
                if financial_ocr and e.get('method') == 'OCR':
                    if slots.metric == 'net_revenue':
                        exact = 'doanh thu thuan' in label_key
                        if 'doanh thu chua thuc hien' in label_key: continue
                    if slots.metric == 'net_income' and 'chua phan phoi' in label_key:
                        continue
                if adaptive and row.get('metric'):
                    exact = row['metric'] == slots.metric
                    if slots.metric and not exact:
                        continue
                if slots.metric and not exact and overlap < 2: continue
                if not slots.metric and slots.intent != 'RESTATEMENT_LIST' and overlap < 1: continue
                adjustment = bool(re.search(r'so lieu da cong bo|so trinh bay lai', f)) and len(cells)==3
                if slots.intent == 'RESTATEMENT_LIST' and not adjustment: continue
                # Ignore unchanged rows in an adjustment list; no numbers certified.
                if slots.intent == 'RESTATEMENT_LIST' and cells[1]['text'].strip() in {'-', '—', '0', ''}: continue
                p = next((c for c in parents if folded(label) in folded(c['text'])), parents[0])
                score = 30*exact + 3*overlap + 8*adjustment + 4*bool(scope) + 3*bool(period and period in slots.years)
                target_cell = None
                if adaptive and exact and row.get('metric'):
                    matched = [c for c in cells if c.get('box') and
                               (c.get('period_end'),c.get('period_type')) in target_periods]
                    if len(matched)==1 and len(target_periods)==1:
                        target_cell=matched[0]
                        score += 16
                    score += 70
                    label = row['row_label_normalized']
                    quote = label + ' | ' + ' | '.join(c['text'] for c in cells)
                if note_end and overlap and row.get('structure_status')=='OCR_GEOMETRIC_CANDIDATE':
                    matched=[c for c in cells if c.get('box') and c.get('period_end')==note_end and
                             (not note_basis or note_basis in folded(c.get('column_label') or ''))]
                    if len(matched)==1:
                        target_cell=matched[0]
                row_id = row['id']; cid = sha256(f"{d['sha256']}:{page}:{row_id}:{e['evidence_sha256']}".encode()).hexdigest()[:24]
                locator=target_cell['box'] if target_cell else row.get('box')
                if target_cell:
                    cid=sha256(f"{cid}:{target_cell['cell_id']}".encode()).hexdigest()[:24]
                pool.append({'chunk_id':p['id'], 'citation_id':cid,'evidence_id':cid,'document_id':d['id'],
                    'source_kind':'PDF','source_sha256':d['sha256'],'filename':d['filename'],
                    'issuer':identity[0] if len(identity)==1 else '', 'page':page,'page_1_based':page,'page_index_0_based':page-1,
                    'text':quote,'text_quote':quote,'row_label':label,'row_id':row_id,'table_id':row.get('table_id'),
                    'column_id':target_cell['cell_id'] if target_cell else None,'char_offsets':None,'word_boxes':None,
                    'box':locator,'row_box':row.get('box'),
                    'rectangles':[locator] if locator else [],'coordinate_space':'PDF_POINTS_TOP_LEFT',
                    'highlight_status':'EXTRACTED_NATIVE_ROW' if e.get('method')=='NATIVE' else 'OCR_GEOMETRY_NOT_VERIFIED',
                    'extraction_method':e.get('method'),'extraction_status':e.get('quality',{}).get('status'),
                    'verification_status':'SOURCE_ROW_UNREVIEWED','numeric_status':'UNVERIFIED','retrieval_status':'RETRIEVED',
                    'statement_scope':row.get('statement_scope') or scope or 'UNKNOWN','scope':row.get('statement_scope') or scope,
                    'report_period':period or '', 'period':target_cell['period'] if target_cell else period,
                    'scope_provenance':{'method':'PAGE_HEADING_OR_CONTINUED_TABLE','page':context_page},
                    'unit':target_cell['unit'] if target_cell else unit,'metric':row.get('metric') or slots.metric,'source_cells':cells,'adjustment_columns_candidate':adjustment,
                    'rerank_score':score,'rank_reasons':{'exact_metric':exact,'row_overlap':overlap,'adjustment_table':adjustment,
                        'scope_match':scope==slots.scope if slots.scope else None,'period_match':period in slots.years},
                    'algorithm_executed':VERSION+'_PDF_ROW_UNION_RERANK','engine_version':VERSION})
    # Retain narrative candidates for explanations and summaries. Their text is
    # evidence, never a verified numerical answer.
    for h in base.get('results',[]):
        if target_page is not None and h['page'] != target_page:continue
        context=page_context.get((h['document_id'],h['page']),{})
        if slots.scope and context.get('statement_scope') not in {slots.scope,'UNKNOWN',None}:continue
        h={**h,**context}
        score = len(terms & _tokens(h.get('text',''))) * .3
        if slots.intent in {'SUMMARIZE','EXPLAIN'}: score += 12
        if h.get('summary_section'):score+=50-h['rank']
        pool.append({**h,'source_kind':'PDF','citation_id':h['chunk_id'],'text_quote':h['text'],
            'page_1_based':h['page'],'page_index_0_based':h['page']-1,'numeric_status':'UNVERIFIED',
            'rerank_score':score,'engine_version':VERSION,'algorithm_executed':VERSION+'_PDF_ROW_UNION_RERANK'})
    from app.product.answer_planner_v2 import plan_question
    from app.product.source_cells_v2 import native_catalog
    semantic_plan=plan_question(question)
    exact_metrics=set(semantic_plan.metrics)
    if semantic_plan.metric=='reportable_segment_net_sales':exact_metrics={'americas_net_sales','europe_net_sales','greater_china_net_sales','japan_net_sales','rest_of_asia_pacific_net_sales','net_revenue'}
    native=[]
    if target_page is None and exact_metrics and semantic_plan.intent not in {'DOCUMENT_IDENTITY','FIND_SECTION','RESTATEMENT_LIST','SUMMARIZE'}:
        native=[c for c in native_catalog(w,document_ids) if c['metric'] in exact_metrics and (not semantic_plan.years or c['period'] in semantic_plan.years) and (not semantic_plan.scope or c['statement_scope']==semantic_plan.scope) and (not semantic_plan.period_type or c['period_type']==semantic_plan.period_type)]
    raw_candidate_count=len(pool)+len(native)
    native_dedup_count=0
    if native:
        # Collapse repeated statements of the same financial cell, retaining the
        # original statement-of-operations source when available. No synthetic fill.
        native.sort(key=lambda c:(not ('CONSOLIDATED STATEMENTS OF OPERATIONS' in c.get('table_heading','')),c['page']))
        selected_native={}
        for c in native:
            key=(c['document_id'],c['metric'],c['period'],c['statement_scope'],c['basis'],c['value_raw'])
            selected_native.setdefault(key,c)
        native_dedup_count=len(native)-len(selected_native)
        pool=[{**c,'text_quote':c['text'],'chunk_id':c['citation_id'],'retrieval_origin':'PDF_CELL','rerank_score':100,'rank_reasons':{'exact_metric':True,'source_bound_native_candidate':True},'report_period':c['period'],'text':c['row_label']+' | '+c['value_raw']+' | '+c['period'],'numeric_status':'UNVERIFIED','highlight_status':'NATIVE_CELL_CANDIDATE'} for c in selected_native.values()]

    metric_filtered_count=0
    if slots.metric and slots.intent in {'FIND_EVIDENCE','COMPARE_PERIODS'} and any(h.get('rank_reasons',{}).get('exact_metric') for h in pool):
        pool=[h for h in pool if h.get('rank_reasons',{}).get('exact_metric')]
    metric_filtered_count=raw_candidate_count-len(pool)
    pool.sort(key=lambda h:(-h['rerank_score'],h['page'],h.get('evidence_id',h['chunk_id'])))
    if slots.intent=='RESTATEMENT_LIST':
        from app.product.native_adjustments import verify_rows
        pool=verify_rows(w,pool)
        pool.sort(key=lambda h:(not bool(h.get('adjustment_verification')),-h['rerank_score'],h['page']))
        groups={}
        for h in pool:groups.setdefault((h['document_id'],h.get('statement_scope','UNKNOWN')),[]).append(h)
        pool=[group[i] for i in range(max((len(g) for g in groups.values()),default=0)) for group in groups.values() if i<len(group)]
    chosen=[];seen=set();counts={}
    for h in pool:
        key=(h['document_id'],h['page'],h.get('row_id',h['chunk_id']))
        if key in seen: continue
        seen.add(key)
        # Diversity is by table/scope, not a page-level dedup that loses rows.
        group=(h['document_id'],h.get('statement_scope'),h['page'])
        if not native and counts.get(group,0)>=max(2,top_k//2):continue
        counts[group]=counts.get(group,0)+1;chosen.append(h)
        if len(chosen)==top_k:break
    from app.product.native_adjustments import verify_rows
    chosen=verify_rows(w,chosen)
    from app.product.answer_planner_v2 import plan_question
    from app.product.source_cells_v2 import section_evidence
    question_plan=plan_question(question)
    if target_page is None and question_plan.intent in {'DOCUMENT_IDENTITY','FIND_SECTION'}:
        headings=section_evidence(w,document_ids,question_plan)
        chosen=[{**h,'chunk_id':h['citation_id'],'retrieval_origin':'PDF_SECTION','score':1.0,'rank':i} for i,h in enumerate(headings[:top_k],1)] or chosen
    for rank,h in enumerate(chosen,1):h['rank']=rank
    return {**base,'results':chosen,'latency_ms':round((perf_counter()-started)*1000,2),
        'intent':slots.public(),'query_plan':question_plan.public(),'evidence_status':'RELATED_UNVERIFIED_EVIDENCE' if chosen else 'NO_SUFFICIENT_EVIDENCE',
        'search_profile':'faith_r_product_v1','engine_version':VERSION,'candidate_count':len(pool),'scope_availability':sorted(observed_scopes),
        'scope_missing':bool(slots.scope and observed_scopes and slots.scope not in observed_scopes),
        'routing_reason':fallback,'mode':base.get('mode',mode),'candidate_count':raw_candidate_count,'dedup_count':native_dedup_count+max(0,len(pool)-len({(h['document_id'],h['page'],h.get('row_id',h['chunk_id'])) for h in pool})),
        'filter_reason':'METRIC_SCOPE_AND_TABLE_DIVERSITY' if native or metric_filtered_count or len(chosen)<min(top_k,len(pool)) else None,
        'truncation_reason':'TOP_K_LIMIT' if len(chosen)==top_k else 'FEWER_DISTINCT_MATCHING_EVIDENCE',
        'algorithm_executed':'FAITH_R_NATIVE_CELL_TARGETING_V3' if native else VERSION+'_PDF_ROW_UNION_RERANK'}

def evidence_answer(question, result):
    """Safe extractive narrative; citations survive every numerical abstention."""
    slots=understand(question);hits=result.get('results',[])
    if not hits:return None
    if slots.intent not in {'FIND_EVIDENCE','RESTATEMENT_LIST','SUMMARIZE','EXPLAIN','COMPARE_PERIODS'}:return None
    if result.get('scope_missing'):
        return {'status':'CLARIFY','answer':'Tài liệu có bằng chứng cho phạm vi '+', '.join(result['scope_availability'])+'; chưa tìm thấy phạm vi '+str(slots.scope)+'. Hãy chọn đúng báo cáo. Các đoạn liên quan dưới đây giữ nguyên phạm vi nguồn.',
            'citations':hits,'values':[],'verification_status':'REQUESTED_SCOPE_NOT_FOUND','search_profile':'faith_r_product_v1','query_understanding':slots.public(),
            'retrieval_trace':{k:result.get(k) for k in ('engine_version','algorithm_executed','latency_ms','candidate_count','generation')}}
    title={'FIND_EVIDENCE':'Đã tìm thấy các đoạn nguồn liên quan', 'RESTATEMENT_LIST':'Các dòng điều chỉnh tìm được (danh sách một phần)',
           'SUMMARIZE':'Tổng hợp trích đoạn từ tài liệu đã chọn','EXPLAIN':'Ngữ cảnh nguồn để giải thích',
           'COMPARE_PERIODS':'Các dòng nguồn để đối chiếu; phép tính chưa được xác minh'}[slots.intent]
    from app.product.native_adjustments import comparison_answer
    comparison=comparison_answer(question,hits)
    if comparison:return {**comparison,'query_understanding':slots.public(),'generation':result.get('generation'),
        'retrieval_trace':{k:result.get(k) for k in ('engine_version','algorithm_executed','latency_ms','candidate_count','generation')}}
    lines=[title+'.']
    for i,h in enumerate(hits,1):
        scope={'SEPARATE':'Riêng / công ty mẹ','CONSOLIDATED':'Hợp nhất'}.get(h.get('statement_scope'),'Phạm vi chưa xác định')
        check=' · ô/cột native đã đối chiếu' if h.get('adjustment_verification') else ' · số chưa xác minh'
        section=(h.get('summary_section')+' · ') if h.get('summary_section') else ''
        lines.append(f"[{i}] {section}{scope}{check} · trang {h.get('page') or 'SEC HTML'}: {h['text'][:600]}")
    if any(h.get('adjustment_columns_candidate') for h in hits):
        lines.append('Các cột ứng viên: đã công bố | điều chỉnh | trình bày lại. Chỉ dòng ghi ô/cột native đã đối chiếu đủ điều kiện tính; các dòng còn lại cần xác minh.')
    if slots.intent=='COMPARE_PERIODS':lines.append('Cần đối chiếu ô và đơn vị trước khi tính chênh lệch. Các trích dẫn vẫn mở được để kiểm tra.')
    return {'status':'SOURCE_EXCERPTS','answer':'\n\n'.join(lines),'citations':hits,'values':[],
        'verification_status':'SOURCE_TEXT_UNREVIEWED','numeric_verification':{'status':'UNVERIFIED','reason':'SOURCE_CELLS_REQUIRE_VERIFICATION'},
        'search_profile':'faith_r_product_v1','query_understanding':slots.public(),
        'retrieval_trace':{k:result.get(k) for k in ('engine_version','algorithm_executed','latency_ms','candidate_count','generation')},
        'warnings':['Trích đoạn nguồn; giá trị số chưa được xác minh độc lập.'],'generation':result.get('generation')}

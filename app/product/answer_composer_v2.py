"""Direct answers built only from a typed, independently audited claim plan."""
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal, localcontext, ROUND_HALF_UP
from hashlib import sha256
import json
import re
import pymupdf
from app.product.answer_planner_v2 import plan_question
from app.product.source_cells_v2 import native_catalog, section_evidence, cell_id
from app.product.independent_verifier_v2 import AnswerPlan,Claim,verify_plan,verify_rendered_numerals
from app.product.pdf_extract import folded

VERSION='VERIFIED_ANSWER_COMPOSER_V2'
LABELS={'net_revenue':('doanh thu thuần','total net sales'),'net_income':('lợi nhuận sau thuế','net income'),
    'services_net_sales':('doanh thu Services','Services net sales'),'products_net_sales':('doanh thu Products','Products net sales'),
    'services_gross_margin_percentage':('biên lợi nhuận gộp Services','Services gross margin'),
    'products_gross_margin_percentage':('biên lợi nhuận gộp Products','Products gross margin'),
    'gross_profit':('lợi nhuận gộp','gross margin'),'retained_earnings':('lợi nhuận sau thuế chưa phân phối','retained earnings'),
    'operating_income':('lợi nhuận hoạt động','operating income'),'effective_tax_rate':('thuế suất thực tế','effective tax rate'),
    **{m:(name+' — doanh thu',name+' net sales') for m,name in {'greater_china_net_sales':'Greater China','americas_net_sales':'Americas','europe_net_sales':'Europe','japan_net_sales':'Japan','rest_of_asia_pacific_net_sales':'Rest of Asia Pacific','us_net_sales':'U.S.'}.items()}}
UNITS={'MILLION_USD':('triệu USD','million USD'),'USD':('USD','USD'),'TRIEU_VND':('triệu đồng','million VND'),
    'VND':('đồng','VND'),'TY_VND':('tỷ đồng','billion VND'),'%':('%','%'),'PERCENTAGE_POINTS':('điểm phần trăm','percentage points')}

def display(value,language='vi'):
    d=Decimal(value);s=format(d,',f')
    return s.replace(',','_').replace('.',',').replace('_','.') if language=='vi' else s

def _calculate(op,operands,proposed=None):
    """Producer implementation; the independent gate never calls this helper."""
    nums=[Decimal(c['value_raw'].strip().rstrip('%').strip('()').replace(',',''))*(-1 if c['value_raw'].strip().startswith('(') else 1) for c in operands]
    with localcontext() as ctx:
        ctx.prec=40
        if op=='EXTRACT':r=nums[0]
        elif op=='PROPOSAL_DIFFERENCE':r=Decimal(proposed)-nums[0]
        elif op in {'ABS_CHANGE','SCOPE_DIFFERENCE','GEOGRAPHY_DIFFERENCE','PERCENTAGE_POINT_DIFFERENCE','RATE_POINT_CHANGE'}:r=nums[0]-nums[1]
        elif op in {'SHARE_PERCENT','PER_100','RELATIVE_DIFFERENCE','RESTATEMENT_GROWTH','PERCENT_CHANGE'}:
            if not nums[1]:raise ValueError('ZERO_DENOMINATOR')
            r=((nums[0]-nums[1]) if op in {'PERCENT_CHANGE','RELATIVE_DIFFERENCE'} else nums[0])/nums[1]*100
        elif op in {'RESTATEMENT_IDENTITY','PART_WHOLE_CHECK'}:r=nums[0]+nums[1]-nums[2]
        elif op=='SUM':r=nums[0]+nums[1]
        else:raise ValueError('UNSUPPORTED_OPERATION')
        return str(r.quantize(Decimal('.01'),rounding=ROUND_HALF_UP) if op in {'SHARE_PERCENT','PER_100','RELATIVE_DIFFERENCE','RESTATEMENT_GROWTH','PERCENT_CHANGE','PERCENTAGE_POINT_DIFFERENCE','RATE_POINT_CHANGE'} else r)

def adjustment_cells(w,hits,metric=None):
    from app.product.native_adjustments import verify_rows
    out=[]
    for h in verify_rows(w,deepcopy(hits)):
        if not h.get('adjustment_verification'):continue
        proof=h['adjustment_verification']
        with pymupdf.open(w.source_file(h['document_id'])) as pdf:
            page=pdf[h['page']-1];words=[v for v in page.get_text('words') if v[3]<min(h['box'][1]-4,150)]
            marker=[]
            for word in ('đã','chỉnh','trình'):
                m=next(v for v in words if v[4].casefold().strip('():.')==word);marker.append((m[0]+m[2])/2)
            edges=[max(0,marker[0]-60),(marker[0]+marker[1])/2,(marker[1]+marker[2])/2,min(page.rect.width,marker[2]+80)]
            top=min(v[1] for v in words if v[0]>edges[0]);bottom=max(v[3] for v in words if v[0]>edges[0] and v[1]<90)
        for i,c in enumerate(proof['cells']):
            record={'document_id':h['document_id'],'source_sha256':h['source_sha256'],'source_kind':'PDF','page':h['page'],
                'box':c['box'],'row_box':h['row_box'],'header_box':[edges[i],top,edges[i+1],bottom],
                'row_label':h['row_label'],'metric':metric or h.get('metric') or 'restatement:'+folded(h['row_label']),
                'value_raw':c['raw'],'period':h['report_period'],'period_end':proof['period_end'],
                'period_type':'INSTANT','basis':c['basis'],'statement_scope':h['statement_scope'],
                'scope_source_page':proof['scope_source_page'],'currency':'VND','scale':'1000000','unit':'TRIEU_VND',
                'extraction_method':'NATIVE','filename':h.get('filename'),'text':h['text'],'issuer':h.get('issuer')}
            record['citation_id']=cell_id(record);record['evidence_id']=record['citation_id'];out.append(record)
    return out

def _select(catalog,metric,year,scope=None,basis='AS_REPORTED'):
    found=[c for c in catalog if c['metric']==metric and c['period']==year and (not scope or c['statement_scope']==scope) and c['basis']==basis]
    if not found:return None
    if len({(c['value_raw'],c['unit'],c['statement_scope'],c['period_type']) for c in found})!=1:raise ValueError('CONFLICTING_SOURCE_CELLS')
    found.sort(key=lambda c:(not ('CONSOLIDATED STATEMENTS OF OPERATIONS' in c.get('table_heading','')),c['page']))
    return deepcopy(found[0])

def _compose_single_answer(w,question,result,document_ids,plan=None):
    p=deepcopy(plan) if plan else plan_question(question);en=p.language=='en';lang=p.language
    hits=deepcopy(result.get('results',[]));citations=[];claims=[];operands=[];calculations=[];explanation='';steps=[]
    status='SOURCE_SUPPORTED_NON_NUMERIC';answer='';values=[];reason=None
    def cite(c):
        c=deepcopy(c);c.setdefault('citation_id',c.get('evidence_id') or c.get('chunk_id'));c.setdefault('evidence_id',c['citation_id'])
        if c['citation_id'] not in {c['citation_id'] for c in citations}:citations.append(c)
        return '['+str(next(i for i,v in enumerate(citations,1) if v['citation_id']==c['citation_id']))+']'
    def factual(text,sources,scope=None):
        for c in sources:cite(c)
        claims.append(Claim('claim_'+str(len(claims)+1),'SOURCE_FACT',[c['citation_id'] for c in sources],scope,p.years,'SOURCE_SUPPORTED_NON_NUMERIC',text=text))
        return text
    def calc(op,inputs,label=None):
        for c in inputs:
            c['operand_id']=c['citation_id'];c['value']=str(Decimal(c['value_raw'].strip().rstrip('%').strip('()').replace(',',''))*(-1 if c['value_raw'].strip().startswith('(') else 1))
            if c['operand_id'] not in {v['operand_id'] for v in operands}:operands.append(c)
            cite(c)
        value=_calculate(op,inputs,p.proposed_amount)
        unit='%' if op in {'SHARE_PERCENT','PER_100','RELATIVE_DIFFERENCE','RESTATEMENT_GROWTH','PERCENT_CHANGE'} else 'PERCENTAGE_POINTS' if op in {'PERCENTAGE_POINT_DIFFERENCE','RATE_POINT_CHANGE'} else inputs[0]['unit']
        if op=='EXTRACT' and p.requested_unit and p.requested_unit not in {'%',unit}:
            scales={'USD':('USD','1'),'VND':('VND','1'),'TRIEU_VND':('VND','1000000'),'TY_VND':('VND','1000000000'),'MILLION_USD':('USD','1000000')}
            target=scales.get(p.requested_unit)
            if not target or target[0]!=inputs[0]['currency']:raise ValueError('FX_CONVERSION_NOT_AUTHORIZED')
            value=str(Decimal(value)*Decimal(inputs[0]['scale'])/Decimal(target[1]));unit=p.requested_unit
        cid='calculation_'+str(len(calculations)+1)
        expression={ 'PROPOSAL_DIFFERENCE':'user-proposed amount − source amount','RATE_POINT_CHANGE':'current tax rate − previous tax rate','EXTRACT':'source cell','ABS_CHANGE':'current − previous','SCOPE_DIFFERENCE':'consolidated adjustment − separate adjustment',
            'GEOGRAPHY_DIFFERENCE':'Americas net sales − U.S. net sales','PER_100':'part / total × 100','RELATIVE_DIFFERENCE':'(Services margin − Products margin) / Products margin × 100','PERCENT_CHANGE':'(current − previous) / previous × 100','SHARE_PERCENT':'numerator / total net sales × 100',
            'RESTATEMENT_GROWTH':'adjustment / original × 100','PERCENTAGE_POINT_DIFFERENCE':'Services margin % − Products margin %',
            'RESTATEMENT_IDENTITY':'original + adjustment − restated','SUM':'Products + Services','PART_WHOLE_CHECK':'Products + Services − total net sales'}[op]
        calculations.append({'calculation_id':cid,'operation':op,'operand_ids':[c['operand_id'] for c in inputs],'proposed_result':value,'result_unit':unit,'round_places':2})
        claims.append(Claim('claim_'+str(len(claims)+1),'NUMERIC',[c['citation_id'] for c in inputs],inputs[0]['statement_scope'] if len({c['statement_scope'] for c in inputs})==1 else None,
            sorted({c['period'] for c in inputs}),'PENDING_INDEPENDENT_GATE',value=value,calculation_id=cid,operand_ids=[c['operand_id'] for c in inputs]))
        steps.append({'calculation_id':cid,'title':label or expression,'operation':op,'formula':expression,'substitution':[{'value':c['value_raw'],'period':c['period'],'scope':c['statement_scope'],'basis':c['basis'],'unit':c['unit'],'citation':cite(c)} for c in inputs],
            'result':value,'unit':unit,'rounding':'ROUND_HALF_UP; 2 decimal places for percentages/percentage points; exact Decimal for amounts'})
        return display(value,lang)+' '+UNITS.get(unit,(unit,unit))[int(en)],value
    try:
        # Literal title/heading evidence has priority over any financial row.
        title_plan=replace(p,intent='DOCUMENT_IDENTITY');titles=section_evidence(w,document_ids,title_plan)
        available={c['statement_scope'] for c in titles if c['statement_scope']!='UNKNOWN'}
        if p.scope and available and p.scope not in available:
            sources=[h for h in titles if h['statement_scope'] in available][:1]
            suffix=cite(sources[0]) if sources else ''
            observed='separate parent-company' if available=={'SEPARATE'} else 'consolidated'
            requested='consolidated' if p.scope=='CONSOLIDATED' else 'separate parent-company'
            vietnamese='riêng công ty mẹ' if available=={'SEPARATE'} else 'hợp nhất'
            answer=factual((f'The selected source provides {observed} statements. The requested {requested} scope has not been provided. ' if en else f'Tài liệu đang chọn là báo cáo {vietnamese}. Chưa có nguồn cho phạm vi được hỏi; hãy chọn báo cáo phù hợp. ')+suffix,sources,next(iter(available)))
            status='UNSUPPORTED_SCOPE';reason='SELECTED_REPORT_SCOPE_NOT_PROVIDED'
        elif p.intent in {'DOCUMENT_IDENTITY','FIND_SECTION'}:
            sources=titles if p.intent=='DOCUMENT_IDENTITY' else section_evidence(w,document_ids,p)
            if not sources:raise ValueError('REQUESTED_HEADING_NOT_FOUND')
            sources=sources[:2]
            if p.intent=='DOCUMENT_IDENTITY':
                description='a separate parent-company financial report' if available=={'SEPARATE'} else 'a consolidated financial report' if available=={'CONSOLIDATED'} else 'a document containing both separate and consolidated statements'
                vietnamese='báo cáo tài chính riêng của công ty mẹ, không phải báo cáo hợp nhất' if available=={'SEPARATE'} else 'báo cáo tài chính hợp nhất' if available=={'CONSOLIDATED'} else 'tài liệu có cả báo cáo riêng và hợp nhất'
                answer=('This is '+description+'. ' if en else 'Đây là '+vietnamese+'. ')+''.join(cite(c) for c in sources)
                explanation='The classification comes from the actual report title and statement heading.' if en else 'Phạm vi được xác định từ tiêu đề báo cáo và tên bảng trên trang nguồn, không từ doanh nghiệp được nhắc trong thuyết minh.'
            else:
                answer=('The requested statement starts on physical PDF page ' if en else 'Bảng bạn cần bắt đầu tại trang PDF ')+str(sources[0]['page'])+' '+cite(sources[0])+'.'
                explanation=('Related continuation headings: ' if en else 'Các trang có tiêu đề liên quan: ')+', '.join(str(c['page'])+cite(c) for c in sources)+'.'
            factual(answer,sources,next(iter(available)) if len(available)==1 and p.intent=='DOCUMENT_IDENTITY' else None)
        elif p.intent=='TABLE_LOOKUP' or (p.intent=='FOLLOW_UP' and not re.search('don vi|unit',folded(question))):
            sources=[h for h in hits if h.get('row_label') and (not p.metric or h.get('metric')==p.metric)][:3] or hits[:2]
            if not sources:raise ValueError('ROW_NOT_FOUND')
            names=[]
            for h in sources:
                scope={'SEPARATE':'riêng / công ty mẹ','CONSOLIDATED':'hợp nhất'}.get(h.get('statement_scope'),'phạm vi chưa xác định')
                names.append(('PDF page ' if en else 'trang PDF ')+str(h['page'])+' ('+scope+') '+cite(h))
            label=LABELS.get(p.metric,(p.metric or 'chỉ tiêu',p.metric or 'requested line'))[int(en)]
            answer=('The '+label+' line is located at ' if en else 'Dòng '+label+' nằm tại ')+'; '.join(names)+'.'
            factual(answer,sources)
            explanation='Open the citation to inspect the original row; locating it does not certify OCR digits.' if en else 'Nhấn nguồn để xem đúng dòng. Việc tìm thấy dòng không tự xác minh các chữ số OCR.'
        elif p.intent=='RESTATEMENT_LIST':
            certified=adjustment_cells(w,hits)
            groups={}
            for c in certified:groups.setdefault((c['document_id'],c['page'],c['row_label']),[]).append(c)
            rows=[]
            for group in list(groups.values())[:6]:
                group.sort(key=lambda c:('ORIGINAL','ADJUSTMENT','RESTATED').index(c['basis']))
                if len(group)!=3:continue
                cells=[]
                for c in group:amount,_=calc('EXTRACT',[c]);cells.append(amount+' '+cite(c))
                scope='Riêng' if group[0]['statement_scope']=='SEPARATE' else 'Hợp nhất'
                rows.append('| '+scope+' · '+group[0]['row_label']+' | '+' | '.join(cells)+' |')
            if not rows:raise ValueError('ADJUSTMENT_ROWS_REQUIRE_SOURCE_REVIEW')
            answer='Các dòng dưới đây có ô và cột điều chỉnh đã được đối chiếu với PDF gốc. Đây là danh sách một phần, chưa phải toàn bộ các điều chỉnh.\n\n| Phạm vi / chỉ tiêu | Đã công bố | Điều chỉnh | Trình bày lại |\n|---|---|---|---|\n'+'\n'.join(rows)
            status='PARTIAL_VERIFIED';explanation='Đơn vị trong bảng là triệu đồng. Mỗi cột có citation tới đúng ô; có thể mở các trang còn lại của tài liệu để kiểm tra độ phủ.'
        elif p.intent=='EXPLAIN' and p.metric=='geography_definition':
            catalog=native_catalog(w,document_ids);year=(p.years or sorted({c['period'] for c in catalog},reverse=True))[:1]
            us=_select(catalog,'us_net_sales',year[0]);americas=_select(catalog,'americas_net_sales',year[0])
            if not us or not americas:raise ValueError('GEOGRAPHY_DEFINITIONS_REQUIRE_TWO_SOURCES')
            geography=section_evidence(w,document_ids,p)[:1]
            if not geography:raise ValueError('GEOGRAPHY_DEFINITION_SOURCE_REQUIRED')
            a,_=calc('EXTRACT',[us]);b,_=calc('EXTRACT',[americas]);difference,dv=calc('GEOGRAPHY_DIFFERENCE',[americas,us]);values=[us['value'],americas['value'],dv]
            answer=('No. U.S. net sales cover the United States; the Americas segment includes North and South America. ' if en else 'Không. U.S. sales là doanh thu tại Hoa Kỳ; Americas bao gồm cả Bắc Mỹ và Nam Mỹ. ')+cite(geography[0])+f' FY{year[0]}: U.S. {a} {cite(us)}; Americas {b} {cite(americas)}. '+('The difference is ' if en else 'Chênh lệch là ')+difference+'.'
            factual('The Americas segment includes both North and South America.',geography)
            status='VERIFIED_ANSWER'
            explanation='These reporting scopes are different and cannot substitute for each other.' if en else 'Hai phạm vi báo cáo khác nhau, không được dùng thay thế lẫn nhau.'
        elif p.intent in {'SUMMARIZE','EXPLAIN'} or (p.intent=='FOLLOW_UP' and re.search('don vi|unit',folded(question))):
            if not titles:raise ValueError('NO_SUPPORTED_REPORT_TITLE')
            sources=titles[:1]
            balance=section_evidence(w,document_ids,replace(p,intent='FIND_SECTION',section='BALANCE_SHEET'))[:1]
            income=section_evidence(w,document_ids,replace(p,intent='FIND_SECTION',section='INCOME_STATEMENT'))[:1]
            sources+=balance+income
            if p.intent=='FOLLOW_UP':
                unit=next((h.get('unit') for h in hits if h.get('unit')),None)
                if not unit:raise ValueError('UNIT_REQUIRES_SOURCE_DECLARATION')
                answer=('The source presentation unit is ' if en else 'Đơn vị trình bày của nguồn là ')+UNITS.get(unit,(unit,unit))[int(en)]+' '+cite(hits[0])+'.';sources=[hits[0]]
            else:
                scope='báo cáo riêng công ty mẹ' if available=={'SEPARATE'} else 'báo cáo hợp nhất' if available=={'CONSOLIDATED'} else 'tài liệu có báo cáo riêng và hợp nhất'
                answer=('The selected document contains source-backed financial statements. ' if en else 'Tài liệu đang chọn là '+scope+'. ')+cite(sources[0])
                if balance:answer+=(' The balance sheet is on PDF page ' if en else ' Bảng cân đối kế toán bắt đầu ở trang ')+str(balance[0]['page'])+cite(balance[0])+'.'
                if income:answer+=(' The income statement is on PDF page ' if en else ' Báo cáo kết quả kinh doanh bắt đầu ở trang ')+str(income[0]['page'])+cite(income[0])+'.'
                explanation=('This is a source-based overview. Causality beyond these statements has not been established.' if en else 'Đây là tổng hợp theo cấu trúc và phạm vi báo cáo. Các đoạn bảng không đủ để suy diễn nguyên nhân chênh lệch; số OCR phải được đối chiếu riêng.')
            factual(answer,sources)
        else:
            if p.requested_unit in {'EUR','CAD','AUD','HKD','JPY','CNY','GBP'}:raise ValueError('FX_CONVERSION_NOT_AUTHORIZED')
            catalog=native_catalog(w,document_ids)
            if p.metric=='retained_earnings':catalog+=adjustment_cells(w,hits,'retained_earnings')
            if not catalog or not any(c['metric'] in p.metrics for c in catalog):
                ocr=any(w.page_evidence(d,min(5,w.document(d)['pages'])).get('method') in {'OCR','REGION_FUSION'} for d in document_ids) if hasattr(w,'page_evidence') else False
                raise ValueError('OCR_OR_UNSUPPORTED_CELL_BINDING' if ocr else 'UNSUPPORTED_METRIC_PARSER' if not p.metric else 'UNSUPPORTED_SOURCE_CELL_LAYOUT')
            if p.period_type and p.period_type not in {'FY','INSTANT'} and any(c['period_type']=='FY' for c in catalog if c['metric'] in p.metrics):raise ValueError('QUARTER_YTD_FY_NOT_INTERCHANGEABLE')
            years=p.years
            if not years:
                source_periods={str(w.document(d).get('report_period',''))[:4] for d in document_ids}
                available_years={c['period'] for c in catalog if c['metric'] in p.metrics}
                matching=source_periods&available_years
                if len(matching)!=1:raise ValueError('SELECT_FINANCIAL_YEAR')
                years=sorted(matching);p.years=years
            if p.operation in {'ABS_CHANGE','PERCENT_CHANGE','CHANGE_AND_GROWTH'} and len(years)==1:
                previous=str(int(years[0])-1)
                if any(c['period']==previous and c['metric']==p.metric for c in catalog):years=sorted([previous,*years]);p.years=years
            def select(metric,year,basis='AS_REPORTED',scope=None):
                c=_select(catalog,metric,year,scope or p.scope,basis)
                if c is None:raise ValueError('REQUESTED_PERIOD_OR_CELL_NOT_AVAILABLE')
                return c
            name=LABELS.get(p.metric,(p.metric or 'chỉ tiêu',p.metric or 'metric'))[int(en)]
            if p.operation=='SCOPE_DIFFERENCE':
                if len(years)!=1:raise ValueError('SINGLE_PERIOD_REQUIRED')
                a=select(p.metric,years[0],'ADJUSTMENT','CONSOLIDATED');b=select(p.metric,years[0],'ADJUSTMENT','SEPARATE')
                amount,v=calc('SCOPE_DIFFERENCE',[a,b]);values=[v]
                answer=f'FY{years[0]}, '+('the consolidated adjustment exceeds the separate-bank adjustment by ' if en else 'mức điều chỉnh hợp nhất cao hơn riêng ngân hàng ')+amount+'. '+cite(a)+cite(b)
                explanation=('Consolidated adjustment: ' if en else 'Điều chỉnh hợp nhất: ')+display(a['value'],lang)+'; '+('separate: ' if en else 'riêng: ')+display(b['value'],lang)+' '+UNITS[a['unit']][int(en)]+'.'
            elif p.operation=='RATE_POINT_CHANGE':
                inputs=[select(p.metric,years[-1]),select(p.metric,years[0])]
                amount,v=calc('RATE_POINT_CHANGE',inputs);values=[v]
                answer=('The effective tax rate changed by ' if en else 'Thuế suất thực tế thay đổi ')+amount+'. '+''.join(cite(c) for c in inputs)
            elif p.operation in {'ABS_CHANGE','PERCENT_CHANGE','CHANGE_AND_GROWTH'}:
                if len(years)!=2:raise ValueError('TWO_COMPARABLE_PERIODS_REQUIRED')
                a=select(p.metric,years[-1]);b=select(p.metric,years[0]);amount,v=calc('ABS_CHANGE' if p.operation=='CHANGE_AND_GROWTH' else p.operation,[a,b]);values=[v]
                answer=f'FY{years[-1]} {name}: '+display(a['value'],lang)+' '+UNITS[a['unit']][int(en)]+' '+cite(a)+f'; FY{years[0]}: '+display(b['value'],lang)+' '+UNITS[b['unit']][int(en)]+' '+cite(b)+'. '
                answer+=('The change is ' if en else 'Mức thay đổi là ')+amount
                if p.operation=='CHANGE_AND_GROWTH':growth,g=calc('PERCENT_CHANGE',[a,b]);values.append(g);answer+=(' and ' if en else ', tương đương ')+growth
                answer+='.';explanation='The calculation uses the exact source amounts, not the rounded growth percentage displayed in the report.' if en else 'Phép tính dùng giá trị ô gốc; không dùng tỷ lệ tăng trưởng đã làm tròn trong báo cáo.'
            elif p.operation in {'SHARE_PERCENT','PER_100','RELATIVE_DIFFERENCE','PERCENTAGE_POINT_DIFFERENCE','SUM','PART_WHOLE_CHECK'}:
                if len(years)!=1:raise ValueError('SINGLE_PERIOD_REQUIRED')
                inputs=[select(m,years[0]) for m in p.metrics];amount,v=calc(p.operation,inputs);values=[v]
                if p.operation in {'SHARE_PERCENT','PER_100'}:answer=('In ' if en else 'Trong ')+f'FY{years[0]}, '+name+(' accounts for ' if en else ' chiếm ')+amount+(' of total net sales. ' if en else ' doanh thu thuần. ')+''.join(cite(c) for c in inputs)
                elif p.operation=='RELATIVE_DIFFERENCE':answer=('Relative to Products, Services gross margin is higher by ' if en else 'So với Products, biên lợi nhuận gộp Services cao hơn tương đối ')+amount+'. '+''.join(cite(c) for c in inputs)+(' This is a relative comparison with Products in the same fiscal year, not year-over-year growth.' if en else ' Đây là so sánh tương đối với Products trong cùng năm tài chính, không phải tăng trưởng so với năm trước.');explanation='(Services − Products) / Products × 100; same fiscal period, not year-over-year growth.' if en else '(Services − Products) / Products × 100; cùng kỳ tài chính, không phải tăng trưởng so với năm trước.'
                elif p.operation=='PERCENTAGE_POINT_DIFFERENCE':answer=f'FY{years[0]}: Services '+display(inputs[0]['value'],lang)+'% '+cite(inputs[0])+'; Products '+display(inputs[1]['value'],lang)+'% '+cite(inputs[1])+'. Services '+('gross margin is higher than Products by ' if en else 'có biên lợi nhuận gộp cao hơn Products ')+amount+'. '+''.join(cite(c) for c in inputs);explanation='This subtracts the published margin percentages; the result is percentage points, not percent growth.' if en else 'Lấy hiệu hai tỷ lệ đã công bố. Kết quả là điểm phần trăm, không phải phần trăm tăng trưởng.'
                if p.operation=='PER_100':
                    currency=inputs[0]['currency']
                    answer=(f'For every 100 {currency} of total net sales, Services contributes approximately ' if en else f'Trong mỗi 100 {currency} doanh thu thuần, Services đóng góp khoảng ')+display(v,lang)+' '+currency+' ('+display(v,lang)+'%). '+''.join(cite(c) for c in inputs)
                elif p.operation in {'SUM','PART_WHOLE_CHECK'}:answer=('The source-bound result is ' if en else 'Kết quả từ các ô nguồn là ')+amount+'. '+''.join(cite(c) for c in inputs)
            elif p.operation=='RESTATEMENT_IDENTITY':
                if len(years)!=1 or not p.scope:raise ValueError('SELECT_SEPARATE_OR_CONSOLIDATED')
                inputs=[select(p.metric,years[0],basis) for basis in ('ORIGINAL','ADJUSTMENT','RESTATED')]
                amount,v=calc('RESTATEMENT_IDENTITY',inputs);values=[v]
                answer=('Yes: ' if en and Decimal(v)==0 else 'Đúng: ' if Decimal(v)==0 else '')+display(inputs[0]['value'],lang)+' '+cite(inputs[0])+' + '+display(inputs[1]['value'],lang)+' '+cite(inputs[1])+' = '+display(inputs[2]['value'],lang)+' '+UNITS[inputs[0]['unit']][int(en)]+' '+cite(inputs[2])+'. '+('Reconciliation residual: ' if en else 'Chênh lệch kiểm tra: ')+amount+'.'
                explanation=('The three source columns reconcile exactly.' if en else 'Ba cột nguồn khớp hoàn toàn vì chênh lệch bằng không.') if Decimal(v)==0 else ('The source columns do not reconcile.' if en else 'Ba cột nguồn còn chênh lệch; cần kiểm tra lại.')
            elif p.operation=='RESTATEMENT_GROWTH':
                if len(years)!=1 or not p.scope:raise ValueError('SELECT_SEPARATE_OR_CONSOLIDATED')
                a=select(p.metric,years[0],'ADJUSTMENT');b=select(p.metric,years[0],'ORIGINAL');amount,v=calc('RESTATEMENT_GROWTH',[a,b]);values=[v]
                answer=('The adjustment is ' if en else 'Mức điều chỉnh tương đương ')+amount+(' of the original amount. ' if en else ' số đã công bố. ')+cite(a)+cite(b)
            else:
                if len(years)!=1:raise ValueError('SELECT_ONE_FINANCIAL_YEAR')
                basis=(p.basis or 'RESTATED') if p.metric=='retained_earnings' else 'AS_REPORTED'
                if p.metric=='retained_earnings' and not p.scope:raise ValueError('SELECT_SEPARATE_OR_CONSOLIDATED')
                c=select(p.metric,years[0],basis);amount,v=calc('EXTRACT',[c]);values=[v]
                answer=f'FY{years[0]}, {name} '+('was ' if en else 'là ')+amount+' '+cite(c)+'.'
                if p.proposed_amount and p.requested_unit==c['unit']:
                    difference,d=calc('PROPOSAL_DIFFERENCE',[c])
                    answer+=(' Your proposed amount minus the source amount is ' if en else ' Số bạn nêu trừ số trong báo cáo là ')+difference+' '+cite(c)+'.'
                explanation=('This is the consolidated annual source amount.' if en else 'Giá trị được đọc từ ô nguồn, gắn với đúng kỳ, đơn vị và phạm vi báo cáo.')
            status='VERIFIED_ANSWER'
    except (ValueError,KeyError,IndexError,StopIteration) as exc:
        reason=str(exc);values=[];operands=[];calculations=[];claims=[];steps=[];citations=[]
        sources=hits[:2]
        if reason=='OCR_OR_UNSUPPORTED_CELL_BINDING':
            from app.product.ocr_financial_workspace import FinancialOcrWorkspace
            if isinstance(w,FinancialOcrWorkspace):
                sources=([h for h in hits if h.get('rank_reasons',{}).get('exact_metric')] or sources)[:1]
                answer=('Open the original page to confirm the row, amount and reporting period. The OCR reading is still unverified. ' if en else 'Bạn có thể mở trang nguồn để đối chiếu dòng, chữ số và kỳ báo cáo. Kết quả đọc OCR vẫn chưa được xác minh. ')
            else:
                statement=section_evidence(w,document_ids,replace(p,intent='FIND_SECTION',section='BALANCE_SHEET' if p.metric=='assets' else 'INCOME_STATEMENT'))
                pages={h['page'] for h in statement}
                sources=([h for h in hits if h.get('page') in pages][:1] or statement[:1] or sources)
                answer=('I located the relevant statement, but cannot certify the amount: OCR has not reliably bound the row to the requested quarter/year column. Open the source for review. ' if en else 'Tôi tìm thấy báo cáo/dòng liên quan, nhưng chưa thể công bố giá trị: OCR chưa xác minh chắc chữ số và cột quý IV so với cả năm. Mở nguồn để đối chiếu. ')
        elif reason=='REQUESTED_PERIOD_OR_CELL_NOT_AVAILABLE' and p.years:
            answer=(f'The selected filing does not verify {LABELS.get(p.metric,(p.metric,p.metric))[1]} for FY'+', FY'.join(p.years)+'. No result from another year has been substituted. ' if en else 'Tài liệu đang chọn chưa xác nhận chỉ tiêu này cho kỳ '+', '.join(p.years)+'. Không dùng số năm khác thay thế. ')
        elif reason.startswith(('SELECT_','TWO_','SINGLE_')):answer=('Please specify the financial year and separate/consolidated scope to identify one unambiguous source cell. ' if en else 'Bạn muốn kỳ nào và phạm vi riêng hay hợp nhất? Cần xác định rõ để chọn đúng ô nguồn. ')
        elif reason=='QUARTER_YTD_FY_NOT_INTERCHANGEABLE':answer=('The available cells are fiscal-year values. A quarter/YTD value cannot be substituted. ' if en else 'Các ô hiện có là số cả năm tài chính; không thể dùng thay số quý hoặc lũy kế được hỏi. ')
        elif reason in {'UNSUPPORTED_METRIC_PARSER','UNSUPPORTED_SOURCE_CELL_LAYOUT'}:
            answer=('The selected PDF has native text, but this metric or cell layout is not supported yet; this is not an OCR failure. ' if en else 'PDF có lớp chữ gốc, nhưng bộ phân tích chưa hỗ trợ chỉ tiêu hoặc cấu trúc ô này; đây không phải lỗi OCR. ')
        elif reason=='FX_CONVERSION_NOT_AUTHORIZED':answer=('No source-backed exchange rate is provided for this currency conversion. ' if en else 'Chưa có tỷ giá kèm thời điểm và nguồn để đổi sang tiền tệ được yêu cầu. ')
        else:answer=('The requested metric/period cannot be verified from the selected source. ' if en else 'Chưa xác minh được chỉ tiêu/kỳ yêu cầu từ tài liệu đang chọn. ')
        answer+=''.join(cite(c) for c in sources)
        if sources:factual(answer,sources)
        status='CONFLICTING_EVIDENCE' if reason=='CONFLICTING_SOURCE_CELLS' else 'REQUIRES_SOURCE_REVIEW'
    plan=AnswerPlan(p.public(),claims,citations,operands,calculations)
    audit=verify_plan(w,plan) if citations else {'version':'INDEPENDENT_FINANCIAL_GATE_V2','status':'SOURCE_SUPPORTED_NON_NUMERIC','stage_a':[],'stage_b':[]}
    if audit['status']=='VERIFIED' and not verify_rendered_numerals(answer+' '+explanation,plan):
        audit.update(status='REJECTED',reason='RENDERED_NUMERAL_NOT_AUTHORIZED')
    if audit['status']=='REJECTED':
        status='CONFLICTING_EVIDENCE';values=[];answer=('Independent verification rejected this answer. The sources remain available for review. ' if en else 'Kiểm chứng độc lập đã chặn kết quả này. Các nguồn vẫn được giữ để đối chiếu. ')+''.join('['+str(i)+']' for i in range(1,len(citations)+1));reason=audit.get('reason');steps=[]
    for claim in claims:
        claim.verification_status='VERIFIED' if claim.type=='NUMERIC' and audit['status']=='VERIFIED' else 'REJECTED' if audit['status']=='REJECTED' else 'SOURCE_SUPPORTED_NON_NUMERIC'
    legacy='SUPPORTED' if status=='VERIFIED_ANSWER' else 'SOURCE_EXCERPTS' if status in {'SOURCE_SUPPORTED_NON_NUMERIC','PARTIAL_VERIFIED','REQUIRES_SOURCE_REVIEW'} else 'CLARIFY' if status=='UNSUPPORTED_SCOPE' else 'CONFLICTING_EVIDENCE'
    for c in citations:
        if c.get('operand_id') and audit['status']=='VERIFIED':c['verification']='INDEPENDENT_SOURCE_CELL_VERIFIED';c['numeric_status']='CELL_VERIFIED'
    return {'status':legacy,'answer_status':status,'answer':answer,'answer_explanation':explanation,'values':values,'citations':citations,
        'operands':operands,'calculation_steps':steps,'formula':steps[0]['formula'] if steps else None,
        'unit':steps[0]['unit'] if steps else None,'verification_status':audit['status'],'independent_verification':audit,
        'answer_plan':plan.public(),'query_plan':p.public(),'conversation_slots':{**p.public(),'document_ids':document_ids,
            'source_hashes':sorted({c['source_sha256'] for c in citations}),'citation_ids':[c['citation_id'] for c in citations],
            'verified_operand_ids':[c['operand_id'] for c in operands] if audit['status']=='VERIFIED' else []},
        'period':operands[0]['period_end'] if len({c['period_end'] for c in operands})==1 else None,'source_periods':sorted({c['period_end'] for c in operands}),'answer_source_chunk_id':None,'answer_evidence_ids':[c['evidence_id'] for c in citations],
        'retrieved_excerpt_verification':'SOURCE_TEXT_UNREVIEWED','reason':reason,'warnings':[],'search_profile':result.get('search_profile'),'composer_version':VERSION,
        'retrieval_trace':{k:result.get(k) for k in ('engine_version','algorithm_executed','latency_ms','candidate_count','generation')},
        'generation_trace':{'method':'DETERMINISTIC_VERIFIED_CLAIMS','model_status':'NOT_REQUIRED'}}



def _source_explanation(w,document_ids,metric,years):
    from app.product.independent_verifier_v2 import verify_paragraph
    from app.product.answer_planner_v2 import METRIC_NAMES
    phrase=METRIC_NAMES.get(metric,metric.replace('_',' '))
    candidates=[]
    for doc_id in document_ids:
        doc=w.document(doc_id)
        with pymupdf.open(w.source_file(doc_id)) as pdf:
            for no,page in enumerate(pdf,1):
                for b in page.get_text('blocks'):
                    text=' '.join(b[4].split());f=folded(text)
                    if folded(phrase) not in f or not re.search(r'primarily due|due to|because|includes both',f):continue
                    if years and not all(y in text for y in years):continue
                    c={'document_id':doc_id,'source_sha256':doc['sha256'],'source_kind':'PDF','page':no,'box':list(b[:4]),'text':text,'filename':doc['filename'],'extraction_method':'NATIVE','statement_scope':'CONSOLIDATED'}
                    c['citation_id']='paragraph_'+sha256(json.dumps([doc['sha256'],no,c['box'],text]).encode()).hexdigest()[:28];c['evidence_id']=c['citation_id']
                    if verify_paragraph(w,c):candidates.append(c)
    candidates.sort(key=lambda c:('compared to' not in c['text'].lower(),c['page'],len(c['text'])))
    return candidates[:1]


def compose_answer(w,question,result,document_ids):
    """One source/Decimal engine, orchestrated per requested semantic slot."""
    from app.product.answer_planner_v2 import METRIC_NAMES
    from app.product.semantic_answer_gate import verify_coverage
    p=plan_question(question)
    if not document_ids:
        coverage=verify_coverage(p.public(),[])
        return {'status':'SOURCE_UNAVAILABLE','answer_status':'SOURCE_UNAVAILABLE','answer':'Không có tài liệu phù hợp trong phạm vi đã chọn. Hãy kiểm tra tài liệu và bộ lọc.','citations':[],'values':[],'query_plan':p.public(),'semantic_question_coverage':coverage,'unanswered_subquestions':coverage['unanswered_subquestions'],'verification_status':'SOURCE_UNAVAILABLE'}
    en=p.language=='en';parts=[];outputs=[];responses=[];citations=[];steps=[];values=[]
    def register(c):
        cid=c.get('citation_id',c.get('evidence_id',c.get('chunk_id')))
        if cid not in {v.get('citation_id',v.get('chunk_id')) for v in citations}:citations.append(deepcopy(c))
        return '['+str(next(i for i,v in enumerate(citations,1) if v.get('citation_id',v.get('chunk_id'))==cid))+']'
    def attach(r,slot):
        indices={i:register(c) for i,c in enumerate(r.get('citations',[]),1)}
        def remap(text):return re.sub(r'\[(\d+)\]',lambda m:indices.get(int(m[1]),m[0]),text or '')
        for step in deepcopy(r.get('calculation_steps',[])):
            step['calculation_id']=slot['question_slot_id']+'_'+step['calculation_id']
            for sub in step['substitution']:sub['citation']=remap(sub['citation'])
            steps.append(step)
        values.extend(r.get('values',[]));responses.append(r)
        return remap(r.get('answer',''))
    def run(slot,metric=None,operation=None,include=True):
        metric=metric or slot['metric'];operation=operation or slot['operation']
        metrics=p.metrics if metric==p.metric and operation in {p.operation,'RELATIVE_DIFFERENCE'} else [metric]
        sub=replace(p,metric=metric,metrics=metrics,years=slot['years'],operation=operation,
            intent=p.intent if slot['kind']=='navigation' else 'EXTRACT_VALUE',
            requested_unit='%' if metric=='effective_tax_rate' and operation=='EXTRACT' else None if operation=='RATE_POINT_CHANGE' else p.requested_unit,
            requested_claims=[slot])
        if sub.intent=='SEGMENT_DECLINES':sub.intent='EXTRACT_VALUE'
        r=_compose_single_answer(w,question,result,document_ids,sub)
        text=attach(r,slot) if include else r.get('answer','')
        verified=r.get('independent_verification',{}).get('status')=='VERIFIED'
        good=verified or slot['kind']=='navigation' and bool(r.get('citations')) and r['answer_status'] in {'SOURCE_SUPPORTED_NON_NUMERIC','PARTIAL_VERIFIED'}
        actual_ops={c['operation'] for c in r.get('answer_plan',{}).get('calculations',[])}
        actual_outputs=['amount','period_values','source_operands','calculation'] if verified else ['source_location']
        if 'EXTRACT' in actual_ops and metric=='effective_tax_rate':actual_outputs+=['rate']
        if 'ABS_CHANGE' in actual_ops:actual_outputs+=['absolute_change']
        if 'PERCENT_CHANGE' in actual_ops:actual_outputs+=['percentage_change']
        if 'RATE_POINT_CHANGE' in actual_ops:actual_outputs+=['percentage_point_change']
        if slot['kind']=='navigation':actual_outputs=slot['outputs']
        # Metrics come from the verified operands, never from the requested slot.
        operand_metrics={c['metric'] for c in r.get('operands',[])}
        actual_metric=metric if metric in operand_metrics or slot['kind']=='navigation' else next(iter(operand_metrics),'unknown')
        if p.proposed_amount and verified:actual_outputs.append('confirmation')
        source_scopes={c['statement_scope'] for c in r.get('operands',[])}
        output={'question_slot_id':slot['question_slot_id'],'metric':actual_metric,'years':r.get('query_plan',{}).get('years',[]),'scope':next(iter(source_scopes)) if len(source_scopes)==1 else None,
            'operation':operation,'outputs':actual_outputs,'status':'VERIFIED' if verified else 'SOURCE_SUPPORTED' if good else 'UNANSWERED',
            'numeric_verification':r.get('independent_verification',{}).get('status'),'reason':r.get('reason'),'source_refs':[c['citation_id'] for c in r.get('citations',[])],
            'claims':r.get('answer_plan',{}).get('claims',[]),'operand_metrics':sorted(operand_metrics),'periods_from_operands':sorted({c['period'] for c in r.get('operands',[])}),'calculation_operations':sorted(actual_ops),'calculation_results':r.get('independent_verification',{}).get('stage_b',[]),'issuer':[w.document(d).get('issuer','') for d in document_ids],
            'confirmation':Decimal(p.proposed_amount)==Decimal(r['values'][0]) if p.proposed_amount and verified and r.get('values') else None}
        if verified and operation=='CHANGE_AND_GROWTH' and not {'ABS_CHANGE','PERCENT_CHANGE'}<=actual_ops:output['outputs']=[v for v in actual_outputs if v!='percentage_change']
        for claim in output['claims']:claim['question_slot_id']=slot['question_slot_id']
        outputs.append(output)
        return r,text
    # Keep navigation, list, existing single-purpose math and scope messages
    # backward compatible, then independently assess their requested coverage.
    simple=len(p.requested_claims)==1 and p.intent!='SEGMENT_DECLINES' and p.metric!='effective_tax_rate'
    if p.metric=='geography_definition':
        r=_compose_single_answer(w,question,result,document_ids);parts.append(attach(r,p.requested_claims[0]));responses=[r]
        for slot in p.requested_claims:
            available={c.get('metric') for c in r.get('operands',[])}
            good=(slot['metric'] in available or slot['operation']=='GEOGRAPHY_DIFFERENCE') if slot['kind']=='numeric' else any(c['citation_id'].startswith('heading_') for c in r.get('citations',[]))
            outputs.append({**slot,'years':sorted({c['period'] for c in r.get('operands',[])}) if slot['kind']=='numeric' else slot['years'],
                'status':'VERIFIED' if good else 'UNANSWERED','numeric_verification':r.get('verification_status'),
                **({'operand_metrics':sorted(available | ({'geography_definition'} if slot['operation']=='GEOGRAPHY_DIFFERENCE' else set())),'periods_from_operands':sorted({c['period'] for c in r.get('operands',[])}),'calculation_operations':[c['operation'] for c in r.get('answer_plan',{}).get('calculations',[])],'calculation_results':r.get('independent_verification',{}).get('stage_b',[])} if slot['kind']=='numeric' else {})})
    else:
        for slot in p.requested_claims:
            if slot['kind']=='explanation':
                target=slot['metric']
                if target=='reportable_segment_net_sales':target=next((o['selected_metric'] for o in outputs if o.get('selected_metric')),target)
                sources=_source_explanation(w,document_ids,target,slot['years']) if p.period_type in {None,'FY','INSTANT'} else []
                if slot.get('scope') and sources and sources[0].get('statement_scope')!=slot['scope']:sources=[]
                if sources:
                    original=sources[0]['text']
                    causal=re.search(r'primarily due to lower net sales of (.+?), partially offset by higher net sales of (.+?)\.',original,re.I)
                    if not en and causal:
                        text='Theo báo cáo, nguyên nhân chính là doanh thu '+causal[1]+' thấp hơn, được bù đắp một phần bởi doanh thu '+causal[2]+' cao hơn. '+register(sources[0])
                    else:text=('The filing explains: ' if en else 'Báo cáo giải thích (nguyên văn): ')+original+' '+register(sources[0])
                    parts.append(text)
                    outputs.append({**slot,'scope':sources[0].get('statement_scope'),'status':'SOURCE_SUPPORTED','source_refs':[sources[0]['citation_id']]})
                else:outputs.append({**slot,'status':'UNANSWERED','reason':'NO_MATCHING_SOURCE_EXPLANATION'})
            elif slot['operation']=='FIND_DECLINES':
                catalog=native_catalog(w,document_ids)
                regions=sorted({c['metric'] for c in catalog if c['metric'] in {'americas_net_sales','europe_net_sales','greater_china_net_sales','japan_net_sales','rest_of_asia_pacific_net_sales'}})
                checks=[];declines=[]
                for metric in regions:
                    before=len(outputs);r,text=run(slot,metric,'CHANGE_AND_GROWTH',include=False);o=outputs.pop();checks.append({'metric':metric,'numeric_verification':o['numeric_verification'],'absolute_change':r.get('values',['0'])[0] if r.get('values') else '0','source_refs':o['source_refs'],'operands':r.get('operands',[]),'independent_verification':r.get('independent_verification'),'claims':o['claims']})
                    changes=r.get('values',[])
                    if o['status']=='VERIFIED' and changes and Decimal(changes[0])<0:declines.append((metric,attach(r,slot)))
                if declines:
                    parts.append(('The declining reportable segment was ' if en else 'Khu vực kinh doanh giảm doanh thu là ')+', '.join(METRIC_NAMES[m].removesuffix(' net sales').title() for m,_ in declines)+'.')
                    parts.extend(text for _,text in declines)
                else:parts.append('No verified declining segment was found.' if en else 'Chưa xác minh được khu vực giảm doanh thu.')
                outputs.append({**slot,'status':'VERIFIED' if checks and all(c['numeric_verification']=='VERIFIED' for c in checks) else 'UNANSWERED','numeric_verification':'VERIFIED' if checks and all(c['numeric_verification']=='VERIFIED' for c in checks) else 'REJECTED',
                    'comparison_claims':checks,'selected_metrics':[m for m,_ in declines],'selected_metric':declines[0][0] if len(declines)==1 else None})
            else:
                r,text=run(slot)
                if p.proposed_amount and r.get('answer_status')=='VERIFIED_ANSWER' and r.get('values'):
                    agrees=Decimal(p.proposed_amount)==Decimal(r['values'][0]);text=('Yes. ' if agrees and en else 'Đúng. ' if agrees else 'No, that proposed amount is incorrect. ' if en else 'Không đúng. ')+text
                parts.append(text)
    coverage=verify_coverage(p.public(),outputs)
    # Preserve legacy single-source contracts, while semantic completeness can
    # downgrade an otherwise numerically valid answer.
    base=deepcopy(responses[0]) if responses else {'status':'SOURCE_EXCERPTS','answer_status':'REQUIRES_SOURCE_REVIEW','values':[],
        'answer':'No matching source explanation for the requested metric and period was verified. No cause has been inferred.' if en else 'Chưa xác minh được đoạn giải thích cho đúng chỉ tiêu và kỳ được hỏi. Chưa suy diễn nguyên nhân.'}
    if not responses and not citations:
        for hit in result.get('results',[])[:2]:register(hit)
    if simple and responses:
        base=responses[0];p.years=base.get('query_plan',{}).get('years',p.years)
        # An implicit year resolved from the selected source is valid.
        for slot in p.requested_claims:
            if not slot['years']:slot['years']=p.years
        for o in outputs:
            if not o['years']:o['years']=p.years
        coverage=verify_coverage(p.public(),outputs)
    if base.get('answer_status')=='PARTIAL_VERIFIED' and p.intent=='RESTATEMENT_LIST':
        limit={'question_slot_id':'coverage','metric':'adjustment_rows','years':p.years,'scope':p.scope,'operation':'EXHAUSTIVE_LIST','outputs':['exhaustive_rows'],'kind':'coverage','expected_source_class':'COMPLETE_ADJUSTMENT_TABLE'}
        p.requested_claims.append(limit);outputs.append({**limit,'status':'UNANSWERED','reason':'ADJUSTMENT_COVERAGE_NOT_EXHAUSTIVE'})
        coverage=verify_coverage(p.public(),outputs)
    coverage=verify_coverage(p.public(),outputs,'\n\n'.join(parts))
    missing=coverage['unanswered_subquestions']
    successful=[r for r in responses if r.get('independent_verification',{}).get('status')=='VERIFIED']
    if base.get('answer_status')=='PARTIAL_VERIFIED':status='PARTIAL_VERIFIED'
    elif coverage['status']=='COMPLETE' and successful:status='VERIFIED_ANSWER'
    elif coverage['status']=='COMPLETE' and citations:status='SOURCE_SUPPORTED_NON_NUMERIC'
    elif coverage['status']=='PARTIAL' and successful:status='PARTIAL_VERIFIED'
    elif base.get('answer_status') in {'UNSUPPORTED_SCOPE','CONFLICTING_EVIDENCE'}:status=base['answer_status']
    else:status=base.get('answer_status','REQUIRES_SOURCE_REVIEW')
    if coverage['status']=='UNANSWERED' and status=='VERIFIED_ANSWER':status='REQUIRES_SOURCE_REVIEW'
    if missing and not simple:
        parts.append(('Not established from the selected source: ' if en else 'Chưa đủ bằng chứng từ tài liệu đang chọn: ')+ '; '.join(METRIC_NAMES.get(s['metric'],s['metric'] or 'yêu cầu')+' — '+('source explanation not found' if s['kind']=='explanation' else 'requested cell/period not verified') for s in missing)+'.')
    text='\n\n'.join(parts) or base.get('answer','')
    # Future-year questions explicitly refer to the requested result year, not
    # the publication/selected filing year mentioned later in the sentence.
    return {**base,'status':'SUPPORTED' if status=='VERIFIED_ANSWER' else 'SOURCE_EXCERPTS' if status in {'PARTIAL_VERIFIED','SOURCE_SUPPORTED_NON_NUMERIC','REQUIRES_SOURCE_REVIEW'} else base.get('status','CLARIFY'),
        'answer_status':status,'answer':text,'primary_answer':text.split('\n\n')[0],'answer_explanation':base.get('answer_explanation','') if simple else '',
        'citations':citations,'calculation_steps':steps,'values':values,'supporting_claims':outputs,'unanswered_subquestions':missing,
        'semantic_question_coverage':coverage,'source_numeric_verification':'VERIFIED' if successful else base.get('verification_status'),
        'independent_verification':{'version':'INDEPENDENT_FINANCIAL_GATE_V2','status':'VERIFIED' if successful else base.get('verification_status','SOURCE_SUPPORTED_NON_NUMERIC'),
            'stage_a':[{'question_slot_id':r.get('query_plan',{}).get('raw_text'),**a} for r in successful for a in r['independent_verification']['stage_a']],
            'stage_b':[a for r in successful for a in r['independent_verification']['stage_b']]},
        'query_plan':p.public(),'conversation_slots':{**p.public(),'document_ids':document_ids},'generation_status':'DETERMINISTIC_CLAIMS',
        'limitations':[s['reason'] for s in missing]}

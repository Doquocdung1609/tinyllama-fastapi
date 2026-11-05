"""Apply the shared original-question gate after SEC's original-HTML cell gate.

The producer is the existing typed SEC calculator. This module independently
recalculates its results from authenticated raw cells before answer composition.
"""
from decimal import Decimal,localcontext,ROUND_HALF_UP
from app.product.answer_planner_v2 import plan_question
from app.product.answer_composer_v2 import display
from app.product.semantic_answer_gate import verify_coverage

def annotate(question,result):
    if result.get('status')!='SUPPORTED':return result
    p=plan_question(question);cells=result.get('source_cells',[]);op=result.get('operation')
    try:
        if not cells or any(c['source_status']!='VERIFIED_SOURCE_CELL' for c in cells):raise ValueError('SEC_SOURCE_GATE_NOT_VERIFIED')
        if len({(c['cik'],c['filing_id'],c['raw_sha256'],c['unit'],c['multiplier'],c['row_label'].casefold()) for c in cells})!=1:raise ValueError('SEC_OPERAND_CONTEXT_MISMATCH')
        if p.period_type=='INSTANT' and any(c['period_kind']!='INSTANT' for c in cells):raise ValueError('SEC_INSTANT_PERIOD_REQUIRED')
        if p.period_type=='FY' and any(c['period_months']!=12 for c in cells):raise ValueError('SEC_FULL_YEAR_PERIOD_REQUIRED')
        amounts=[]
        for c in cells:
            raw=c['raw_value'].strip();v=Decimal(raw.strip('()').replace(',',''))*(-1 if raw.startswith('(') else 1)
            amount=v*Decimal(c['multiplier'])
            if v!=Decimal(c['value']) or amount!=Decimal(c['effective_value']):raise ValueError('SEC_SOURCE_SCALE_MISMATCH')
            amounts.append(amount)
        with localcontext() as ctx:
            ctx.prec=50
            if op=='EXTRACT' and len(amounts)==1:expected=amounts
            elif op=='COMPARE' and len(amounts)==2:expected=amounts
            elif op=='ABS_CHANGE' and len(amounts)==2:expected=[amounts[1]-amounts[0]]
            elif op=='PERCENT_CHANGE' and len(amounts)==2 and amounts[0]>0:expected=[(amounts[1]-amounts[0])/amounts[0]*100]
            else:raise ValueError('SEC_UNSUPPORTED_CALCULATION')
            proposed=[Decimal(v) for v in result['values']]
            if op=='PERCENT_CHANGE':
                expected=[v.quantize(Decimal('.01'),rounding=ROUND_HALF_UP) for v in expected]
                proposed=[v.quantize(Decimal('.01'),rounding=ROUND_HALF_UP) for v in proposed]
            if expected!=proposed:raise ValueError('SEC_INDEPENDENT_ARITHMETIC_MISMATCH')
            unit='%' if op=='PERCENT_CHANGE' else cells[0]['unit']
            if unit=='USD' and p.requested_unit=='MILLION_USD':expected=[v/Decimal(1000000) for v in expected];unit='MILLION_USD'
            if p.requested_unit not in {None,'USD','MILLION_USD','%'}:raise ValueError('SEC_CURRENCY_CONVERSION_NOT_AUTHORIZED')
            if p.requested_unit=='%' and unit!='%':raise ValueError('SEC_REQUESTED_PERCENT_REQUIRES_RATIO')
        metric={'net sales':'net_revenue','total assets':'assets'}.get(cells[0]['row_label'].strip().casefold(),'unsupported_source_metric')
        years=sorted({c['period_end'][:4] for c in cells});source_refs=[c['parent_id'] for c in cells]
        proofs=[{'operation':op,'recomputed_result':str(v),'operand_metrics':[metric]*len(cells),'status':'VERIFIED'} for v in expected]
        outputs=[]
        for slot in p.requested_claims:
            if slot['kind']!='numeric':continue
            outputs.append({'question_slot_id':slot['question_slot_id'],'metric':metric,'years':years,'scope':None,'operation':op,
                'outputs':['amount','period_values','source_operands','calculation']+(['absolute_change'] if op=='ABS_CHANGE' else ['percentage_change'] if op=='PERCENT_CHANGE' else []),
                'status':'VERIFIED','numeric_verification':'VERIFIED','operand_metrics':[metric]*len(cells),'periods_from_operands':years,
                'calculation_operations':[op],'calculation_results':proofs,'source_refs':source_refs})
        labels='; '.join(dict.fromkeys(c['row_label']+' · '+c['period_end'] for c in cells))
        unit_label={'MILLION_USD':'triệu USD' if p.language=='vi' else 'million USD'}.get(unit,unit)
        text=labels+': '+', '.join(display(v,p.language)+' '+unit_label for v in expected)+'. '+''.join('['+str(i)+']' for i in range(1,len(result.get('citations',[]))+1))
        coverage=verify_coverage(p.public(),outputs,text);complete=coverage['status']=='COMPLETE'
        if not complete:text=('Related verified source figures; the requested answer is incomplete. ' if p.language=='en' else 'Số liệu nguồn liên quan đã được kiểm tra; chưa trả lời đầy đủ yêu cầu. ')+text
        steps=[]
        if op in {'ABS_CHANGE','PERCENT_CHANGE'}:
            steps=[{'calculation_id':'sec_recomputed','title':result['formula'],'formula':result['formula'],'operation':op,'result':str(expected[0]),'unit':unit,
                'rounding':'ROUND_HALF_UP, two decimals for percentages',
                'substitution':[{'value':c['raw_value'],'period':c['period_end'],'scope':'UNKNOWN','basis':'AS_REPORTED',
                    'unit':'MILLION_USD' if c['multiplier']=='1000000' else c['unit'],'citation':f'[{i}]'} for i,c in enumerate(cells,1)]}]
        return {**result,'status':'SUPPORTED' if complete else 'SOURCE_EXCERPTS','answer_status':'VERIFIED_ANSWER' if complete else 'PARTIAL_VERIFIED',
            'answer':text,'values':[str(v) for v in expected] if complete else [],'related_source_values':[] if complete else [str(v) for v in expected],
            'unit':unit,'query_plan':p.public(),'supporting_claims':outputs,'semantic_question_coverage':coverage,'calculation_steps':steps,
            'unanswered_subquestions':coverage['unanswered_subquestions'],'source_numeric_verification':'VERIFIED',
            'independent_verification':{'status':'VERIFIED','version':'INDEPENDENT_SEC_DECIMAL_AND_SHARED_COVERAGE_V3','stage_a':cells,'stage_b':proofs}}
    except (ValueError,KeyError,ArithmeticError) as e:
        return {**result,'status':'SOURCE_EXCERPTS','answer_status':'REQUIRES_SOURCE_REVIEW','values':[],
            'answer':'Chưa vượt qua kiểm tra độc lập cho câu hỏi này; nguồn được giữ để đối chiếu.','reason':str(e),
            'independent_verification':{'status':'REJECTED','reason':str(e)}}


def verify_comparison(cells, calculations):
    """Recompute the displayed million-USD results from each authenticated cell."""
    values = []
    with localcontext() as ctx:
        ctx.prec = 50
        for cell in cells:
            raw = cell['raw_value'].strip()
            parsed = Decimal(raw.strip('()').replace(',',''))
            if raw.startswith('('):
                parsed = -parsed
            multiplier = Decimal(cell['multiplier'])
            if (cell['source_status']!='VERIFIED_SOURCE_CELL' or cell['unit']!='USD'
                    or multiplier!=Decimal(1_000_000) or parsed!=Decimal(cell['value'])
                    or parsed*multiplier!=Decimal(cell['effective_value'])):
                raise ValueError('SEC_SOURCE_SCALE_MISMATCH')
            values.append(parsed*multiplier)
        proofs = []
        for operation, proposed in calculations:
            if operation=='EXTRACT' and len(values)==1:
                expected = values[0]/1_000_000
            elif operation=='ABS_CHANGE' and len(values)==2:
                expected = (values[1]-values[0])/1_000_000
            elif operation=='PERCENT_CHANGE' and len(values)==2 and values[0]!=0:
                expected = ((values[1]/values[0]-1)*100).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
            else:
                raise ValueError('SEC_UNSUPPORTED_CALCULATION')
            if expected!=Decimal(proposed):
                raise ValueError('SEC_INDEPENDENT_ARITHMETIC_MISMATCH')
            proofs.append({'operation':operation,'recomputed_result':str(expected),'status':'VERIFIED'})
    return {'status':'VERIFIED','version':'SEC_FEDERATED_DECIMAL_V4','stage_b':proofs}

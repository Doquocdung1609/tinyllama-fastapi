"""Independent semantic coverage: source-valid numbers must answer the requested slots."""
VERSION='SEMANTIC_ANSWER_COVERAGE_V1'

def verify_coverage(question_plan,outputs,rendered=None):
    audits=[];missing=[]
    for slot in question_plan['requested_claims']:
        selected=[o for o in outputs if o.get('question_slot_id')==slot['question_slot_id']]
        reasons=[]
        if not selected:reasons.append('REQUESTED_SLOT_NOT_ANSWERED')
        for o in selected:
            if o.get('status') not in {'VERIFIED','SOURCE_SUPPORTED'}:reasons.append(o.get('reason') or 'SOURCE_NOT_VERIFIED');continue
            if o.get('metric')!=slot['metric']:reasons.append('WRONG_METRIC')
            if set(o.get('years',[]))!=set(slot['years']):reasons.append('WRONG_PERIOD')
            if slot.get('scope') and o.get('scope')!=slot['scope']:reasons.append('WRONG_SCOPE')
            if o.get('operation')!=slot['operation']:reasons.append('WRONG_OPERATION')
            if not set(slot['outputs'])<=set(o.get('outputs',[])):reasons.append('MISSING_OUTPUT_DIMENSION')
            if slot.get('proposed_amount'):
                from decimal import Decimal
                extracts=[c['recomputed_result'] for c in o.get('calculation_results',[]) if c['operation']=='EXTRACT']
                if len(extracts)!=1 or o.get('confirmation')!=(Decimal(slot['proposed_amount'])==Decimal(extracts[0])):reasons.append('INCORRECT_AMOUNT_CONFIRMATION')
            if slot['kind']=='numeric' and o.get('numeric_verification')!='VERIFIED':reasons.append('NUMERIC_GATE_NOT_VERIFIED')
            if slot['kind']=='numeric' and slot['operation']=='FIND_DECLINES':
                from decimal import Decimal
                checks=o.get('comparison_claims',[])
                if len({c['metric'] for c in checks})!=5 or any(c['numeric_verification']!='VERIFIED' for c in checks):reasons.append('INCOMPLETE_SEGMENT_SCAN')
                expected={c['metric'] for c in checks if Decimal(c['absolute_change'])<0}
                if set(o.get('selected_metrics',[]))!=expected:reasons.append('WRONG_DECLINING_SEGMENT')
            elif slot['kind']=='numeric' and o.get('operand_metrics') is not None:
                if slot['metric'] not in o['operand_metrics']:reasons.append('OPERAND_METRIC_DOES_NOT_ANSWER_SLOT')
                if set(o.get('periods_from_operands',[]))!=set(slot['years']):reasons.append('OPERAND_PERIOD_MISMATCH')
                operations=set(o.get('calculation_operations',[]))
                required={'ABS_CHANGE','PERCENT_CHANGE'} if slot['operation']=='CHANGE_AND_GROWTH' else {slot['operation']}
                if not required<=operations:reasons.append('REQUESTED_OPERATION_NOT_EXECUTED')
        verdict='ANSWERED' if not reasons else 'UNANSWERED'
        audits.append({'question_slot_id':slot['question_slot_id'],'metric':slot['metric'],'verdict':verdict,'reasons':sorted(set(reasons))})
        if reasons:missing.append({**slot,'reason':';'.join(sorted(set(reasons)))})
    from app.product.question_obligation_auditor import audit
    raw_audit=audit(question_plan.get('raw_text',''),outputs,rendered)
    for requirement in raw_audit['DISCOVERED_REQUIREMENTS']:
        if requirement['verdict']=='MISSING':
            planned=next((s for s in question_plan['requested_claims'] if s['operation'] in requirement['operations']),None)
            if planned:
                existing=next(a for a in audits if a['question_slot_id']==planned['question_slot_id'])
                existing['verdict']='UNANSWERED';existing['reasons']=sorted(set(existing['reasons']+[requirement['reason']]))
                if not any(s['question_slot_id']==planned['question_slot_id'] for s in missing):missing.append({**planned,'reason':requirement['reason']})
            else:
                audits.append({'question_slot_id':'raw_'+requirement['id'],'metric':'raw_question_requirement','verdict':'UNANSWERED','reasons':[requirement['reason']]})
                missing.append({'question_slot_id':'raw_'+requirement['id'],'metric':requirement['id'],'kind':'coverage','reason':requirement['reason']})
    count=sum(a['verdict']=='ANSWERED' for a in audits)
    return {'version':VERSION,'status':'COMPLETE' if count==len(audits) and count else 'PARTIAL' if count else 'UNANSWERED',
        'requested_count':len(audits),'answered_count':count,'slots':audits,'unanswered_subquestions':missing,'original_question_audit':raw_audit}

"""Safe fixed operations only; no eval, model expression, hidden FX or dates."""
from decimal import Decimal,localcontext,ROUND_HALF_EVEN


def bounded_number(value,result=False):
    if not isinstance(value,Decimal) or not value.is_finite() or len(value.as_tuple().digits)>28 or not (-28 if result else -12)<=value.as_tuple().exponent<=12 or value.copy_abs()>Decimal('1e12'):
        raise ValueError('NUMERIC_RESOURCE_BOUND')


def period_key(period):
    return period.kind,period.year,period.quarter,period.end,period.months


def calculate(operation,operands):
    required=1 if operation=='EXTRACT' else 2
    if len(operands)!=required:raise ValueError('OPERATION_OPERAND_COUNT')
    for o in operands:bounded_number(o.displayed_value);bounded_number(o.effective_value);bounded_number(o.multiplier)
    if len(operands)==2:
        a,b=operands
        if a.unit!=b.unit or a.filing_id!=b.filing_id or a.table_id!=b.table_id or a.measurement_basis!=b.measurement_basis or a.entity_basis!=b.entity_basis or a.accounting_basis!=b.accounting_basis or a.entity_basis=='UNKNOWN':
            raise ValueError('INCOMPATIBLE_OPERAND_CONTEXT')
        pa,pb=a.period,b.period
        if pa.kind!=pb.kind or pa.months!=pb.months:raise ValueError('INCOMPATIBLE_MEASUREMENT_PERIOD')
        if operation not in {'COMPARE'}:
            old=(pa.year or 0,pa.quarter or 0,pa.end or '')
            new=(pb.year or 0,pb.quarter or 0,pb.end or '')
            if new<=old:raise ValueError('CHANGE_REQUIRES_OLD_THEN_NEW_PERIOD')
    if any(o.measurement_basis in {'AMOUNT_CHANGE','PERCENT_CHANGE','PERCENTAGE_POINT_CHANGE','CONFLICTED'} for o in operands):
        raise ValueError('CHANGE_COLUMN_IS_NOT_BASE_OPERAND')
    with localcontext() as context:
        context.prec=28;context.rounding=ROUND_HALF_EVEN
        values=[o.effective_value for o in operands]
        unit=operands[0].unit
        if operation=='EXTRACT':result=(values[0],);formula='source[0]'
        elif operation=='COMPARE':result=tuple(values);formula='ordered source[0], source[1]'
        elif operation=='ABS_CHANGE':
            if unit in {'PERCENT','PERCENTAGE_POINTS'}:raise ValueError('PERCENT_DIFFERENCE_REQUIRES_EXPLICIT_POINTS')
            result=(values[1]-values[0],);formula='source[1] - source[0]'
        elif operation=='PERCENTAGE_POINTS':
            if unit!='PERCENT':raise ValueError('PERCENT_OPERANDS_REQUIRED')
            result=(values[1]-values[0],);formula='percent[1] - percent[0]';unit='PERCENTAGE_POINTS'
        elif operation=='PERCENT_CHANGE':
            if values[0]<=0:raise ValueError('NONPOSITIVE_PERCENT_CHANGE_BASE')
            result=((values[1]-values[0])/values[0]*Decimal(100),);formula='(source[1]-source[0])/source[0]*100';unit='PERCENT'
        else:raise ValueError('UNSUPPORTED_OPERATION')
        for v in result:bounded_number(v,result=True)
    return result,unit,formula

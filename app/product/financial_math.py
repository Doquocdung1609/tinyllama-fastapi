"""Deterministic arithmetic shared by automatic and manually reviewed operands.

Source eligibility, units and comparison-set completeness belong to the caller.
"""
from decimal import Decimal, localcontext, ROUND_HALF_UP


def normalize_amount(value,scale):
    a,b=Decimal(value),Decimal(scale)
    with localcontext() as ctx:
        ctx.prec=max(40,len(a.as_tuple().digits)+len(b.as_tuple().digits)+abs(b.as_tuple().exponent)+10)
        return a*b


def calculate(operation,values,round_places=None):
    values=[Decimal(v) for v in values]
    if not values or any(not v.is_finite() for v in values):raise ValueError('INVALID_FINANCIAL_OPERAND')
    counts={'EXTRACT':1,'ABS_CHANGE':2,'PERCENT_CHANGE':2,'DEBT_TO_ASSETS':2,'NET_MARGIN':2,
            'RATIO':2,'ACCOUNTING_IDENTITY':3,'RESTATEMENT_CHECK':3}
    if operation in counts and len(values)!=counts[operation]:raise ValueError('INVALID_OPERAND_COUNT')
    with localcontext() as ctx:
        ctx.prec=max(40,max(len(v.as_tuple().digits)+abs(v.as_tuple().exponent) for v in values)+20)
        if operation=='EXTRACT':value=values[0]
        elif operation=='ABS_CHANGE':value=values[0]-values[1]
        elif operation in {'PERCENT_CHANGE','DEBT_TO_ASSETS','NET_MARGIN','RATIO'}:
            if values[1]==0:raise ValueError('ZERO_DENOMINATOR')
            value=((values[0]-values[1]) if operation=='PERCENT_CHANGE' else values[0])/values[1]*100
        elif operation in {'ACCOUNTING_IDENTITY','RESTATEMENT_CHECK'}:value=values[0]+values[1]-values[2]
        elif operation=='SUM':value=sum(values,Decimal(0))
        elif operation=='MAX':value=max(values)
        elif operation=='MIN':value=min(values)
        else:raise ValueError('UNSUPPORTED_FINANCIAL_OPERATION')
        return value.quantize(Decimal(1).scaleb(-round_places),rounding=ROUND_HALF_UP) if round_places is not None else value

from decimal import Decimal
import pytest
from app.product.financial_math import calculate,normalize_amount


def test_large_decimal_sign_and_scale_are_exact():
    assert normalize_amount('123456789012345678901234567890.12','1000000')==Decimal('123456789012345678901234567890120000.00')
    assert calculate('ABS_CHANGE',['123456789012345678901234567890.12','123456789012345678901234567890.11'])==Decimal('.01')
    assert normalize_amount('-125.50','1000000')==Decimal('-125500000')


@pytest.mark.parametrize('operation,values,expected',[
    ('SUM',['1.25','-0.25'],'1.00'),('MAX',['1','-2','3'],'3'),('MIN',['1','-2','3'],'-2'),
    ('RATIO',['2','8'],'25'),('ACCOUNTING_IDENTITY',['3','7','10'],'0'),
    ('RESTATEMENT_CHECK',['10','-2','8'],'0')])
def test_shared_calculations(operation,values,expected):
    assert calculate(operation,values)==Decimal(expected)


def test_no_nonfinite_zero_denominator_or_unsupported_operation():
    for operation,values in [('EXTRACT',['NaN']),('RATIO',['1','0']),('UNKNOWN',['1']),('EXTRACT',['1','2'])]:
        with pytest.raises(ValueError):calculate(operation,values)

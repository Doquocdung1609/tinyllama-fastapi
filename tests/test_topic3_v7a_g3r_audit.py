from decimal import Decimal

from scripts.topic3_v7a_g3r_audit import (
    compare_numeric_cells, decimal_value, gold_release_eligible,
    negative_question_category, normalize_unit, period_key, unique_rows,
)


def test_decimal_unit_and_duration_keep_financial_meaning():
    assert decimal_value('(1,234.50)') == Decimal('-1234.50')
    assert normalize_unit('NT$', 'millions') == ('TWD', '1000000')
    assert normalize_unit('USD', 'millions') != normalize_unit('USD', 'thousands')
    assert period_key('Year ended 2025-06-30') == ('2025-06-30', 'YEAR')
    assert period_key('Three Months Ended June 30, 2025') == ('2025-06-30', 'THREE_MONTHS')


def test_cell_comparison_detects_period_swap_and_same_number_wrong_source_row():
    source = (b'<html><body><table><tr><th>Year Ended June 30, 2025</th></tr>'
              b'<tr><td>Revenue</td><td>100</td></tr>'
              b'<tr><td>Segment revenue</td><td>100</td></tr></table></body></html>')
    a1 = {'exact_value': '100', 'currency': 'USD', 'scale': 'millions',
          'column_period': 'Year ended 2025-06-30', 'row_label': 'Revenue'}
    a2 = {'value_exact_decimal': '100', 'currency': 'USD', 'scale': 'millions',
          'column_period': 'Year Ended June 30, 2025', 'row_label': 'Revenue',
          'source_xpath': '/html/body/table/tr[2]'}
    cell = {'cell_xpath': '/html/body/table/tr[2]/td[2]',
            'column_period': a1['column_period'], 'value_as_printed': '100'}
    assert compare_numeric_cells(a1, a2, cell, source)[0] == 'EXACT_CELL_AGREEMENT'
    assert compare_numeric_cells(a1, {**a2, 'column_period': 'Year Ended June 30, 2024'}, cell, source)[0] == 'PERIOD_OR_SCOPE_CONFLICT'
    assert compare_numeric_cells(a1, {**a2, 'source_xpath': '/html/body/table/tr[3]'}, cell, source)[0] == 'SOURCE_LOCATOR_CONFLICT'


def test_negative_requires_inspected_statement_and_human_gold_is_explicit():
    assert negative_question_category(relevant_statement_inspected=False,
        target_line_present=False, question_scope_unambiguous=True) == 'SOURCE_INSUFFICIENT'
    assert negative_question_category(relevant_statement_inspected=True,
        target_line_present=False, question_scope_unambiguous=True) == 'NEGATIVE_SUPPORTED'
    assert negative_question_category(relevant_statement_inspected=True,
        target_line_present=False, question_scope_unambiguous=False) == 'AMBIGUOUS'
    assert not gold_release_eligible({'human_decision': 'NEGATIVE_SUPPORTED'})
    assert gold_release_eligible({'human_decision': 'NEGATIVE_SUPPORTED',
        'human_explanation': 'Reviewed statement', 'human_reviewer': 'Reviewer A',
        'human_reviewed_utc': '2026-11-02T12:00:00Z',
        'source_url': 'https://www.sec.gov/Archives/example.htm'})


def test_duplicate_question_ids_are_rejected():
    try:
        unique_rows([{'question_id': 'q1'}, {'question_id': 'q1'}], {'q1'}, 'fixture')
    except ValueError:
        pass
    else:
        raise AssertionError('Duplicate ID was accepted')

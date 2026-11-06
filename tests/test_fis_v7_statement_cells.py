from hashlib import sha256

import pymupdf
import pytest

from app.product.native_statement_cells import catalog
from app.product.statement_question_answer import answer


class SourceWorkspace:
    def __init__(self, path):
        self.path = path
        self.doc = {'id': 'source', 'filename': 'annual-report.pdf', 'sha256': sha256(path.read_bytes()).hexdigest()}

    def source_file(self, document_id):
        assert document_id == self.doc['id']
        return self.path

    def document(self, document_id):
        assert document_id == self.doc['id']
        return self.doc


@pytest.fixture
def financial_table(tmp_path):
    path = tmp_path / 'report.pdf'
    with pymupdf.open() as pdf:
        page = pdf.new_page(width=700, height=450)
        page.insert_text((40, 42), 'Separate statement of income', fontsize=12)
        page.insert_text((40, 58), 'Year 2024', fontsize=10)
        page.insert_text((40, 76), 'Unit: USD millions', fontsize=10)
        page.insert_text((490, 98), 'Previously', fontsize=10)
        page.insert_text((495, 111), 'reported', fontsize=10)
        page.insert_text((377, 111), 'Adjustment', fontsize=10)
        page.insert_text((609, 111), 'Restated', fontsize=10)
        for y, label, amount in (
            (140, 'Network servicing revenue', ('12,345,678', '(4,598)', '12,341,080')),
            (161, 'Cloud migration fee', ('5', '-', '5')),
            (182, 'Pipeline tax credit', ('17', '2', '20')),
        ):
            page.insert_text((40, y), label, fontsize=10)
            for x, text in zip((502, 391, 619), amount):
                page.insert_text((x, y), text, fontsize=10)
        pdf.save(path)
    return SourceWorkspace(path)


def test_multiline_header_and_reordered_source_columns(financial_table):
    result = answer(financial_table, 'Separate network servicing revenue before and after adjustment in 2024?', ['source'])
    assert result['status'] == 'SUPPORTED'
    assert result['values'] == ['12345678', '-4598', '12341080']
    assert [c['basis'] for c in result['citations']] == ['ORIGINAL', 'ADJUSTMENT', 'RESTATED']
    assert [c['header_box'][0] for c in result['citations']] == [490, 377, 609]
    assert all(c['unit'] == 'MILLION_USD' and c['period_type'] == 'FY' for c in result['operands'])
    with pymupdf.open(financial_table.path) as pdf:
        assert [pdf[0].get_text(clip=pymupdf.Rect(c['box'])).strip() for c in result['citations']] == [
            '12,345,678', '(4,598)', '12,341,080',
        ]


def test_printed_dash_is_a_source_marker_and_never_zero(financial_table):
    cells = catalog(financial_table, financial_table.doc)
    dash = next(c for c in cells if c['row_label'] == 'Cloud migration fee' and c['basis'] == 'ADJUSTMENT')
    assert dash['printed_marker'] == 'PRINTED_DASH'
    assert dash['value'] is None
    reply = answer(financial_table, 'Adjustment amount for the cloud migration fee in 2024?', ['source'])
    assert 'Dấu gạch in' in reply['answer']
    assert reply['values'] == []


def test_ledger_mismatch_keeps_source_cells_and_discloses_conflict(financial_table):
    reply = answer(financial_table, 'Pipeline tax credit before and after adjustment in 2024?', ['source'])
    assert reply['status'] == 'SOURCE_EXCERPTS'
    assert 'ba ô nguồn không khớp' in reply['answer']
    assert len(reply['citations']) == 3


def test_requested_missing_period_cannot_use_another_column(financial_table):
    reply = answer(financial_table, 'Network servicing revenue after adjustment in Q4 2025?', ['source'])
    assert reply['reason'] == 'REQUESTED_PERIOD_ABSENT'
    assert reply['values'] == []
    assert reply['citations'] == []


def test_wrong_pdf_bytes_cannot_be_promoted(financial_table):
    with financial_table.path.open('ab') as stream:
        stream.write(b'changed')
    with pytest.raises(ValueError, match='PDF_SOURCE_HASH_MISMATCH'):
        catalog(financial_table, financial_table.doc)

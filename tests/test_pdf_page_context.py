from app.product.pdf_page_context import answer


class SavedPdf:
    def document(self, document_id):
        return {'id': document_id, 'filename': 'report.pdf', 'sha256': 'hash',
                'status': 'READY', 'pages': 3}

    def page_evidence(self, document_id, number):
        texts = {
            2: ['At year end', 'Total assets 100', 'See accompanying notes'],
            3: ['Liabilities and equity', 'Total liabilities 60'],
        }
        return {'method': 'OCR', 'lines': [
            {'text': text, 'box': [0, i, 100, i + 1]}
            for i, text in enumerate(texts[number])
        ]}


def test_page_context_keeps_lines_together_and_cites_each_page_separately():
    result = answer(SavedPdf(), 'Quote total assets on page 2 and total liabilities on page 3', ['doc'])
    assert result['values'] == []
    assert result['verification_status'] == 'SOURCE_TEXT_UNREVIEWED'
    first, second = result['citations']
    assert (first['page'], second['page']) == (2, 3)
    assert first['text'] == 'At year end\nTotal assets 100\nSee accompanying notes'
    assert first['box'] == [0, 1, 100, 2]
    assert 'Total liabilities 60 [2]' in result['answer']


def test_missing_page_preserves_supported_excerpt_and_does_not_borrow_a_citation():
    result = answer(SavedPdf(), 'Quote total assets on page 2 and total liabilities on page 4', ['doc'])
    assert [citation['page'] for citation in result['citations']] == [2]
    assert 'Trang PDF 4** · Chưa đủ' in result['answer']


def test_numeric_operation_stays_in_financial_pipeline():
    assert answer(SavedPdf(), 'Quote total assets on page 2 and calculate liabilities on page 3', ['doc']) is None

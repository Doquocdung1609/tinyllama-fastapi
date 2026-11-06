"""Isolated OCR V2 workspace. Existing uploads and citation hashes stay pinned."""
import json
from pathlib import Path

from app.product import pdf_ocr_financial_v2 as extraction
from app.product import pdf_ocr_financial_v3
from app.product.workspace import PdfWorkspace

MARKER = 'ocr-financial-v2.json'


class FinancialOcrWorkspace(PdfWorkspace):
    ENGINE = extraction
    MARKER = MARKER
    TABLE_LAYOUT_VERSION = extraction.VERSION+'-formula-v1'

    def __init__(self, root, embedder=None):
        root = Path(root).resolve()
        marker = root / self.MARKER
        policy = {'version': self.ENGINE.VERSION}
        if root.exists() and any(root.iterdir()):
            if not marker.is_file() or json.loads(marker.read_text(encoding='utf-8')) != policy:
                raise ValueError('OCR_REQUIRES_ISOLATED_WORKSPACE')
        super().__init__(root, embedder)
        if not marker.exists():
            marker.write_text(json.dumps(policy), encoding='utf-8')

    def _extraction_engine(self):
        return self.ENGINE

    def _page_tables(self, saved, page_number):
        if saved.get('method') == 'OCR':
            if saved.get('version') != self.ENGINE.VERSION:
                raise ValueError('OCR_V2_CHECKPOINT_VERSION_MISMATCH')
            return self.ENGINE.arithmetic_warnings(saved.get('tables', []))
        return super()._page_tables(saved, page_number)


class AdaptiveFinancialOcrWorkspace(FinancialOcrWorkspace):
    ENGINE = pdf_ocr_financial_v3
    MARKER = 'ocr-financial-v3.json'
    TABLE_LAYOUT_VERSION = ENGINE.VERSION

    def _page_tables(self, saved, page_number):
        if saved.get('method') != 'OCR':
            return super()._page_tables(saved,page_number)
        if saved.get('version') != self.ENGINE.VERSION:
            raise ValueError('OCR_V3_CHECKPOINT_VERSION_MISMATCH')
        return [{**row,'cells':[{**cell,'source_sha256':saved['source_sha256']} for cell in row['cells']]}
                for row in saved['tables']]

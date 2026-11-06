"""Isolated OCR V2 workspace. Existing uploads and citation hashes stay pinned."""
import json
from pathlib import Path

from app.product import pdf_ocr_financial_v2 as extraction
from app.product.workspace import PdfWorkspace

MARKER = 'ocr-financial-v2.json'


class FinancialOcrWorkspace(PdfWorkspace):
    TABLE_LAYOUT_VERSION = extraction.VERSION+'-formula-v1'

    def __init__(self, root, embedder=None):
        root = Path(root).resolve()
        marker = root / MARKER
        policy = {'version': extraction.VERSION}
        if root.exists() and any(root.iterdir()):
            if not marker.is_file() or json.loads(marker.read_text(encoding='utf-8')) != policy:
                raise ValueError('OCR_V2_REQUIRES_ISOLATED_WORKSPACE')
        super().__init__(root, embedder)
        if not marker.exists():
            marker.write_text(json.dumps(policy), encoding='utf-8')

    def _extraction_engine(self):
        return extraction

    def _page_tables(self, saved, page_number):
        if saved.get('method') == 'OCR':
            if saved.get('version') != extraction.VERSION:
                raise ValueError('OCR_V2_CHECKPOINT_VERSION_MISMATCH')
            return extraction.arithmetic_warnings(saved.get('tables', []))
        return super()._page_tables(saved, page_number)

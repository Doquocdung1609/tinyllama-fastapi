"""Explicit V3R2 owner clone only. Source checkpoints/layout/reviews are preserved."""
from pathlib import Path
import json
from app.product.derived_workspace import DerivedPdfWorkspace
from app.product.resource_control import ResourceControl

MARKER='search-v3r2.json'
OWNER='TOPIC3_V3R2_OWNER_CLONE'

class ControlledPdfWorkspace(DerivedPdfWorkspace):
    search_candidate_version='V3R2'
    def __init__(self,root,embedder=None):
        root=Path(root)
        if not (root/MARKER).is_file() or json.loads((root/MARKER).read_text(encoding='utf-8')).get('owner')!=OWNER:
            raise ValueError('V3R2_EXPLICIT_NEW_OWNER_CLONE_REQUIRED')
        self.resources=ResourceControl();super().__init__(root,embedder)

    def process(self,document_id):
        try:
            with self.resources.claim('OCR_AND_EMBEDDING',minimum_mb=768):return super().process(document_id)
        except ValueError as exc:
            if str(exc) not in {'LOW_MEMORY_DEFERRED','RESOURCE_BUSY_RETRY'}:raise
            self._stage(document_id,'FAILED',str(exc),error=str(exc))
            return self.document(document_id)

    def search(self,*args,**kwargs):
        with self.resources.claim('BASELINE_OR_DENSE_RETRIEVAL',minimum_mb=256,timeout=10):return super().search(*args,**kwargs)

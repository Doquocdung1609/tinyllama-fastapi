"""Workspace-owned background preparation; every query still verifies source bytes."""
from pathlib import Path
from threading import Lock,Thread
from app.product.search_v3r import FinancialSearchV3R


class SearchPreparation:
    def __init__(self,workspace,root):
        self.is_v3r2=getattr(workspace,'search_candidate_version',None)=='V3R2'
        if self.is_v3r2:
            from app.product.search_v3r2 import FinancialSearchV3R2
            self.engine=FinancialSearchV3R2(workspace,Path(root),workspace.resources)
        else:self.engine=FinancialSearchV3R(workspace,Path(root))
        self.lock=Lock()
        self.state={'status':'NOT_PREPARED'};self.thread=None;self.pending=False;self.discard_pending=False

    def schedule(self,invalidate=False):
        with self.lock:
            self.discard_pending|=invalidate
            if self.state['status']=='PREPARING' and self.thread and self.thread.is_alive():
                self.pending=True
                return
            self.state={'status':'PREPARING'}
            self.thread=Thread(target=self._run,daemon=True);self.thread.start()

    def _run(self):
        while True:
            with self.lock:discard=self.discard_pending;self.discard_pending=False
            if discard and self.is_v3r2:
                # Only the opt-in V3R2 lifecycle drops old in-memory corpora before
                # a changed-document rebuild. Immutable index files are retained.
                with self.engine.base._lock:
                    self.engine.base._cache=None
                    self.engine.base.source._cache=None
                    self.engine._last_entries={}
                import gc
                gc.collect()
            try:state=self.engine.prewarm()
            except Exception as exc:
                resource_reason=str(exc) if str(exc) in {'LOW_MEMORY_DEFERRED','RESOURCE_BUSY_RETRY'} else None
                state={'status':'DEFERRED' if resource_reason else 'FAILED','reason':resource_reason or 'SEARCH_PREPARATION_FAILED_CHECK_SOURCE'}
            with self.lock:
                if self.pending:
                    self.pending=False
                    continue
                self.state=state
                return

    def status(self):
        with self.lock:return dict(self.state)

    def ready_engine(self):
        status=self.status()['status']
        if status=='DEFERRED':raise ValueError(self.status()['reason'])
        if status!='READY':
            if status in {'NOT_PREPARED','FAILED'}:self.schedule()
            raise ValueError('SEARCH_INDEX_PREPARING' if status!='FAILED' else 'SEARCH_PREPARATION_FAILED_CHECK_SOURCE')
        return self.engine

    def close(self):
        if self.thread:self.thread.join()


_creation_lock=Lock()
def preparation(workspace):
    with _creation_lock:
        if not hasattr(workspace,'_v3r_preparation'):
            name='v3r2-product-index' if getattr(workspace,'search_candidate_version',None)=='V3R2' else 'v3r-product-index'
            workspace._v3r_preparation=SearchPreparation(workspace,workspace.root/name)
        return workspace._v3r_preparation

def process_and_prepare(workspace,document_id):
    result=workspace.process(document_id)
    if (workspace.root/'derived-generation.json').exists():preparation(workspace).schedule(invalidate=getattr(workspace,'search_candidate_version',None)=='V3R2')
    return result

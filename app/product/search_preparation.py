"""Workspace-owned background preparation; every query still verifies source bytes."""
from pathlib import Path
from threading import Lock,Thread
from app.product.search_v3r import FinancialSearchV3R


class SearchPreparation:
    def __init__(self,workspace,root):
        self.engine=FinancialSearchV3R(workspace,Path(root));self.lock=Lock()
        self.state={'status':'NOT_PREPARED'};self.thread=None;self.pending=False

    def schedule(self):
        with self.lock:
            if self.state['status']=='PREPARING' and self.thread and self.thread.is_alive():
                self.pending=True
                return
            self.state={'status':'PREPARING'}
            self.thread=Thread(target=self._run,daemon=True);self.thread.start()

    def _run(self):
        while True:
            try:state=self.engine.prewarm()
            except Exception:state={'status':'FAILED','reason':'SEARCH_PREPARATION_FAILED_CHECK_SOURCE'}
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
            workspace._v3r_preparation=SearchPreparation(workspace,workspace.root/'v3r-product-index')
        return workspace._v3r_preparation

def process_and_prepare(workspace,document_id):
    result=workspace.process(document_id)
    if (workspace.root/'derived-generation.json').exists():preparation(workspace).schedule()
    return result

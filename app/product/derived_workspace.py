"""Opt-in V3R generations. Never upgrade an existing legacy workspace in place."""
from contextlib import closing
from functools import partial
from hashlib import sha256
import json
from pathlib import Path
from types import SimpleNamespace

from app.product.workspace import PdfWorkspace,DIGEST
from app.product import pdf_extract_v3r as extraction
from app.product.region_layout import rows_with_fragments,VERSION as LAYOUT_VERSION

OWNER='TOPIC3_V3R_DERIVED_REGION_GENERATION'
MARKER='derived-generation.json'


class DerivedPdfWorkspace(PdfWorkspace):
    TABLE_LAYOUT_VERSION=LAYOUT_VERSION

    def __init__(self,root,embedder=None):
        root=Path(root).resolve();marker=root/MARKER;self.extractor_policy_sha256=extraction.policy_hash()
        if root.exists() and any(root.iterdir()):
            if not marker.is_file():raise ValueError('V3R_REQUIRES_NEW_DERIVED_WORKSPACE')
            payload=json.loads(marker.read_text(encoding='utf-8'))
            if payload.get('owner')!=OWNER or payload.get('extractor_policy_sha256')!=self.extractor_policy_sha256 or payload.get('model_digest')!=DIGEST:
                raise ValueError('V3R_GENERATION_POLICY_MISMATCH_CREATE_NEW_ROOT')
        super().__init__(root,embedder)
        if not marker.exists():marker.write_text(json.dumps({'owner':OWNER,'version':extraction.VERSION,'extractor_policy_sha256':self.extractor_policy_sha256,'model_digest':DIGEST},sort_keys=True)+'\n',encoding='utf-8')
        with closing(self._connect()) as db,db:
            db.execute('CREATE TABLE IF NOT EXISTS extraction_generations(document_id TEXT PRIMARY KEY,manifest_hash TEXT,summary TEXT)')

    def _prior(self,document_id,number):
        folder=self.root/'parents'/document_id
        matches=list(folder.glob(f'p{number}-*.json')) if folder.exists() else []
        if not matches:return None
        if len(matches)!=1:raise ValueError('PRIOR_CHECKPOINT_AMBIGUOUS')
        p=matches[0];raw=p.read_bytes();digest=sha256(raw).hexdigest()
        if p.stem!=f'p{number}-{digest}':raise ValueError('PRIOR_CHECKPOINT_HASH_MISMATCH')
        data=json.loads(raw);doc=self.document(document_id)
        if data.get('source_sha256')!=doc['sha256'] or data.get('page')!=number or data.get('status')=='FAILED':raise ValueError('PRIOR_CHECKPOINT_SOURCE_MISMATCH')
        return {**data,'_parent_sha':digest}

    def _extraction_engine(self):
        def run(path,document_id,checkpoint,save_progress):
            return extraction.extract_document(path,document_id,checkpoint,save_progress,prior=partial(self._prior,document_id))
        return SimpleNamespace(VERSION=extraction.VERSION,extract_document=run)

    def _page_tables(self,saved,page_number):
        if saved.get('version')!=extraction.VERSION:raise ValueError('DERIVED_CHECKPOINT_VERSION_MISMATCH')
        return rows_with_fragments(saved,page_number)

    def _describe(self,doc):
        if not doc:return None
        with closing(self._connect()) as db:
            exists=db.execute("SELECT 1 FROM sqlite_master WHERE name='extraction_generations'").fetchone()
            row=db.execute('SELECT manifest_hash,summary FROM extraction_generations WHERE document_id=?',(doc['id'],)).fetchone() if exists else None
        if row:
            summary=json.loads(row['summary'])
            manifest=self.root/'generations'/(row['manifest_hash']+'.json')
            if not manifest.is_file() or sha256(manifest.read_bytes()).hexdigest()!=row['manifest_hash']:
                raise ValueError('DERIVED_MANIFEST_INTEGRITY_FAILED')
            identity=json.loads(manifest.read_bytes())
            if identity['summary']!=summary or identity['source_sha256']!=doc['sha256'] or identity['extractor_policy_sha256']!=self.extractor_policy_sha256:
                raise ValueError('DERIVED_SUMMARY_INTEGRITY_FAILED')
            return {**doc,**summary,'derived_generation':row['manifest_hash']}
        return {**doc,'processing_status':'PROCESSING_COMPLETE' if doc['status'] in {'READY','FAILED'} else 'PROCESSING',
            'extraction_coverage_status':'EXTRACTION_COVERAGE_WARNING','coverage_warnings':['DERIVED_COVERAGE_NOT_SEALED'],
            'financial_evidence_status':'FINANCIAL_EVIDENCE_REVIEW_PENDING','extraction_profile':extraction.VERSION}

    def document(self,document_id):return self._describe(super().document(document_id))

    def list_documents(self):return [self._describe(d) for d in super().list_documents()]

    def process(self,document_id):
        doc=super().process(document_id)
        if doc['status']=='READY':self._seal(document_id)
        return self.document(document_id)

    def _seal(self,document_id):
        doc=super().document(document_id);self.source_file(document_id)
        with closing(self._connect()) as db:
            rows=db.execute('SELECT page,payload,payload_hash FROM page_evidence WHERE document_id=? ORDER BY page',(document_id,)).fetchall()
            chunks=db.execute('SELECT id,text_hash FROM chunks WHERE document_id=? ORDER BY id',(document_id,)).fetchall()
        pages=[];warnings=[];regions=0;cells=0
        for row in rows:
            if sha256(row['payload'].encode()).hexdigest()!=row['payload_hash']:raise ValueError('DERIVED_CHECKPOINT_HASH_MISMATCH')
            p=json.loads(row['payload']);warnings.extend(p.get('coverage_warnings',[]));regions+=len(p.get('regions',[]));cells+=sum(len(r['cells']) for r in p.get('tables',[]))
            pages.append({'page':row['page'],'checkpoint_sha256':row['payload_hash'],'prior_checkpoint_sha256':p.get('prior_checkpoint_sha256')})
        if len(rows)!=doc['pages']:warnings.append('MISSING_PAGE_CHECKPOINT')
        summary={'processing_status':'PROCESSING_COMPLETE','extraction_coverage_status':'EXTRACTION_COVERAGE_WARNING' if warnings else 'EXTRACTION_COMPLETE',
            'coverage_warnings':sorted(set(warnings)),'financial_evidence_status':'FINANCIAL_EVIDENCE_REVIEW_PENDING','candidate_cells':cells,'regions_processed':regions,
            'extraction_profile':extraction.VERSION,'coverage_scope':'REGIONS_PROCESSED_UNDER_POLICY;NOT_FINANCIAL_ACCURACY_OR_FULL_CELL_REVIEW'}
        manifest={'owner':OWNER,'document_id':document_id,'source_sha256':doc['sha256'],'extractor_policy_sha256':self.extractor_policy_sha256,'pages':pages,
            'chunks':[(r['id'],r['text_hash']) for r in chunks],'model_digest':DIGEST,'summary':summary}
        raw=(json.dumps(manifest,sort_keys=True,ensure_ascii=False)+'\n').encode();digest=sha256(raw).hexdigest();folder=self.root/'generations';folder.mkdir(exist_ok=True);target=folder/(digest+'.json')
        if target.exists() and target.read_bytes()!=raw:raise ValueError('DERIVED_MANIFEST_CHANGED')
        if not target.exists():target.write_bytes(raw)
        with closing(self._connect()) as db,db:db.execute('INSERT OR REPLACE INTO extraction_generations VALUES(?,?,?)',(document_id,digest,json.dumps(summary)))

    def extraction_status(self,document_id):
        status=super().extraction_status(document_id);doc=self.document(document_id)
        return {**status,**{k:doc[k] for k in ['processing_status','extraction_coverage_status','coverage_warnings','financial_evidence_status','extraction_profile']},'derived_generation':doc.get('derived_generation')}

    def verify_generation(self):
        """Bind current checkpoint/chunk membership to immutable extraction manifests."""
        for doc in self.list_documents():
            if doc['status']!='READY':continue
            identity=json.loads((self.root/'generations'/(doc['derived_generation']+'.json')).read_bytes())
            with closing(self._connect()) as db:
                pages=db.execute('SELECT page,payload_hash FROM page_evidence WHERE document_id=? ORDER BY page',(doc['id'],)).fetchall()
                chunks=db.execute('SELECT id,text_hash FROM chunks WHERE document_id=? ORDER BY id',(doc['id'],)).fetchall()
            actual=[(r['page'],r['payload_hash']) for r in pages]
            expected=[(r['page'],r['checkpoint_sha256']) for r in identity['pages']]
            # V2.prepare independently hashes every payload's actual bytes. Ancestry is
            # inside that payload,so reparsing all OCR JSON adds no integrity guarantee.
            if actual!=expected or [list(r) for r in chunks]!=identity['chunks']:raise ValueError('DERIVED_GENERATION_MEMBERSHIP_CHANGED')

    def delete(self,document_id):
        removed=super().delete(document_id)
        if removed:
            with closing(self._connect()) as db,db:db.execute('DELETE FROM extraction_generations WHERE document_id=?',(document_id,))
        return removed

"""Product snapshot ownership without impersonating a frozen research dataset."""
import json
from pathlib import Path
from threading import RLock
from typing import Literal
from pydantic import Field
from app.research_retrieval.snapshot import FrozenResearchSnapshot
from app.financial_index.lexical import LexicalIndex
from app.financial_index.corpus import ProvenanceCache
from app.financial_query.contracts import CatalogFilingV1,CorpusCatalogV1

class ProductCatalogFiling(CatalogFilingV1):
    form: Literal['10-K','10-Q','10-K/A','10-Q/A','20-F']


class ProductCorpusCatalog(CorpusCatalogV1):
    filings: list[ProductCatalogFiling] = Field(max_length=50000)


class ProductSecSnapshot(FrozenResearchSnapshot):
    def __init__(self,root):
        self.root=Path(root).resolve()
        owner=json.loads((self.root/'ownership.json').read_text(encoding='utf-8'))
        if owner.get('owner')!='FIS_USER_SEC_LIBRARY_V1' or self.root.parent.name!=owner.get('id'):raise ValueError('PRODUCT_SEC_OWNERSHIP_REQUIRED')
        self.freeze=json.loads((self.root/'frozen_v1/freeze.json').read_text(encoding='utf-8'))
        self.catalog=ProductCorpusCatalog.model_validate_json((self.root/'frozen_v1/catalog.json').read_bytes())
        if self.catalog.manifest_hash!=self.freeze['manifest_hash'] or self.catalog.generation_id!=self.freeze['generation']:raise ValueError('PRODUCT_GENERATION_MISMATCH')
        from app.financial_ingestion.schemas import DatasetManifest
        manifest=DatasetManifest.model_validate_json((self.root/'frozen_v1/manifest.json').read_bytes())
        if manifest.content_hash()!=self.freeze['manifest_hash']:raise ValueError('PRODUCT_MANIFEST_HASH_MISMATCH')
        if {s['raw_hash'] for s in self.freeze['source_groups']}!=set(manifest.raw_hashes.values()):raise ValueError('PRODUCT_RAW_MEMBERSHIP_MISMATCH')
        self.product_source_registry=self.freeze
        from app.product.sec_import_identity import validate
        from app.financial_ingestion.schemas import FilingMetadata
        from hashlib import sha256
        for source in json.loads((self.root/'frozen_v1/sources.json').read_text(encoding='utf-8')):
            raw_path=Path(source['raw_path']).resolve();structured=Path(source['structured_path']).resolve()
            if not raw_path.is_relative_to(self.root) or not structured.is_relative_to(self.root):raise ValueError('PRODUCT_SOURCE_PATH_ESCAPE')
            raw=raw_path.read_bytes()
            if sha256(raw).hexdigest()!=source['raw_hash']:raise ValueError('PRODUCT_RAW_HASH_MISMATCH')
            m=FilingMetadata.model_validate(json.loads(structured.read_bytes())['metadata']);validate(raw,m)
        self.lexical=LexicalIndex(self.root/'lexical_v1.sqlite3')
        self.cache=ProvenanceCache(max_entries=1,max_bytes=32*1024*1024);self.lock=RLock()

def snapshot(root):
    owner=json.loads((Path(root)/'ownership.json').read_text(encoding='utf-8'))
    result=ProductSecSnapshot(root) if owner.get('owner')=='FIS_USER_SEC_LIBRARY_V1' else FrozenResearchSnapshot(root)
    result.product_verification=True
    return result

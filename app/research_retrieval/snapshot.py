"""Read only frozen research artifacts; only owned lexical storage is opened."""
from contextlib import closing,contextmanager
import json
from pathlib import Path
from threading import RLock
from app.financial_index.corpus import verified_source,ProvenanceCache
from app.financial_index.lexical import LexicalIndex
from app.financial_query.contracts import CorpusCatalogV1
from app.research_retrieval.adapters import candidate
from app.research_retrieval.contracts import ChannelUnavailable
from app.table_evidence.identity import digest


class FrozenResearchSnapshot:
    def __init__(self,root):
        self.root=Path(root).resolve()
        owner=json.loads((self.root/'ownership.json').read_text())
        if owner.get('owner')!='TOPIC3_AUTONOMOUS_D2_TO_D5_GATED_EXECUTION_AUTHORIZED':raise ValueError('RESEARCH_OWNERSHIP_REQUIRED')
        self.freeze=json.loads((self.root/'frozen_v1/freeze.json').read_text())
        self.catalog=CorpusCatalogV1.model_validate_json((self.root/'frozen_v1/catalog.json').read_bytes())
        if self.catalog.manifest_hash!=self.freeze['manifest_hash'] or self.catalog.generation_id!=self.freeze['generation']:raise ValueError('FROZEN_SCOPE_IDENTITY_MISMATCH')
        self.lexical=LexicalIndex(self.root/'lexical_v1.sqlite3')
        self.cache=ProvenanceCache(max_entries=1,max_bytes=32*1024*1024);self.lock=RLock()

    @contextmanager
    def pin(self,scope):
        with self.lock:
            if scope.generation_id!=self.freeze['generation'] or scope.manifest_hash!=self.freeze['manifest_hash']:raise ValueError('SNAPSHOT_PIN_MISMATCH')
            yield

    def search(self,question,scope,channel,limit,deadline):
        if channel!='B':raise ChannelUnavailable('DENSE_NOT_AVAILABLE_NO_RESEARCH_VECTORS')
        record=self.lexical.generation(scope.dataset_id,scope.generation_id)
        hits=self.lexical.search(question,record,limit,{'cik':scope.cik,'filing_ids':scope.eligible_filing_ids})
        verified={};results=[]
        with closing(self.lexical.connect()) as conn:
            for hit in hits:
                row=conn.execute('SELECT d.payload,d.payload_hash,m.source FROM documents d JOIN members m ON m.cid=d.cid WHERE d.cid=? AND m.generation=?',(hit['chunk_id'],scope.generation_id)).fetchone()
                payload=json.loads(row['payload']);frozen=json.loads(row['source'])
                for key in ['raw_path','structured_path','chunks_path']:
                    if not Path(frozen[key]).resolve().is_relative_to(self.root):raise ValueError('RESEARCH_SOURCE_PATH_ESCAPE')
                if digest(payload)!=row['payload_hash'] or frozen['manifest_hash']!=scope.manifest_hash:raise ValueError('RESEARCH_PARENT_HASH_MISMATCH')
                key=frozen['raw_hash']
                if key not in verified:verified[key]=verified_source(frozen,cache=self.cache,generation=scope.generation_id)
                p=verified[key].get(hit['chunk_id'])
                if p is None or p.model_dump(mode='json')!=payload:raise ValueError('PROVENANCE_CHUNK_CONTEXT_MISMATCH')
                results.append(candidate(p,scope,'B',hit['bm25_score']))
        return results

    def evidence_lookup(self,hit):
        # Full source contexts here exceed D2's reviewed cap. Do not pretend
        # a hash-only window is a verified D2 context or award table bonuses.
        return None

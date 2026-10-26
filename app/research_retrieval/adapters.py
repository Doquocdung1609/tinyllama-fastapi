"""Isolated adapters over accepted C retrieval. Never point at owner history."""
from contextlib import contextmanager
import json
import requests
from threading import local
from app.financial_ingestion.schemas import FinancialChunk
from app.financial_index.service import OllamaVectors
from app.research_retrieval.contracts import CandidateV1,ChannelUnavailable
from app.table_evidence.identity import digest


def candidate(parent,scope,channel,score):
    return CandidateV1(chunk_id=parent.chunk_id,generation=scope.generation_id,manifest_hash=scope.manifest_hash,
        cik=parent.metadata['cik'],filing_id=parent.filing_id,parent_json=parent.model_dump_json(),
        payload_hash=digest(parent.model_dump(mode='json')),channel=channel,score=score)


class BoundedResearchVectors(OllamaVectors):
    """Same model/prefix/truncation contract; bounded research I/O only."""
    research_timeout_seconds=30
    def _embed(self,texts):
        from app.config import get_settings
        settings=get_settings()
        response=self.session.post(settings.ollama_base_url+'/api/embed',json={'model':settings.embedding_model,
            'input':texts,'truncate':True,'keep_alive':'5m'},timeout=self.research_timeout_seconds)
        response.raise_for_status();return response.json()['embeddings']


class CSearchAdapter:
    def __init__(self,index):self.index=index;self._request=local()

    @contextmanager
    def pin(self,scope):
        with self.index._query_access():
            record=self.index.lexical.generation(scope.dataset_id,scope.generation_id)
            if record['state']!='READY':raise RuntimeError('INDEX_NOT_READY')
            if sorted(s['manifest']['manifest_hash'] for s in record['metadata']['sources'])!=[scope.manifest_hash]:
                raise ValueError('PINNED_MANIFEST_MISMATCH')
            self._request.generation=scope.generation_id
            try:yield
            finally:self._request.generation=None

    def search(self,question,scope,channel,limit,deadline):
        if getattr(self._request,'generation',None)!=scope.generation_id:raise ValueError('REQUEST_PIN_REQUIRED')
        if channel=='D' and getattr(self.index.provider,'research_timeout_seconds',float('inf'))>deadline:
            raise RuntimeError('DENSE_PROVIDER_TIMEOUT_NOT_BOUNDED')
        try:
            # Already inside C's outer query pin. Nesting its public query
            # guard can deadlock against concurrent cleanup waiting on us.
            r=self.index._search(scope.dataset_id,question,'bm25' if channel=='B' else 'dense',generation=scope.generation_id,
                top_k=limit,candidate_limit=limit,expected_manifests=[scope.manifest_hash],
                filters={'cik':scope.cik,'filing_ids':scope.eligible_filing_ids},allow_degraded=False)
        except requests.RequestException as exc:raise ChannelUnavailable('CHANNEL_NETWORK_UNAVAILABLE') from exc
        except RuntimeError as exc:
            # C wraps Dense exceptions. Preserve fail-closed identity/source
            # failures; only a causal network exception is operational absence.
            if isinstance(exc.__cause__,requests.RequestException):raise ChannelUnavailable('CHANNEL_NETWORK_UNAVAILABLE') from exc
            raise
        if r['generation']!=scope.generation_id or r['manifests']!=[scope.manifest_hash]:raise ValueError('RESPONSE_IDENTITY_MISMATCH')
        results=[]
        for hit in r['results']:
            if hit['provenance_status']!='VERIFIED' or hit['source_manifest_hash']!=scope.manifest_hash:raise ValueError('SOURCE_NOT_VERIFIED')
            p=FinancialChunk.model_validate({k:hit[k] for k in FinancialChunk.model_fields})
            results.append(candidate(p,scope,channel,hit['bm25_score'] if channel=='B' else hit['dense_score']))
        return results


class OwnedLexicalAdapter:
    """B-only research index. Explicitly no Dense/F result is manufactured."""
    def __init__(self,lexical,contexts):
        self.lexical=lexical;self.contexts=tuple(contexts)

    @contextmanager
    def pin(self,scope):
        record=self.lexical.generation(scope.dataset_id,scope.generation_id)
        if record['state']!='READY':raise RuntimeError('INDEX_NOT_READY')
        # Publication of a different active generation cannot change this ID.
        yield

    def search(self,question,scope,channel,limit,deadline):
        if channel!='B':raise ChannelUnavailable('DENSE_NOT_AVAILABLE_IN_LEXICAL_ONLY_RESEARCH')
        record=self.lexical.generation(scope.dataset_id,scope.generation_id)
        hits=self.lexical.search(question,record,limit,{'cik':scope.cik,'filing_ids':scope.eligible_filing_ids})
        result=[]
        for hit in hits:
            parents=[ctx.parent(hit['chunk_id']) for ctx in self.contexts if ctx.binding.generation_id==scope.generation_id and ctx.binding.manifest_hash==scope.manifest_hash]
            parents=[p for p in parents if p is not None]
            if len(parents)!=1:raise ValueError('VERIFIED_PARENT_MEMBERSHIP_MISSING')
            result.append(candidate(parents[0],scope,'B',hit['bm25_score']))
        return result

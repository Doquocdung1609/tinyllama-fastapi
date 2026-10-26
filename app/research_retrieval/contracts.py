"""Versioned opt-in D3 contracts; scores are not confidence probabilities."""
from math import isfinite
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field,model_validator
from app.table_evidence.identity import digest
from app.financial_ingestion.schemas import FinancialChunk

Arm=Literal['B','D','F','R','T','A','AT']


class ChannelUnavailable(RuntimeError):
    """Availability only. Integrity/identity failures must never use this type."""


class Contract(BaseModel):
    model_config=ConfigDict(extra='forbid',frozen=True)


class CandidateV1(Contract):
    chunk_id:str
    generation:str
    manifest_hash:str
    cik:str
    filing_id:str
    parent_json:str=Field(max_length=250000)
    payload_hash:str
    score:float
    channel:Literal['B','D']

    @model_validator(mode='after')
    def coherent(self):
        p=FinancialChunk.model_validate_json(self.parent_json)
        if not isfinite(self.score) or p.chunk_id!=self.chunk_id or p.filing_id!=self.filing_id or p.metadata.get('cik')!=self.cik or digest(p.model_dump(mode='json'))!=self.payload_hash:
            raise ValueError('CANDIDATE_PAYLOAD_IDENTITY_MISMATCH')
        return self


class RankedCandidateV1(Contract):
    candidate:CandidateV1
    rank:int
    score:float
    b_rank:int|None=None
    d_rank:int|None=None
    b_contribution:float=0
    d_contribution:float=0
    row_bonus:float=0
    role_bonus:float=0


class RetrievalResultV1(Contract):
    contract_version:Literal['financial-research-retrieval/v1']='financial-research-retrieval/v1'
    policy_version:Literal['financial-research-policy/v1']='financial-research-policy/v1'
    requested_arm:Arm
    effective_mode:str
    status:Literal['OK','NEEDS_CLARIFICATION','NO_ELIGIBLE_EVIDENCE','UNSUPPORTED','INVALID_INPUT','BLOCKED']
    generation:str|None=None
    manifest_hash:str|None=None
    scope_json:str|None=None
    results:tuple[RankedCandidateV1,...]=()
    b_candidates:tuple[str,...]=()
    d_candidates:tuple[str,...]=()
    trace:tuple[str,...]=()
    failure_code:str|None=None
    timings_ms:tuple[tuple[str,float],...]=()


class PolicyV1(Contract):
    contract_version:Literal['financial-research-policy/v1']='financial-research-policy/v1'
    top_k:int=Field(default=5,ge=1,le=10)
    candidate_limit:Literal[40]=40
    rrf_k:Literal[60]=60
    table_limit:Literal[20]=20
    row_weight:Literal[0.05]=.05
    role_weight:Literal[0.05]=.05
    channel_deadline_seconds:float=Field(default=30,gt=0,le=30)

    def identity(self):return digest(self.model_dump(mode='json'))

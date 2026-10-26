"""Typed D4 operands/claims. No arbitrary expression or free-form number input."""
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field,model_validator
from app.table_evidence.contracts import PeriodContextV1

Operation=Literal['EXTRACT','COMPARE','ABS_CHANGE','PERCENT_CHANGE','PERCENTAGE_POINTS']


class Contract(BaseModel):
    model_config=ConfigDict(extra='forbid',frozen=True,str_max_length=4000)


class NumericRequestV1(Contract):
    contract_version:Literal['financial-numeric-request/v1']='financial-numeric-request/v1'
    operation:Operation
    metric:str=Field(min_length=1,max_length=300)
    cell_ids:tuple[str,...]=Field(min_length=1,max_length=8)
    measurement_basis:str|None=Field(default=None,max_length=80)

    @model_validator(mode='after')
    def bounded(self):
        import re
        if len(set(self.cell_ids))!=len(self.cell_ids) or any(not re.fullmatch('cell_[0-9a-f]{64}',x) for x in self.cell_ids):
            raise ValueError('INVALID_OPERAND_REFERENCES')
        return self


class OperandV1(Contract):
    cell_id:str
    parent_id:str
    parent_payload_hash:str
    raw_value:str
    displayed_value:Decimal
    effective_value:Decimal
    unit:str
    multiplier:Decimal
    sign_representation:str
    period:PeriodContextV1
    measurement_basis:str
    entity_basis:str
    accounting_basis:str
    header_path:tuple[str,...]
    table_id:str
    row:int
    column:int
    source_url:str
    structural_path:str
    filing_id:str


class NumericClaimV1(Contract):
    contract_version:Literal['financial-numeric-claim/v1']='financial-numeric-claim/v1'
    claim_id:str
    operation:Operation
    metric:str
    operands:tuple[OperandV1,...]
    result_values:tuple[Decimal,...]
    unit:str
    formula:str
    rounding_rule:Literal['DECIMAL_CONTEXT_28_HALF_EVEN']='DECIMAL_CONTEXT_28_HALF_EVEN'
    generation:str
    manifest_hash:str
    evidence_bundle_hash:str


class AnswerResultV1(Contract):
    contract_version:Literal['financial-grounded-answer/v1']='financial-grounded-answer/v1'
    status:Literal['SUPPORTED','NEEDS_CLARIFICATION','INSUFFICIENT_EVIDENCE','CONFLICTED_EVIDENCE','UNSUPPORTED_OPERATION','INVALID_INPUT']
    claims:tuple[NumericClaimV1,...]=()
    reasons:tuple[str,...]=()
    warnings:tuple[str,...]=()

    @model_validator(mode='after')
    def coherent(self):
        if (self.status=='SUPPORTED')!=bool(self.claims):raise ValueError('CLAIM_STATUS_MISMATCH')
        return self

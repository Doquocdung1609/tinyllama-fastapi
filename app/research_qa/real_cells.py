"""Research-only deterministic arithmetic on freshly authenticated SEC cells.

This deliberately requires explicit parent and period identities. It cannot
promote an uncertain D1 scope or an unverified D2 cell into a financial answer.
"""
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.table_evidence.real_source import RealCellObservationV1, verified_real_cells
from app.table_evidence.contracts import PeriodContextV1
from app.table_evidence.identity import digest
from app.research_qa.contracts import OperandV1
from app.research_qa.numeric import calculate


class RealCellRequestV1(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    contract_version: Literal['real-sec-cell-request/v1'] = 'real-sec-cell-request/v1'
    parent_id: str = Field(pattern=r'^fin_[0-9a-f]+$', max_length=100)
    cik: str = Field(pattern=r'^[0-9]{10}$')
    accession: str = Field(pattern=r'^[0-9]{10}-[0-9]{2}-[0-9]{6}$')
    table_id: str = Field(pattern=r'^table_[0-9a-f]+$', max_length=100)
    row_label: Literal['net sales'] = 'net sales'
    period_ends: tuple[str, ...] = Field(min_length=1, max_length=2)
    period_months: Literal[3, 6, 9, 12] = 3
    operation: Literal['EXTRACT', 'COMPARE', 'ABS_CHANGE', 'PERCENT_CHANGE'] = 'EXTRACT'

    @model_validator(mode='after')
    def periods_match_operation(self):
        import re
        from datetime import date
        if len(self.period_ends) != (1 if self.operation == 'EXTRACT' else 2):
            raise ValueError('OPERATION_PERIOD_COUNT')
        if len(set(self.period_ends)) != len(self.period_ends):
            raise ValueError('DUPLICATE_PERIOD')
        for end in self.period_ends:
            if not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', end):
                raise ValueError('PERIOD_DATE_SYNTAX')
            date.fromisoformat(end)
        if len(self.period_ends) == 2 and self.period_ends[0] >= self.period_ends[1]:
            raise ValueError('PERIODS_MUST_BE_OLD_THEN_NEW')
        return self


class RealCellAnswerV1(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    contract_version: Literal['real-sec-cell-answer/v1'] = 'real-sec-cell-answer/v1'
    status: Literal['SUPPORTED', 'INSUFFICIENT_EVIDENCE', 'CONFLICTED_EVIDENCE']
    operation: str
    result_values: tuple[Decimal, ...] = ()
    result_unit: str | None = None
    operands: tuple[RealCellObservationV1, ...] = ()
    reason: str | None = None
    formula: str | None = None

    @model_validator(mode='after')
    def coherent(self):
        if self.status == 'SUPPORTED' and (not self.operands or not self.result_values):
            raise ValueError('SUPPORTED_REQUIRES_SOURCE_OPERANDS')
        if self.status != 'SUPPORTED' and (self.operands or self.result_values):
            raise ValueError('ABSTENTION_HAS_NO_CLAIM')
        return self


def answer_from_verified_real_cells(snapshot, request: RealCellRequestV1):
    """Reauthenticate source bytes for every request, then calculate with Decimal."""
    cells = verified_real_cells(snapshot, request.parent_id)
    common = dict(operation=request.operation)
    eligible = [c for c in cells if c.cik == request.cik and c.accession == request.accession
                and c.table_id == request.table_id and c.row_label.casefold() == request.row_label
                and c.period_kind == 'DURATION' and c.period_months == request.period_months
                and c.unit == 'USD' and c.source_status == 'VERIFIED_SOURCE_CELL']
    operands = []
    for end in request.period_ends:
        matches = [c for c in eligible if c.period_end == end]
        if not matches:
            return RealCellAnswerV1(status='INSUFFICIENT_EVIDENCE', reason='EXACT_VERIFIED_CELL_NOT_FOUND', **common)
        if len(matches) != 1:
            return RealCellAnswerV1(status='CONFLICTED_EVIDENCE', reason='MULTIPLE_SOURCE_CELLS_FOR_PERIOD', **common)
        operands.append(matches[0])
    if len(operands) == 2:
        a, b = operands
        if (a.filing_id, a.parent_id, a.table_id, a.row, a.fact_name, a.unit, a.multiplier) != (
            b.filing_id, b.parent_id, b.table_id, b.row, b.fact_name, b.unit, b.multiplier):
            return RealCellAnswerV1(status='CONFLICTED_EVIDENCE', reason='INCOMPATIBLE_SOURCE_OPERANDS', **common)
    typed=[]
    for cell in operands:
        typed.append(OperandV1(cell_id='cell_'+digest(cell.model_dump(mode='json')),
            parent_id=cell.parent_id,parent_payload_hash=cell.parent_payload_hash,
            raw_value=cell.raw_value,displayed_value=cell.value,effective_value=cell.effective_value,
            unit=cell.unit,multiplier=cell.multiplier,
            sign_representation='MINUS' if cell.value<0 else 'NONE',
            period=PeriodContextV1(kind=cell.period_kind,end=cell.period_end,months=cell.period_months,
                                   raw_labels=cell.header_path),
            measurement_basis='BASE_AMOUNT',entity_basis='UNDIMENSIONED_ISSUER',
            accounting_basis='GAAP' if cell.fact_name.casefold().startswith('us-gaap:') else 'NO_EXPLICIT_QUALIFIER',
            header_path=cell.header_path,table_id=cell.table_id,row=cell.row,column=cell.column,
            source_url=cell.source_url,structural_path=cell.structural_path,filing_id=cell.filing_id))
    try:result,unit,formula=calculate(request.operation,typed)
    except ValueError as exc:
        return RealCellAnswerV1(status='INSUFFICIENT_EVIDENCE',reason=str(exc),**common)
    return RealCellAnswerV1(status='SUPPORTED', operation=request.operation, result_values=result,
                            result_unit=unit, operands=tuple(operands), formula=formula)

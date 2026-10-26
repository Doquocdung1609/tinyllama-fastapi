"""Candidate-time derivation: preserve physical cells, never zip sorted periods."""
import json
from decimal import Decimal
from app.financial_ingestion.schemas import FinancialChunk, TableCell
from app.table_evidence.contracts import (
    REPRESENTATION, CellEvidenceV1, ConflictV1, EvidenceValidationResultV1,
    HeaderContextV1, LocatorV1, TableEvidenceV1,
)
from app.table_evidence.identity import canonical, digest
from app.table_evidence.interpretation import period_context, parse_number, measurement, units, exact_effective
from app.table_evidence.source import SourceVerificationContext
from app.table_evidence.bounds import validate_budget


def _locator(cell, table_id):
    loc=cell.source_location
    if loc.row_index!=cell.row or loc.column_index!=cell.column or loc.table_id!=table_id or not loc.structural_path:
        raise ValueError('INCONSISTENT_CELL_LOCATOR')
    return LocatorV1(structural_path=loc.structural_path,source_location_json=loc.canonical(),
        table_id=table_id,row=cell.row,column=cell.column)


def _headers(table, column, row):
    if table is None or not table.row_indices:
        return ()
    end=min(table.row_indices)-1
    result=[]
    for h in sorted(table.cells,key=lambda h:(h.row,h.column)):
        if h.row<=end and h.row<row and h.column<=column<h.column+h.colspan:
            period,reason=period_context([h.text])
            result.append(HeaderContextV1(row=h.row,column=h.column,rowspan=h.rowspan,colspan=h.colspan,
                original_text=h.text,locator=_locator(h,table.table_id),period=period,
                interpretation_status='PARTIAL_CONTEXT' if reason else 'VERIFIED_CONTEXT'))
    return tuple(result)


def _validate_geometry(table):
    occupied=set()
    for c in table.cells:
        if c.row<0 or c.column<0 or not 1<=c.rowspan<=32 or not 1<=c.colspan<=32:
            raise ValueError('UNSUPPORTED_CELL_GEOMETRY')
        _locator(c,table.table_id)
        for r in range(c.row,c.row+c.rowspan):
            for col in range(c.column,c.column+c.colspan):
                if (r,col) in occupied:
                    raise ValueError('OVERLAPPING_SOURCE_CELLS')
                occupied.add((r,col))


def _inline_checks(facts, value, sign, unit, scale, basis):
    conflicts=[]; unresolved=[]
    if len(facts)>1:
        unresolved.append('MULTIPLE_INLINE_FACTS_IN_CELL')
    for fact in facts:
        # These are opaque resource IDs, not an authenticated currency or date.
        if fact.get('contextref'):
            unresolved.append('XBRL_CONTEXT_RESOURCE_NOT_RETAINED')
        if fact.get('unitref'):
            unresolved.append('XBRL_UNIT_RESOURCE_NOT_RETAINED')
        if fact.get('format') and fact['format'].split(':')[-1].casefold() not in {'num-dot-decimal','numdotdecimal'}:
            unresolved.append('UNSUPPORTED_XBRL_FORMAT')
        if fact.get('source_text') and fact['source_text'].strip() and value is not None:
            fv,_,_,_=parse_number(fact['source_text'])
            if fv is None or fv.copy_abs()!=value.copy_abs():
                conflicts.append('INLINE_DISPLAY_VALUE_CONFLICT')
        attr_sign=fact.get('sign')
        if attr_sign not in {None,'','-','+'}:
            unresolved.append('UNSUPPORTED_INLINE_SIGN')
        if value is not None:
            if attr_sign=='-' and sign=='PLUS' or attr_sign=='+' and value<0:
                conflicts.append('INLINE_DISPLAY_SIGN_CONFLICT')
            elif attr_sign=='-' and value>0:
                # An unsigned positive display plus '-' encodes the inline sign once.
                value=value.copy_negate(); sign='INLINE'
        if 'scale' in fact:
            try:
                exp=int(fact['scale'])
                if not -12<=exp<=12:
                    raise ValueError()
                inline_scale=Decimal('1e'+str(exp))
                if scale is not None and scale!=inline_scale:
                    conflicts.append('INLINE_HEADER_SCALE_CONFLICT')
                elif scale is None:
                    unresolved.append('INLINE_SCALE_WITHOUT_VERIFIED_UNIT')
            except ValueError:
                unresolved.append('UNSUPPORTED_INLINE_SCALE')
        name=fact.get('name','').casefold()
        if name:
            # Concept-to-row correspondence is not established by a generic
            # AMOUNT role. Preserve tags but never certify arbitrary concepts.
            unresolved.append('INLINE_CONCEPT_ROW_CORRESPONDENCE_UNVERIFIED')
        if basis=='CARRYING_VALUE' and 'fairvalue' in name or basis=='FAIR_VALUE' and 'carrying' in name:
            conflicts.append('INLINE_HEADER_MEASUREMENT_CONFLICT')
        if basis=='BASIC_EPS' and 'diluted' in name or basis=='DILUTED_EPS' and 'basic' in name:
            conflicts.append('INLINE_HEADER_EPS_CONFLICT')
    return value,sign,conflicts,unresolved


def build_table_evidence(parent_chunk, verification_context=None, representation_version=REPRESENTATION):
    """Pure view over a C row. No context => explicitly unauthenticated derivative.

    VERIFIED_CONTEXT is structural/source correspondence relative to a trusted
    upstream binding, never financial-answer certification. Context must come
    from context_from_snapshot in trusted application code, not request JSON.
    """
    try:
        if representation_version!=REPRESENTATION:
            raise ValueError('UNSUPPORTED_REPRESENTATION')
        if not isinstance(parent_chunk,FinancialChunk):
            raise ValueError('EXPECTED_FINANCIAL_CHUNK')
        validate_budget(parent_chunk)
        encoded=parent_chunk.model_dump_json()
        if len(encoded)>250000:
            raise ValueError('PARENT_SIZE_BUDGET')
        parent=FinancialChunk.model_validate_json(encoded)
        ctx=verification_context
        if ctx is not None and not isinstance(ctx,SourceVerificationContext):
            raise ValueError('EXPECTED_TRUSTED_PROCESS_CONTEXT')
        table=None
        if ctx is not None:
            original=ctx.parent(parent.chunk_id)
            if original is None or original.model_dump()!=parent.model_dump():
                raise ValueError('PARENT_PAYLOAD_MISMATCH')
            table=next((t for t in ctx.filing().tables if t.table_id==parent.source_location.table_id),None)
        if parent.kind!='table':
            return EvidenceValidationResultV1(status='UNSUPPORTED_STRUCTURE',warnings=('NOT_A_TABLE_ROW',))
        m=parent.metadata
        tid=m['table_id']; row=parent.source_location.row_index
        if row is None or row<0 or row!=m['row_index'] or tid!=parent.source_location.table_id:
            raise ValueError('PARENT_COORDINATE_MISMATCH')
        cells=[TableCell.model_validate(c) for c in m.get('cells',[])]
        if len(cells)>256 or any(c.row!=row for c in cells):
            raise ValueError('PARENT_CELL_MEMBERSHIP')
        if not cells:
            return EvidenceValidationResultV1(status='UNSUPPORTED_STRUCTURE',warnings=('NO_PHYSICAL_CELLS_FOR_ROW',))
        if table is not None:
            _validate_geometry(table)
            if [c.model_dump() for c in cells]!=[c.model_dump() for c in table.cells if c.row==row]:
                raise ValueError('SOURCE_ROW_CELL_MISMATCH')
        elif ctx is not None:
            raise ValueError('SOURCE_TABLE_MISSING')
        warnings=list(m.get('extraction_warnings',[]))
        if ctx is None:
            warnings.append('UPSTREAM_SOURCE_AUTHENTICATION_ABSENT')
        if parent.extraction_status!='OK' or m.get('document_status')=='PARTIAL_EXTRACTION':
            warnings.append('PARTIAL_EXTRACTION')
        if table and (table.parent_table_id or 'NESTED_TABLE_PRESERVED_SEPARATELY' in table.extraction_warnings):
            return EvidenceValidationResultV1(status='UNSUPPORTED_STRUCTURE',warnings=('NESTED_TABLE',))
        if m.get('continuation_of'):
            warnings.append('CONTINUATION_CONTEXT_NOT_EXPANDED')
        results=[]
        label=m.get('row_label','')
        for cell in sorted(cells,key=lambda c:(c.row,c.column)):
            locator=_locator(cell,tid)
            headers=_headers(table,cell.column,row)
            labels=[h.original_text for h in headers if h.original_text]
            period,period_reason=period_context(labels)
            repeated_header = table is not None and any(
                min(table.row_indices)<=h.row<row and h.column<=cell.column<h.column+h.colspan
                and (h.is_header or period_context([h.text])[0] is not None)
                for h in table.cells)
            if repeated_header:
                period=None
                period_reason='REPEATED_BODY_HEADER_UNRESOLVED'
            basis=measurement(label,labels)
            value,sign,missing,number_reason=parse_number(cell.text)
            unit,scale,unit_reason=units(cell.text,label,labels,m.get('unit_context'))
            unresolved=[]; conflict_codes=[]
            if period_reason=='CONFLICTING_HEADER_PERIODS':
                conflict_codes.append(period_reason)
            elif period_reason:
                unresolved.append(period_reason)
            if unit_reason and unit_reason.startswith('CONFLICTING'):
                conflict_codes.append(unit_reason)
            elif unit_reason:
                unresolved.append(unit_reason)
            if basis=='CONFLICTED':
                conflict_codes.append('ROW_HEADER_MEASUREMENT_CONFLICT')
            if number_reason:
                if number_reason.startswith('CONFLICTING'):
                    conflict_codes.append(number_reason)
                else:
                    unresolved.append(number_reason)
            value,sign,ix_conflicts,ix_unresolved=_inline_checks(cell.numeric_facts,value,sign,unit,scale,basis)
            conflict_codes+=ix_conflicts; unresolved+=ix_unresolved
            if missing!='NUMBER':
                unresolved.append('NO_NUMERIC_OBSERVATION')
            if ctx is None:
                unresolved.append('UNAUTHENTICATED_SOURCE')
            if cell.column==min(c.column for c in cells) and missing=='NUMBER':
                unresolved.append('NUMERIC_ROW_LABEL_NOT_AN_OBSERVATION')
            if cell.colspan>1 or cell.rowspan>1:
                unresolved.append('MERGED_BODY_CELL_NOT_MULTIPLE_OBSERVATIONS')
            if warnings:
                unresolved.append('PARENT_EXTRACTION_OR_CONTEXT_WARNING')
            conflicts=tuple(ConflictV1(code=code,row=row,column=cell.column,detail=code) for code in sorted(set(conflict_codes)))
            status='CONFLICTED_CONTEXT' if conflicts else 'PARTIAL_CONTEXT' if unresolved else 'VERIFIED_CONTEXT'
            effective=exact_effective(value,scale) if status=='VERIFIED_CONTEXT' else None
            entity='CONSOLIDATED' if 'consolidated' in (label+' '+(m.get('statement_title') or '')).casefold() else 'SEGMENT_LABELED' if re_segment(label) else 'UNKNOWN'
            body=dict(table_id=tid,row=row,column=cell.column,rowspan=cell.rowspan,colspan=cell.colspan,
                original_text=cell.text,raw_numeric_string=cell.text if missing=='NUMBER' else None,value=value,
                sign_representation=sign,missing_kind=missing,header_path=headers,period=period,
                measurement_basis=basis,entity_basis=entity,unit=unit,multiplier=scale,effective_value=effective,
                locator=locator,inline_attributes=tuple(canonical(f) for f in cell.numeric_facts),footnote_references=(),
                status=status,unresolved_fields=tuple(sorted(set(unresolved))),conflicts=conflicts)
            # Hash all semantics, not only coordinates; source generation binds identity.
            provisional=CellEvidenceV1(evidence_id='',**body)
            cid=digest({'parent':digest(parent.model_dump(mode='json')),'generation':ctx.binding.generation_id if ctx else None,
                        'manifest':ctx.binding.manifest_hash if ctx else None,'version':REPRESENTATION,
                        'cell':provisional.model_dump(mode='json',exclude={'evidence_id'})})
            results.append(provisional.model_copy(update={'evidence_id':'cell_'+cid}))
        # Text labels remain evidence, but are not counted as failed numeric facts.
        observations=[c for c in results if c.missing_kind!='TEXT' or c.column!=min(x.column for x in results)]
        status='CONFLICTED_CONTEXT' if any(c.status=='CONFLICTED_CONTEXT' for c in results) else 'PARTIAL_CONTEXT' if not observations or any(c.status!='VERIFIED_CONTEXT' for c in observations) else 'VERIFIED_CONTEXT'
        body=dict(parent_chunk_id=parent.chunk_id,parent_payload_hash=digest(parent.model_dump(mode='json')),
            original_parent_text=parent.text,original_parent_json=canonical(parent.model_dump(mode='json')),
            filing_id=parent.filing_id,document_version=parent.document_version,cik=m['cik'],accession=m['accession_number'],
            form=m['form_type'],filing_date=m.get('filing_date'),source_url=m['source_url'],parser_version=m['parser_version'],
            chunker_version=m['chunker_version'],table_id=tid,caption=m.get('table_title'),section=m.get('section'),
            row_label=label,row_group=m.get('row_context'),original_row=row,original_locator_json=parent.source_location.canonical(),
            footnotes=tuple(m.get('footnotes',[])),footnote_locations=tuple(canonical(x) for x in m.get('footnote_locations',[])),
            context_locations=tuple(canonical(x) for x in m.get('context_locations',[])),continuation_of=m.get('continuation_of'),
            extraction_warnings=tuple(sorted(set(warnings))),parent_provenance='MATCHED_UPSTREAM_BINDING' if ctx else 'UNAUTHENTICATED',
            source_generation=ctx.binding.generation_id if ctx else None,manifest_hash=ctx.binding.manifest_hash if ctx else None,
            cells=tuple(results),status=status)
        provisional=TableEvidenceV1(evidence_hash='',**body)
        return EvidenceValidationResultV1(status=status,evidence=provisional.model_copy(update={
            'evidence_hash':digest(provisional.model_dump(mode='json',exclude={'evidence_hash'}))}),warnings=tuple(sorted(set(warnings))))
    except (ValueError,TypeError,KeyError,OverflowError,RecursionError):
        return EvidenceValidationResultV1(status='INVALID_SOURCE',warnings=('INVALID_PARENT_OR_SOURCE_CONTEXT',))


def re_segment(label):
    import re
    return bool(re.search(r'\bsegment\b',label,re.I))

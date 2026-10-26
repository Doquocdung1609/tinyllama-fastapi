"""Reconstruct evidence before trusting cells, numbers, claims or citations."""
from app.table_evidence import build_evidence_bundle
from app.table_evidence.source import SourceVerificationContext
from app.table_evidence.bounds import validate_budget
from app.table_evidence.contracts import EvidenceBundleV1
from app.table_evidence.identity import digest,canonical
import re
from app.research_qa.contracts import NumericRequestV1,OperandV1,NumericClaimV1,AnswerResultV1
from app.research_qa.numeric import calculate


def answer_from_bundle(request,bundle,context):
    def stop(status,reason):return AnswerResultV1(status=status,reasons=(reason,))
    try:
        validate_budget(request);validate_budget(bundle)
        if not isinstance(request,NumericRequestV1) or not isinstance(bundle,EvidenceBundleV1):return stop('INVALID_INPUT','TYPED_REQUEST_AND_BUNDLE_REQUIRED')
        request=NumericRequestV1.model_validate(request.model_dump())
        if not isinstance(context,SourceVerificationContext):return stop('INSUFFICIENT_EVIDENCE','TRUSTED_SOURCE_CONTEXT_REQUIRED')
        if bundle.source_generation!=context.binding.generation_id or bundle.manifest_hash!=context.binding.manifest_hash:return stop('CONFLICTED_EVIDENCE','BUNDLE_SOURCE_IDENTITY_MISMATCH')
        if digest(bundle.model_dump(mode='json',exclude={'evidence_hash'}))!=bundle.evidence_hash:return stop('CONFLICTED_EVIDENCE','DERIVED_BUNDLE_TAMPERED')
        parents=[context.parent(cid) for cid in bundle.selected_parent_ids]
        if any(p is None for p in parents):return stop('CONFLICTED_EVIDENCE','PARENT_MEMBERSHIP_MISSING')
        expected=build_evidence_bundle(parents,context,expand=bool(bundle.expanded_parent_ids))
        if expected.evidence_hash!=bundle.evidence_hash:return stop('CONFLICTED_EVIDENCE','DERIVATION_RECONSTRUCTION_MISMATCH')
        if expected.completeness_status=='CONFLICTED_CONTEXT':return stop('CONFLICTED_EVIDENCE','D2_CONTEXT_CONFLICT')
        if expected.completeness_status!='VERIFIED_CONTEXT':return stop('INSUFFICIENT_EVIDENCE','D2_CONTEXT_INCOMPLETE')
        all_cells={}
        for result in expected.results:
            e=result.evidence
            for c in e.cells:all_cells[c.evidence_id]=(e,c)
        operands=[]
        for cid in request.cell_ids:
            if cid not in all_cells:return stop('INSUFFICIENT_EVIDENCE','OPERAND_NOT_IN_BUNDLE')
            e,c=all_cells[cid]
            if c.status!='VERIFIED_CONTEXT' or c.value is None or c.effective_value is None or c.period is None:
                return stop('INSUFFICIENT_EVIDENCE','OPERAND_CONTEXT_UNVERIFIED')
            if e.row_label.casefold().strip()!=request.metric.casefold().strip():return stop('NEEDS_CLARIFICATION','METRIC_ROW_MISMATCH')
            if request.measurement_basis and c.measurement_basis!=request.measurement_basis:return stop('CONFLICTED_EVIDENCE','MEASUREMENT_BASIS_MISMATCH')
            labels=' / '.join(h.original_text for h in c.header_path).casefold()
            if re.search(r'\bsegment\b',labels+' '+e.row_label.casefold()):
                return stop('INSUFFICIENT_EVIDENCE','SEGMENT_DIMENSION_NOT_INDEPENDENTLY_RESOLVED')
            accounting='NON_GAAP' if re.search(r'non[ -]gaap',labels) else 'ADJUSTED' if 'adjusted' in labels else 'GAAP' if re.search(r'\bgaap\b',labels) else 'NO_EXPLICIT_QUALIFIER'
            operands.append(OperandV1(cell_id=cid,parent_id=e.parent_chunk_id,parent_payload_hash=e.parent_payload_hash,
                raw_value=c.original_text,displayed_value=c.value,effective_value=c.effective_value,unit=c.unit,multiplier=c.multiplier,
                sign_representation=c.sign_representation,period=c.period,measurement_basis=c.measurement_basis,entity_basis=c.entity_basis,
                accounting_basis=accounting,header_path=tuple(canonical({'row':h.row,'column':h.column,'text':h.original_text,'locator':h.locator.structural_path}) for h in c.header_path),
                table_id=c.table_id,row=c.row,column=c.column,source_url=e.source_url,structural_path=c.locator.structural_path,filing_id=e.filing_id))
        try:values,unit,formula=calculate(request.operation,operands)
        except ValueError as exc:return stop('UNSUPPORTED_OPERATION',str(exc))
        claim=NumericClaimV1(claim_id='',operation=request.operation,metric=request.metric,operands=tuple(operands),result_values=values,
            unit=unit,formula=formula,generation=bundle.source_generation,manifest_hash=bundle.manifest_hash,evidence_bundle_hash=bundle.evidence_hash)
        claim=claim.model_copy(update={'claim_id':'claim_'+digest(claim.model_dump(mode='json',exclude={'claim_id'}))})
        return AnswerResultV1(status='SUPPORTED',claims=(claim,),warnings=('SUPPORTED_ONLY_RELATIVE_TO_AUTHENTICATED_UPSTREAM_SOURCE_BINDING',))
    except (ValueError,TypeError,KeyError,RecursionError):return stop('INVALID_INPUT','INVALID_NUMERIC_REQUEST_OR_EVIDENCE')


def verify_claim(request,claim,bundle,context):
    expected=answer_from_bundle(request,bundle,context)
    return expected.status=='SUPPORTED' and len(expected.claims)==1 and expected.claims[0].model_dump(mode='json')==claim.model_dump(mode='json')

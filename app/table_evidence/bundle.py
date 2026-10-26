"""Bounded, optional same-table row-group expansion. No ranking or I/O."""
from app.financial_query.contracts import ResolvedScopeV1, Status
from app.table_evidence.builder import build_table_evidence
from app.table_evidence.contracts import EvidenceBundleV1
from app.table_evidence.identity import digest
from app.table_evidence.source import SourceVerificationContext


def build_evidence_bundle(verified_candidates, verification_context, scope=None, expansion_budget=20, expand=False):
    """Preserve selected order; at most5 selected and20 total parents.

    Only an immediate same-table row-group, already in authenticated source,
    can add a parent. Footnotes/headers are embedded source context, not fetched.
    Continuation across tables stays unresolved. Explicit periods disable row
    expansion; out-of-scope cells are preserved raw but never accepted as scope.
    """
    if not isinstance(verification_context,SourceVerificationContext):
        raise ValueError('TRUSTED_CONTEXT_REQUIRED')
    if not isinstance(verified_candidates,(list,tuple)) or not 1<=len(verified_candidates)<=5:
        raise ValueError('CANDIDATE_BUDGET')
    if isinstance(expansion_budget,bool) or not isinstance(expansion_budget,int) or not len(verified_candidates)<=expansion_budget<=20:
        raise ValueError('EXPANSION_BUDGET')
    ctx=verification_context; parents=list(verified_candidates); warnings=[]
    ids=[p.chunk_id for p in parents]
    if len(ids)!=len(set(ids)):
        raise ValueError('DUPLICATE_CANDIDATE')
    if scope is not None:
        if not isinstance(scope,ResolvedScopeV1):
            raise ValueError('TYPED_D1_SCOPE_REQUIRED')
        scope=ResolvedScopeV1.model_validate(scope.model_dump())
        if scope.status!=Status.RESOLVED or scope.generation_id!=ctx.binding.generation_id or scope.manifest_hash!=ctx.binding.manifest_hash or scope.dataset_id!=ctx.binding.dataset_id:
            raise ValueError('SCOPE_IDENTITY_MISMATCH')
    results=[]
    for p in parents:
        result=build_table_evidence(p,ctx)
        if result.status=='INVALID_SOURCE':
            raise ValueError('UNVERIFIED_BUNDLE_MEMBER')
        if scope is not None:
            if p.filing_id not in scope.eligible_filing_ids or p.metadata['cik']!=scope.cik:
                raise ValueError('OUTSIDE_EXPLICIT_SCOPE')
            if scope.requested_periods:
                # Refuse an apparent scope guarantee when cell-level period
                # does not exactly match every displayed numeric observation.
                wanted={(v.kind,v.year,v.quarter,str(v.end) if v.end else None,v.months) for v in scope.requested_periods}
                for c in result.evidence.cells if result.evidence else ():
                    if c.value is not None and (c.period is None or (c.period.kind,c.period.year,c.period.quarter,c.period.end,c.period.months) not in wanted):
                        raise ValueError('CELL_PERIOD_OUTSIDE_EXPLICIT_SCOPE')
        results.append(result)
    expanded=[]
    if expand and (scope is None or not scope.requested_periods):
        for p in verified_candidates:
            group=p.metadata.get('row_context')
            matches=[]
            if group:
                for identifier,_ in ctx.parents:
                    candidate=ctx.parent(identifier)
                    if candidate.kind=='table' and candidate.filing_id==p.filing_id and candidate.source_location.table_id==p.source_location.table_id and candidate.source_location.row_index==p.source_location.row_index-1 and candidate.metadata.get('row_label')==group:
                        matches.append(candidate)
            if len(matches)==1 and matches[0].chunk_id not in ids:
                if len(parents)>=expansion_budget:
                    warnings.append('EXPANSION_BUDGET_REACHED'); continue
                candidate=matches[0]; results.append(build_table_evidence(candidate,ctx)); parents.append(candidate)
                ids.append(candidate.chunk_id); expanded.append(candidate.chunk_id)
            elif group:
                warnings.append('ROW_GROUP_REFERENCE_NOT_UNIQUELY_MAPPED')
    if any(p.metadata.get('continuation_of') for p in parents):
        warnings.append('CONTINUATION_NOT_EXPANDED')
    statuses=[r.status for r in results]
    status=next((s for s in ['INVALID_SOURCE','UNSUPPORTED_STRUCTURE','CONFLICTED_CONTEXT','PARTIAL_CONTEXT'] if s in statuses),'VERIFIED_CONTEXT')
    body=dict(source_generation=ctx.binding.generation_id,manifest_hash=ctx.binding.manifest_hash,
        selected_parent_ids=tuple(p.chunk_id for p in verified_candidates),expanded_parent_ids=tuple(expanded),
        results=tuple(results),completeness_status=status,warnings=tuple(sorted(set(warnings))))
    bundle=EvidenceBundleV1(evidence_hash='',**body)
    return bundle.model_copy(update={'evidence_hash':digest(bundle.model_dump(mode='json',exclude={'evidence_hash'}))})

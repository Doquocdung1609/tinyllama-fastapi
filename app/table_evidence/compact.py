"""Optional presentation derivative; original parent remains in full evidence.

No ranker consumes this view. A compact view alone is not a complete source or
an authenticated token: resolve its parent/hash through the full verified bundle.
"""
def compact_view(evidence):
    return {
        'representation_version':evidence.representation_version,
        'evidence_hash':evidence.evidence_hash,'parent_chunk_id':evidence.parent_chunk_id,
        'parent_payload_hash':evidence.parent_payload_hash,'manifest_hash':evidence.manifest_hash,
        'source_generation':evidence.source_generation,'filing_id':evidence.filing_id,
        'table_id':evidence.table_id,'row':evidence.original_row,'row_label':evidence.row_label,
        'status':evidence.status,'cells':[
            {'id':c.evidence_id,'row':c.row,'column':c.column,'raw':c.original_text,
             'locator':c.locator.structural_path,'headers':[(h.row,h.column,h.original_text) for h in c.header_path],
             'period':c.period.model_dump(mode='json') if c.period else None,
             'value':str(c.value) if c.value is not None else None,'unit':c.unit,
             'multiplier':str(c.multiplier) if c.multiplier is not None else None,
             'measurement':c.measurement_basis,'status':c.status,
             'unresolved':c.unresolved_fields,'conflicts':[v.code for v in c.conflicts]}
            for c in evidence.cells],
        'footnotes':evidence.footnotes,'warnings':evidence.extraction_warnings,
    }

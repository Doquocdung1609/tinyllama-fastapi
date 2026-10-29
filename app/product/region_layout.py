"""Recover short source-table fragments split across adjacent embedded images."""
from app.product.pdf_extract import _lines,table_candidates
from app.product.query_intent import metric_matches

VERSION='TABLE_LAYOUT_V3R_REGIONS_V2_FRAGMENTS'

def rows_with_fragments(saved,number):
    rows=list(saved.get('tables',[]));regions=saved.get('regions',[])
    for region in regions:
        if region.get('kind')!='TEXT_IMAGE':continue
        box=region['box'];neighbors=[]
        for other in regions:
            if other.get('kind')!='TABLE_IMAGE_CANDIDATE':continue
            b=other['box'];overlap=max(0,min(box[2],b[2])-max(box[0],b[0]))
            gap=max(0,box[1]-b[3],b[1]-box[3])
            if overlap>=.8*min(box[2]-box[0],b[2]-b[0]) and gap<=30:neighbors.append(other)
        if not neighbors:continue
        words=[w for line in saved['lines'] for w in line['words'] if w.get('region_id')==region['id']]
        lines=_lines(words);candidates=table_candidates(lines,number,saved['engine'].get('correction_clockwise',0))
        for i,row in enumerate(candidates):
            # Sparse dates/logos/signatures are not enough:require financial source label,
            # two actual amount cells and a neighboring image already containing a table.
            if not metric_matches(row['row_label']) or sum(bool(c['text']) for c in row['cells'])<2:continue
            if any(old['box']==row['box'] for old in rows):continue
            row.update(id=f'p{number}-{region["id"]}-fragment-r{i}',table_id=f'p{number}-{region["id"]}-fragment',region_id=region['id'],source_region=box,
                layout_basis='SOURCE_FINANCIAL_LABEL_TWO_AMOUNTS_ADJACENT_TABLE_IMAGE',verification='NUMERIC_EVIDENCE_UNVERIFIED',source_sha256=saved.get('source_sha256'),page=number)
            for cell in row['cells']:cell.update(source='PRESERVED_CHECKPOINT_WORDS',financial_evidence_status='FINANCIAL_EVIDENCE_REVIEW_PENDING')
            rows.append(row)
    return rows

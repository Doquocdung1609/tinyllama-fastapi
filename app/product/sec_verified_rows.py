"""Collapse repeated, independently authenticated facts; retain real conflicts."""
import re

def collapse_identical(eligible):
    if len(eligible)<2:return eligible
    def signature(item):
        return tuple(sorted((c.cik,c.filing_id,c.raw_sha256,c.row_label.casefold(),c.period_kind,c.period_start or '',c.period_end,
            c.period_months or 0,c.unit,str(c.multiplier),str(c.effective_value)) for c in item[2]))
    if len({signature(item) for item in eligible})!=1:return eligible
    def preference(item):
        title=str(item[1].metadata.get('statement_title',''))
        primary=bool(re.search(r'consolidated.*(?:statements?|balance)|(?:statements?|balance).*consolidated',title,re.I))
        return not primary,item[0],item[1].chunk_id
    return [min(eligible,key=preference)]

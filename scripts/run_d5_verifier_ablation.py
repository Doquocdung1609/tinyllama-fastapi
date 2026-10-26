"""Offline synthetic mutation ablation; forged drafts are never API answers."""
import json
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from app.research_qa.backend import DemoResearchBackend
from app.research_qa.contracts import NumericRequestV1
from app.research_qa.verifier import answer_from_bundle,verify_claim
from app.table_evidence import build_table_evidence,build_evidence_bundle

def main():
    with TemporaryDirectory() as d:
        demo=DemoResearchBackend(Path(d)/'demo');context=demo.context
        for identifier,_ in context.binding.parent_hashes:
            parent=context.parent(identifier)
            if parent.kind!='table':continue
            evidence=build_table_evidence(parent,context).evidence
            if evidence and evidence.row_label=='Net sales':break
        else:raise ValueError('FIXTURE_SOURCE_ROW_MISSING')
        cell=next(c for c in evidence.cells if c.period and c.period.year==2025)
        bundle=build_evidence_bundle([parent],context)
        request=NumericRequestV1(operation='EXTRACT',metric='Net sales',cell_ids=(cell.evidence_id,))
        original=answer_from_bundle(request,bundle,context).claims[0]
        operand=original.operands[0]
        variants={'authentic':original,
            'forged_number':original.model_copy(update={'result_values':(Decimal('999'),)}),
            'forged_unit':original.model_copy(update={'unit':'USD_PER_SHARE'}),
            'forged_period':original.model_copy(update={'operands':(operand.model_copy(update={'period':operand.period.model_copy(update={'year':2099})}),)}),
            'forged_locator':original.model_copy(update={'operands':(operand.model_copy(update={'structural_path':'/document[1]/fake[1]'}),)}),
            'forged_generation':original.model_copy(update={'generation':'f'*64})}
        rows=[{'variant':name,'known_authentic':name=='authentic','without_verifier_accepted':True,
               'with_verifier_accepted':verify_claim(request,claim,bundle,context)} for name,claim in variants.items()]
    output={'identity':'d5-synthetic-verifier-ablation/v1','source_type':'SYNTHETIC_DEMO',
        'same_frozen_source_bundle_and_candidates':True,'unverified_drafts_exposed_to_api':False,
        'known_forgery_count':5,'forgeries_rejected_with_verifier':sum(not r['with_verifier_accepted'] for r in rows if not r['known_authentic']),
        'forgeries_accepted_without_verifier':sum(r['without_verifier_accepted'] for r in rows if not r['known_authentic']),
        'authentic_accepted_with_verifier':rows[0]['with_verifier_accepted'],
        'interpretation':'Deterministic mutation rejection on one synthetic bundle only; not LLM hallucination or real SEC QA accuracy',
        'rows':rows}
    path=Path('docs/topic3/milestone_d/autonomous_execution/D5_VERIFIER_ABLATION_v1.json')
    with path.open('x',encoding='utf-8') as f:json.dump(output,f,indent=2)
    print(json.dumps(output,indent=2))

if __name__=='__main__':main()

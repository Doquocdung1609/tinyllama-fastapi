"""Attach clearly labelled AI proposals to a new human-review input version."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def run(base: Path, ai_ledger: Path, ai_manifest: Path, out: Path) -> dict:
    if out.exists():
        raise FileExistsError(out)
    dataset = json.loads(base.read_text(encoding='utf-8'))
    rows = {x['question_id']:x for x in
            (json.loads(line) for line in ai_ledger.read_text(encoding='utf-8').splitlines())}
    manifest = json.loads(ai_manifest.read_text(encoding='utf-8'))
    if len(rows) != 94 or manifest['ledger_sha256'] != hashlib.sha256(ai_ledger.read_bytes()).hexdigest():
        raise ValueError('AI-only ledger integrity changed')
    if len(dataset['records']) != 94 or {x['question_id'] for x in dataset['records']} != set(rows):
        raise ValueError('Frozen human queue identity mismatch')
    for record in dataset['records']:
        ai = rows[record['question_id']]
        if ai['source_sha256'] != record['source_sha256'] or ai['accession'] != record['accession']:
            raise ValueError('AI/source evidence mismatch')
        record.update(ai_technical_label=ai['technical_label'],
                      ai_reason=ai['reason'], ai_limitation=ai['counterexample_or_limitation'],
                      ai_provenance='AI_ASSISTED_SOURCE_FIRST_NOT_HUMAN_GOLD')
    dataset['schema'] = 'g3t_human_review_input_with_ai_proposals/v1'
    dataset['g3t_ai_manifest_sha256'] = hashlib.sha256(ai_manifest.read_bytes()).hexdigest()
    dataset['g3t_ai_proposals_are_human_approvals'] = False
    out.write_text(json.dumps(dataset, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    return {'questions':94, 'sha256':hashlib.sha256(out.read_bytes()).hexdigest()}


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('base','ai_ledger','ai_manifest','out'):
        p.add_argument('--'+name.replace('_','-'),type=Path,required=True)
    print(json.dumps(run(**vars(p.parse_args())),indent=2))

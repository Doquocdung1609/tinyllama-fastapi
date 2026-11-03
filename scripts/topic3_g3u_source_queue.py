"""Source-only blind original-chunk queue; explicitly not a ranked union."""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import random

from scripts.topic3_g3u_pool import frozen_inputs, sha, validate_registry


def run(registry: Path, protocol: Path, questions: Path, corpus_zip: Path,
        sources: Path, c1_ledger: Path, out: Path) -> dict:
    if out.exists():
        raise FileExistsError(out)
    rules = validate_registry(registry, protocol, questions)
    chunks, prompts, source_map = frozen_inputs(corpus_zip, questions, sources, c1_ledger, rules)
    c1 = {r['question_id']: r for r in
          (json.loads(s) for s in c1_ledger.read_text(encoding='utf-8').splitlines())}
    by_acc = defaultdict(list)
    for chunk in chunks.values():
        by_acc[chunk['document_id'].split('_')[-1]].append(chunk)
    rows = []
    for qid in sorted(prompts):
        target = c1[qid]['accession']
        source = source_map[target]
        for chunk in sorted(by_acc[target], key=lambda x: x['chunk_id']):
            body = chunk['text']
            rows.append({'schema': 'g3u_source_audit_blind_original_chunk/v1',
                         'question_id': qid, 'question': prompts[qid],
                         'chunk_id': chunk['chunk_id'], 'original_text': body,
                         'original_text_sha256': sha(body.encode('utf-8')),
                         'original_record_text_hash': chunk['text_hash'],
                         'chunk_accession': target, 'chunk_issuer': chunk['ticker'],
                         'chunk_section': chunk.get('section'),
                         'source_url': source['source_url'],
                         'source_sha256': source['sha256'],
                         'queue_origin': 'STATIC_TARGET_FILING_SOURCE_AUDIT_NOT_RANKED',
                         'human_decision': None, 'ai_qrel_proposal': None})
    random.Random(rules['blind_seed']).shuffle(rows)
    out.mkdir(parents=True)
    queue_path = out / 'G3U_SOURCE_AUDIT_BLIND_POOL.jsonl'
    queue_path.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows), encoding='utf-8')
    manifest = {'schema': 'g3u_source_audit_queue_manifest/v1',
                'status': 'SOURCE_AUDIT_QUEUE_NOT_RANKED_POOL',
                'question_count': 94, 'unique_blind_pairs': len(rows),
                'blind_sha256': sha(queue_path.read_bytes()),
                'source_only_target_filing': True,
                'ranked_pool_generated': False, 'off_target_retrieval_coverage': 'NOT_ASSESSED',
                'retrieval_quality_scoring_allowed': False,
                'frozen_corpus_sha256': rules['frozen_corpus_sha256']}
    (out / 'G3U_SOURCE_AUDIT_QUEUE_MANIFEST.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')
    return manifest


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for n in ('registry','protocol','questions','corpus_zip','sources','c1_ledger','out'):
        p.add_argument('--'+n.replace('_','-'), type=Path, required=True)
    print(json.dumps(run(**vars(p.parse_args())), indent=2))

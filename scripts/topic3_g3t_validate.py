"""Fail-closed G3T ledger/qrel gate audit and synthetic evaluation dry run."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import random
import statistics

from scripts.topic3_v7a_g3s_review_tool import verify_events


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical(data: dict) -> bytes:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')


def rows(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x]


def verify_ai_chain(ledger: list[dict], policy_sha: str, c1_sha: str) -> None:
    previous, ids = 'GENESIS', set()
    for record in ledger:
        body = {k:v for k,v in record.items() if k != 'record_sha256'}
        qid = record['question_id']
        if (qid in ids or record['previous_record_sha256'] != previous or
                sha(canonical(body)) != record['record_sha256'] or
                record['reviewer_type'] != 'AI_ASSISTED_SOURCE_FIRST' or
                record['human_approval_status'] != 'PENDING' or
                record['protocol_sha256'] != policy_sha or record['c1_ledger_sha256'] != c1_sha or
                'human_interaction_ack' in record):
            raise ValueError(f'AI adjudication integrity failed at {qid}')
        ids.add(qid)
        previous = record['record_sha256']
    if len(ids) != 94:
        raise ValueError('AI adjudication must contain 94 unique IDs')


def verify_human_import(events_path: Path, dataset_path: Path, ai_ledger_path: Path) -> dict:
    if events_path.resolve() == ai_ledger_path.resolve():
        raise ValueError('AI and human event paths must never coincide')
    dataset = json.loads(dataset_path.read_text(encoding='utf-8'))
    expected_sha = sha(dataset_path.read_bytes())
    source = {x['question_id']: x for x in dataset['records']}
    events = verify_events(events_path)
    event_ids = set()
    for e in events:
        if (e.get('event_id') in event_ids or not e.get('event_id') or
                e.get('evidence_sha256') != expected_sha or e.get('question_id') not in source or
                e.get('decision') not in {'APPROVE','REJECT','AMBIGUOUS','REQUEST_CORRECTION','EXCLUDE'} or
                e.get('reviewer_type') == 'AI_ASSISTED_SOURCE_FIRST' or
                e.get('schema') == 'g3t_ai_source_adjudication/v1'):
            raise ValueError('Human event import failed identity/version/schema validation')
        event_ids.add(e['event_id'])
    return {'events': len(events), 'approvals': sum(e['decision']=='APPROVE' for e in events),
            'identity_assurance': 'SELF_DECLARED_NOT_CRYPTOGRAPHICALLY_VERIFIED'}


def synthetic_cluster_bootstrap(seed: int = 20261103, replicates: int = 1000) -> dict:
    """Fixture only: no G2 questions, qrels or ranking output are accessed."""
    fixture = {'filing_1': [1,1], 'filing_2': [1,0],
               'filing_3': [0,0], 'filing_4': [1,1]}
    clusters = list(fixture)
    rng = random.Random(seed)
    means = []
    for _ in range(replicates):
        chosen = [rng.choice(clusters) for _ in clusters]
        values = [v for name in chosen for v in fixture[name]]
        means.append(statistics.mean(values))
    means.sort()
    return {'fixture': 'SYNTHETIC_FOUR_FILINGS_EIGHT_PAIRS_NOT_G2',
            'seed': seed, 'replicates': replicates,
            'mean': statistics.mean(v for values in fixture.values() for v in values),
            'clustered_95pct_interval': [means[int(.025*replicates)], means[int(.975*replicates)-1]]}


def run(c1_path: Path, c2_path: Path, c3_dir: Path, policy_path: Path,
        review_dataset: Path, human_events: Path, out: Path) -> dict:
    if out.exists():
        raise FileExistsError(out)
    policy_sha = sha(policy_path.read_bytes())
    c1, c2 = rows(c1_path), rows(c2_path)
    if len(c1) != 94 or len({x['question_id'] for x in c1}) != 94:
        raise ValueError('C1 94-ID integrity failed')
    verify_ai_chain(c2, policy_sha, sha(c1_path.read_bytes()))
    if {x['question_id'] for x in c1} != {x['question_id'] for x in c2}:
        raise ValueError('C1/C2 question set mismatch')
    human = verify_human_import(human_events, review_dataset, c2_path)
    provenance = rows(c3_dir / 'G3T_C3_ORIGINAL_CHUNK_PROVENANCE.jsonl')
    chunks = {x['chunk_id']:x for x in provenance}
    if len(provenance) != 8670 or len(chunks) != 8670:
        raise ValueError('Original chunk provenance incomplete')
    qrels = rows(c3_dir / 'G3T_C3_QRELS_PROVISIONAL.jsonl')
    qrel_keys = set()
    grades = Counter()
    by_question = {x['question_id']:x for x in c1}
    for q in qrels:
        key = q['question_id'], q['chunk_id']
        if key in qrel_keys or q['question_id'] not in by_question or q['chunk_id'] not in chunks:
            raise ValueError('Qrel invented or duplicate original chunk ID')
        qrel_keys.add(key)
        if (q['grade'] not in {'EXACT','PARTIAL','NONE','UNJUDGED','DISPUTED','SOURCE_INSUFFICIENT'} or
                q['human_certified'] is not False or
                (q['grade'] in {'UNJUDGED','DISPUTED','SOURCE_INSUFFICIENT'}) != (q['graded_value'] is None) or
                q['original_text_sha256'] != chunks[q['chunk_id']]['original_text_sha256'] or
                q['source_sha256'] != by_question[q['question_id']]['source_sha256']):
            raise ValueError('Qrel grade/source/text hash or unknown-state invalid')
        grades[q['grade']] += 1
    if not qrels or len({x['question_id'] for x in qrels}) != 94:
        raise ValueError('Qrel target filing coverage incomplete')
    statuses = {'tier_A_ai_provisional': 'BLOCKED' if not grades['EXACT'] else 'PARTIAL',
                'tier_H_human_certified': 'BLOCKED' if not human['approvals'] else 'PARTIAL',
                'one_shot_ai_provisional': 'ONE_SHOT_AI_PROVISIONAL_NOT_RUN',
                'human_final_benchmark': 'NOT_RUN'}
    result = {'schema': 'g3t_c3_benchmark_precheck/v1', 'question_count': 94,
              'original_chunks': 8670, 'qrel_pairs': len(qrels), 'qrel_grades': dict(grades),
              'human': human, 'status': statuses, 'reasons': [
                  'No EXACT original single-chunk judgments; static row/value co-occurrence is at most PARTIAL.',
                  'Full six-author/FAITH-R depth-20 ranked pool has not been generated or judged.',
                  'No genuine human approval; source facts and AI labels are not human gold.'],
              'synthetic_dry_run': synthetic_cluster_bootstrap(),
              'c1_sha256': sha(c1_path.read_bytes()), 'c2_sha256': sha(c2_path.read_bytes()),
              'qrels_sha256': sha((c3_dir / 'G3T_C3_QRELS_PROVISIONAL.jsonl').read_bytes()),
              'protocol_sha256': policy_sha}
    out.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('c1_path','c2_path','c3_dir','policy_path','review_dataset','human_events','out'):
        p.add_argument('--'+name.replace('_','-'), type=Path, required=True)
    print(json.dumps(run(**vars(p.parse_args())), indent=2))

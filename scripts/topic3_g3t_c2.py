"""Create an AI-only source disposition ledger; never write human review events."""

from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from scripts.topic3_v7a_g3s_review_tool import verify_events


POLICY_SHA = '2a8372f17d0a421879bbca858ae09224b8b91d948e80ff2d239e771ebacc4b59'
SPECIAL = {
    '05_01': ('AI_AMBIGUOUS', 'Total cost of sales is printed; cost-of-revenue synonym needs declared accounting equivalence.'),
    '09_02': ('AI_PARTIAL', 'Client is a disclosed business line inside Client and Gaming, not an independent reportable segment.'),
    '12_01': ('AI_NEGATIVE_SUPPORTED', 'Bounded consolidated operations statement lacks a standalone gross-profit line; no computed substitute.'),
    '12_02': ('AI_SUPPORTED_EXACT', 'Current FY2023 and prior FY2022 operating income are mandatory; FY2021 is supplemental under preregistered rule.'),
    '14_02': ('AI_AMBIGUOUS', 'Question does not choose three-month versus six-month operating expense comparison.'),
    '15_01': ('AI_SUPPORTED_EXACT', 'Point-in-time current balance-sheet property and equipment is required; prior balance is supplemental.'),
    '21_01': ('AI_AMBIGUOUS', 'Gross margin is represented both as monetary amount and percentage; unit acceptance needs policy.'),
    '24_01': ('AI_AMBIGUOUS', 'Cost of sales/revenue equivalence and three-month source column need explicit policy.'),
    '25_02': ('AI_QUESTION_INVALID', 'Cash-flow period is year-ended duration; frozen question calls it as-of.'),
    '30_01': ('AI_PARTIAL', 'Interim 10-Q gives specific revenue-recognition judgments, not a complete annual policy.'),
    '32_01': ('AI_PARTIAL', 'Interim 10-Q gives specific revenue-recognition judgments, not a complete annual policy.'),
    '38_01': ('AI_QUESTION_INVALID', 'Revenue-recognition policy is qualitative; question requests a numeric-style reporting unit.'),
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value: dict) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')


def csv_rows(path: Path) -> list[dict]:
    with path.open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def run(c1_dir: Path, review_dataset: Path, human_events: Path, policy: Path, out: Path) -> dict:
    if out.exists():
        raise FileExistsError(out)
    if sha(policy.read_bytes()) != POLICY_SHA:
        raise ValueError('Pre-registered policy changed')
    c1_path = c1_dir / 'G3T_C1_94_EVIDENCE_LEDGER.jsonl'
    c1 = {x['question_id']: x for x in (json.loads(s) for s in c1_path.read_text(encoding='utf-8').splitlines())}
    dataset = json.loads(review_dataset.read_text(encoding='utf-8'))
    review = {x['question_id']: x for x in dataset['records']}
    narrative = {x['question_id']: x for x in csv_rows(c1_dir / 'G3T_C1_NARRATIVE_PROPOSITION_AUDIT.csv')}
    if len(c1) != 94 or set(c1) != set(review):
        raise ValueError('94 frozen IDs missing/duplicated in AI source review')
    events = verify_events(human_events)
    # Self-declared UI identities are never cryptographically verified by this process.
    records, comparisons = [], []
    prior_hash = 'GENESIS'
    timestamp = datetime.now(timezone.utc).isoformat()
    for qid in sorted(c1):
        source, prior = c1[qid], review[qid]
        if source['source_sha256'] != prior['source_sha256'] or source['accession'] != prior['accession']:
            raise ValueError(f'{qid}: source changed between G3T and review queue')
        status = source['c1_outcome']
        reason = f'SEC primary source checked; C1 outcome {status}.'
        if qid[-5:] in SPECIAL:
            label, reason = SPECIAL[qid[-5:]]
        elif status in ('SOURCE_CELL_REVALIDATED', 'SOURCE_CELL_VERIFIED', 'DUAL_AI_CELL_AGREEMENT'):
            label = 'AI_SUPPORTED_EXACT'
            reason = ('Original SEC row, printed value, year/duration and HTML locator rechecked. '
                      'Unit/scale metadata follows the prior source-reviewed proposal and requires '
                      'independent human confirmation; human certification remains pending.')
        elif status == 'SOURCE_PASSAGE_VERIFIED':
            label = 'AI_PARTIAL'
            reason = 'Relevant source anchors verified; full narrative proposition and limitations still require semantic/human review.'
        elif status == 'SOURCE_PASSAGE_CANDIDATE':
            label = 'AI_PARTIAL'
            reason = 'Original SEC excerpt verified; passage may not answer the full qualitative question.'
        elif status == 'SOURCE_FACT_VERIFIED_BUT_QUESTION_SCOPE_PENDING':
            label = 'AI_AMBIGUOUS'
            reason = 'Exact source cell exists but question period or comparative scope remains unresolved.'
        else:
            label = 'AI_UNRESOLVED'
            reason = 'Available original source does not yet resolve prior disagreement or exact question scope.'
        if label == 'AI_SUPPORTED_EXACT' and not source['source_cells']:
            raise ValueError(f'{qid}: exact numeric support without source cells')
        narrative_record = narrative.get(qid)
        body = {'schema': 'g3t_ai_source_adjudication/v1', 'question_id': qid,
                'question_sha256': source['question_sha256'], 'accession': source['accession'],
                'source_sha256': source['source_sha256'], 'source_url': source['source_url'],
                'source_fact_evidence': source['source_cells'],
                'narrative_evidence': narrative_record or {},
                'agent1_prior_decision': prior['agent1_decision'],
                'agent2_prior_decision': prior['agent2_decision'],
                'agent_relation': prior['cell_relation'],
                'technical_label': label, 'reason': reason,
                'counterexample_or_limitation': (prior['coordinator_recommendation'] or
                    prior['review_reason'] or 'Source-cell presence does not establish retrieval relevance.'),
                'question_validity_flag': prior['question_validity_flag'],
                'inclusion_proposal': 'ELIGIBLE_AI_ONLY_CANDIDATE' if label in ('AI_SUPPORTED_EXACT','AI_NEGATIVE_SUPPORTED') else 'NOT_EXACT_SCORABLE_PENDING_POLICY_OR_EVIDENCE',
                'review_priority': prior['priority'],
                'human_approval_status': 'PENDING',
                'reviewer_type': 'AI_ASSISTED_SOURCE_FIRST',
                'blindness_disclosure': 'Prior Agent 1/2 labels and G3R reconciliation were available; this is not a new blind independent annotation.',
                'model_prediction_exposure': 'No new G2 author/FAITH-R predictions used for this disposition.',
                'evidence_utc': timestamp, 'protocol_sha256': POLICY_SHA,
                'c1_ledger_sha256': sha(c1_path.read_bytes()),
                'previous_record_sha256': prior_hash}
        record = {**body, 'record_sha256': sha(canonical(body))}
        records.append(record)
        prior_hash = record['record_sha256']
        comparisons.append({'question_id': qid, 'agent1_decision': prior['agent1_decision'],
                            'agent2_decision': prior['agent2_decision'], 'c1_outcome': status,
                            'ai_technical_label': label, 'human_status': 'PENDING'})
    out.mkdir(parents=True)
    ledger_path = out / 'G3T_C2_AI_ADJUDICATION_94.jsonl'
    ledger_path.write_text(''.join(json.dumps(x, ensure_ascii=False)+'\n' for x in records), encoding='utf-8')
    with (out / 'G3T_C2_CONSENSUS_DISAGREEMENT_MATRIX.csv').open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(comparisons[0])); writer.writeheader(); writer.writerows(comparisons)
    human_audit = {'schema': 'g3t_human_events_audit/v1', 'human_event_count': len(events),
                   'human_approved_count': sum(x['decision']=='APPROVE' for x in events),
                   'hash_chain': 'PASS', 'identity_assurance': 'SELF_DECLARED_NOT_CRYPTOGRAPHICALLY_AUTHENTICATED',
                   'ai_ledger_never_imported': True}
    (out / 'G3T_C2_HUMAN_REVIEW_EVENTS_AUDIT.json').write_text(json.dumps(human_audit, indent=2)+'\n', encoding='utf-8')
    counts = dict(Counter(x['technical_label'] for x in records))
    manifest = {'schema': 'g3t_ai_source_adjudication_manifest/v1',
                'question_count': len(records), 'counts': counts,
                'ledger_sha256': sha(ledger_path.read_bytes()),
                'c1_ledger_sha256': sha(c1_path.read_bytes()),
                'review_dataset_sha256': sha(review_dataset.read_bytes()),
                'protocol_sha256': POLICY_SHA, 'reviewer_type': 'AI_ASSISTED_SOURCE_FIRST',
                'human_approved_count': human_audit['human_approved_count'],
                'prediction_leakage_rule': 'No new model rankings/scores read',
                'human_ledger_separate': True}
    (out / 'G3T_C2_AI_ADJUDICATION_MANIFEST.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')
    eligible = [r['question_id'] for r in records if r['inclusion_proposal']=='ELIGIBLE_AI_ONLY_CANDIDATE']
    release = {'schema': 'g3t_ai_source_adjudicated_v1', 'status': 'AI_ONLY_PROVISIONAL_NOT_HUMAN_GOLD',
               'adjudication_manifest_sha256': sha((out / 'G3T_C2_AI_ADJUDICATION_MANIFEST.json').read_bytes()),
               'eligible_candidate_ids': eligible, 'eligible_candidate_count': len(eligible),
               'excluded_or_unresolved_count': 94-len(eligible),
               'human_approved_count': human_audit['human_approved_count'],
               'qrels_scoring_gate': 'NOT_YET_ASSESSED'}
    (out / 'G3T_C2_AI_ONLY_RELEASE.json').write_text(json.dumps(release, indent=2)+'\n', encoding='utf-8')
    return manifest


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('c1_dir','review_dataset','human_events','policy','out'):
        p.add_argument('--'+name.replace('_','-'), required=True, type=Path)
    print(json.dumps(run(**vars(p.parse_args())), indent=2))

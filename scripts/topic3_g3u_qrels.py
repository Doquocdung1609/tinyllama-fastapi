"""Blind original-chunk review preparation; never promotes static matches to gold."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path
import re

from scripts.topic3_g3u_pool import FORBIDDEN_BLIND_KEYS, sha


PRIORITY = {'V7A_G2_' + x for x in ('05_01', '09_02', '12_01', '12_02',
    '14_02', '15_01', '21_01', '24_01', '25_02', '30_01', '32_01', '38_01')}
AMD = {'V7A_G2_09_01', 'V7A_G2_10_01', 'V7A_G2_10_02'}


def norm(text: str) -> str:
    return ' '.join(re.findall(r'[a-z0-9]+', text.casefold()))


def value_hit(text: str, value: str) -> bool:
    digits = re.sub(r'\D', '', str(value))
    return bool(digits and re.search(r'(?<!\d)' + r'[\s,]*'.join(digits) + r'(?!\d)', text))


def challenge_one_chunk(chunk: dict, source: dict) -> dict:
    """Mechanical partial candidate only; never decide EXACT or NONE."""
    body = chunk['original_text']
    cells = source.get('source_cells', [])
    candidates = []
    for cell in cells:
        row = cell.get('row')
        value = cell.get('value_decimal')
        if not row or value is None:
            continue
        row_present = norm(row) in norm(body)
        value_present = value_hit(body, str(value))
        period = str(cell.get('period', ''))
        year = re.search(r'20\d\d', period)
        year_present = bool(year and year.group() in body)
        scale = str(cell.get('scale', '')).casefold()
        scale_present = bool(scale and (scale in body.casefold() or scale.rstrip('s') in body.casefold()))
        candidates.append({'row_present': row_present, 'value_present': value_present,
                           'period_year_present': year_present, 'scale_text_present': scale_present})
    meaningful = (chunk['chunk_accession'] == source['accession'] and
                  any(x['row_present'] and x['value_present'] for x in candidates))
    return {'provisional_grade': 'PARTIAL' if meaningful else 'UNJUDGED',
            'graded_value': 1 if meaningful else None,
            'challenge': ('Same original chunk contains a target-row phrase and printed-value digits; '
                          'column, duration, scale, comparison and completeness remain unproven.'
                          if meaningful else
                          'No sufficient deterministic source-cell signal; semantic chunk relevance unjudged.'),
            'cell_checks': candidates,
            'exact_claim': False, 'none_claim': False}


def select_stratified(c1: dict, question_category: dict) -> set[str]:
    """Prospective question-only subset, independent of ranked candidates."""
    groups = defaultdict(list)
    for qid, row in c1.items():
        groups[(row['accession'][:10], question_category[qid])].append(qid)
    return {sorted(ids)[0] for ids in groups.values()}


def run(blind_path: Path, pool_manifest: Path, c1_path: Path,
        question_csv: Path, out: Path) -> dict:
    if out.exists():
        raise FileExistsError(out)
    manifest = json.loads(pool_manifest.read_text(encoding='utf-8'))
    if (manifest['status'] not in {'POOL_GENERATED_NOT_SCORED', 'SOURCE_AUDIT_QUEUE_NOT_RANKED_POOL'} or
            sha(blind_path.read_bytes()) != manifest['blind_sha256']):
        raise ValueError('Blind pool hash/status changed')
    c1 = {r['question_id']: r for r in
          (json.loads(s) for s in c1_path.read_text(encoding='utf-8').splitlines())}
    with question_csv.open(encoding='utf-8-sig', newline='') as stream:
        question_category = {r['question_id']: r['category'] for r in csv.DictReader(stream)}
    if len(c1) != 94 or set(c1) != set(question_category):
        raise ValueError('Frozen question map changed')
    subset = select_stratified(c1, question_category) | PRIORITY | AMD
    blind = [json.loads(s) for s in blind_path.read_text(encoding='utf-8').splitlines()]
    if len(blind) != manifest['unique_blind_pairs']:
        raise ValueError('Blind pool count changed')
    qrel_rows, queue_rows, conflicts, by_question = [], [], [], Counter()
    pair_ids = set()
    for candidate in blind:
        if FORBIDDEN_BLIND_KEYS & set(candidate):
            raise ValueError('Rank/method/score leaked into judge input')
        qid, cid = candidate['question_id'], candidate['chunk_id']
        if qid not in c1 or (qid, cid) in pair_ids:
            raise ValueError('Unknown/duplicate blind qrel candidate')
        pair_ids.add((qid, cid))
        if sha(candidate['original_text'].encode('utf-8')) != candidate['original_text_sha256']:
            raise ValueError('Original chunk text hash changed')
        assessment = challenge_one_chunk(candidate, c1[qid])
        evidence = {'schema': 'g3u_ai_qrel_provisional/v1', 'question_id': qid,
                    'chunk_id': cid, 'original_text_sha256': candidate['original_text_sha256'],
                    'source_sha256': candidate['source_sha256'],
                    'grade': assessment['provisional_grade'],
                    'graded_value': assessment['graded_value'],
                    'reviewer_type': 'AI_QREL_PROVISIONAL_DETERMINISTIC_RULES',
                    'model_identity': 'NO_GENERATIVE_MODEL_DETERMINISTIC_ROW_VALUE_CHECK_V1',
                    'prompt_config': 'single original chunk; target accession plus row/value co-occurrence; no rank/model output',
                    'challenge': assessment['challenge'],
                    'cell_checks': assessment['cell_checks'],
                    'stage1_mechanical_signal': {'row_value_same_chunk':
                        any(x['row_present'] and x['value_present'] for x in assessment['cell_checks']),
                        'target_accession': candidate['chunk_accession'] == c1[qid]['accession']},
                    'stage2_counterexample_check': {'period_year_signals':
                        [x['period_year_present'] for x in assessment['cell_checks']],
                        'scale_text_signals':
                        [x['scale_text_present'] for x in assessment['cell_checks']],
                        'duration_column_binding': 'NOT_VERIFIED',
                        'comparative_completeness': 'NOT_VERIFIED',
                        'narrative_sufficiency': 'NOT_VERIFIED',
                        'decision': 'NO_AUTOMATIC_EXACT_OR_NONE'},
                    'uncertainty': 'HIGH_COLUMN_PERIOD_UNIT_SEMANTIC_REVIEW_PENDING',
                    'human_certified': False, 'rank_exposure': False}
        qrel_rows.append(evidence)
        queue_rows.append({'schema': 'g3u_human_chunk_review_queue/v1',
                           **candidate, 'review_priority':
                           'TWELVE_SOURCE_DISPUTE' if qid in PRIORITY else
                           'AMD_CORPUS_GAP' if qid in AMD else
                           'PROSPECTIVE_STRATIFIED' if qid in subset else 'GENERAL',
                           'ai_assessment_visible_to_blind_judge': False})
        if assessment['provisional_grade'] == 'PARTIAL' or qid in PRIORITY | AMD:
            conflicts.append({'question_id': qid, 'chunk_id': cid,
                              'original_text_sha256': candidate['original_text_sha256'],
                              'source_sha256': candidate['source_sha256'],
                              'reason': assessment['challenge'],
                              'human_status': 'PENDING'})
        by_question[qid] += 1
    if len(by_question) != 94:
        raise ValueError('Ranked pool failed 94-question coverage')
    out.mkdir(parents=True)
    paths = {'ai': out / 'G3U_AI_QREL_PROVISIONAL.jsonl',
             'queue': out / 'G3U_HUMAN_CHUNK_REVIEW_QUEUE.jsonl',
             'challenge': out / 'G3U_QREL_CHALLENGE_QUEUE.jsonl'}
    for name, data in [('ai', qrel_rows), ('queue', queue_rows), ('challenge', conflicts)]:
        paths[name].write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in data), encoding='utf-8')
    grades = Counter(r['grade'] for r in qrel_rows)
    result = {'schema': 'g3u_qrel_preparation_manifest/v1',
              'status': 'AI_PARTIAL_AND_UNJUDGED_ONLY_HUMAN_PENDING',
              'input_status': manifest['status'],
              'blind_pool_sha256': manifest['blind_sha256'],
              'question_count': 94, 'pairs': len(qrel_rows), 'grades': dict(grades),
              'human_events': 0, 'human_approved': 0,
              'priority_question_count': len(PRIORITY), 'amd_question_count': len(AMD),
              'prospective_stratified_question_count': len(subset),
              'question_selection_rule': 'One sorted ID per issuer CIK prefix/category, plus frozen twelve and three AMD; before ranked-output inspection',
              'challenge_rows': len(conflicts),
              'files': {name: {'sha256': sha(path.read_bytes()), 'bytes': path.stat().st_size}
                        for name, path in paths.items()},
              'ranking_metrics': 'NOT_COMPUTED', 'exact_judgments': 0,
              'none_judgments': 0}
    (out / 'G3U_QREL_PREPARATION_MANIFEST.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for n in ('blind_path', 'pool_manifest', 'c1_path', 'question_csv', 'out'):
        p.add_argument('--'+n.replace('_','-'), type=Path, required=True)
    print(json.dumps(run(**vars(p.parse_args())), indent=2))

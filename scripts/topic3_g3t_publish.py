"""Publish redacted G3T status/manifests; preserve value-bearing ledgers outside Git."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def csv_rows(path: Path) -> list[dict]:
    with path.open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def write_csv(path: Path, rows: list[dict], fields: tuple[str, ...]) -> None:
    with path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows({k: r.get(k, '') for k in fields} for r in rows)


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def run(c1: Path, c2: Path, c3: Path, review_dataset: Path, prior_casebook: Path,
        out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    source_cases = csv_rows(c1 / 'G3T_C1_11_CASE_SOURCE_CLOSURE.csv')
    narratives = csv_rows(c1 / 'G3T_C1_NARRATIVE_PROPOSITION_AUDIT.csv')
    gaps = csv_rows(c1 / 'G3T_C1_SOURCE_CORPUS_GAP_MATRIX.csv')
    coverage = csv_rows(c3 / 'G3T_C3_SOURCE_CORPUS_COVERAGE.csv')
    if (len(source_cases),len(narratives),len(gaps),len(coverage)) != (11,13,11,94):
        raise ValueError('C1/C3 required coverage incomplete')
    write_csv(out / 'G3T_C1_11_CASE_SOURCE_CLOSURE.csv', source_cases,
              ('question_id','case_type','accession','source_sha256','verified_cells','minimum_required_cells','outcome','human_review'))
    write_csv(out / 'G3T_C1_NARRATIVE_PROPOSITION_AUDIT.csv', narratives,
              ('question_id','accession','source_sha256','anchor_set_verified','agent1_excerpt_in_source','source_evidence_level','whole_proposition_status','human_review'))
    write_csv(out / 'G3T_C1_SOURCE_CORPUS_GAP_MATRIX.csv', gaps,
              ('question_id','accession','diagnosis','method','retrieval_miss'))
    write_csv(out / 'G3T_C3_SOURCE_CORPUS_COVERAGE.csv', coverage,
              ('question_id','accession','target_filing_chunk_count','static_partial_chunk_count',
               'exact_original_chunk_judgments','pool_status','source_present','retrieval_miss'))
    for name, path in (
        ('G3T_C2_AI_ADJUDICATION_MANIFEST.json', c2 / 'G3T_C2_AI_ADJUDICATION_MANIFEST.json'),
        ('G3T_C2_HUMAN_REVIEW_EVENTS_AUDIT.json', c2 / 'G3T_C2_HUMAN_REVIEW_EVENTS_AUDIT.json'),
        ('G3T_C3_BENCHMARK_PRECHECK.json', c3 / 'G3T_C3_BENCHMARK_PRECHECK.json'),
        ('G3T_C3_ORIGINAL_CHUNK_PROVENANCE_MANIFEST.json', c3 / 'G3T_C3_PROVENANCE_MANIFEST.json')):
        write_json(out / name, json.loads(path.read_text(encoding='utf-8')))
    release = json.loads((c2 / 'G3T_C2_AI_ONLY_RELEASE.json').read_text(encoding='utf-8'))
    write_json(out / 'G3T_C2_AI_ONLY_RELEASE.json', {k:v for k,v in release.items() if k != 'eligible_candidate_ids'})
    dataset = json.loads(review_dataset.read_text(encoding='utf-8'))
    queue = [{'priority': r['priority'], 'question_id': r['question_id'],
              'ticker': r['ticker'], 'accession': r['accession'],
              'source_evidence_level': r['source_evidence_level'],
              'human_decision': ''} for r in dataset['records']]
    write_csv(out / 'G3T_C2_HUMAN_REVIEW_QUEUE_94.csv', queue,
              ('priority','question_id','ticker','accession','source_evidence_level','human_decision'))
    if (c2 / 'G3T_C2_TWELVE_DISPUTE_CASEBOOK.md').exists():
        raise FileExistsError('Private twelve-case book already exists')
    by_id = {r['question_id']:r for r in dataset['records']}
    addenda = ['\n# Three post-source unresolved cases\n',
              'These are AI technical proposals, not human approvals.\n']
    for suffix, disposition in [('30_01','AI_PARTIAL'),('32_01','AI_PARTIAL'),('38_01','AI_QUESTION_INVALID')]:
        qid = 'V7A_G2_' + suffix
        r = by_id[qid]
        addenda.append(f'\n## {qid}\n\nFrozen question: {r["question"]}\n\nSEC accession `{r["accession"]}`, form `{r["form"]}`, source SHA-256 `{r["source_sha256"]}`, URL {r["source_url"]}. Source excerpt: {r["source_excerpt"]}\n\nAgent 1: `{r["agent1_decision"]}`; Agent 2: `{r["agent2_decision"]}`. Proposed disposition `{disposition}`; reason: interim policy scope/complete proposition for Microsoft, qualitative-policy versus numeric unit for Tesla. Competing interpretation: a narrower source passage is present but may not satisfy the frozen wording. Human decision: **PENDING**.\n')
    (c2 / 'G3T_C2_TWELVE_DISPUTE_CASEBOOK.md').write_text(
        prior_casebook.read_text(encoding='utf-8') + '\n'.join(addenda), encoding='utf-8')
    private = {}
    for group, directory in [('C1',c1),('C2',c2),('C3',c3)]:
        private[group] = {p.name:{'sha256':sha(p),'bytes':p.stat().st_size}
                          for p in sorted(directory.iterdir()) if p.is_file()}
    manifest = {'schema':'g3t_private_evidence_manifest/v1',
                'location':'PRIVATE_OWNER_MACHINE_HANDOFF_OUTSIDE_GIT',
                'contains_value_bearing_answers_or_qrels': True,
                'files':private}
    write_json(out / 'G3T_PRIVATE_EVIDENCE_MANIFEST.json', manifest)
    return {'public_dir':str(out), 'case_count':len(source_cases), 'narratives':len(narratives),
            'queue':len(queue), 'corpus_coverage':len(coverage),
            'private_manifest_sha256':sha(out / 'G3T_PRIVATE_EVIDENCE_MANIFEST.json')}


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('c1','c2','c3','review_dataset','prior_casebook','out'):
        p.add_argument('--'+name.replace('_','-'), type=Path, required=True)
    print(json.dumps(run(**vars(p.parse_args())), indent=2))

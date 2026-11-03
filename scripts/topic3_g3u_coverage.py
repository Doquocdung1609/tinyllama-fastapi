"""Redacted source-only qrel coverage by question, issuer, form and answer type."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import json
from pathlib import Path


def run(qrels: Path, c1_ledger: Path, questions: Path,
        sources: Path, out_csv: Path, out_json: Path,
        pool_origin: str = 'STATIC_TARGET_FILING_SOURCE_AUDIT') -> dict:
    if out_csv.exists() or out_json.exists():
        raise FileExistsError('Versioned coverage output exists')
    c1 = {r['question_id']: r for r in
          (json.loads(s) for s in c1_ledger.read_text(encoding='utf-8').splitlines())}
    with questions.open(encoding='utf-8-sig', newline='') as stream:
        types = {r['question_id']: r['category'] for r in csv.DictReader(stream)}
    source_map = {r['accession']: r for r in json.loads(sources.read_text(encoding='utf-8'))['sources']}
    by_qid = defaultdict(Counter)
    for line in qrels.read_text(encoding='utf-8').splitlines():
        r = json.loads(line)
        by_qid[r['question_id']][r['grade']] += 1
    if not (len(c1) == len(types) == len(by_qid) == 94 and
            set(c1) == set(types) == set(by_qid)):
        raise ValueError('Question/qrel coverage incomplete')
    rows = []
    for qid in sorted(c1):
        source = source_map[c1[qid]['accession']]
        grades = by_qid[qid]
        rows.append({'question_id': qid, 'ticker': source['ticker'],
                     'accession': source['accession'], 'form': source['form'],
                     'answer_type': types[qid], 'pool_origin': pool_origin,
                     'partial': grades['PARTIAL'], 'unjudged': grades['UNJUDGED'],
                     'exact': grades['EXACT'], 'none': grades['NONE'],
                     'human_approved': 0, 'arm': 'BLIND_UNION_ARM_HIDDEN' if pool_origin ==
                     'RANKED_MIXED_ARM_BLIND_UNION' else 'NOT_APPLICABLE_NO_RANKED_POOL'})
    with out_csv.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    groups = {}
    for field in ('ticker', 'form', 'answer_type'):
        groups[field] = {name: {'questions': len(items),
                                'partial': sum(int(x['partial']) for x in items),
                                'unjudged': sum(int(x['unjudged']) for x in items)}
                         for name in sorted({x[field] for x in rows})
                         for items in [[x for x in rows if x[field] == name]]}
    report = {'schema':'g3u_qrel_coverage_by_stratum/v1', 'questions':94,
              'pairs':sum(int(r['partial'])+int(r['unjudged']) for r in rows),
              'by':groups, 'pool_origin': pool_origin,
              'ranked_arm_coverage':'BLIND_UNION_ARMS_HIDDEN' if pool_origin ==
                  'RANKED_MIXED_ARM_BLIND_UNION' else 'NOT_APPLICABLE_NO_COMPLETE_POOL',
              'human_decisions':0, 'exact':0, 'none':0}
    out_json.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    return report


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('qrels','c1_ledger','questions','sources','out_csv','out_json'):
        p.add_argument('--'+n.replace('_','-'), type=Path, required=True)
    p.add_argument('--pool-origin', choices=('STATIC_TARGET_FILING_SOURCE_AUDIT',
                   'RANKED_MIXED_ARM_BLIND_UNION'), default='STATIC_TARGET_FILING_SOURCE_AUDIT')
    report=run(**vars(p.parse_args()))
    print(json.dumps({k:report[k] for k in ('questions','pairs','human_decisions','exact','none')},indent=2))

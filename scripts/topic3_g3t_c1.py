"""Source-first G3T C1 closure, preserving all frozen G3S evidence."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import re
import zipfile

from lxml import html

from scripts.topic3_v7a_g3s_evidence import SourceStore, NARRATIVE_NEEDLES, choose_candidate, decimal, norm, source_cell_candidates


POLICY_SHA = '2a8372f17d0a421879bbca858ae09224b8b91d948e80ff2d239e771ebacc4b59'
PRIMARY_TABLE = {
    '09_01': '/html/body/div[217]/table', '10_01': '/html/body/div[224]/table',
    '10_02': '/html/body/div[224]/table', '13_01': '/html/body/div[385]/table',
    '18_02': '/html/body/div[96]/table', '21_02': '/html/body/div[1130]/table',
    '23_01': '/html/body/div[116]/table', '37_01': '/html/body/div[64]/table',
    '12_02': '/html/body/div[552]/table', '14_02': '/html/body/div[69]/table',
    '15_01': '/html/body/div[86]/table',
}
SCOPE_CASES = {'12_02', '14_02', '15_01'}
REQUIRED_COUNT = {'12_02': 2, '14_02': 2, '15_01': 1}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def rows(path: Path) -> list[dict]:
    with path.open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def write_csv(path: Path, data: list[dict]) -> None:
    with path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(dict.fromkeys(k for x in data for k in x)))
        writer.writeheader()
        writer.writerows(data)


def run(args: argparse.Namespace) -> dict:
    if args.out.exists():
        raise FileExistsError(args.out)
    if sha(args.policy.read_bytes()) != POLICY_SHA:
        raise ValueError('Pre-registered rubric changed')
    public = {x['question_id']: x for x in rows(args.audit)}
    prior = {x['question_id']: x for x in rows(args.prior)}
    post_agent1 = {x['question_id']: x for x in rows(args.post_agent1)}
    g3s_narrative = {x['question_id']: x for x in rows(args.narrative_g3s)}
    cells = defaultdict(list)
    for line in args.cells.read_text(encoding='utf-8').splitlines():
        c = json.loads(line)
        cells[c['question_id']].append(c)
    if len(public) != 94 or set(public) != set(prior):
        raise ValueError('94 G2 question IDs do not align')
    source_store = SourceStore(args.registry, args.nine, args.eight, args.thirty)
    corpus_raw = zipfile.ZipFile(args.corpus_zip).read('corpus/chunks_frozen.jsonl')
    if sha(corpus_raw) != '7c6852a8c68ed1c64194c2da9339fbb4719482949e5705596499db53114abb1f':
        raise ValueError('Frozen corpus SHA mismatch')
    chunks = [json.loads(line) for line in corpus_raw.splitlines()]
    if len(chunks) != 8670 or len({c['chunk_id'] for c in chunks}) != 8670:
        raise ValueError('Frozen corpus count/IDs invalid')
    by_acc = defaultdict(list)
    for chunk in chunks:
        accession = chunk['document_id'].split('_')[-1]
        by_acc[accession].append(chunk)

    case_rows, casebook, ledger, gap, narrative = [], ['# G3T C1 eleven source-first cases\n'], [], [], []
    try:
        for qid in sorted(public):
            audit, old = public[qid], prior[qid]
            acc = audit['accession']
            source = source_store.by_acc[acc]
            if source['sha256'] != audit['source_sha256'] or old['question'] != audit['question']:
                raise ValueError(f'Changed source/question: {qid}')
            question_sha = sha(old['question'].encode('utf-8'))
            source_bytes = source_store.bytes(acc)
            status = audit['source_evidence_level']
            case_evidence = []
            if qid == 'V7A_G2_12_01':
                doc = html.fromstring(source_bytes)
                tables = doc.xpath('/html/body/div[552]/table')
                if len(tables) != 1:
                    raise ValueError('Amazon consolidated operations table not located')
                labels = [norm(' '.join(row.xpath('./td[1]//text()|./th[1]//text()')))
                          for row in tables[0].xpath('.//tr')]
                if not any('total net sales' in x for x in labels) or not any('operating income' in x for x in labels):
                    raise ValueError('Amazon bounded statement incomplete')
                if any('gross profit' in x for x in labels):
                    raise ValueError('Amazon gross-profit negative contradicted by source')
                case_evidence.append({'source_statement_xpath': '/html/body/div[552]/table',
                    'bounded_negative': 'No standalone Gross profit row in consolidated operations statement',
                    'scope': 'Consolidated Statements of Operations', 'verification': 'COMPLETE_STATEMENT_ROWS_INSPECTED'})
            if qid == 'V7A_G2_25_02':
                doc = html.fromstring(source_bytes)
                source_rows = doc.xpath('/html/body/div[1528]/table/tr[22]')
                if len(source_rows) != 1 or 'net cash provided by operating activities' not in norm(' '.join(source_rows[0].itertext())):
                    raise ValueError('Meta cash-flow source row not located')
                if '91328' not in norm(' '.join(source_rows[0].itertext())).replace(' ', ''):
                    raise ValueError('Meta cash-flow value not in verified row')
                case_evidence.append({'source_row_xpath': '/html/body/div[1528]/table/tr[22]',
                    'scope': 'Year-ended cash-flow statement, not point-in-time balance sheet',
                    'verification': 'SOURCE_ROW_AND_QUESTION_DURATION_CONFLICT'})
            if status == 'SOURCE_CELL_REVALIDATED':
                doc = html.fromstring(source_bytes)
                if not cells[qid]:
                    raise ValueError(f'{qid}: historical numeric cells missing')
                for c in cells[qid]:
                    candidates = source_cell_candidates(doc, {'row_label': c['row'],
                        'column_header': c['period'], 'exact_value': c['value_as_printed']}, old['question'])
                    if not any(v['cell_xpath'] == c['source_locator'] and
                               v['year_column_bound'] and v['duration_column_bound'] for v in candidates):
                        raise ValueError(f'{qid}: former source cell failed independent recheck')
                    case_evidence.append({'row': c['row'], 'period': c['period'],
                        'value_decimal': str(decimal(c['value_as_printed'])), 'currency': c['currency'],
                        'scale': c['scale'], 'scope': c['scope'], 'primary_xpath': c['source_locator'],
                        'verification': 'SOURCE_ROW_VALUE_YEAR_DURATION_RECHECKED'})
            if status == 'DUAL_AI_CELL_AGREEMENT':
                post = post_agent1.get(qid)
                if not post or post['source_html_sha256'] != source['sha256']:
                    raise ValueError(f'{qid}: post-source numeric submission missing/hash changed')
                doc = html.fromstring(source_bytes)
                proposed = {'row_label': post['row_label'], 'column_header': post['column_period'],
                            'exact_value': post['exact_value']}
                candidates = source_cell_candidates(doc, proposed, old['question'])
                submitted_row = re.search(r'xpath=([^;]+)', post['source_locator'] or '')
                bound_at_locator = [v for v in candidates if v['year_column_bound'] and
                                    v['duration_column_bound'] and submitted_row and
                                    v['row_xpath'] == submitted_row.group(1)]
                if len(bound_at_locator) == 1:
                    level, selected = 'SOURCE_CELL_REVALIDATED_AT_SUBMITTED_LOCATOR', bound_at_locator[0]
                else:
                    level, selected = choose_candidate(candidates, post['statement_or_section'])
                if not selected or level not in ('SOURCE_CELL_REVALIDATED', 'SOURCE_CELL_REVALIDATED_STATEMENT_MATCH',
                                                 'SOURCE_CELL_REVALIDATED_AT_SUBMITTED_LOCATOR'):
                    status = 'POST_SOURCE_CELL_RECHECK_UNRESOLVED'
                else:
                    case_evidence.append({'row': post['row_label'], 'period': post['column_period'],
                        'value_decimal': str(decimal(post['exact_value'])), 'currency': post['currency'],
                        'scale': post['scale'], 'scope': post['accounting_scope'],
                        'primary_xpath': selected['cell_xpath'], 'source_row_text': selected['source_row_text'],
                        'verification': 'POST_SOURCE_CELL_INDEPENDENT_RECHECK'})
            if qid[-5:] in PRIMARY_TABLE:
                suffix = qid[-5:]
                doc = html.fromstring(source_bytes)
                table_path = PRIMARY_TABLE[suffix]
                primary_table = doc.xpath(table_path)
                if len(primary_table) != 1:
                    raise ValueError(f'{qid}: primary SEC table missing')
                for c in cells[qid]:
                    candidates = source_cell_candidates(doc, {
                        'row_label': c['row'], 'column_header': c['period'],
                        'exact_value': c['value_as_printed']}, old['question'])
                    bound = [v for v in candidates if v['year_column_bound'] and v['duration_column_bound']]
                    selected = [v for v in bound if v['table_xpath'] == table_path]
                    if len(selected) != 1:
                        raise ValueError(f'{qid}: primary table has {len(selected)} matching cells')
                    s = selected[0]
                    if decimal(c['value_as_printed']) is None:
                        raise ValueError(f'{qid}: non-Decimal proposed value')
                    # Static lookup is a corpus-presence diagnostic, never a retrieval hit.
                    matches = [chunk['chunk_id'] for chunk in by_acc[acc]
                               if norm(c['row']) in norm(chunk['text']) and
                               c['value_as_printed'].replace(',', '') in chunk['text'].replace(',', '')]
                    case_evidence.append({
                        'cell_index': c['cell_index'], 'row': c['row'], 'period': c['period'],
                        'value_decimal': str(decimal(c['value_as_printed'])),
                        'currency': c['currency'], 'scale': c['scale'], 'scope': c['scope'],
                        'primary_xpath': s['cell_xpath'], 'header_context': s['header_context'],
                        'source_row_text': s['source_row_text'],
                        'candidate_xpaths': [v['cell_xpath'] for v in bound],
                        'candidate_table_xpaths': [v['table_xpath'] for v in bound],
                        'duplicate_or_alternate': ('IDENTICAL_PRESENTATION_DUPLICATE' if len(bound)>1 and all(v['table_text'] == bound[0]['table_text'] for v in bound) else
                                                   'ALTERNATE_SECTION_OR_STATEMENT' if len(bound)>1 else 'UNIQUE'),
                        'static_original_chunk_ids': matches,
                        'corpus_mapping': 'SOURCE_AND_CHUNK_PRESENT_BUT_UNJUDGED' if matches else 'STATIC_TEXT_NOT_FOUND_REQUIRES_MANUAL_CORPUS_CHECK',
                    })
                minimum = REQUIRED_COUNT.get(suffix, len(case_evidence))
                if len(case_evidence) < minimum:
                    raise ValueError(f'{qid}: incomplete comparative set')
                status = 'SOURCE_FACT_VERIFIED_BUT_QUESTION_SCOPE_PENDING' if suffix in SCOPE_CASES else 'SOURCE_CELL_VERIFIED'
                case_rows.append({'question_id': qid, 'case_type': 'COMPARATIVE_SCOPE' if suffix in SCOPE_CASES else 'MULTIPLE_LOCATORS',
                                  'accession': acc, 'source_sha256': source['sha256'],
                                  'verified_cells': len(case_evidence), 'minimum_required_cells': minimum,
                                  'outcome': status, 'human_review': 'PENDING'})
                casebook.append(f'\n## {qid}\n\nFrozen question: {old["question"]}\n\nQuestion SHA-256: `{question_sha}`; accession `{acc}`; source SHA-256 `{source["sha256"]}`; form `{source["form"]}`; URL {source["source_url"]}.\n\nResult: **{status}**. Pre-registered current/prior comparison rule applies. A source fact can be checked while question equivalence or extra comparison remains human-policy pending. Original Agent 1: `{old["agent1_decision"]}`; Agent 2: `{old["agent2_decision"]}`. No human approval.\n')
                for c in case_evidence:
                    casebook.append(f'\n- `{c["primary_xpath"]}`: row **{c["row"]}**, period **{c["period"]}**, Decimal **{c["value_decimal"]}** {c["currency"]} {c["scale"]}; scope **{c["scope"]}**. Alternative/duplicate: `{c["duplicate_or_alternate"]}`. Candidate paths: `{c["candidate_xpaths"]}`. Header: `{c["header_context"][:220]}`. Static chunk IDs: `{c["static_original_chunk_ids"][:12]}`; `{c["corpus_mapping"]}`.\n')
            if status in ('SOURCE_PASSAGE_VERIFIED', 'SOURCE_PASSAGE_CANDIDATE'):
                doc = html.fromstring(source_bytes)
                excerpt = (g3s_narrative.get(qid, {}).get('source_excerpt') or
                           post_agent1.get(qid, {}).get('verbatim_evidence_excerpt') or
                           old.get('agent1_evidence') or '')
                normalized = norm(' '.join(doc.itertext()))
                excerpt_present = bool(norm(excerpt)[:65] and norm(excerpt)[:65] in normalized)
                anchors = []
                for needle in NARRATIVE_NEEDLES.get(qid, []):
                    if needle not in normalized:
                        continue
                    options = []
                    for node in doc.xpath('//p|//tr|//td|//span'):
                        node_text = norm(' '.join(node.itertext()))
                        if needle in node_text:
                            options.append((len(node_text), doc.getroottree().getpath(node), node_text[:500]))
                    anchors.append({'phrase': needle, 'xpath': min(options)[1] if options else '',
                                    'excerpt': min(options)[2] if options else ''})
                anchor_set_verified = bool(NARRATIVE_NEEDLES.get(qid)) and len(anchors) == len(NARRATIVE_NEEDLES[qid])
                narrative.append({'question_id': qid, 'accession': acc,
                                  'source_sha256': source['sha256'], 'question': old['question'],
                                  'agent1_excerpt_in_source': excerpt_present,
                                  'proposed_source_excerpt': excerpt[:1200],
                                  'verified_source_anchors_json': json.dumps(anchors, ensure_ascii=False),
                                  'anchor_set_verified': anchor_set_verified,
                                  'source_locator': (g3s_narrative.get(qid, {}).get('curated_source_locator') or
                                                     post_agent1.get(qid, {}).get('source_locator') or ''),
                                  'source_evidence_level': status,
                                  'whole_proposition_status': ('SOURCE_ANCHORS_VERIFIED_SEMANTIC_REVIEW_PENDING' if anchor_set_verified else
                                                               'SOURCE_EXCERPT_VERIFIED_SEMANTIC_REVIEW_PENDING' if excerpt_present else
                                                               'SOURCE_EXCERPT_NOT_VERIFIED'),
                                  'human_review': 'PENDING'})
            mapped = sorted({cid for c in case_evidence for cid in c.get('static_original_chunk_ids', [])})
            if qid[-5:] in PRIMARY_TABLE:
                gap.append({'question_id': qid, 'accession': acc, 'static_original_chunk_ids': '|'.join(mapped),
                            'diagnosis': 'SOURCE_AND_CHUNK_PRESENT_BUT_UNJUDGED' if mapped else 'STATIC_TEXT_NOT_FOUND_REQUIRES_MANUAL_CORPUS_CHECK',
                            'method': 'STATIC_CORPUS_AUDIT', 'retrieval_miss': 'NOT_ASSESSED'})
            ledger.append({'schema': 'g3t_c1_source_evidence/v1', 'question_id': qid,
                           'question_sha256': question_sha, 'accession': acc, 'issuer': audit['ticker'],
                           'form': source['form'], 'source_url': source['source_url'],
                           'source_sha256': source['sha256'], 'prior_g3s_level': audit['source_evidence_level'],
                           'c1_outcome': status, 'source_cells': case_evidence,
                           'review_method': 'SEC_PRIMARY_SOURCE_FIRST_STATIC_CORPUS_AUDIT',
                           'human_approval': 'PENDING', 'protocol_sha256': POLICY_SHA,
                           'evidence_utc': datetime.now(timezone.utc).isoformat()})
    finally:
        source_store.close()
    if len(case_rows) != 11 or len(ledger) != 94 or len(narrative) != 13:
        raise ValueError('C1 required case/question/narrative coverage incomplete')
    args.out.mkdir(parents=True)
    write_csv(args.out / 'G3T_C1_11_CASE_SOURCE_CLOSURE.csv', case_rows)
    (args.out / 'G3T_C1_11_CASEBOOK.md').write_text('\n'.join(casebook), encoding='utf-8')
    (args.out / 'G3T_C1_94_EVIDENCE_LEDGER.jsonl').write_text(''.join(json.dumps(x, ensure_ascii=False)+'\n' for x in ledger), encoding='utf-8')
    write_csv(args.out / 'G3T_C1_NARRATIVE_PROPOSITION_AUDIT.csv', narrative)
    write_csv(args.out / 'G3T_C1_SOURCE_CORPUS_GAP_MATRIX.csv', gap)
    summary = {'questions': 94, 'eleven_cases': len(case_rows), 'narratives': len(narrative),
               'outcomes': dict(Counter(x['c1_outcome'] for x in ledger)),
               'source_corpus_gap_counts': dict(Counter(x['diagnosis'] for x in gap)),
               'human_approved': 0, 'policy_sha256': POLICY_SHA,
               'frozen_corpus_sha256': sha(corpus_raw)}
    (args.out / 'G3T_C1_SUMMARY.json').write_text(json.dumps(summary, indent=2)+'\n', encoding='utf-8')
    return summary


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('policy','audit','prior','post_agent1','narrative_g3s','cells','registry','nine','eight','thirty','corpus_zip','out'):
        p.add_argument('--'+name.replace('_','-'), required=True, type=Path)
    print(json.dumps(run(p.parse_args()), indent=2))

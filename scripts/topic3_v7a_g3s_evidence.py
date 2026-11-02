"""Conservative source-first audit of frozen G3 proposals; no gold promotion."""

from __future__ import annotations

import argparse
import csv
from decimal import Decimal, InvalidOperation
from functools import lru_cache
import hashlib
import io
import json
from pathlib import Path
import re
import zipfile

from lxml import html


NARRATIVE_NEEDLES = {
    'V7A_G2_33_01': ['we determine revenue recognition through the following steps',
                      'identification of the performance obligations'],
    'V7A_G2_33_02': ['invested over 37 billion in research and development since our inception'],
    'V7A_G2_35_01': ['we determine revenue recognition through the following steps'],
    'V7A_G2_46_01': ['changes in the shareholdings', 'changes in the pledge',
                      'acquisition and disposition of assets', 'capital appropriations',
                      'unsecured bonds', 'cancellation of'],
    'V7A_G2_46_02': ['for the month of november 2025'],
    'V7A_G2_47_01': ['election of directors', 'tsmc arizona corporation'],
    'V7A_G2_47_02': ['shareholders meeting resolutions of tsmc arizona corporation',
                      'election of directors'],
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def csv_rows(data: bytes) -> list[dict]:
    return list(csv.DictReader(io.StringIO(data.decode('utf-8-sig'))))


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(dict.fromkeys(k for row in rows for k in row)))
        writer.writeheader()
        writer.writerows(rows)


def decimal(raw: object) -> Decimal | None:
    text = str(raw or '').strip().replace(',', '').replace('$', '')
    if text.startswith('(') and text.endswith(')'):
        text = '-' + text[1:-1]
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def norm(text: object) -> str:
    return ' '.join(re.findall(r'[a-z0-9]+', str(text or '').lower()))


def period_signature(text: str) -> tuple[str, str, str]:
    raw = str(text or '').lower()
    full = re.findall(r'20\d\d-\d\d-\d\d', raw)
    year = full[0][:4] if full else (re.search(r'20\d\d', raw).group(0) if re.search(r'20\d\d', raw) else '')
    duration = ('3M' if re.search(r'3\s*m\b|three\s+months|\bq[1-4]\b', raw) else
                '6M' if re.search(r'6\s*m\b|six\s+months', raw) else
                '9M' if re.search(r'9\s*m\b|nine\s+months', raw) else
                'FY' if re.search(r'fy\s*20|year\s+ended|fiscal\s+year|years\s+ended', raw) else
                'ASOF' if re.search(r'as.of|balance', raw) else '')
    return year, duration, full[0] if full else ''


def same_period(a: str, b: str) -> bool:
    ya, da, full_a = period_signature(a)
    yb, db, full_b = period_signature(b)
    if not ya or not yb or ya != yb:
        return False
    if full_a and full_b and full_a != full_b:
        return False
    if da and db and da != db:
        return False
    return True


def scale_factor(value: object) -> Decimal | None:
    label = str(value or '').strip().lower()
    return {'million': Decimal(1000000), 'millions': Decimal(1000000),
            'thousand': Decimal(1000), 'thousands': Decimal(1000),
            'billion': Decimal(1000000000), 'billions': Decimal(1000000000),
            'percent': Decimal(1), 'percentage': Decimal(1)}.get(label, decimal(value))


def currency_compatible(a: object, b: object, scale: object) -> bool:
    first, second = norm(a), norm(b)
    return first == second or (scale_factor(scale) == 1 and
        'percent' in first and second in ('not applicable', 'na', ''))


def typed_ai_cells(a: list[dict], b: list[dict]) -> tuple[str, int]:
    matched = set()
    for cell in a:
        value = decimal(cell.get('exact_value'))
        if value is None:
            return 'NON_NUMERIC_CELL_IN_FINANCIAL_SET', len(matched)
        candidates = []
        for j, other in enumerate(b):
            if j in matched:
                continue
            if (decimal(other.get('numeric_value')) == value and
                    same_period(cell.get('column_header', ''), other.get('period_label', '')) and
                    currency_compatible(cell.get('currency'), other.get('currency'), cell.get('scale')) and
                    scale_factor(cell.get('scale')) == scale_factor(other.get('scale'))):
                candidates.append(j)
        if not candidates:
            if len(matched) == len(b):
                return 'A1_HAS_ADDITIONAL_CELLS', len(matched)
            return 'VALUE_PERIOD_OR_CURRENCY_CONFLICT', len(matched)
        matched.add(candidates[0])
    return ('FULL_AI_CELL_MAPPING' if len(matched) == len(b) else 'A2_HAS_ADDITIONAL_CELLS'), len(matched)


def grid(row) -> list[tuple[object, int, int]]:
    result, position = [], 0
    for cell in row.xpath('./td|./th'):
        span = int(cell.get('colspan') or '1')
        result.append((cell, position, position + span))
        position += span
    return result


def source_cell_candidates(root, cell: dict, question: str = '') -> list[dict]:
    label, target = norm(cell.get('row_label')), decimal(cell.get('exact_value'))
    year, duration, _ = period_signature(cell.get('column_header', ''))
    if not duration:
        duration = period_signature(question)[1]
    if not label or target is None or not year:
        return []
    candidates = []
    for tr in root.xpath('//tr'):
        cells = grid(tr)
        if not cells or norm(' '.join(cells[0][0].itertext())) != label:
            continue
        for node, start, end in cells[1:]:
            if decimal(''.join(node.itertext())) != target:
                continue
            tables = tr.xpath('ancestor::table[1]')
            if not tables:
                continue
            table = tables[0]
            head_rows = table.xpath('.//tr')[:8]
            year_bound = False
            duration_bound = duration not in ('3M', '6M', '9M')
            for head in head_rows:
                for header, hstart, hend in grid(head):
                    htext = norm(' '.join(header.itertext()))
                    if hstart < end and start < hend:
                        if year in htext:
                            year_bound = True
                        if duration == '3M' and 'three months' in htext:
                            duration_bound = True
                        if duration == '6M' and 'six months' in htext:
                            duration_bound = True
                        if duration == '9M' and 'nine months' in htext:
                            duration_bound = True
            head_text = norm(' '.join(' '.join(r.itertext()) for r in head_rows))
            table_text = norm(' '.join(table.itertext()))
            candidates.append({'cell_xpath': root.getroottree().getpath(node),
                               'row_xpath': root.getroottree().getpath(tr),
                               'table_xpath': root.getroottree().getpath(table),
                               'row_value_pass': True, 'year_column_bound': year_bound,
                               'duration_column_bound': duration_bound,
                               'header_context': head_text[:500],
                               'table_text': table_text,
                               'source_row_text': ' '.join(' '.join(tr.itertext()).split())[:400]})
    return candidates


def statement_score(candidate: dict, statement: str) -> int:
    source, claim = candidate['table_text'], norm(statement)
    if 'balance sheet' in claim:
        return (3 * ('total assets' in source) + 3 * ('total liabilities' in source)
                + 2 * ('stockholders equity' in source))
    if 'statements of operations' in claim or 'statements of income' in claim:
        return (3 * ('net income' in source) + 2 * ('operating income' in source)
                + 2 * ('earnings per share' in source or 'per share' in source)
                + 1 * ('net sales' in source or 'net revenue' in source or 'revenues' in source))
    if 'segment' in claim:
        return 2 * ('segment' in source) + 1 * ('net revenue' in source or 'net sales' in source)
    if 'research and development table' in claim:
        return 2 * ('research and development' in source)
    return 0


def choose_candidate(candidates: list[dict], statement: str = '') -> tuple[str, dict | None]:
    bound = [r for r in candidates if r['year_column_bound'] and r['duration_column_bound']]
    if len(bound) == 1:
        return 'SOURCE_CELL_REVALIDATED', bound[0]
    if len(bound) > 1:
        ranked = sorted(((statement_score(r, statement), r) for r in bound),
                        key=lambda pair: pair[0], reverse=True)
        if ranked[0][0] >= 3 and ranked[0][0] > ranked[1][0]:
            return 'SOURCE_CELL_REVALIDATED_STATEMENT_MATCH', ranked[0][1]
        return 'MULTIPLE_SOURCE_CELLS_REQUIRE_SCOPE_REVIEW', bound[0]
    if candidates:
        return 'SOURCE_ROW_VALUE_VERIFIED_PERIOD_PENDING', candidates[0]
    return 'SOURCE_CELL_NOT_LOCATED', None


def narrative_anchors(root, needles: list[str]) -> tuple[bool, str, str]:
    text = norm(' '.join(root.itertext()))
    matched = [needle for needle in needles if needle in text]
    if len(matched) != len(needles):
        return False, '', '|'.join(needle for needle in needles if needle not in matched)
    first = matched[0]
    candidates = []
    for node in root.xpath('//p|//tr|//td'):
        candidate = norm(' '.join(node.itertext()))
        if first in candidate:
            candidates.append((len(candidate), root.getroottree().getpath(node)))
    locator = min(candidates)[1] if candidates else ''
    return True, locator, ''


class SourceStore:
    def __init__(self, registry: Path, nine_zip: Path, eight_zip: Path, thirty_dir: Path):
        self.registry = json.loads(registry.read_text(encoding='utf-8'))
        if self.registry['verified'] != 47:
            raise ValueError('Source registry is incomplete')
        self.by_acc = {r['accession']: r for r in self.registry['sources']}
        if len(self.by_acc) != 47:
            raise ValueError('Source registry accession uniqueness failed')
        self.zips = {'G3_NINE': zipfile.ZipFile(nine_zip), 'G3R_EIGHT': zipfile.ZipFile(eight_zip)}
        self.thirty_dir = thirty_dir

    @lru_cache(maxsize=4)
    def bytes(self, accession: str) -> bytes:
        item = self.by_acc[accession]
        if item['origin_package'] == 'G3S_THIRTY':
            data = (self.thirty_dir / item['source_zip_member']).read_bytes()
        else:
            data = self.zips[item['origin_package']].read(item['source_zip_member'])
        if sha(data) != item['sha256']:
            raise ValueError(f'Source SHA changed: {accession}')
        return data

    def close(self) -> None:
        for z in self.zips.values():
            z.close()


def audit(prior_path: Path, post_path: Path, source_registry: Path,
          nine_zip: Path, eight_zip: Path, thirty_dir: Path, out: Path) -> dict:
    if out.exists():
        raise FileExistsError(out)
    prior = {r['question_id']: r for r in csv_rows(prior_path.read_bytes())}
    post = {r['question_id']: r for r in csv_rows(post_path.read_bytes())}
    if len(prior) != 94 or len(post) != 94 or set(prior) != set(post):
        raise ValueError('94-question reconciliation does not align')
    store = SourceStore(source_registry, nine_zip, eight_zip, thirty_dir)
    evidence, financial, narrative = [], [], []
    try:
        for qid in sorted(prior):
            r, p = prior[qid], post[qid]
            accession = r['accession']
            source = store.by_acc[accession]
            if r['source_url'] != source['source_url']:
                raise ValueError(f'Question source URL changed: {qid}')
            raw = store.bytes(accession)
            document = html.fromstring(raw)  # HTML scripts are never executed
            a = json.loads(r['agent1_values_json'])
            b = json.loads(r['agent2_values_json'])
            status = 'HUMAN_REVIEW_PENDING'
            cell_levels = []
            if r['classification'] == 'AGREED_SUPPORTED_DECISION_ONLY' and a:
                ai_relation, matched = typed_ai_cells(a, b)
                for index, cell in enumerate(a):
                    candidates = source_cell_candidates(document, cell, r['question'])
                    level, chosen = choose_candidate(candidates, r['agent1_statement'])
                    cell_levels.append(level)
                    financial.append({'question_id': qid, 'cell_index': index,
                                      'accession': accession, 'source_sha256': source['sha256'],
                                      'metric': r['agent1_metric'], 'scope': cell.get('scope') or r['agent1_scope'],
                                      'row': cell.get('row_label'), 'period': cell.get('column_header'),
                                      'value_as_printed': cell.get('exact_value'),
                                      'currency': cell.get('currency'), 'scale': cell.get('scale'),
                                      'ai_typed_relation': ai_relation, 'source_evidence_level': level,
                                      'source_locator': chosen['cell_xpath'] if chosen else '',
                                      'source_excerpt': chosen['source_row_text'] if chosen else '',
                                      'source_header_context': chosen['header_context'] if chosen else '',
                                      'candidate_count': len(candidates),
                                      'all_candidate_locators': [x['cell_xpath'] for x in candidates],
                                      'human_decision': ''})
                status = ('SOURCE_CELL_REVALIDATED' if all(x.startswith('SOURCE_CELL_REVALIDATED') for x in cell_levels)
                          and ai_relation == 'FULL_AI_CELL_MAPPING' else
                          'SOURCE_EVIDENCE_PARTIAL_REVIEW_REQUIRED')
            elif r['classification'] == 'AGREED_SUPPORTED_DECISION_ONLY':
                text = norm(' '.join(document.itertext()))
                a_excerpt, b_excerpt = norm(r['agent1_evidence']), norm(r['agent2_evidence'])
                a_found = bool(a_excerpt and a_excerpt[:80] in text)
                b_found = bool(b_excerpt and b_excerpt[:80] in text)
                anchored, locator, missing = narrative_anchors(document, NARRATIVE_NEEDLES.get(qid, [])) if qid in NARRATIVE_NEEDLES else (False, '', '')
                source_excerpt = ' '.join(' '.join(document.xpath(locator)[0].itertext()).split())[:600] if locator else ''
                status = 'SOURCE_PASSAGE_VERIFIED' if anchored else ('SOURCE_PASSAGE_CANDIDATE' if a_found or b_found else 'NARRATIVE_SOURCE_REVIEW_REQUIRED')
                narrative.append({'question_id': qid, 'accession': accession,
                                  'source_sha256': source['sha256'], 'agent1_excerpt_found': a_found,
                                  'agent2_excerpt_found': b_found, 'source_evidence_level': status,
                                  'curated_source_locator': locator, 'missing_anchors': missing,
                                  'source_excerpt': source_excerpt,
                                  'whole_proposition_human_verified': 'NO', 'human_decision': ''})
            elif p['pass'] == 'POST_SOURCE_ADDITIVE':
                status = 'DUAL_AI_CELL_AGREEMENT' if p['cell_relation'] == 'EXACT_CELL_AGREEMENT' else (
                    'UNRESOLVED' if p['decision_relation'] != 'AGREED_SUPPORTED' else 'SOURCE_PASSAGE_CANDIDATE')
                if status == 'SOURCE_PASSAGE_CANDIDATE':
                    narrative.append({'question_id': qid, 'accession': accession,
                                      'source_sha256': source['sha256'], 'agent1_excerpt_found': 'REVIEWED_IN_POST_SOURCE',
                                      'agent2_excerpt_found': 'REVIEWED_IN_POST_SOURCE',
                                      'source_evidence_level': status,
                                      'whole_proposition_human_verified': 'NO', 'human_decision': ''})
            else:
                status = 'HISTORICAL_DISPUTE_SOURCE_AVAILABLE'
            evidence.append({'question_id': qid, 'accession': accession, 'ticker': r['ticker'],
                             'question': r['question'], 'source_url': source['source_url'],
                             'source_sha256': source['sha256'], 'historical_classification': r['classification'],
                             'post_source_decision_relation': p['decision_relation'],
                             'proposed_cell_count': len(a), 'source_cell_levels': '|'.join(cell_levels),
                             'source_evidence_level': status, 'human_review_state': 'PENDING'})
    finally:
        store.close()
    out.mkdir(parents=True)
    write_csv(out / 'V7A_G3S_94_SOURCE_EVIDENCE_AUDIT.csv', evidence)
    (out / 'V7A_G3S_FINANCIAL_CELL_EVIDENCE.jsonl').write_text(
        ''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in financial), encoding='utf-8')
    write_csv(out / 'V7A_G3S_NARRATIVE_SUPPORT_AUDIT.csv', narrative)
    from collections import Counter
    summary = {'questions': len(evidence), 'financial_cells_examined': len(financial),
               'source_evidence_levels': dict(Counter(r['source_evidence_level'] for r in evidence)),
               'cell_levels': dict(Counter(r['source_evidence_level'] for r in financial)),
               'narrative_count': len(narrative), 'human_approved': 0,
               'source_registry_sha256': sha(source_registry.read_bytes())}
    (out / 'V7A_G3S_SOURCE_EVIDENCE_SUMMARY.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('prior', 'post', 'source_registry', 'nine_zip', 'eight_zip', 'thirty_dir', 'out'):
        parser.add_argument('--' + name.replace('_', '-'), type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.prior, args.post, args.source_registry, args.nine_zip,
                           args.eight_zip, args.thirty_dir, args.out), indent=2))

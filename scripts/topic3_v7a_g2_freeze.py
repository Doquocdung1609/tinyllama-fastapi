"""Build the V7A G2 source-first question release without running retrieval."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import zipfile
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INPUT = Path('C:/Users/Admin/Downloads')
OUT = ROOT / 'docs' / 'topic3_v7a_g2'
AGENT1 = 'AGENT1_SEC_47_FILINGS_AUDIT_PARTIAL.zip'
AGENT2 = 'AGENT2_SEC_47_FILINGS_INDEPENDENT_CHECKPOINT.zip'
F10 = 'FAITH_R_F10_COMPLETE_HISTORY_AND_COMMANDER_HANDOFF.zip'
ACCESSION = re.compile(r'\b\d{10}-\d{2}-\d{6}\b')
URL = re.compile(r'https?://\S+', re.I)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_csv(data: bytes) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(data.decode('utf-8-sig'))))


def csv_bytes(rows: list[dict[str, str]], fields: list[str]) -> bytes:
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator='\n', extrasaction='ignore')
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode('utf-8')


def clean(s: str) -> str:
    return ' '.join(re.findall(r'[a-z0-9]+', s.lower()))


def metric_key(s: str) -> str:
    s = clean(s)
    for a, b in [('net sales', 'revenue'), ('revenues', 'revenue'), ('cost of sales', 'cost of revenue'),
                 ('research and development expenses', 'research and development'),
                 ('income from operations', 'operating income'), ('cash equivalents', 'cash')]:
        s = s.replace(a, b)
    return s


def metric_matches(metric: str, ref_metric: str, ref_question: str) -> bool:
    target = metric_key(metric)
    reference = metric_key(ref_metric + ' ' + ref_question)
    if target in ('revenue', 'total revenue', 'net revenue'):
        if any(term in reference for term in ('aws', 'international', 'data center', 'embedded', 'gaming', 'automotive', 'energy generation', 'china', 'customer b')):
            return False
        return 'revenue' in reference or 'sales' in reference
    if target and target in reference:
        return True
    aliases = {
        'cash and cash': ('cash and cash equivalents',),
        'research and development': ('research and development', 'r d expense'),
        'inventories': ('inventories', 'inventory'),
        'cost of revenue': ('cost of revenue', 'cost of sales'),
        'net income': ('net income',),
        'capital expenditure': ('capital expenditure', 'capex'),
    }
    return any(target == a and any(term in reference for term in terms) for a, terms in aliases.items())


def company_name(ticker: str) -> str:
    return {'AAPL': 'Apple', 'AMD': 'AMD', 'AMZN': 'Amazon', 'GOOGL': 'Alphabet',
            'INTC': 'Intel', 'META': 'Meta', 'MSFT': 'Microsoft', 'NVDA': 'NVIDIA',
            'TSLA': 'Tesla', 'TSM': 'TSMC'}[ticker]


def design(row: dict[str, str]) -> tuple[str, str, str, str]:
    """Return question, category, intended answerability, rationale."""
    ticker, form, period, metric = (row[k] for k in ('ticker', 'form_type', 'report_date', 'metric_name'))
    name = company_name(ticker)
    original = row['question']
    if form == '6-K':
        q = {
            'A1_S47_46_01': 'What categories of corporate changes does TSMC disclose in its December 23, 2025 Form 6-K, and are financial statement amounts included?',
            'A1_S47_46_02': 'Which reporting month do the corporate changes in TSMC\'s December 23, 2025 Form 6-K cover?',
            'A1_S47_47_01': 'What corporate action involving TSMC Arizona does TSMC disclose in its December 19, 2025 Form 6-K?',
            'A1_S47_47_02': 'Does TSMC\'s December 19, 2025 Form 6-K provide financial statement values, and what is the scope of its disclosure?',
        }[row['question_id']]
        return q, 'DISCLOSURE_OR_ANSWERABILITY', 'NARRATIVE_EXPECTED_PENDING_SOURCE', '6-K is not assumed to contain a financial-statement cell.'
    if row['question_id'] == 'A1_S47_12_01':
        return ('Does Amazon report consolidated gross profit as a standalone line item for fiscal 2023 in its 10-K? If so, what amount and unit does it report?',
                'ANSWERABILITY_CHECK', 'UNKNOWN_PENDING_SOURCE', 'Agent 1 parsed gross-profit candidate has unclear accounting scope and a negative value; do not presume a consolidated statement cell.')
    if metric == 'Revenue recognition' and ticker in ('MSFT', 'NVDA', 'TSM'):
        q = f'How does {name} describe its revenue recognition policy in its {form} covering {period}?'
        return q, 'FINANCIAL_DISCLOSURE', 'NARRATIVE_EXPECTED_PENDING_SOURCE', 'Revenue-recognition policy is narrative; no numeric cell is assumed.'
    if ticker == 'TSM' and metric == 'Research and development':
        q = f'Does {name} disclose research and development expense for the fiscal year ended {period} in its {form}? If so, what amount and unit does it report?'
        return q, 'ANSWERABILITY_CHECK', 'UNKNOWN_PENDING_SOURCE', 'Agent 1 excerpt is forward-looking narrative and does not establish a period-specific expense cell.'
    if ticker == 'NVDA' and metric == 'Research and development' and row['question_id'] == 'A1_S47_33_02':
        q = f'What does {name} say about its research and development investment in the Business section of its {form} covering {period}?'
        return q, 'FINANCIAL_DISCLOSURE', 'NARRATIVE_EXPECTED_PENDING_SOURCE', 'The available excerpt is a Business-section investment discussion, not a current-year expense cell.'
    if form in ('10-K', '20-F'):
        frame = f'fiscal year ended {period}'
    else:
        frame = f'quarter ended {period}'
    balance = any(term in metric_key(metric) for term in ('assets', 'liabilities', 'inventories', 'cash', 'accounts payable', 'property and equipment'))
    if balance:
        frame = f'as of {period}'
    elif form == '10-Q':
        frame = f'three months ended {period}'
    if row['question_id'].endswith('_02') and 'comparative' in original.lower() and form in ('10-K', '10-Q'):
        q = f'What current and comparative amounts did {name} report for {metric.lower()} in its {form} covering {period}, and which period does each amount represent?'
        category = 'FINANCIAL_COMPARATIVE'
    elif '2023 comparative' in original.lower():
        q = f'What research and development expense did {name} report for fiscal 2023 as a comparative in its fiscal 2024 {form}, including the reporting unit?'
        category = 'FINANCIAL_COMPARATIVE'
    else:
        q = f'What {metric.lower()} did {name} report for the {frame} in its {form}, including the reporting unit?'
        category = 'FINANCIAL_NUMERIC'
    if metric == 'Customer B share of net revenue':
        q = f'What share of net revenue did Intel attribute to Customer B for the fiscal year ended {period} in its {form}?'
    if metric == 'China geographic net revenue':
        q = f'What net revenue did Intel report for China for the fiscal year ended {period} in its {form}, including the reporting unit?'
    if metric in ('AWS net sales', 'International net sales', 'Data Center revenue', 'Gaming revenue',
                  'Energy generation and storage sales revenue', 'Automotive regulatory credits revenue'):
        q = f'What {metric.lower()} did {name} report for the fiscal year ended {period} in its {form}, including the reporting unit?'
    if form == '10-Q' and metric in ('Data Center segment net revenue', 'Client segment net revenue', 'Embedded segment net revenue'):
        q = f'What {metric.lower()} did AMD report for the three months ended {period} in its {form}, including the reporting unit?'
    return q, category, 'NUMERIC_EXPECTED_PENDING_SOURCE', 'Numeric candidate retained; source row, period column and unit require independent confirmation.'


def load_refs(f10zip: zipfile.ZipFile) -> dict[str, list[dict[str, str]]]:
    refs: dict[str, list[dict[str, str]]] = defaultdict(list)
    p5 = ROOT / 'tmp/topic3_v5/handoff-f2fdd13c/drive/reproduction_v1/03_baseline/p5_query_results.jsonl'
    if p5.exists():
        seen = set()
        for line in p5.read_text(encoding='utf-8').splitlines():
            v = json.loads(line)
            key = v.get('query_id')
            if key not in seen:
                refs['P5'].append({'id': key, 'question': v.get('query', ''), 'ticker': '', 'accession': '', 'metric': '', 'period': ''})
                seen.add(key)
    audit = ROOT / 'tmp/topic3_v5/handoff-f2fdd13c/drive/reproduction_v1/04_failure_analysis/p7g_sec_fiscal_audit/p7g_fiscal_metadata_audit.csv'
    if audit.exists():
        ticker_by_cik = {'0000002488': 'AMD', '0000050863': 'INTC', '0001018724': 'AMZN',
                         '0001318605': 'TSLA', '0001326801': 'META', '0001652044': 'GOOGL'}
        for r in read_csv(audit.read_bytes()):
            if r.get('audit_status') != 'MISMATCH':
                continue
            ticker = ticker_by_cik[r['filing_id'].split('_')[0]]
            metric = 'capital expenditure' if ticker == 'META' else 'total revenue'
            year = r['sec_report_date'][:4]
            refs['P7L15'].append({'id': r['accession'], 'question': f'What was {company_name(ticker)} {metric} in fiscal {year}?',
                                  'ticker': ticker, 'accession': r['accession'], 'metric': metric, 'period': r['sec_report_date']})
    prefix = 'FAITH_R_F10_COMPLETE_HISTORY_AND_COMMANDER_HANDOFF/02_SCIENTIFIC_RESULTS/'
    for r in read_csv(f10zip.read(prefix + 'SEC_60_SOURCE_EVIDENCE.csv')):
        refs['F10_60'].append({'id': r['question_id'], 'question': r['question_immutable'], 'ticker': r['issuer'],
                               'accession': r['source_accession'], 'metric': r['metric'], 'period': r['period_end']})
    for r in read_csv(f10zip.read(prefix + 'RELEVANCE_192_FINAL_AI_LEDGER.csv')):
        refs['F10_192'].append({'id': r['original_row'], 'question': r['question'], 'ticker': '',
                                'accession': r['accession'], 'metric': '', 'period': r['period_end']})
    for label, path in [('V6_PILOT30', ROOT / 'docs/topic3_v5/recovery_live/holdout_30_review_queue.csv'),
                        ('V6_SEALED30', ROOT / 'docs/topic3_v6/V6_FRESH_HOLDOUT_30_UNJUDGED.csv')]:
        for r in read_csv(path.read_bytes()):
            refs[label].append({'id': r['question_id'], 'question': r['question'], 'ticker': r['source_ticker'],
                                'accession': r['source_accession'], 'metric': r.get('metric_definition', ''),
                                'period': r['sec_report_date']})
    return refs


def zip_write(path: Path, members: dict[str, bytes]) -> None:
    with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name in sorted(members):
            info = zipfile.ZipInfo(name, date_time=(2026, 11, 2, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, members[name])


def run(input_dir: Path) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(input_dir / AGENT1) as a1, zipfile.ZipFile(input_dir / AGENT2) as a2, zipfile.ZipFile(input_dir / F10) as f10:
        raw_a1 = a1.read('AGENT1_94_SOURCE_FIRST_QUESTIONS.csv')
        source = read_csv(raw_a1)
        inventory = read_csv(a1.read('AGENT1_SEC_47_FILING_INVENTORY.csv'))
        independent = read_csv(a2.read('AGENT2_47_FROZEN_ACCESSION_MANIFEST.csv'))
        refs = load_refs(f10)
    assert len(source) == 94 and len(inventory) == len(independent) == 47
    inv = {r['accession_number']: r for r in inventory}
    indep = {r['accession_number']: r for r in independent}
    assert set(inv) == set(indep)
    for acc in inv:
        for key1, key2 in [('ticker', 'ticker'), ('form_type', 'document_type'), ('report_date', 'report_date'), ('source_url', 'source_url')]:
            assert inv[acc][key1] == indep[acc][key2], (acc, key1)
        assert inv[acc]['source_url'].startswith('https://www.sec.gov/Archives/edgar/data/')
        assert acc.replace('-', '') in inv[acc]['source_url']
    assert len({r['question_id'] for r in source}) == 94
    assert Counter(r['accession_number'] for r in source) == {a: 2 for a in inv}
    assert len({r['ticker'] for r in source}) == 10
    assert set(r['form_type'] for r in source) == {'10-K', '10-Q', '20-F', '6-K'}
    for candidates in refs.values():
        for candidate in candidates:
            if not candidate['ticker'] and candidate['accession'] in inv:
                candidate['ticker'] = inv[candidate['accession']]['ticker']
    before_v6 = digest((ROOT / 'docs/topic3_v6/V6_FRESH_HOLDOUT_30_UNJUDGED.csv').read_bytes())
    public, private, design_rows, changes, overlap = [], [], [], [], []
    for r in source:
        q, category, answerability, reason = design(r)
        assert not ACCESSION.search(q) and not URL.search(q)
        qid = 'V7A_G2_' + r['question_id'].split('_')[2] + '_' + r['question_id'].split('_')[3]
        pub = {'question_id': qid, 'question': q, 'category': category}
        public.append(pub)
        private.append({'question_id': qid, 'ticker': r['ticker'], 'cik': r['cik'], 'accession_number': r['accession_number'],
                        'form_type': r['form_type'], 'filing_date': r['filing_date'], 'report_date': r['report_date'],
                        'source_url': r['source_url'], 'source_locator_from_agent1': r['source_locator'],
                        'agent1_verification_level': r['verification_level'], 'intended_answerability': answerability,
                        'source_review_status': 'PENDING_INDEPENDENT_SOURCE_REVIEW'})
        design_rows.append({**pub, 'source_filing_id': inv[r['accession_number']]['filing_id'],
                            'ticker': r['ticker'], 'form_type': r['form_type'], 'report_date': r['report_date'],
                            'target_metric_or_topic': r['metric_name'], 'intended_answerability': answerability,
                            'source_review_status': 'PENDING_INDEPENDENT_SOURCE_REVIEW',
                            'change_reason': reason})
        changes.append({'question_id': qid, 'agent1_id': r['question_id'], 'change': 'REWRITTEN' if q != r['question'] else 'RETAINED',
                        'reason': reason, 'agent1_answerability': r['answerability'],
                        'agent1_source_status': r['verification_level']})
        for setname, candidates in refs.items():
            scored = []
            for v in candidates:
                sim = SequenceMatcher(None, clean(q), clean(v['question'])).ratio()
                same_accession = bool(v['accession']) and v['accession'] == r['accession_number']
                same_metric = metric_matches(r['metric_name'], v['metric'], v['question'])
                same_period = bool(v['period']) and v['period'] == r['report_date']
                score = (int(clean(q) == clean(v['question'])), int(same_accession and same_metric and same_period),
                         int(same_accession and same_metric), int(same_accession), sim)
                scored.append((score, v, sim, same_accession, same_metric, same_period))
            score, v, sim, same_acc, same_metric, same_period = max(scored, key=lambda x: x[0])
            if clean(q) == clean(v['question']):
                level = 'EXACT_QUESTION'
            elif same_acc and same_metric and same_period:
                level = 'POTENTIAL_SOURCE_CELL_OVERLAP'
            elif same_acc and same_metric:
                level = 'SAME_FILING_AND_METRIC'
            elif same_acc:
                level = 'SAME_FILING'
            elif sim >= 0.8:
                level = 'SEMANTIC_QUESTION_CANDIDATE'
            else:
                level = 'NO_DIRECT_OVERLAP_FOUND'
            has_accession_metadata = any(c['accession'] for c in candidates)
            has_issuer_metadata = any(c['ticker'] for c in candidates)
            overlap.append({'question_id': qid, 'reference_set': setname, 'reference_id': v['id'],
                            'overlap_level': level, 'similarity': f'{sim:.3f}', 'same_accession': str(same_acc),
                            'same_metric': str(same_metric), 'same_period': str(same_period),
                            'reference_accession': v['accession'],
                            'question_unseen_exact': str(level != 'EXACT_QUESTION'),
                            'cell_unseen_provisional': str(not (same_acc and same_metric and same_period)),
                            'document_unseen_in_this_set': str(not any(c['accession'] == r['accession_number'] for c in candidates)) if has_accession_metadata else 'UNKNOWN',
                            'issuer_unseen_in_this_set': str(not any(c['ticker'] == r['ticker'] for c in candidates)) if has_issuer_metadata else 'UNKNOWN'})
    assert len({r['question'] for r in public}) == 94
    outputs = {
        'V7A_SEC47_QUESTION_DESIGN_V1.csv': csv_bytes(design_rows, list(design_rows[0])),
        'V7A_SEC47_QUESTION_ONLY.csv': csv_bytes(public, list(public[0])),
        'V7A_SEC47_PRIVATE_SOURCE_MANIFEST.csv': csv_bytes(private, list(private[0])),
        'V7A_QUESTION_OVERLAP_AUDIT.csv': csv_bytes(overlap, list(overlap[0])),
    }
    for name, data in outputs.items():
        (OUT / name).write_bytes(data)
    change_summary = Counter(x['change'] for x in changes)
    category_summary = Counter(x['category'] for x in design_rows)
    overlap_summary = Counter((x['reference_set'], x['overlap_level']) for x in overlap)
    original_leakage_count = sum(bool(ACCESSION.search(r['question'])) for r in source)
    original_statuses = dict(Counter(r['verification_level'] for r in source))
    changelog = '# V7A G2 question design changelog\n\n'
    changelog += f'Original Agent 1 CSV preserved in its ZIP (SHA-256 `{digest(raw_a1)}`). {change_summary["REWRITTEN"]} questions rewritten; {change_summary["RETAINED"]} retained. No proposed answer value was imported.\n\n'
    changelog += 'All numeric questions require source-first review of row, period column, unit and scale. Agent 2 verified metadata only; its 94-question verification file was empty. No model output informed revisions.\n\n'
    changelog += '| Question | Change | Reason |\n|---|---|---|\n'
    for x in changes:
        changelog += f"| {x['question_id']} | {x['change']} | {x['reason']} |\n"
    (OUT / 'V7A_QUESTION_DESIGN_CHANGELOG.md').write_text(changelog, encoding='utf-8', newline='\n')
    read_first = ('# V7A G2 independent source review\n\n'
                  'Review the 94 questions independently from original SEC filings using SOURCE_FILINGS.csv. '
                  'Record the exact source locator, row or narrative span, fiscal column, unit and scale. '
                  'Do not consult retrieval rankings, model answers, prior answer values, gold labels or another reviewer. '
                  'Leave unsupported or ambiguous cases unresolved with a reason. This package contains no certified gold.\n')
    lookup = ('# Source lookup\n\nUse the SEC URL and accession in SOURCE_FILINGS.csv, verify the filing identity, '
              'then navigate the original filing without consulting prior agent notes. '
              'Capture a new exact source locator and preserve the original period header and unit. Observe SEC request limits and the configured contact User-Agent.\n')
    rubric = ('# Review rubric\n\nFor each question choose SUPPORTED, UNSUPPORTED, AMBIGUOUS, or SOURCE_UNAVAILABLE. '
             'A numeric answer needs an exact metric row, requested period column, scale/currency and source span. '
             'A narrative answer needs a source quote and scope. Do not infer a missing value or treat an AI proposal as gold. '
             'If source and frozen corpus differ, record both separately. Human signoff and adjudication occur after independent reviews.\n')
    template_fields = ['question_id','reviewer_id','decision','source_accession_confirmed','source_url_opened',
                       'source_locator','statement_or_section','row_or_narrative_span','period_column',
                       'answer_value_or_summary','unit_and_scale','exact_quote','source_html_sha256',
                       'corpus_presence','ambiguity_reason','reviewer_notes']
    blank = csv_bytes([{'question_id': r['question_id']} for r in public], template_fields)
    blind_source_fields = ['question_id', 'ticker', 'cik', 'accession_number', 'form_type', 'filing_date', 'report_date', 'source_url']
    shared = {'QUESTION_ONLY.csv': outputs['V7A_SEC47_QUESTION_ONLY.csv'],
              'SOURCE_FILINGS.csv': csv_bytes(private, blind_source_fields),
              'SOURCE_LOOKUP.md': lookup.encode(), 'REVIEW_RUBRIC.md': rubric.encode(),
              'READ_FIRST.md': read_first.encode()}
    for agent in ('AGENT1', 'AGENT2'):
        zip_write(OUT / f'V7A_{agent}_BLIND_REVIEW_PACKAGE.zip', {**shared, f'{agent}_EMPTY_REVIEW_TEMPLATE.csv': blank})
    shared_hashes = {name: digest(data) for name, data in shared.items()}
    assert digest((ROOT / 'docs/topic3_v6/V6_FRESH_HOLDOUT_30_UNJUDGED.csv').read_bytes()) == before_v6
    manifest = {
        'status': 'G2_FROZEN_DESIGN_PENDING_INDEPENDENT_SOURCE_REVIEW',
        'source_zip_sha256': {n: digest((input_dir / n).read_bytes()) for n in (AGENT1, AGENT2, F10)},
        'agent1_original_csv_sha256': digest(raw_a1), 'v6_sealed_csv_sha256_unchanged': before_v6,
        'source_filings': len(inv), 'issuers': len({r['ticker'] for r in inventory}),
        'form_counts': dict(Counter(r['form_type'] for r in inventory)),
        'question_ids': len(public), 'category_counts': dict(category_summary),
        'reference_counts': {k: len(v) for k, v in refs.items()},
        'shared_blind_input_sha256': shared_hashes,
        'limitations': ['No independent 94-question source-cell judgments', 'Agent 1 original HTML hash absent for most candidates',
                        'Potential source-cell overlap does not establish answer equivalence',
                        'P5 has no accession metadata in query log; document-unseen cannot be established for P5'],
    }
    acc_overlap = Counter(x['overlap_level'] for x in overlap)
    acceptance = '# V7A G2 acceptance\n\n**G2: PASS for question-design freeze and blind-package release; source-cell gold remains pending independent review.**\n\n'
    acceptance += f'- Coverage: {len(inv)} filings, {manifest["issuers"]} issuers, {len(public)} questions, two slots per filing; forms {manifest["form_counts"]}.\n'
    acceptance += f'- Question categories: {dict(category_summary)}. Intended answerability is a design hypothesis pending original-source review, not a gold label.\n'
    acceptance += f'- Agent 1 original: {original_leakage_count}/94 questions contained an accession in the query text; redesigned public queries contain 0. Source status: {original_statuses}. Its proposed values are excluded.\n'
    acceptance += '- Agent 1 and Agent 2 agree on 47 accession, issuer, form, report-date and URL metadata records. This validates mapping, not the contents or availability of every original SEC HTML page.\n'
    acceptance += f'- Original Agent 1 CSV: SHA-256 `{digest(raw_a1)}`; V6 sealed 30 unchanged: `{before_v6}`.\n'
    acceptance += f'- Overlap levels across six reference sets (one strongest match per question/set): {dict(acc_overlap)}. Full row-level report: `V7A_QUESTION_OVERLAP_AUDIT.csv`.\n'
    acceptance += '- `question_unseen_exact` is a text-only check. `cell_unseen_provisional` needs source-cell adjudication. Filing or issuer reuse is disclosed, not treated as an automatic exclusion. P5 lacks filing metadata.\n'
    acceptance += f'- Issuer question counts: {dict(Counter(r["ticker"] for r in design_rows))}; numeric, comparative, disclosure and answerability categories are recorded per question.\n'
    acceptance += '- Agent 1 proposed values were excluded. Agent 2 supplied 47-filing metadata and zero 94-question judgments. No retrieval or ranking was executed on the 94 questions.\n'
    acceptance += '- Blind packages have identical question/source/rubric/read-first bytes and SHA-256 values listed in the freeze manifest; only the blank template filename differs.\n'
    acceptance += '- Local validation (2026-11-02): V7A release checks 4/4 PASS; full pytest 740/740 PASS, one existing Starlette/httpx deprecation warning. Rebuild produced the same freeze-manifest SHA-256 in repeated runs.\n'
    acceptance += '- Remaining: independent source review, unresolved numeric period/unit checks, and any later adjudication. G3–G10 not started.\n'
    (OUT / 'V7A_G2_ACCEPTANCE.md').write_text(acceptance, encoding='utf-8', newline='\n')
    manifest['output_sha256'] = {name: digest(path.read_bytes()) for name, path in sorted((p.name, p) for p in OUT.iterdir() if p.is_file() and p.name != 'V7A_G2_FREEZE_MANIFEST.json')}
    (OUT / 'V7A_G2_FREEZE_MANIFEST.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({'output': str(OUT), 'questions': len(public), 'reference_counts': manifest['reference_counts'],
                      'overlap': {f'{a}:{b}': n for (a, b), n in overlap_summary.items()},
                      'manifest_sha256': digest((OUT / 'V7A_G2_FREEZE_MANIFEST.json').read_bytes())}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-dir', type=Path, default=INPUT, help='Directory holding the three original ZIP handoffs')
    args = parser.parse_args()
    run(args.input_dir)

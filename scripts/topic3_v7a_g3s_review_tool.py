"""Local, append-only human review UI for frozen SEC-47 evidence.

No event is created by loading the page or by the source-audit scripts. A review
event requires an explicit POST from the local browser form with reviewer input.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
from pathlib import Path
import re
from threading import Lock
from urllib.parse import urlparse
import uuid


DECISIONS = {'APPROVE', 'REJECT', 'AMBIGUOUS', 'REQUEST_CORRECTION', 'EXCLUDE'}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def csv_rows(path: Path) -> list[dict]:
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def jsonl_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def casebook_recommendations(path: Path) -> tuple[dict[str, str], dict[str, str]]:
    recommendations, source_excerpts = {}, {}
    for block in re.split(r'(?=^## V7A_G2_)', path.read_text(encoding='utf-8'), flags=re.M):
        match = re.match(r'## (V7A_G2_\d+_\d+)', block)
        if not match:
            continue
        qid = match.group(1)
        rec = re.search(r'^Coordinator recommendation: (.+)$', block, re.M)
        excerpt = re.search(r'^Source row/table: (.+)$', block, re.M)
        if rec:
            recommendations[qid] = rec.group(1)
        if excerpt:
            source_excerpts[qid] = excerpt.group(1)
    return recommendations, source_excerpts


def proposed_cells(raw: str) -> list[dict]:
    try:
        parsed = json.loads(raw or '[]')
        return parsed if isinstance(parsed, list) else []
    except json.JSONDecodeError:
        return []


def build_dataset(queue: Path, evidence: Path, cells: Path, narratives: Path,
                  registry: Path, casebook: Path, post_agent1: Path, out: Path) -> dict:
    if out.exists():
        raise FileExistsError(out)
    review = {r['question_id']: r for r in csv_rows(queue)}
    source_audit = {r['question_id']: r for r in csv_rows(evidence)}
    financial = {}
    for cell in jsonl_rows(cells):
        financial.setdefault(cell['question_id'], []).append(cell)
    narrative = {r['question_id']: r for r in csv_rows(narratives)}
    post = {r['question_id']: r for r in csv_rows(post_agent1)}
    sources = {r['accession']: r for r in json.loads(registry.read_text(encoding='utf-8'))['sources']}
    recommendations, case_excerpts = casebook_recommendations(casebook)
    if len(review) != 94 or len(source_audit) != 94 or set(review) != set(source_audit):
        raise ValueError('Review queue and source audit must have 94 matching IDs')
    records = []
    for qid in sorted(review):
        row, audit = review[qid], source_audit[qid]
        source = sources[row['accession']]
        if source['state'] != 'VERIFIED_RAW_PRIMARY' or row['source_url'] != source['source_url']:
            raise ValueError(f'Unverified source in review queue: {qid}')
        candidates = financial.get(qid, [])
        narrative_row = narrative.get(qid, {})
        excerpt = (case_excerpts.get(qid) or
                   next((c['source_excerpt'] for c in candidates if c.get('source_excerpt')), '') or
                   narrative_row.get('source_excerpt') or
                   (post.get(qid, {}).get('verbatim_evidence_excerpt') or ''))
        if not excerpt:
            excerpt = 'Open the verified original SEC source and inspect the listed locator.'
        priority = (0 if qid in recommendations else 1 if audit['source_evidence_level'] == 'UNRESOLVED'
                    else 2 if audit['source_evidence_level'] == 'SOURCE_EVIDENCE_PARTIAL_REVIEW_REQUIRED'
                    else 3 if audit['source_evidence_level'] == 'SOURCE_PASSAGE_CANDIDATE' else 4)
        records.append({'question_id': qid, 'question': row['question'],
                        'ticker': audit['ticker'], 'accession': row['accession'],
                        'form': source['form'], 'report_date': source['report_date'],
                        'source_url': source['source_url'], 'source_sha256': source['sha256'],
                        'source_excerpt': excerpt[:1200], 'source_evidence_level': audit['source_evidence_level'],
                        'agent1_decision': row['agent1_decision'], 'agent2_decision': row['agent2_decision'],
                        'agent1_locator': row['agent1_locator'], 'agent2_locator': row['agent2_locator'],
                        'agent1_value': row['agent1_value'], 'agent2_value': row['agent2_value'],
                        'agent1_proposed_cells': proposed_cells(row['agent1_value']),
                        'agent2_proposed_cells': proposed_cells(row['agent2_value']),
                        'cell_relation': row['cell_relation'], 'review_reason': row['review_reason'],
                        'candidate_cells': candidates, 'coordinator_recommendation': recommendations.get(qid, ''),
                        'priority': priority, 'question_validity_flag':
                        'REVIEW_WORDING' if qid in {'V7A_G2_25_02', 'V7A_G2_38_01', 'V7A_G2_30_01', 'V7A_G2_32_01'} else ''})
    records.sort(key=lambda r: (r['priority'], r['question_id']))
    dataset = {'schema': 'g3s_human_review_input/v1', 'question_count': 94,
               'source_registry_sha256': sha(registry.read_bytes()),
               'queue_sha256': sha(queue.read_bytes()), 'source_audit_sha256': sha(evidence.read_bytes()),
               'records': records}
    out.write_text(json.dumps(dataset, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return dataset


def event_hash(event: dict) -> str:
    return sha(json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8'))


def verify_events(path: Path) -> list[dict]:
    if not path.exists():
        return []
    result, previous = [], 'GENESIS'
    for index, event in enumerate(jsonl_rows(path), 1):
        actual = event.get('event_sha256')
        body = {k: v for k, v in event.items() if k != 'event_sha256'}
        if body.get('previous_event_sha256') != previous or event_hash(body) != actual:
            raise ValueError(f'Human event hash chain failed at event {index}')
        result.append(event)
        previous = actual
    return result


def validate_review(payload: dict, dataset: dict) -> dict:
    ids = {r['question_id'] for r in dataset['records']}
    qid = str(payload.get('question_id') or '')
    decision = str(payload.get('decision') or '')
    reviewer = str(payload.get('reviewer') or '').strip()
    explanation = str(payload.get('explanation') or '').strip()
    evidence_reference = str(payload.get('evidence_reference') or '').strip()
    erratum_id = str(payload.get('erratum_id') or '').strip()
    if qid not in ids or decision not in DECISIONS:
        raise ValueError('Unknown question or decision')
    if len(reviewer) < 2 or len(reviewer) > 120 or len(explanation) < 12 or len(explanation) > 5000:
        raise ValueError('Reviewer identity or rationale is missing/invalid')
    if len(evidence_reference) < 5 or len(evidence_reference) > 1500:
        raise ValueError('Evidence reference is required')
    if len(erratum_id) > 120:
        raise ValueError('Erratum identifier is too long')
    if payload.get('evidence_sha256') != dataset['evidence_sha256']:
        raise ValueError('Review input version changed; reload the page')
    if payload.get('human_interaction_ack') is not True:
        raise ValueError('Explicit human review acknowledgement required')
    return {'question_id': qid, 'decision': decision, 'reviewer': reviewer,
            'explanation': explanation, 'evidence_reference': evidence_reference,
            'erratum_id': erratum_id,
            'evidence_sha256': dataset['evidence_sha256']}


def append_event(path: Path, payload: dict, dataset: dict) -> dict:
    review = validate_review(payload, dataset)
    previous_events = verify_events(path)
    body = {**review, 'event_id': str(uuid.uuid4()),
            'reviewed_utc': datetime.now(timezone.utc).isoformat(),
            'previous_event_sha256': previous_events[-1]['event_sha256'] if previous_events else 'GENESIS'}
    event = {**body, 'event_sha256': event_hash(body)}
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a', encoding='utf-8', newline='\n') as f:
        f.write(json.dumps(event, ensure_ascii=False, separators=(',', ':')) + '\n')
        f.flush()
    return event


def release_preview(dataset: dict, events_path: Path) -> dict:
    """Export human-reviewed subset metadata, never fabricate or score gold."""
    events = verify_events(events_path)
    latest = {event['question_id']: event for event in events}
    approved, blocked, excluded, pending = [], [], [], []
    for record in dataset['records']:
        qid = record['question_id']
        event = latest.get(qid)
        if event is None:
            pending.append(qid)
            continue
        if event['decision'] == 'EXCLUDE':
            excluded.append({'question_id': qid, 'event_sha256': event['event_sha256']})
            continue
        if event['decision'] != 'APPROVE':
            blocked.append({'question_id': qid, 'reason': event['decision'],
                            'event_sha256': event['event_sha256']})
            continue
        if record['question_validity_flag'] and not event.get('erratum_id'):
            blocked.append({'question_id': qid, 'reason': 'ERRATUM_REQUIRED',
                            'event_sha256': event['event_sha256']})
            continue
        if record['source_evidence_level'] in ('UNRESOLVED', 'HISTORICAL_DISPUTE_SOURCE_AVAILABLE',
                                                'SOURCE_EVIDENCE_PARTIAL_REVIEW_REQUIRED',
                                                'SOURCE_PASSAGE_CANDIDATE'):
            blocked.append({'question_id': qid, 'reason': 'STRUCTURED_SOURCE_EVIDENCE_REQUIRED',
                            'event_sha256': event['event_sha256']})
            continue
        approved.append({'question_id': qid, 'source_accession': record['accession'],
                         'source_sha256': record['source_sha256'],
                         'review_event_sha256': event['event_sha256'],
                         'reviewer': event['reviewer'], 'reviewed_utc': event['reviewed_utc'],
                         'decision': event['decision'], 'evidence_reference': event['evidence_reference'],
                         'erratum_id': event.get('erratum_id') or '',
                         'source_cell_candidates': record['candidate_cells'],
                         'original_chunk_qrels': 'UNJUDGED'})
    return {'schema': 'g3s_human_reviewed_subset/v1',
            'status': 'REVIEW_PREVIEW_NOT_FINAL_BENCHMARK',
            'question_manifest_count': 94, 'approved_count': len(approved),
            'pending_count': len(pending), 'blocked_count': len(blocked),
            'excluded_count': len(excluded),
            'selection_method': 'chronological human review progress; not an unbiased full benchmark',
            'source_dataset_sha256': dataset['evidence_sha256'],
            'f10_policy': 'ORIGINAL_SINGLE_CHUNK_ONLY; supplemental source evidence is not retrieval credit',
            'approved': approved, 'blocked': blocked, 'excluded': excluded, 'pending': pending}


def create_handler(dataset: dict, events_path: Path, html_path: Path):
    write_lock = Lock()
    class Handler(BaseHTTPRequestHandler):
        def send(self, code: int, body: bytes, content_type: str):
            self.send_response(code)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; connect-src 'self'; base-uri 'none'")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):  # noqa: N802
            path = urlparse(self.path).path
            if path == '/':
                self.send(200, html_path.read_bytes(), 'text/html; charset=utf-8')
            elif path == '/api/questions':
                current = {e['question_id']: e for e in verify_events(events_path)}
                body = json.dumps({**dataset, 'reviews': current}, ensure_ascii=False).encode('utf-8')
                self.send(200, body, 'application/json; charset=utf-8')
            elif path == '/api/health':
                self.send(200, json.dumps({'status': 'READY', 'questions': 94,
                                           'events': len(verify_events(events_path))}).encode(), 'application/json')
            else:
                self.send(404, b'Not found', 'text/plain')

        def do_POST(self):  # noqa: N802
            if urlparse(self.path).path != '/api/reviews':
                self.send(404, b'Not found', 'text/plain')
                return
            try:
                size = int(self.headers.get('Content-Length') or '0')
                if not 0 < size <= 10000:
                    raise ValueError('Invalid request size')
                payload = json.loads(self.rfile.read(size))
                with write_lock:
                    event = append_event(events_path, payload, dataset)
                self.send(201, json.dumps(event, ensure_ascii=False).encode(), 'application/json; charset=utf-8')
            except (ValueError, json.JSONDecodeError) as exc:
                self.send(400, json.dumps({'error': str(exc)}).encode(), 'application/json')

        def log_message(self, format, *args):
            return  # avoid logging source question and reviewer identity

    return Handler


def serve(dataset_path: Path, events_path: Path, html_path: Path, port: int):
    dataset = json.loads(dataset_path.read_text(encoding='utf-8'))
    if len(dataset['records']) != 94:
        raise ValueError('Review dataset must contain 94 questions')
    dataset['evidence_sha256'] = sha(dataset_path.read_bytes())
    verify_events(events_path)
    server = ThreadingHTTPServer(('127.0.0.1', port), create_handler(dataset, events_path, html_path))
    print(f'G3S review tool: http://127.0.0.1:{port}/ (0 automatic approvals)', flush=True)
    server.serve_forever()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', action='store_true')
    for name in ('queue', 'evidence', 'cells', 'narratives', 'registry', 'casebook',
                 'post_agent1', 'dataset', 'events', 'html'):
        parser.add_argument('--' + name.replace('_', '-'), type=Path)
    parser.add_argument('--port', type=int, default=18747)
    parser.add_argument('--export', type=Path)
    args = parser.parse_args()
    if args.build:
        required = (args.queue, args.evidence, args.cells, args.narratives,
                    args.registry, args.casebook, args.post_agent1, args.dataset)
        if any(p is None for p in required):
            parser.error('Build requires queue, evidence, cells, narratives, registry, casebook, post-agent1 and dataset')
        result = build_dataset(args.queue, args.evidence, args.cells, args.narratives,
                               args.registry, args.casebook, args.post_agent1, args.dataset)
        print(args.dataset, len(result['records']), sha(args.dataset.read_bytes()))
    elif args.export is not None:
        if args.dataset is None or args.events is None:
            parser.error('Export requires dataset and events')
        if args.export.exists():
            raise FileExistsError(args.export)
        dataset = json.loads(args.dataset.read_text(encoding='utf-8'))
        dataset['evidence_sha256'] = sha(args.dataset.read_bytes())
        result = release_preview(dataset, args.events)
        args.export.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(args.export, result['approved_count'], sha(args.export.read_bytes()))
    else:
        if args.dataset is None or args.events is None or args.html is None:
            parser.error('Serve requires dataset, events and html')
        serve(args.dataset, args.events, args.html, args.port)

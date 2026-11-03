"""Local blind original-chunk human review; no automatic approval or gold export."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from threading import Lock
from urllib.parse import parse_qs, urlparse
import uuid

from scripts.topic3_g3u_pool import FORBIDDEN_BLIND_KEYS


DECISIONS = {'EXACT', 'PARTIAL', 'NONE', 'DISPUTED', 'SOURCE_INSUFFICIENT'}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(data: dict) -> bytes:
    return json.dumps(data, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':')).encode('utf-8')


def load_queue(path: Path) -> tuple[list[dict], str]:
    raw = path.read_bytes()
    rows = [json.loads(s) for s in raw.splitlines() if s]
    pairs = {(r['question_id'], r['chunk_id']) for r in rows}
    if not rows or len(pairs) != len(rows) or len({r['question_id'] for r in rows}) != 94:
        raise ValueError('Blind queue incomplete/duplicate')
    if any(FORBIDDEN_BLIND_KEYS & set(r) for r in rows):
        raise ValueError('Rank/method/score leaked into human UI input')
    return rows, sha(raw)


def verify_events(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = [json.loads(s) for s in path.read_text(encoding='utf-8').splitlines() if s]
    previous = 'GENESIS'
    ids = set()
    for event in rows:
        body = {k: v for k, v in event.items() if k != 'event_sha256'}
        if (body.get('previous_event_sha256') != previous or
                sha(canonical(body)) != event.get('event_sha256') or
                event.get('event_id') in ids or
                event.get('reviewer_type') != 'HUMAN_SELF_DECLARED'):
            raise ValueError('Chunk human event hash/schema chain failed')
        ids.add(event['event_id'])
        previous = event['event_sha256']
    return rows


def validate(payload: dict, queue: dict[tuple[str, str], dict], queue_sha: str) -> dict:
    qid, cid = str(payload.get('question_id', '')), str(payload.get('chunk_id', ''))
    reviewer = str(payload.get('reviewer', '')).strip()
    reason = str(payload.get('reason', '')).strip()
    evidence = str(payload.get('evidence_reference', '')).strip()
    if (qid, cid) not in queue or payload.get('queue_sha256') != queue_sha:
        raise ValueError('Unknown chunk or changed blind queue')
    if (payload.get('decision') not in DECISIONS or
            not 2 <= len(reviewer) <= 120 or not 20 <= len(reason) <= 6000 or
            not 5 <= len(evidence) <= 1500 or payload.get('human_interaction_ack') is not True or
            payload.get('reviewer_type') == 'AI_QREL_PROVISIONAL_DETERMINISTIC_RULES'):
        raise ValueError('Genuine human review fields/acknowledgement required')
    return {'schema': 'g3u_human_original_chunk_event/v1', 'question_id': qid,
            'chunk_id': cid, 'original_text_sha256': queue[(qid, cid)]['original_text_sha256'],
            'decision': payload['decision'], 'reviewer': reviewer, 'reason': reason,
            'evidence_reference': evidence, 'queue_sha256': queue_sha,
            'reviewer_type': 'HUMAN_SELF_DECLARED',
            'identity_assurance': 'SELF_DECLARED_REQUIRES_OWNER_CHECK'}


def serve(dataset: Path, events: Path, html: Path, port: int) -> None:
    if events.resolve() == dataset.resolve() or 'AI_QREL' in events.name.upper():
        raise ValueError('Human events must be separate from blind/AI input')
    rows, digest = load_queue(dataset)
    lookup = {(r['question_id'], r['chunk_id']): r for r in rows}
    lock = Lock()
    priority = {'TWELVE_SOURCE_DISPUTE': 0, 'AMD_CORPUS_GAP': 1,
                'PROSPECTIVE_STRATIFIED': 2, 'GENERAL': 3}
    sorted_rows = sorted(rows, key=lambda r: (priority[r['review_priority']], r['question_id'], r['chunk_id']))
    verify_events(events)

    class Handler(BaseHTTPRequestHandler):
        def _json(self, obj: object, status: int = 200) -> None:
            raw = json.dumps(obj, ensure_ascii=False).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self):  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path == '/':
                raw = html.read_bytes()
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
            elif parsed.path == '/api/health':
                self._json({'status': 'READY', 'pairs': len(rows), 'questions': 94,
                            'human_events': len(verify_events(events)),
                            'queue_sha256': digest})
            elif parsed.path == '/api/candidates':
                query = parse_qs(parsed.query)
                offset = max(0, int(query.get('offset', ['0'])[0]))
                limit = min(100, max(1, int(query.get('limit', ['20'])[0])))
                selected_priority = query.get('priority', ['ALL'])[0]
                filtered = (sorted_rows if selected_priority == 'ALL' else
                            [r for r in sorted_rows if r['review_priority'] == selected_priority])
                selected = filtered[offset:offset + limit]
                self._json({'total': len(filtered), 'offset': offset, 'queue_sha256': digest,
                            'candidates': selected})
            else:
                self._json({'error': 'Not found'}, 404)

        def do_POST(self):  # noqa: N802
            if urlparse(self.path).path != '/api/reviews':
                self._json({'error': 'Not found'}, 404)
                return
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 15000:
                    raise ValueError('Invalid body size')
                payload = json.loads(self.rfile.read(length))
                reviewed = validate(payload, lookup, digest)
                with lock:
                    previous = verify_events(events)
                    body = {**reviewed, 'event_id': str(uuid.uuid4()),
                            'reviewed_utc': datetime.now(timezone.utc).isoformat(),
                            'previous_event_sha256': previous[-1]['event_sha256'] if previous else 'GENESIS'}
                    event = {**body, 'event_sha256': sha(canonical(body))}
                    events.parent.mkdir(parents=True, exist_ok=True)
                    with events.open('a', encoding='utf-8', newline='\n') as stream:
                        stream.write(json.dumps(event, ensure_ascii=False) + '\n')
                        stream.flush()
                self._json({'event_id': event['event_id'], 'decision': event['decision'],
                            'human_event_count': len(previous) + 1})
            except (ValueError, KeyError, json.JSONDecodeError) as exc:
                self._json({'error': str(exc)}, 400)

        def log_message(self, fmt: str, *args: object) -> None:
            return

    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    print(f'G3U blind chunk review: http://127.0.0.1:{port}/ (0 automatic approvals)', flush=True)
    server.serve_forever()


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('dataset', 'events', 'html'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--port', type=int, default=18748)
    serve(**vars(p.parse_args()))

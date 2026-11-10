#!/usr/bin/env python3
r"""Read-only FIS PDF/OCR UTF-8 diagnostic with bounded API timeouts.

Examples (PowerShell, in the worktree):
    python .\FIS_OCR_API_UTF8_DIAGNOSE_V2.py --pages 3 --timeout 10
    python .\FIS_OCR_API_UTF8_DIAGNOSE_V2.py --pages 3,4,5,6,12,13,24 --continue-on-error

Only reads local FIS API. Does NOT OCR, rebuild, overwrite source/indexes, or print the token.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import socket
import sys
import time
import urllib.error
import urllib.request

MARKERS = ('Ã', 'á»', 'Ä', 'Æ', 'â\x80', 'Â')


def corruption_score(text: str) -> int:
    return sum(text.count(part) for part in MARKERS)


def reversible_repair(text: str) -> str | None:
    try:
        candidate = text.encode('latin-1').decode('utf-8', 'strict')
        if candidate.encode('utf-8').decode('latin-1') == text:
            return candidate
    except (UnicodeError, ValueError):
        pass
    return None


def call_json(url: str, token: str, timeout: float) -> tuple[dict, bytes, str, float]:
    req = urllib.request.Request(
        url,
        headers={'Authorization': f'Bearer {token}', 'Accept': 'application/json'},
    )
    t0 = time.monotonic()
    with urllib.request.urlopen(req, timeout=timeout) as response:
        data = response.read()
        content_type = response.headers.get('Content-Type', '')
    elapsed = time.monotonic() - t0
    text = data.decode('utf-8', errors='strict')
    obj = json.loads(text)
    if not isinstance(obj, dict):
        raise ValueError('Expected top-level JSON object')
    return obj, data, content_type, elapsed


def public_error(err: Exception) -> str:
    if isinstance(err, urllib.error.HTTPError):
        return f'HTTP {err.code} {err.reason}'
    if isinstance(err, (TimeoutError, socket.timeout)):
        return 'REQUEST_TIMEOUT (server accepted request but did not respond in time)'
    if isinstance(err, urllib.error.URLError):
        return f'CONNECTION_ERROR ({err.reason})'
    if isinstance(err, (UnicodeError, json.JSONDecodeError)):
        return f'INVALID_UTF8_OR_JSON ({type(err).__name__})'
    return f'{type(err).__name__}: {str(err)[:140]}'


def main() -> int:
    ap = argparse.ArgumentParser(description='Diagnose local FIS OCR JSON encoding (read-only)')
    ap.add_argument('--base', default='http://127.0.0.1:18110/studio')
    ap.add_argument('--token-file', default='tmp/studio-runtime/access-token.txt')
    ap.add_argument('--document-id', default='4a92af827aaf1e73e017544d0ff20d0d')
    ap.add_argument('--pages', default='3')
    ap.add_argument('--timeout', type=float, default=10.0, help='Per page timeout in seconds')
    ap.add_argument('--preflight-timeout', type=float, default=4.0)
    ap.add_argument('--skip-preflight', action='store_true')
    ap.add_argument('--continue-on-error', action='store_true', help='Normally stop at first timeout')
    ap.add_argument('--output', default='tmp/ocr-utf8-api-diagnostic-v2')
    args = ap.parse_args()
    if args.timeout <= 0 or args.preflight_timeout <= 0:
        ap.error('Timeouts must be positive')
    token_file = Path(args.token_file)
    if not token_file.is_file():
        print(f'ERROR: token file not found: {token_file}', file=sys.stderr)
        return 2
    token = token_file.read_text(encoding='utf-8-sig').strip()
    if not token:
        print('ERROR: empty token file', file=sys.stderr)
        return 2
    pages = [int(p.strip()) for p in args.pages.split(',') if p.strip()]
    if not pages or any(p < 1 for p in pages):
        ap.error('--pages requires one or more positive page numbers')
    outdir = Path(args.output)
    outdir.mkdir(parents=True, exist_ok=True)
    report: dict = {'source': 'LOCAL_FIS_API_READ_ONLY', 'document_id': args.document_id,
                    'pages_requested': pages, 'preflight': None, 'pages': []}

    def save_report() -> None:
        (outdir / 'report.json').write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8-sig')

    if not args.skip_preflight:
        print('PREFLIGHT: GET /studio/documents ...', flush=True)
        try:
            obj, _data, _content_type, elapsed = call_json(
                f'{args.base.rstrip("/")}/documents', token, args.preflight_timeout,
            )
            report['preflight'] = {'status': 'OK', 'seconds': round(elapsed, 3),
                                   'document_count': len(obj.get('documents', []))}
            print(f'PREFLIGHT OK in {elapsed:.2f}s', flush=True)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError,
                socket.timeout, OSError, UnicodeError, json.JSONDecodeError,
                ValueError) as err:
            reason = public_error(err)
            report['preflight'] = {'status': 'FAILED', 'error': reason}
            save_report()
            print(f'PREFLIGHT FAILED: {reason}', file=sys.stderr)
            print('Diagnosis: API or server is unavailable/busy; no OCR text was checked.',
                  file=sys.stderr)
            print(f'Report: {outdir / "report.json"}', file=sys.stderr)
            return 3
    failures = 0
    for page in pages:
        print(f'PAGE {page}: requesting source evidence ...', flush=True)
        url = f'{args.base.rstrip("/")}/documents/{args.document_id}/pages/{page}/evidence'
        try:
            obj, data, content_type, elapsed = call_json(url, token, args.timeout)
            extracted = obj.get('text', '')
            if not isinstance(extracted, str):
                raise ValueError('API response .text is not a string')
            score = corruption_score(extracted)
            repaired = reversible_repair(extracted) if score >= 6 else None
            repaired_score = corruption_score(repaired) if repaired is not None else None
            verdict = ('API_TEXT_CONTAINS_REVERSIBLE_MOJIBAKE'
                       if repaired is not None and repaired_score < score
                       else 'API_TEXT_NOT_SYSTEMATICALLY_MOJIBAKE')
            prefix = outdir / f'HPG_page_{page}'
            (outdir / f'HPG_page_{page}.api_utf8.txt').write_text(extracted, encoding='utf-8-sig')
            (outdir / f'HPG_page_{page}.api_raw.json').write_bytes(data)
            if verdict == 'API_TEXT_CONTAINS_REVERSIBLE_MOJIBAKE':
                (outdir / f'HPG_page_{page}.api_display_repair_only.txt').write_text(
                    repaired or '', encoding='utf-8-sig')
            item = {'page': page, 'method': obj.get('method'), 'quality': obj.get('quality'),
                    'content_type': content_type, 'raw_response_sha256': hashlib.sha256(data).hexdigest(),
                    'response_bytes': len(data), 'seconds': round(elapsed, 3),
                    'utf8_valid': True, 'mojibake_score': score,
                    'score_after_display_repair': repaired_score, 'diagnosis': verdict}
            report['pages'].append(item)
            save_report()
            print(f'PAGE {page} OK ({elapsed:.2f}s): {verdict}; score={score}; '
                  f'method={item["method"]}; bytes={len(data)}', flush=True)
            for line in [v.strip() for v in extracted.splitlines() if v.strip()][:3]:
                print('  RAW:', line[:110], flush=True)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError,
                socket.timeout, OSError, UnicodeError, json.JSONDecodeError,
                ValueError) as err:
            failures += 1
            reason = public_error(err)
            report['pages'].append({'page': page, 'error': reason})
            save_report()
            print(f'PAGE {page} FAILED: {reason}', file=sys.stderr, flush=True)
            if not args.continue_on_error:
                print('Stopping after first failure. Run with --continue-on-error only '
                      'after API is healthy.', file=sys.stderr)
                break
    print(f'Diagnostic report: {outdir / "report.json"}')
    if failures:
        print('At least one API request failed. This does NOT establish an OCR/encoding error.')
        return 4
    print('API requests completed. Inspect raw API text and compare to the PDF image.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

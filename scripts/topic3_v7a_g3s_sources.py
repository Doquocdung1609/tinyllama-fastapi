"""Acquire only missing G2 SEC primary documents; keep raw bytes outside Git."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlparse
import zipfile

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.config import get_settings  # noqa: E402
from app.financial_ingestion.sec_client import SECClient, filing_source_url  # noqa: E402

G2 = ROOT / 'docs/topic3_v7a_g2/V7A_SEC47_PRIVATE_SOURCE_MANIFEST.csv'


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def rows(data: bytes) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(data.decode('utf-8-sig'))))


def index_identity(data: bytes, accession: str, primary: str, form: str) -> dict:
    soup = BeautifulSoup(data, 'html.parser')
    text = soup.get_text(' ', strip=True)
    found = re.search(r'\bForm\s+(10-K|10-Q|20-F|6-K)\b', text, re.I)
    return {'form': found.group(1).upper() if found else None,
            'form_matches': bool(found and found.group(1).upper() == form),
            'accession_present': accession in text,
            'primary_filename_present': primary in text}


def read_existing(nine_zip: Path, eight_zip: Path) -> tuple[dict, dict]:
    existing = {}
    packages = {}
    for label, path in (('G3_NINE', nine_zip), ('G3R_EIGHT', eight_zip)):
        with zipfile.ZipFile(path) as z:
            if z.testzip() is not None:
                raise ValueError(f'{label} ZIP CRC failed')
            packages[label] = {'path': str(path), 'sha256': sha(path.read_bytes())}
            for line in z.read('SHA256SUMS.txt' if label == 'G3_NINE' else 'SOURCE_SHA256SUMS.txt').decode().splitlines():
                expected, member = line.split(None, 1)
                if sha(z.read(member.strip())) != expected:
                    raise ValueError(f'{label}/{member}: SHA256SUMS mismatch')
            if label == 'G3_NINE':
                manifest = json.loads(z.read('V7A_G3_SOURCE_ACQUISITION_MANIFEST.json'))
                for item in manifest['sources']:
                    raw = z.read(item['file'])
                    if sha(raw) != item['sha256'] or not item['identity_pass']:
                        raise ValueError(f'G3 nine raw source failed: {item["accession"]}')
                    existing[item['accession']] = {'origin_package': label, 'source_zip_member': item['file'],
                        'sha256': sha(raw), 'byte_size': len(raw), 'url': item['original_sec_url'],
                        'form': item['form'], 'cik': item['cik'], 'identity_pass': True,
                        'representation_note': item['archive_byte_equivalence']}
            else:
                manifest = json.loads(z.read('ACQUISITION_MANIFEST.json'))
                for item in manifest:
                    raw = z.read(item['file'])
                    index = z.read(item['accession'] + '__index.html')
                    if (sha(raw) != item['sha256'] or sha(index) != item['index_sha256'] or
                            item['http_status'] != 200 or item['index_http_status'] != 200 or
                            not item['index_primary_filename_present'] or not item['index_accession_present']):
                        raise ValueError(f'G3R eight raw source failed: {item["accession"]}')
                    existing[item['accession']] = {'origin_package': label, 'source_zip_member': item['file'],
                        'sha256': sha(raw), 'byte_size': len(raw), 'url': item['url'],
                        'form': item['index_form'], 'identity_pass': True,
                        'representation_note': 'SEC-served response bytes; pristine archive equivalence not asserted'}
    if len(existing) != 17:
        raise ValueError(f'Expected 17 distinct verified sources, found {len(existing)}')
    return existing, packages


def acquire(nine_zip: Path, eight_zip: Path, out: Path) -> dict:
    if out.exists():
        raise FileExistsError(f'Refusing to overwrite source acquisition: {out}')
    frozen = {r['accession_number']: r for r in rows(G2.read_bytes())}
    if len(frozen) != 47 or len({r['ticker'] for r in frozen.values()}) != 10:
        raise ValueError('Frozen G2 47-filing/10-issuer identity invalid')
    existing, packages = read_existing(nine_zip, eight_zip)
    for accession, source in existing.items():
        g2 = frozen.get(accession)
        if g2 is None or g2['source_url'] != source['url'] or g2['form_type'] != source['form']:
            raise ValueError(f'Existing source differs from G2: {accession}')
    missing = {acc: r for acc, r in frozen.items() if acc not in existing}
    if len(missing) != 30:
        raise ValueError(f'Expected 30 missing accessions, found {len(missing)}')
    out.mkdir(parents=True)
    raw_dir, index_dir = out / 'raw', out / 'indexes'
    raw_dir.mkdir()
    index_dir.mkdir()
    client = SECClient(get_settings().sec_user_agent, requests_per_second=1,
                       timeout_seconds=40, max_retries=1)
    acquired, failures = {}, []
    for accession, item in sorted(missing.items()):
        url, form = item['source_url'], item['form_type']
        primary = Path(urlparse(url).path).name
        if url != filing_source_url(item['cik'], accession, primary):
            raise ValueError(f'Frozen URL identity invalid: {accession}')
        source_path = raw_dir / f'{accession}__{primary}'
        index_url = url.rsplit('/', 1)[0] + '/' + accession + '-index.html'
        index_path = index_dir / f'{accession}__index.html'
        record = {'accession': accession, 'cik': item['cik'], 'ticker': item['ticker'],
                  'form': form, 'filing_date': item['filing_date'], 'report_date': item['report_date'],
                  'url': url, 'primary_filename': primary, 'index_url': index_url}
        try:
            result = client.download(url, source_path)
            raw = source_path.read_bytes()
            if result.status_code != 200 or result.final_url != url or 'html' not in (result.content_type or ''):
                raise ValueError('Primary HTTP/final URL/content type invalid')
            low = raw.lower()
            if b'<html' not in low[:8192] or b'</html>' not in low[-8192:]:
                raise ValueError('Primary HTML boundaries invalid')
            index_result = client.download(index_url, index_path)
            index = index_path.read_bytes()
            identity = index_identity(index, accession, primary, form)
            if (index_result.status_code != 200 or index_result.final_url != index_url or
                    not all(identity[k] for k in ('form_matches', 'accession_present', 'primary_filename_present'))):
                raise ValueError('SEC filing-index identity invalid')
            record.update(origin_package='G3S_THIRTY', source_zip_member='raw/' + source_path.name,
                          index_zip_member='indexes/' + index_path.name,
                          sha256=sha(raw), byte_size=len(raw), acquired_utc=result.retrieved_at,
                          http_status=result.status_code, content_type=result.content_type,
                          final_url=result.final_url, index_sha256=sha(index),
                          index_http_status=index_result.status_code, index_identity=identity,
                          table_open_count=low.count(b'<table'), table_close_count=low.count(b'</table>'),
                          identity_pass=True, representation_note='Official SEC-served response bytes; pristine archive equivalence not asserted')
            acquired[accession] = record
            print(f'{accession} PASS {form} {len(raw)} {record["sha256"]}', flush=True)
        except Exception as exc:
            record.update(identity_pass=False, failure_type=type(exc).__name__,
                          failure_reason=str(exc), attempted_utc=datetime.now(timezone.utc).isoformat())
            failures.append(record)
            print(f'{accession} FAIL {type(exc).__name__}: {exc}', flush=True)
    registry = []
    for accession, item in sorted(frozen.items()):
        source = existing.get(accession) or acquired.get(accession)
        registry.append({'accession': accession, 'ticker': item['ticker'], 'cik': item['cik'],
                         'form': item['form_type'], 'report_date': item['report_date'],
                         'source_url': item['source_url'], 'state': 'VERIFIED_RAW_PRIMARY' if source else 'MISSING',
                         **(source or {})})
    manifest = {'schema': 'g3s_sec47_source_registry/v1',
                'frozen_g2_manifest_sha256': sha(G2.read_bytes()), 'expected': 47,
                'verified': sum(r['state'] == 'VERIFIED_RAW_PRIMARY' for r in registry),
                'newly_acquired': len(acquired), 'failed': len(failures),
                'request_rate_per_second': 1, 'contact_user_agent_configured': True,
                'packages': packages, 'sources': registry, 'failures': failures}
    manifest_path = out / 'V7A_G3S_SEC47_RAW_SOURCE_MANIFEST.json'
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    sums = ''.join(sha(p.read_bytes()) + '  ' + p.relative_to(out).as_posix() + '\n'
                   for p in sorted((*raw_dir.iterdir(), *index_dir.iterdir(), manifest_path)))
    (out / 'SHA256SUMS.txt').write_text(sums, encoding='utf-8')
    bundle = out.parent / (out.name + '_SOURCE_HANDOFF.zip')
    if bundle.exists():
        raise FileExistsError(bundle)
    with zipfile.ZipFile(bundle, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for p in sorted((*raw_dir.iterdir(), *index_dir.iterdir(), manifest_path, out / 'SHA256SUMS.txt')):
            z.write(p, p.relative_to(out).as_posix())
    with zipfile.ZipFile(bundle) as z:
        if z.testzip() is not None:
            raise ValueError('New G3S handoff ZIP CRC failed')
        for line in z.read('SHA256SUMS.txt').decode().splitlines():
            expected, member = line.split(None, 1)
            if sha(z.read(member.strip())) != expected:
                raise ValueError(f'New G3S handoff SHA failed: {member}')
    manifest['new_source_zip_path'] = str(bundle)
    manifest['new_source_zip_sha256'] = sha(bundle.read_bytes())
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('nine_zip', 'eight_zip', 'out'):
        parser.add_argument('--' + name.replace('_', '-'), type=Path, required=True)
    args = parser.parse_args()
    result = acquire(args.nine_zip, args.eight_zip, args.out)
    print(json.dumps({k: v for k, v in result.items() if k not in ('sources', 'failures')}, indent=2))

"""Package identical validated G3 source bytes with each G2 blind-review input.

No prior answer, gold label, prediction or other reviewer's annotations are read.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import zipfile


ROOT = Path(__file__).resolve().parents[1]
G2 = ROOT / 'docs/topic3_v7a_g2'


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def add(z: zipfile.ZipFile, name: str, data: bytes) -> None:
    info = zipfile.ZipInfo(name, date_time=(2026, 11, 2, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    z.writestr(info, data)


def release(source_zip: Path, output_dir: Path) -> dict[str, object]:
    source_bytes = source_zip.read_bytes()
    with zipfile.ZipFile(io.BytesIO(source_bytes)) as z:
        if z.testzip() is not None:
            raise ValueError('Source ZIP CRC failed')
        manifest = json.loads(z.read('V7A_G3_SOURCE_ACQUISITION_MANIFEST.json'))
    if manifest['acquired_primary_html'] != 9 or manifest['identity_pass'] != 9:
        raise ValueError('All nine sources must pass before reviewer release')
    source_hash = sha(source_bytes)
    source_by_acc = {r['accession']: r for r in manifest['sources']}
    with (G2 / 'V7A_SEC47_PRIVATE_SOURCE_MANIFEST.csv').open(encoding='utf-8', newline='') as stream:
        g2_rows = list(csv.DictReader(stream))
    ready_rows = []
    for row in g2_rows:
        source = source_by_acc.get(row['accession_number'])
        if source:
            ready_rows.append({'question_id': row['question_id'], 'accession': row['accession_number'],
                               'form': row['form_type'], 'source_url': row['source_url'],
                               'source_zip_member': source['file'], 'source_sha256': source['sha256']})
    if len(ready_rows) != 18:
        raise ValueError('Expected exactly 18 questions mapped to the nine recovered filings')
    table = io.StringIO(newline='')
    writer = csv.DictWriter(table, fieldnames=list(ready_rows[0]), lineterminator='\n')
    writer.writeheader()
    writer.writerows(sorted(ready_rows, key=lambda r: r['question_id']))
    ready_bytes = table.getvalue().encode('utf-8')
    packages: dict[str, object] = {}
    for agent in ('AGENT1', 'AGENT2'):
        blind = (G2 / f'V7A_{agent}_BLIND_REVIEW_PACKAGE.zip').read_bytes()
        with zipfile.ZipFile(io.BytesIO(blind)) as z:
            if z.testzip() is not None:
                raise ValueError(f'{agent} G2 blind ZIP CRC failed')
            if 'QUESTION_ONLY.csv' not in z.namelist() or 'SOURCE_FILINGS.csv' not in z.namelist():
                raise ValueError(f'{agent} G2 blind ZIP incomplete')
        dest = output_dir / f'V7A_G3_{agent}_SOURCE_REVIEW_INPUT_V2.zip'
        if dest.exists():
            raise FileExistsError(f'Refusing to replace reviewer release: {dest}')
        readme = (f'# {agent} independent G3 source review input\n\n'
                  'Unpack the G2 blind question ZIP and the shared SEC source ZIP separately. '
                  'Start with the 18 source-ready questions listed in SOURCE_READY_18.csv. Review them against the original SEC primary HTML and filing-index evidence. '
                  'Record accession, row or narrative span, requested period header, unit/scale, exact source locator and uncertainty. '
                  'Do not consult prior answer values, rankings, F10 labels or the other reviewer. '
                  'Make an additive post-source review delta; do not rewrite your frozen earlier ledger. Freeze and hash the delta before comparison.\n\n'
                  f'SEC source ZIP SHA-256: `{source_hash}`.\n'
                  f'G2 blind ZIP SHA-256: `{sha(blind)}`.\n'
                  'This package contains no reviewed answers or gold.\n').encode()
        with zipfile.ZipFile(dest, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            add(z, 'READ_FIRST.md', readme)
            add(z, 'G3_SEC9_SOURCE_HANDOFF.zip', source_bytes)
            add(z, 'G2_BLIND_QUESTION_INPUT.zip', blind)
            add(z, 'SOURCE_READY_18.csv', ready_bytes)
        packages[agent] = {'path': str(dest), 'sha256': sha(dest.read_bytes()),
                           'source_zip_sha256': source_hash, 'g2_blind_zip_sha256': sha(blind),
                           'source_ready_18_sha256': sha(ready_bytes)}
    return packages


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-zip', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(release(args.source_zip, args.output_dir), indent=2))

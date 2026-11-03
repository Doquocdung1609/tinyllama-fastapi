"""Read-only verification of all three SEC-47 source handoff ZIPs."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import zipfile


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify(manifest_path: Path, frozen_path: Path) -> dict:
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    with frozen_path.open(encoding='utf-8-sig', newline='') as stream:
        frozen = {r['accession_number']: r for r in csv.DictReader(stream)}
    if len(frozen) != 47 or sha(frozen_path.read_bytes()) != manifest['frozen_g2_manifest_sha256']:
        raise ValueError('Frozen filing manifest invalid or changed')
    sources = manifest['sources']
    if len(sources) != 47 or len({x['accession'] for x in sources}) != 47:
        raise ValueError('Source registry must contain 47 distinct accessions')
    checked = 0
    packages = {}
    for name, package in manifest['source_packages'].items():
        path = Path(package['path'])
        if sha(path.read_bytes()) != package['sha256']:
            raise ValueError(f'{name}: package hash mismatch')
        with zipfile.ZipFile(path) as archive:
            if archive.testzip() is not None:
                raise ValueError(f'{name}: ZIP CRC mismatch')
            for source in (x for x in sources if x['origin_package'] == name):
                g2 = frozen[source['accession']]
                if (source['form'] != g2['form_type'] or source['source_url'] != g2['source_url'] or
                        source['cik'] != g2['cik'] or source['state'] != 'VERIFIED_RAW_PRIMARY'):
                    raise ValueError(f'{source["accession"]}: frozen filing identity mismatch')
                raw = archive.read(source['source_zip_member'])
                if sha(raw) != source['sha256'] or len(raw) != source['byte_size']:
                    raise ValueError(f'{source["accession"]}: raw byte integrity mismatch')
                low = raw.lower()
                if b'<html' not in low[:8192] or b'</html>' not in low[-8192:]:
                    raise ValueError(f'{source["accession"]}: HTML boundary mismatch')
                checked += 1
            packages[name] = {'sha256': package['sha256'], 'crc': 'PASS'}
    if checked != 47:
        raise ValueError(f'Only {checked} raw source members verified')
    return {'verified_sources': checked, 'frozen_manifest_sha256': sha(frozen_path.read_bytes()),
            'packages': packages, 'result': 'PASS'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=Path('docs/topic3_v7a_g3/V7A_G3S_SEC47_RAW_SOURCE_MANIFEST.json'))
    parser.add_argument('--frozen', type=Path, default=Path('docs/topic3_v7a_g2/V7A_SEC47_PRIVATE_SOURCE_MANIFEST.csv'))
    args = parser.parse_args()
    print(json.dumps(verify(args.manifest, args.frozen), indent=2))

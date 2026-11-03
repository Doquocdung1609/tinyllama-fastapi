"""Detached byte attestation for frozen Agent 2 V3; never edits the ZIP."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import zipfile


MANIFEST = 'AGENT2_G3_POST_SOURCE_FREEZE_MANIFEST.json'
SUMS = 'SHA256SUMS.txt'


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def attest(source: Path) -> dict:
    with zipfile.ZipFile(source) as z:
        if z.testzip() is not None:
            raise ValueError('ZIP CRC failed')
        manifest = json.loads(z.read(MANIFEST))
        actual = {name: sha(z.read(name)) for name in z.namelist() if not name.endswith('/')}
        sums = {}
        for line in z.read(SUMS).decode().splitlines():
            digest, name = line.split(None, 1)
            name = name.strip()
            if name in sums:
                raise ValueError(f'Duplicate SHA256SUMS member: {name}')
            sums[name] = digest
        if set(sums) != set(actual) - {SUMS}:
            raise ValueError('SHA256SUMS member set incomplete')
        for name, digest in sums.items():
            if actual[name] != digest:
                raise ValueError(f'SHA256SUMS data mismatch: {name}')
        data = {}
        warnings = {}
        for name, declared in manifest['artifact_sha256'].items():
            if name not in actual:
                raise ValueError(f'Manifest member absent: {name}')
            if declared != actual[name]:
                if name in (MANIFEST, SUMS):
                    warnings[name] = {'declared_in_manifest': declared,
                                      'actual_sha256': actual[name]}
                else:
                    raise ValueError(f'Manifest data-member mismatch: {name}')
            else:
                data[name] = actual[name]
    return {'schema': 'g3s_external_hash_attestation/v1',
            'original_zip_sha256': sha(source.read_bytes()),
            'zip_crc': 'PASS', 'sha256sums_entries': 'PASS',
            'manifest_data_members': 'PASS', 'actual_manifest_sha256': actual[MANIFEST],
            'actual_sha256sums_sha256': actual[SUMS],
            'verified_data_member_sha256': data, 'self_reference_warnings': warnings,
            'explanation': 'The manifest declares stale hashes for itself and SHA256SUMS. '
                           'A file cannot reliably contain its own final SHA-256. SHA256SUMS contains '
                           'the actual manifest hash but cannot include its own hash without the same cycle. '
                           'This detached attestation hashes the original immutable ZIP and reports both actual bytes. '
                           'It does not repair or rewrite Agent 2 V3.',
            'verification_code': 'scripts/topic3_v7a_g3s_attest.py'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError(args.out)
    args.out.write_text(json.dumps(attest(args.source), indent=2) + '\n', encoding='utf-8')
    print(args.out, sha(args.out.read_bytes()))

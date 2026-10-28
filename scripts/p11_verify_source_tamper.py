"""Non-destructive P11 source-byte fault injection in an owned temporary copy."""
import argparse
import json
from pathlib import Path
import tempfile

from app.financial_index.corpus import verified_source
from scripts.p11_acquire_official_sec import atomic_json
from scripts.p11_build_dev_indexes import frozen_sources


def verify(root):
    parents, _, _, _, generation = frozen_sources(root)
    frozen = parents[0]["frozen"]
    source = Path(frozen["raw_path"])
    with tempfile.TemporaryDirectory(prefix="p11-tamper-", dir=root) as temporary:
        clone = Path(temporary) / source.name
        raw = source.read_bytes()
        if not raw:
            raise ValueError("P11_EMPTY_SOURCE")
        clone.write_bytes(bytes([raw[0] ^ 1]) + raw[1:])
        changed = {**frozen, "raw_path": str(clone)}
        try:
            verified_source(changed, generation=generation)
        except ValueError as exc:
            reason = str(exc)
            if reason != "SOURCE_ARTIFACT_HASH_MISMATCH":
                raise
        else:
            raise AssertionError("P11_TAMPERED_SOURCE_ACCEPTED")
    return {"control": "FROZEN_SOURCES_CANONICAL_REPARSE_PASSED",
            "tamper": "ONE_BYTE_MUTATION_REJECTED",
            "reason": reason, "source_sha256": frozen["raw_hash"],
            "generation": generation, "owner_source_modified": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = verify(args.root)
    atomic_json(args.output, result)
    print(json.dumps(result))

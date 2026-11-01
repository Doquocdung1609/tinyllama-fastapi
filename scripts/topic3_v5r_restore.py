"""Verify the V5R handoff and restore isolated, writable Qdrant copies."""

from __future__ import annotations

import hashlib
import io
import json
import sys
import zipfile
from pathlib import Path, PurePosixPath


REPO = Path(__file__).resolve().parents[1]
SOURCE = Path(r"C:\Users\Admin\Downloads\code\FAITH_R_V5_RESTORED_BASELINE_HANDOFF.zip")
WORK = REPO / "tmp/topic3_v5r/restored"
REPORT = REPO / "docs/topic3_v5/recovery_live/restore_manifest.json"
SNAPSHOTS = {"A": "snapshots/FAITH_R_P3D_RECOVERED_8670.zip",
             "B": "snapshots/FAITH_R_P7K_CORRECTED_8670.zip"}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_name(name: str) -> Path:
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or "\\" in name or ":" in name:
        raise ValueError(f"Unsafe ZIP member: {name}")
    return Path(*path.parts)


def main() -> None:
    if not SOURCE.is_file():
        raise SystemExit(f"Missing handoff: {SOURCE}")
    result = {"outer_sha256": digest(SOURCE.read_bytes()), "outer_crc": None, "files": {}, "snapshots": {}}
    with zipfile.ZipFile(SOURCE) as outer:
        result["outer_crc"] = outer.testzip()
        manifest = json.loads(outer.read("COMMANDER_HANDOFF_MANIFEST.json"))
        recovery = json.loads(outer.read("snapshots/COMMANDER_INDEX_RECOVERY_MANIFEST.json"))
        if result["outer_crc"] is not None:
            raise ValueError("Outer ZIP CRC failed")
        for member in outer.namelist():
            safe_name(member)
        for row in manifest["files"]:
            content = outer.read(row["name"])
            good = len(content) == row["size_bytes"] and digest(content) == row["sha256"]
            result["files"][row["name"]] = {"sha256": digest(content), "bytes": len(content), "matches_manifest": good}
            if not good:
                raise ValueError(f"Manifest mismatch: {row['name']}")
        corpus = outer.read("corpus/chunks_frozen.jsonl")
        if digest(corpus) != recovery["corpus_sha256"] or len(corpus.splitlines()) != 8670:
            raise ValueError("Frozen corpus mismatch")
        result["corpus_sha256"] = digest(corpus)
        for arm, member in SNAPSHOTS.items():
            raw = outer.read(member)
            expected = recovery["baseline_archive" if arm == "A" else "corrected_archive"]
            if digest(raw) != expected["sha256"]:
                raise ValueError(f"Nested snapshot checksum mismatch: {arm}")
            with zipfile.ZipFile(io.BytesIO(raw)) as nested:
                bad = nested.testzip()
                if bad is not None:
                    raise ValueError(f"Nested ZIP CRC failed {arm}: {bad}")
                target = WORK / arm
                target.mkdir(parents=True, exist_ok=True)
                for item in nested.infolist():
                    rel = safe_name(item.filename)
                    if item.is_dir() or rel.name == ".lock":
                        continue
                    dest = target / rel
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    data = nested.read(item)
                    if dest.exists():
                        if digest(dest.read_bytes()) != digest(data):
                            raise ValueError(f"Refusing to overwrite modified workspace: {dest}")
                    else:
                        dest.write_bytes(data)
                result["snapshots"][arm] = {"sha256": digest(raw), "crc": bad,
                                             "sqlite_sha256": digest(nested.read("collection/financial_docs/storage.sqlite")),
                                             "collection_meta": json.loads(nested.read("meta.json"))}
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"outer_sha256": result["outer_sha256"], "verified_files": len(result["files"]),
                      "corpus_sha256": result["corpus_sha256"],
                      "snapshots": {k: v["sha256"] for k, v in result["snapshots"].items()}}, indent=2))


if __name__ == "__main__":
    main()

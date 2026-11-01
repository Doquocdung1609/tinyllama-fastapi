"""Audit the supplied FAITH-R archives without mutating their source files."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import zipfile
from collections import Counter
from pathlib import Path, PurePosixPath


CORPUS = "reproduction_v1/01_corpus/chunks_frozen.jsonl"
EXPECTED_CORPUS_SHA256 = "7c6852a8c68ed1c64194c2da9339fbb4719482949e5705596499db53114abb1f"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_members(archive: zipfile.ZipFile) -> list[str]:
    names = []
    for entry in archive.infolist():
        path = PurePosixPath(entry.filename)
        if path.is_absolute() or ".." in path.parts or "\\" in entry.filename or ":" in entry.filename:
            raise ValueError(f"unsafe archive path: {entry.filename!r}")
        names.append(entry.filename)
    return names


def corpus_audit(archive: zipfile.ZipFile) -> dict:
    raw = archive.read(CORPUS)
    counts = Counter()
    filing_ids = set()
    dense_dims = Counter()
    bm25 = Counter()
    splade = Counter()
    ids = set()
    duplicates = []
    for line in io.BytesIO(raw):
        row = json.loads(line)
        counts["chunks"] += 1
        filing_ids.add((row.get("cik"), row.get("accession_number")))
        chunk_id = row.get("chunk_id")
        if chunk_id in ids:
            duplicates.append(chunk_id)
        ids.add(chunk_id)
        vector = row.get("dense_vector")
        dense_dims[len(vector) if isinstance(vector, list) else "MISSING"] += 1
        for name, target in (("bm25", bm25), ("sparse", splade)):
            indices = row.get(f"{name}_indices")
            values = row.get(f"{name}_values")
            target["PRESENT" if isinstance(indices, list) and isinstance(values, list) and len(indices) == len(values) else "MISSING_OR_BAD"] += 1
    return {"sha256": sha256(raw), "expected_sha256": EXPECTED_CORPUS_SHA256,
            "sha256_matches": sha256(raw) == EXPECTED_CORPUS_SHA256,
            "chunk_count": counts["chunks"], "filing_count": len(filing_ids),
            "duplicate_ids": duplicates[:10], "dense_dimensions": dict(dense_dims),
            "bm25_vectors": dict(bm25), "splade_vectors": dict(splade)}


def inventory_audit(repack: zipfile.ZipFile) -> list[dict]:
    manifest = csv.DictReader(io.StringIO(repack.read("COMMANDER_FILE_INVENTORY.csv").decode("utf-8-sig")))
    findings = []
    for row in manifest:
        name = row["filename"]
        paths = [f"EVIDENCE/{name}", name]
        member = next((path for path in paths if path in repack.namelist()), None)
        if member is None:
            findings.append({"filename": name, "status": "MISSING"})
            continue
        data = repack.read(member)
        findings.append({"filename": name, "status": "MATCH" if len(data) == int(row["size_bytes"]) and sha256(data) == row["sha256"] else "MISMATCH",
                         "actual_size": len(data), "actual_sha256": sha256(data)})
    return findings


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True, help="Directory containing the two handoff archives")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    drive = args.source / "FAITH_R_COMMANDER_DRIVE_PART_01_OF_01.zip"
    repack = args.source / "FAITH_R_COMMANDER_COMPLETE_REPACK.zip"
    with zipfile.ZipFile(drive) as a, zipfile.ZipFile(repack) as b:
        names_a, names_b = safe_members(a), safe_members(b)
        inventory = inventory_audit(b)
        report = {"archives": {drive.name: {"sha256": sha256(drive.read_bytes()), "members": len(names_a), "uncompressed_bytes": sum(i.file_size for i in a.infolist()), "bad_crc_member": a.testzip()},
                               repack.name: {"sha256": sha256(repack.read_bytes()), "members": len(names_b), "uncompressed_bytes": sum(i.file_size for i in b.infolist()), "bad_crc_member": b.testzip()}},
                  "inventory": inventory, "inventory_matched": sum(x["status"] == "MATCH" for x in inventory),
                  "corpus": corpus_audit(a),
                  "external_ledger": {"sha256": sha256((args.source / "FAITH_R_EVIDENCE_LEDGER_2026-11-01.md").read_bytes()),
                                      "matches_repack": (args.source / "FAITH_R_EVIDENCE_LEDGER_2026-11-01.md").read_bytes() == b.read("EVIDENCE/FAITH_R_EVIDENCE_LEDGER_2026-11-01.md")}}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"corpus": report["corpus"], "inventory_matched": report["inventory_matched"], "inventory_total": len(inventory), "external_ledger": report["external_ledger"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()

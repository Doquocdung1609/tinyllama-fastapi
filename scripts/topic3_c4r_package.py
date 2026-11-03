"""Package immutable private C4R outputs with per-member SHA/CRC checks."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import zipfile


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def package(private_dir: Path, output_zip: Path, public_manifest: Path) -> dict:
    if output_zip.exists() or public_manifest.exists():
        raise FileExistsError("C4R private handoff already exists")
    files = sorted(p for p in private_dir.rglob("*") if p.is_file() and p != output_zip)
    if not files or not any(p.name == "C4R_NEW_EVALUATION_PRIVATE.json" for p in files):
        raise ValueError("Missing frozen source-first reference")
    metadata = {str(p.relative_to(private_dir)).replace("\\", "/"):
                {"bytes": p.stat().st_size, "sha256": sha(p.read_bytes())} for p in files}
    internal = {"schema": "c4r_private_handoff_sha256/v1",
                "created_utc": datetime.now(timezone.utc).isoformat(),
                "source_truth_not_human_certified": True,
                "files": metadata}
    with zipfile.ZipFile(output_zip, "x", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=6, allowZip64=True) as archive:
        for p in files:
            archive.write(p, str(p.relative_to(private_dir)).replace("\\", "/"))
        archive.writestr("SHA256_MANIFEST.json", json.dumps(internal, indent=2) + "\n")
    with zipfile.ZipFile(output_zip) as archive:
        if archive.testzip() is not None:
            raise ValueError("Private handoff ZIP CRC failure")
        for name, meta in metadata.items():
            raw = archive.read(name)
            if len(raw) != meta["bytes"] or sha(raw) != meta["sha256"]:
                raise ValueError(f"Private handoff member changed: {name}")
    public = {"schema": "c4r_private_handoff_public_manifest/v1",
              "zip_path": str(output_zip), "zip_bytes": output_zip.stat().st_size,
              "zip_sha256": sha(output_zip.read_bytes()),
              "crc_and_member_sha_verified": True,
              "member_count_excluding_manifest": len(files),
              "files": metadata,
              "private_answer_values_in_git": False}
    public_manifest.parent.mkdir(parents=True, exist_ok=True)
    public_manifest.write_text(json.dumps(public, indent=2) + "\n", encoding="utf-8")
    return public


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--private-dir", type=Path, required=True)
    p.add_argument("--output-zip", type=Path, required=True)
    p.add_argument("--public-manifest", type=Path, required=True)
    print(json.dumps(package(**vars(p.parse_args())), indent=2))

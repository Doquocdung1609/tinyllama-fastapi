"""Hash public Topic 3 evidence without reading local tokens or owner workspaces."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "docs/topic3"
OUTPUT = BASE / "09_RELEASE/RELEASE_ARTIFACT_MANIFEST.json"


def main() -> None:
    records = []
    for path in sorted(BASE.rglob("*")):
        if not path.is_file() or path == OUTPUT:
            continue
        relative = path.relative_to(ROOT).as_posix()
        if "/original-author/" in relative or "/tmp/" in relative:
            continue
        blob = path.read_bytes()
        records.append({"path": relative, "bytes": len(blob), "sha256": hashlib.sha256(blob).hexdigest()})
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps({"scope": "COMMITTED_TOPIC3_EVIDENCE_CANDIDATE", "files": records}, indent=2) + "\n", encoding="utf-8")
    print(f"hashed {len(records)} files")


if __name__ == "__main__":
    main()

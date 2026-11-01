"""Copy validated handoff ZIP members to a new local, untracked directory."""

from __future__ import annotations

import argparse
import shutil
import zipfile
from pathlib import Path

from topic3_v5_audit_handoff import safe_members


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    if args.destination.exists():
        raise SystemExit("destination already exists; refusing to overwrite")
    args.destination.mkdir(parents=True)
    for archive_name, subdir in (("FAITH_R_COMMANDER_DRIVE_PART_01_OF_01.zip", "drive"),
                                 ("FAITH_R_COMMANDER_COMPLETE_REPACK.zip", "repack")):
        with zipfile.ZipFile(args.source / archive_name) as archive:
            for name in safe_members(archive):
                if name.endswith("/"):
                    continue
                target = args.destination / subdir / name
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(name) as source, target.open("xb") as dest:
                    shutil.copyfileobj(source, dest)
    print(args.destination.resolve())


if __name__ == "__main__":
    main()

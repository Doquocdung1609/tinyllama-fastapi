"""Conservative Windows path preflight for atomic corpus/index writes."""
from __future__ import annotations

import os
from pathlib import Path


def ensure_path_capacity(root: Path, projected_relative: Path, *, platform: str | None = None) -> None:
    if (platform or os.name) != "nt":
        return
    projected = Path(root).resolve() / projected_relative
    # Keep margin below legacy MAX_PATH because third-party libraries create
    # temporary/nested files below the path supplied by this application.
    if len(str(projected)) >= 250:
        raise ValueError("WINDOWS_PATH_CAPACITY_EXCEEDED")

"""OS-backed exclusive ownership for embedded financial-index Qdrant storage."""
from __future__ import annotations

from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version as package_version
import json
import os
from pathlib import Path
import re

import portalocker


def require_supported_embedded_qdrant() -> str:
    """Fail early instead of letting an incompatible client reinterpret storage."""
    try:
        raw = package_version("qdrant-client")
    except PackageNotFoundError as exc:
        raise RuntimeError("EMBEDDED_QDRANT_CLIENT_VERSION_UNSUPPORTED") from exc
    match = re.match(r"^(\d+)\.(\d+)", raw)
    if match is None or (int(match.group(1)), int(match.group(2))) != (1, 20):
        raise RuntimeError("EMBEDDED_QDRANT_CLIENT_VERSION_UNSUPPORTED")
    return raw


class LocalQdrantOwnership:
    """Hold a kernel lock for one embedded-Qdrant owner; stale files are harmless."""

    def __init__(self, root: Path):
        self.path = Path(root) / ".qdrant-owner.lock"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._stream = self.path.open("a+", encoding="utf-8")
        try:
            portalocker.lock(self._stream, portalocker.LOCK_EX | portalocker.LOCK_NB)
        except portalocker.LockException as exc:
            self._stream.close()
            self._stream = None
            raise RuntimeError("LOCAL_QDRANT_ALREADY_OWNED") from exc
        self._stream.seek(0)
        self._stream.truncate()
        json.dump({"pid": os.getpid(), "acquired_at": datetime.now(timezone.utc).isoformat()},
                  self._stream, sort_keys=True)
        self._stream.flush()
        os.fsync(self._stream.fileno())

    def close(self):
        if self._stream is None:
            return
        try:
            portalocker.unlock(self._stream)
        finally:
            self._stream.close()
            self._stream = None

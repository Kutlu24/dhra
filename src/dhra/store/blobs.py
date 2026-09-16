"""Content-addressed blob store -- DHRA_BUILD_SPEC.md section 4.1.

Written once, never modified, never deleted. Every acquisition writes the
bytes exactly as received before anything else happens (I3, I4).
"""

from __future__ import annotations

import hashlib
from pathlib import Path


class BlobStore:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path_for(self, sha256: str) -> Path:
        return self.root / sha256[:2] / sha256

    def put(self, data: bytes) -> str:
        sha256 = hashlib.sha256(data).hexdigest()
        path = self._path_for(sha256)
        if path.exists():
            # Content-addressed: identical bytes already stored, this is not a mutation.
            return sha256
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_bytes(data)
        tmp.rename(path)  # atomic on same filesystem
        return sha256

    def get(self, sha256: str) -> bytes:
        path = self._path_for(sha256)
        data = path.read_bytes()
        actual = hashlib.sha256(data).hexdigest()
        if actual != sha256:
            raise ValueError(f"Blob corruption: {sha256} resolved to bytes hashing to {actual}")
        return data

    def exists(self, sha256: str) -> bool:
        return self._path_for(sha256).exists()

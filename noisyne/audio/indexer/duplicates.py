from __future__ import annotations

from pathlib import Path
import hashlib


class DuplicateDetector:

    def file_hash(
        self,
        path: str | Path,
        chunk_size: int = 1024 * 1024,
    ) -> str:

        sha = hashlib.sha256()

        with open(path, "rb") as f:

            while True:

                chunk = f.read(chunk_size)

                if not chunk:
                    break

                sha.update(chunk)

        return sha.hexdigest()
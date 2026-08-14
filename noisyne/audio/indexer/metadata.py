from __future__ import annotations

from pathlib import Path


class MetadataExtractor:

    def extract(
        self,
        path: str | Path,
    ) -> dict:

        path = Path(path)

        return {
            "filename": path.name,
            "stem": path.stem,
            "extension": path.suffix.lower(),
            "parent": path.parent.name,
            "path": str(path),
        }
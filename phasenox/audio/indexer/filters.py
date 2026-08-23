from __future__ import annotations

from pathlib import Path


class AudioFilter:

    def accept(
        self,
        path: Path,
    ) -> bool:

        return path.is_file()
"""Qt-backed desktop path resolution."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QStandardPaths


def user_data_directory() -> Path:
    """Return a writable OS-scoped path, never an install-relative fallback."""
    location = QStandardPaths.writableLocation(QStandardPaths.AppLocalDataLocation)
    if not location:
        raise RuntimeError("Qt could not resolve a writable application data directory.")
    return Path(location)

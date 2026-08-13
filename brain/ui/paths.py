"""Qt-backed desktop path resolution."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QStandardPaths

_BACKEND_ROOT_ENVIRONMENT = "SOUNDBRAIN_ROOT"


@dataclass(frozen=True, slots=True)
class DesktopPathLayout:
    root: Path
    state: Path
    logs: Path
    cache: Path
    models: Path
    reports: Path

    @property
    def writable_directories(self) -> tuple[Path, ...]:
        return (self.root, self.state, self.logs, self.cache, self.models, self.reports)


def user_data_directory() -> Path:
    """Return a writable OS-scoped path, never an install-relative fallback."""
    location = QStandardPaths.writableLocation(QStandardPaths.AppLocalDataLocation)
    if not location:
        raise RuntimeError("Qt could not resolve a writable application data directory.")
    return Path(location)


def session_state_path() -> Path:
    """Return the versioned user-scoped desktop session path."""
    return user_data_directory() / "state" / "session-v1.json"


def desktop_path_layout(root: Path | None = None) -> DesktopPathLayout:
    selected_root = root or user_data_directory()
    return DesktopPathLayout(
        root=selected_root,
        state=selected_root / "state",
        logs=selected_root / "logs",
        cache=selected_root / "data" / "cache",
        # runtime.yaml intentionally keeps V1's ../Models convention.
        models=selected_root.parent / "Models",
        reports=selected_root / "reports",
    )


def initialize_user_directories(root: Path | None = None) -> DesktopPathLayout:
    """Create the minimal writable Desktop layout; safe to call repeatedly."""
    layout = desktop_path_layout(root)
    for directory in layout.writable_directories:
        directory.mkdir(parents=True, exist_ok=True)
    return layout


def prepare_packaged_runtime(root: Path | None = None) -> DesktopPathLayout | None:
    """Redirect relative frozen V1 paths outside the read-only application bundle."""
    if not getattr(sys, "frozen", False):
        return None
    layout = desktop_path_layout(root)
    os.environ.setdefault(_BACKEND_ROOT_ENVIRONMENT, str(layout.root.resolve()))
    return initialize_user_directories(layout.root)

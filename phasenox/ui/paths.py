"""Qt-backed active Desktop paths, separate from the backend Data Root."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QStandardPaths


@dataclass(frozen=True, slots=True)
class DesktopStateLayout:
    root: Path
    state: Path
    logs: Path

    @property
    def writable_directories(self) -> tuple[Path, ...]:
        return (self.root, self.state, self.logs)


def user_data_directory() -> Path:
    """Return a writable OS-scoped path, never an install-relative fallback."""
    location = QStandardPaths.writableLocation(QStandardPaths.AppLocalDataLocation)
    if not location:
        raise RuntimeError("Qt could not resolve a writable application data directory.")
    return Path(location)


def session_state_path() -> Path:
    """Return the versioned user-scoped desktop session path."""
    return user_data_directory() / "state" / "session-v1.json"


def desktop_state_layout(root: Path | None = None) -> DesktopStateLayout:
    selected_root = root or user_data_directory()
    return DesktopStateLayout(
        root=selected_root,
        state=selected_root / "state",
        logs=selected_root / "logs",
    )


def initialize_desktop_state(root: Path | None = None) -> DesktopStateLayout:
    """Create only the canonical small-state layout; safe to call repeatedly."""
    layout = desktop_state_layout(root)
    for directory in layout.writable_directories:
        directory.mkdir(parents=True, exist_ok=True)
    return layout


def prepare_packaged_runtime(root: Path | None = None) -> DesktopStateLayout | None:
    """Initialize small state only after a backend root has been selected."""
    if not getattr(sys, "frozen", False):
        return None
    if not os.environ.get("PHASENOX_ROOT", "").strip():
        raise RuntimeError("Packaged startup requires an explicit PHASENOX Data Root.")
    return initialize_desktop_state(root)


# Compatibility names for Sprint 17 callers. They now describe small Desktop
# state only and deliberately have no backend cache/model/report fields.
DesktopPathLayout = DesktopStateLayout
desktop_path_layout = desktop_state_layout
initialize_user_directories = initialize_desktop_state


__all__ = [
    "DesktopPathLayout",
    "DesktopStateLayout",
    "desktop_path_layout",
    "desktop_state_layout",
    "initialize_desktop_state",
    "initialize_user_directories",
    "prepare_packaged_runtime",
    "session_state_path",
    "user_data_directory",
]

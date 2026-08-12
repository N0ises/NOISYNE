"""Desktop logging setup using the OS user-data location."""

from __future__ import annotations

import logging
from pathlib import Path

from .paths import user_data_directory


def configure_logging() -> Path:
    log_directory = user_data_directory() / "logs"
    log_directory.mkdir(parents=True, exist_ok=True)
    log_path = log_directory / "desktop.log"

    root = logging.getLogger()
    if not any(getattr(handler, "_desktop_handler", False) for handler in root.handlers):
        handler = logging.FileHandler(log_path, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        handler._desktop_handler = True  # type: ignore[attr-defined]
        root.addHandler(handler)
        root.setLevel(logging.INFO)
    return log_path

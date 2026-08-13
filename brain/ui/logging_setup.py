"""Desktop logging setup using the OS user-data location."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from .paths import user_data_directory


def configure_logging() -> Path | None:
    log_directory = user_data_directory() / "logs"
    log_path = log_directory / "desktop.log"
    root_logger = logging.getLogger()
    if any(getattr(handler, "_desktop_handler", False) for handler in root_logger.handlers):
        return log_path
    try:
        log_directory.mkdir(parents=True, exist_ok=True)
        handler: logging.Handler = logging.FileHandler(log_path, encoding="utf-8")
    except OSError:
        handler = logging.StreamHandler(sys.stderr)
        log_path = None
    if not any(getattr(item, "_desktop_handler", False) for item in root_logger.handlers):
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        handler._desktop_handler = True  # type: ignore[attr-defined]
        root_logger.addHandler(handler)
        root_logger.setLevel(logging.INFO)
    return log_path

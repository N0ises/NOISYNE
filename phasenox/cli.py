"""Installed console-script entry point for NØISYNE.

The canonical command is ``noisyne``; ``soundbrain`` remains a supported
backward-compatible alias registered in ``pyproject.toml``.
"""

from main import main

__all__ = ["main"]

if __name__ == "__main__":
    raise SystemExit(main())

"""Installed ``phasenox`` console-script entry point."""

from main import main

__all__ = ["main"]

if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import PluginMatch

DEFAULT_REGISTRY_PATH = Path("configs/plugin_registry.json")


class PluginRegistry:
    """Data-only registry of concrete plugin products. No decision logic."""

    def __init__(self, source: Path | dict[str, Any] | None = None) -> None:
        self._plugins: list[PluginMatch] = []

        if isinstance(source, dict):
            self._load_from_dict(source)
        elif isinstance(source, Path):
            self._load_from_path(source)
        elif isinstance(source, str):
            self._load_from_path(Path(source))
        else:
            self._load_default()

    def _load_default(self) -> None:
        if DEFAULT_REGISTRY_PATH.exists():
            self._load_from_path(DEFAULT_REGISTRY_PATH)

    def _load_from_path(self, path: Path) -> None:
        data = json.loads(path.read_text(encoding="utf-8"))
        self._load_from_dict(data)

    def _load_from_dict(self, data: dict[str, Any]) -> None:
        for item in data.get("plugins", []):
            self._plugins.append(
                PluginMatch(
                    brand=item.get("brand", ""),
                    name=item.get("name", ""),
                    formats=item.get("formats", []),
                    category=item.get("category", ""),
                    identifier=item.get("identifier"),
                )
            )

    def register(self, match: PluginMatch) -> None:
        self._plugins.append(match)

    def matches(
        self,
        category: str,
        formats: list[str] | None = None,
    ) -> list[PluginMatch]:
        results = [p for p in self._plugins if p.category == category]
        if formats:
            results = [p for p in results if any(fmt in p.formats for fmt in formats)]
        return results

    def categories(self) -> list[str]:
        return sorted({p.category for p in self._plugins if p.category})

    def __len__(self) -> int:
        return len(self._plugins)

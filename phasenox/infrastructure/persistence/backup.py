"""Non-executing backup-plan abstractions for future persistence migration."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Protocol

from .manifest import PersistenceManifest


class BackupStrategy(str, Enum):
    COLD_DIRECTORY_COPY = "cold_directory_copy"
    SQLITE_BACKUP_API = "sqlite_backup_api"


@dataclass(frozen=True, slots=True)
class BackupItem:
    store_name: str
    source: Path
    destination: Path
    strategy: BackupStrategy

    def to_dict(self) -> dict[str, str]:
        return {
            "destination": str(self.destination),
            "source": str(self.source),
            "store_name": self.store_name,
            "strategy": self.strategy.value,
        }


@dataclass(frozen=True, slots=True)
class BackupPlan:
    active_root: Path
    destination: Path
    source_manifest_sha256: str
    items: tuple[BackupItem, ...]

    @property
    def plan_id(self) -> str:
        payload = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(payload).hexdigest()

    def to_dict(self) -> dict[str, object]:
        return {
            "active_root": str(self.active_root),
            "destination": str(self.destination),
            "items": [item.to_dict() for item in self.items],
            "source_manifest_sha256": self.source_manifest_sha256,
        }


class BackupBackend(Protocol):
    """Interface for a future explicitly selected backup implementation."""

    def backup_directory(self, item: BackupItem) -> None: ...

    def backup_sqlite(self, item: BackupItem) -> None: ...


def create_backup_plan(
    manifest: PersistenceManifest,
    destination: str | Path,
) -> BackupPlan:
    """Create a deterministic plan; this function never creates or copies files."""
    active_root = manifest.inventory.active_root.resolve()
    target = Path(destination).expanduser().resolve()
    if target == active_root or target.is_relative_to(active_root):
        raise ValueError("backup destination must be outside the active application root")

    items = []
    for store in sorted(manifest.inventory.stores, key=lambda item: item.name):
        if not store.exists:
            continue
        try:
            relative = store.path.relative_to(active_root)
        except ValueError:
            relative = Path(store.name)
        strategy = (
            BackupStrategy.COLD_DIRECTORY_COPY
            if store.kind == "chroma"
            else BackupStrategy.SQLITE_BACKUP_API
        )
        item_destination = target / relative
        source = store.path.resolve()
        if item_destination == source or item_destination.is_relative_to(source):
            raise ValueError(f"backup destination overlaps source store: {source}")
        items.append(
            BackupItem(
                store_name=store.name,
                source=source,
                destination=item_destination,
                strategy=strategy,
            )
        )

    return BackupPlan(
        active_root=active_root,
        destination=target,
        source_manifest_sha256=manifest.manifest_sha256,
        items=tuple(items),
    )


__all__ = [
    "BackupBackend",
    "BackupItem",
    "BackupPlan",
    "BackupStrategy",
    "create_backup_plan",
]

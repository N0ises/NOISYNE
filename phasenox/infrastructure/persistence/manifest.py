"""Deterministic persistence manifests."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .inventory import PersistenceInventory

MANIFEST_FORMAT_VERSION = 1


@dataclass(frozen=True, slots=True)
class PersistenceManifest:
    """Canonical JSON representation of a persistence inventory."""

    inventory: PersistenceInventory
    format_version: int = MANIFEST_FORMAT_VERSION

    @property
    def manifest_sha256(self) -> str:
        return hashlib.sha256(_canonical_json_bytes(self._payload())).hexdigest()

    def _payload(self) -> dict[str, object]:
        return {
            "format_version": self.format_version,
            "inventory": self.inventory.to_dict(),
        }

    def to_dict(self) -> dict[str, object]:
        return {
            **self._payload(),
            "manifest_sha256": self.manifest_sha256,
        }

    def to_json(self) -> str:
        return _canonical_json_bytes(self.to_dict()).decode("utf-8") + "\n"


def create_manifest(inventory: PersistenceInventory) -> PersistenceManifest:
    """Create an in-memory manifest without writing to any store."""
    return PersistenceManifest(inventory=inventory)


def manifest_payload_from_json(value: str) -> dict[str, Any]:
    """Parse and verify a serialized manifest without touching persistence."""
    data = json.loads(value)
    if not isinstance(data, dict):
        raise TypeError("manifest must be a JSON object")
    supplied_digest = data.get("manifest_sha256")
    payload = {key: item for key, item in data.items() if key != "manifest_sha256"}
    calculated_digest = hashlib.sha256(_canonical_json_bytes(payload)).hexdigest()
    if supplied_digest != calculated_digest:
        raise ValueError("manifest SHA-256 does not match its payload")
    if data.get("format_version") != MANIFEST_FORMAT_VERSION:
        raise ValueError("unsupported persistence manifest format")
    return data


def write_manifest(manifest: PersistenceManifest, path: str | Path) -> Path:
    """Write exclusively to an explicit destination without replacing an existing manifest."""
    target = Path(path)
    with target.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(manifest.to_json())
    return target


def _canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


__all__ = [
    "MANIFEST_FORMAT_VERSION",
    "PersistenceManifest",
    "create_manifest",
    "manifest_payload_from_json",
    "write_manifest",
]

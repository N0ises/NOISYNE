"""Qt-free contracts for bounded DAW bridge integrations."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class DawConnectionState(StrEnum):
    STOPPED = "stopped"
    BRIDGE_AVAILABLE = "bridge_available"
    CONNECTED = "connected"
    VERSION_MISMATCH = "version_mismatch"


@dataclass(frozen=True, slots=True)
class DawProjectIdentity:
    name: str
    persistent_id: str | None = None


@dataclass(frozen=True, slots=True)
class DawTrackIdentity:
    name: str
    index: int | None = None
    persistent_id: str | None = None


@dataclass(frozen=True, slots=True)
class DawAudioExport:
    export_id: str
    path: Path
    size_bytes: int
    modified_ns: int


@dataclass(frozen=True, slots=True)
class DawImportRequest:
    project: DawProjectIdentity
    track: DawTrackIdentity | None
    audio_export: DawAudioExport


@dataclass(frozen=True, slots=True)
class DawBridgeCapability:
    name: str
    available: bool
    description: str


@dataclass(frozen=True, slots=True)
class DawBridgeStatus:
    state: DawConnectionState
    protocol_version: int
    endpoint: str | None
    client_name: str | None = None
    client_version: str | None = None
    daw_version: str | None = None
    reason: str | None = None
    queued_exports: int = 0


class DawBridgeError(ValueError):
    """Safe protocol error with a stable machine-readable code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


__all__ = [
    "DawAudioExport",
    "DawBridgeCapability",
    "DawBridgeError",
    "DawBridgeStatus",
    "DawConnectionState",
    "DawImportRequest",
    "DawProjectIdentity",
    "DawTrackIdentity",
]

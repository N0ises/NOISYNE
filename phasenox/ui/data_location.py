"""Qt-free Desktop state and backend Data Root selection contracts."""

from __future__ import annotations

import json
import os
import stat
import sys
import threading
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from tempfile import NamedTemporaryFile

ORGANIZATION_NAME = "PHASENOX"
LEGACY_DESKTOP_IDENTITY = "soundbrain.desktop"
CANONICAL_DESKTOP_IDENTITY = "phasenox.desktop"
DATA_ROOT_POINTER_SCHEMA = 1
MAX_POINTER_BYTES = 16 * 1024


class DataRootSource(StrEnum):
    PHASENOX_ENVIRONMENT = "phasenox_environment"
    POINTER = "pointer"
    LEGACY_UPGRADE = "legacy_upgrade"
    NOISYNE_ENVIRONMENT = "noisyne_environment"
    SOUNDBRAIN_ENVIRONMENT = "soundbrain_environment"
    USER = "user"
    INSTALLER = "installer"
    TEMPORARY = "temporary"
    UNSELECTED = "unselected"


class DataRootAvailability(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    NOT_DIRECTORY = "not_directory"
    NOT_READABLE = "not_readable"
    READ_ONLY = "read_only"
    UNSAFE = "unsafe"
    VALIDATION_TIMEOUT = "validation_timeout"
    TEMPORARY = "temporary"
    UNSELECTED = "unselected"


class RecoveryIntent(StrEnum):
    RETRY_DATA_ROOT = "retry_data_root"
    LOCATE_EXISTING_DATA = "locate_existing_data"
    CHOOSE_ANOTHER_LOCATION = "choose_another_location"
    TEMPORARY_SESSION = "temporary_session"
    CHOOSE_LEGACY_SESSION = "choose_legacy_session"
    CHOOSE_CANONICAL_SESSION = "choose_canonical_session"


@dataclass(frozen=True, slots=True)
class DesktopStateLocations:
    organization_root: Path
    legacy_root: Path
    canonical_root: Path
    migration_lock: Path


@dataclass(frozen=True, slots=True)
class DataRootPointer:
    path: Path
    selection_source: DataRootSource
    selected_at: datetime
    schema_version: int = DATA_ROOT_POINTER_SCHEMA


@dataclass(frozen=True, slots=True)
class DataRootSelection:
    path: Path | None
    source: DataRootSource
    availability: DataRootAvailability
    reason_unavailable: str | None = None
    explicitly_selected: bool = False
    legacy_upgrade_compatibility: bool = False
    pointer_source: DataRootSource | None = None

    @property
    def persistent_backend_enabled(self) -> bool:
        return self.path is not None and self.availability is DataRootAvailability.AVAILABLE


@dataclass(frozen=True, slots=True)
class DataRootResolution:
    selection: DataRootSelection
    conflicts: tuple[str, ...] = ()
    pointer_error: str | None = None
    recovery_intents: tuple[RecoveryIntent, ...] = ()

    @property
    def status_code(self) -> str:
        if self.selection.persistent_backend_enabled:
            return "DATA_LOCATION_AVAILABLE"
        if self.selection.source is DataRootSource.TEMPORARY:
            return "TEMPORARY_SESSION"
        return "DATA_LOCATION_UNAVAILABLE"


def normalize_path(value: str | Path) -> Path:
    """Return a deterministic absolute path without requiring it to exist."""
    return Path(value).expanduser().resolve(strict=False)


def organization_state_root(
    *,
    environ: Mapping[str, str] | None = None,
    platform: str | None = None,
    home: Path | None = None,
) -> Path:
    """Resolve the stable per-user organization root without importing Qt."""
    values = os.environ if environ is None else environ
    selected_platform = sys.platform if platform is None else platform
    user_home = Path.home() if home is None else home
    if selected_platform == "win32":
        base = Path(values.get("LOCALAPPDATA") or user_home / "AppData" / "Local")
    elif selected_platform == "darwin":
        base = user_home / "Library" / "Application Support"
    else:
        base = Path(values.get("XDG_DATA_HOME") or user_home / ".local" / "share")
    return normalize_path(base / ORGANIZATION_NAME)


def desktop_state_locations(organization_root: Path | None = None) -> DesktopStateLocations:
    """Return deterministic legacy/canonical locations without touching disk."""
    root = normalize_path(organization_root or organization_state_root())
    return DesktopStateLocations(
        organization_root=root,
        legacy_root=root / LEGACY_DESKTOP_IDENTITY,
        canonical_root=root / CANONICAL_DESKTOP_IDENTITY,
        migration_lock=root / ".desktop-state-migration.lock",
    )


def data_root_pointer_path(canonical_root: Path) -> Path:
    return canonical_root / "state" / "data-root.json"


def read_data_root_pointer(path: Path) -> tuple[DataRootPointer | None, str | None]:
    """Read a bounded pointer without creating, renaming, or rewriting anything."""
    try:
        size = path.stat().st_size
        if size > MAX_POINTER_BYTES:
            return None, "pointer_too_large"
        raw = path.read_bytes()
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict):
            raise TypeError("pointer must be a JSON object")
        if payload.get("schema_version") != DATA_ROOT_POINTER_SCHEMA:
            raise ValueError("unsupported pointer schema")
        raw_path = payload.get("path")
        if not isinstance(raw_path, str) or not raw_path.strip():
            raise ValueError("pointer path is empty")
        source = DataRootSource(str(payload.get("selection_source")))
        if source not in {
            DataRootSource.LEGACY_UPGRADE,
            DataRootSource.USER,
            DataRootSource.INSTALLER,
        }:
            raise ValueError("pointer selection source is not durable")
        selected_at = datetime.fromisoformat(str(payload.get("selected_at")))
        if selected_at.tzinfo is None:
            raise ValueError("pointer timestamp must include a timezone")
        return DataRootPointer(normalize_path(raw_path), source, selected_at), None
    except FileNotFoundError:
        return None, None
    except (OSError, UnicodeDecodeError, ValueError, TypeError, json.JSONDecodeError) as exc:
        return None, f"{type(exc).__name__}: {exc}"


def write_data_root_pointer(path: Path, pointer: DataRootPointer) -> None:
    """Atomically persist a validated durable pointer."""
    if pointer.selection_source not in {
        DataRootSource.LEGACY_UPGRADE,
        DataRootSource.USER,
        DataRootSource.INSTALLER,
    }:
        raise ValueError("Environment and temporary selections must not be persisted.")
    payload = {
        "schema_version": DATA_ROOT_POINTER_SCHEMA,
        "path": str(normalize_path(pointer.path)),
        "selection_source": pointer.selection_source.value,
        "selected_at": pointer.selected_at.astimezone(UTC).isoformat(),
    }
    _atomic_json_write(path, payload)


def validate_data_root(path: Path, *, require_writable: bool = True) -> DataRootAvailability:
    """Validate a selected root without creating or opening backend stores."""
    normalized = normalize_path(path)
    try:
        metadata = normalized.lstat()
    except (FileNotFoundError, OSError):
        return DataRootAvailability.UNAVAILABLE
    if stat.S_ISLNK(metadata.st_mode) or bool(
        getattr(metadata, "st_file_attributes", 0)
        & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    ):
        return DataRootAvailability.UNSAFE
    if not normalized.is_dir():
        return DataRootAvailability.NOT_DIRECTORY
    if not os.access(normalized, os.R_OK):
        return DataRootAvailability.NOT_READABLE
    if require_writable and not os.access(normalized, os.W_OK):
        return DataRootAvailability.READ_ONLY
    return DataRootAvailability.AVAILABLE


def validate_data_root_bounded(
    path: Path,
    *,
    require_writable: bool = True,
    timeout_seconds: float = 2.0,
) -> DataRootAvailability:
    """Bound potentially slow removable/network filesystem validation."""
    result: list[DataRootAvailability] = []

    def validate() -> None:
        result.append(validate_data_root(path, require_writable=require_writable))

    worker = threading.Thread(target=validate, name="data-root-validation", daemon=True)
    worker.start()
    worker.join(timeout=max(0.0, timeout_seconds))
    if worker.is_alive():
        return DataRootAvailability.VALIDATION_TIMEOUT
    return result[0] if result else DataRootAvailability.UNAVAILABLE


def resolve_data_root(
    *,
    pointer_path: Path,
    environ: Mapping[str, str] | None = None,
    legacy_upgrade_root: Path | None = None,
    temporary: bool = False,
    require_writable: bool = True,
) -> DataRootResolution:
    """Apply Desktop precedence and report conflicts without mutating state."""
    values = os.environ if environ is None else environ
    pointer, pointer_error = read_data_root_pointer(pointer_path)
    candidates: list[tuple[DataRootSource, Path, bool, DataRootSource | None]] = []
    canonical_value = values.get("PHASENOX_ROOT", "").strip()
    if canonical_value:
        candidates.append(
            (DataRootSource.PHASENOX_ENVIRONMENT, normalize_path(canonical_value), True, None)
        )
    if pointer is not None:
        candidates.append((DataRootSource.POINTER, pointer.path, True, pointer.selection_source))
    if legacy_upgrade_root is not None:
        candidates.append(
            (
                DataRootSource.LEGACY_UPGRADE,
                normalize_path(legacy_upgrade_root),
                False,
                None,
            )
        )
    for variable, source in (
        ("NOISYNE_ROOT", DataRootSource.NOISYNE_ENVIRONMENT),
        ("SOUNDBRAIN_ROOT", DataRootSource.SOUNDBRAIN_ENVIRONMENT),
    ):
        value = values.get(variable, "").strip()
        if value:
            candidates.append((source, normalize_path(value), True, None))

    if temporary:
        return DataRootResolution(
            DataRootSelection(
                None,
                DataRootSource.TEMPORARY,
                DataRootAvailability.TEMPORARY,
                explicitly_selected=True,
            ),
            pointer_error=pointer_error,
        )
    if not candidates:
        return DataRootResolution(
            DataRootSelection(
                None,
                DataRootSource.UNSELECTED,
                DataRootAvailability.UNSELECTED,
                reason_unavailable="No PHASENOX Data Root has been selected.",
            ),
            pointer_error=pointer_error,
            recovery_intents=_DATA_ROOT_RECOVERY,
        )

    source, path, explicit, pointer_source = candidates[0]
    availability = validate_data_root_bounded(path, require_writable=require_writable)
    conflicts = tuple(
        f"{other_source.value}={other_path}"
        for other_source, other_path, _explicit, _pointer_source in candidates[1:]
        if other_path != path
    )
    reason = None
    recovery = ()
    if availability is not DataRootAvailability.AVAILABLE:
        reason = f"Selected Data Root is {availability.value}: {path}"
        recovery = _DATA_ROOT_RECOVERY
    return DataRootResolution(
        DataRootSelection(
            path,
            source,
            availability,
            reason_unavailable=reason,
            explicitly_selected=explicit,
            legacy_upgrade_compatibility=(
                source is DataRootSource.LEGACY_UPGRADE
                or pointer_source is DataRootSource.LEGACY_UPGRADE
            ),
            pointer_source=pointer_source,
        ),
        conflicts=conflicts,
        pointer_error=pointer_error,
        recovery_intents=recovery,
    )


def _atomic_json_write(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            json.dump(payload, temporary, indent=2, sort_keys=True)
            temporary.write("\n")
            temporary.flush()
            os.fsync(temporary.fileno())
            temporary_path = Path(temporary.name)
        temporary_path.replace(path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


_DATA_ROOT_RECOVERY = (
    RecoveryIntent.RETRY_DATA_ROOT,
    RecoveryIntent.LOCATE_EXISTING_DATA,
    RecoveryIntent.CHOOSE_ANOTHER_LOCATION,
    RecoveryIntent.TEMPORARY_SESSION,
)


__all__ = [
    "CANONICAL_DESKTOP_IDENTITY",
    "DATA_ROOT_POINTER_SCHEMA",
    "LEGACY_DESKTOP_IDENTITY",
    "ORGANIZATION_NAME",
    "DataRootAvailability",
    "DataRootPointer",
    "DataRootResolution",
    "DataRootSelection",
    "DataRootSource",
    "DesktopStateLocations",
    "RecoveryIntent",
    "data_root_pointer_path",
    "desktop_state_locations",
    "normalize_path",
    "organization_state_root",
    "read_data_root_pointer",
    "resolve_data_root",
    "validate_data_root",
    "validate_data_root_bounded",
    "write_data_root_pointer",
]

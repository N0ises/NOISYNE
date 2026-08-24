"""Copy-first migration of small Desktop state across Qt identities."""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Self

from .data_location import (
    CANONICAL_DESKTOP_IDENTITY,
    LEGACY_DESKTOP_IDENTITY,
    DesktopStateLocations,
    RecoveryIntent,
)
from .session_persistence import MAX_SESSION_BYTES, SessionState, validate_session_bytes

MIGRATION_SCHEMA_VERSION = 1
MAX_MARKER_BYTES = 32 * 1024
SESSION_RELATIVE_PATH = Path("state") / "session-v1.json"
MARKER_RELATIVE_PATH = Path("state") / "desktop-state-migration.json"


class SessionFileStatus(StrEnum):
    ABSENT = "absent"
    VALID = "valid"
    CORRUPT = "corrupt"


class SessionMigrationDecision(StrEnum):
    CLEAN_CANONICAL = "clean_canonical"
    MIGRATE_LEGACY = "migrate_legacy"
    USE_CANONICAL = "use_canonical"
    ADOPT_IDENTICAL = "adopt_identical"
    CHOICE_REQUIRED = "choice_required"
    SAFE_DEFAULT_REQUIRED = "safe_default_required"
    RESUME_MIGRATION = "resume_migration"


@dataclass(frozen=True, slots=True)
class SessionInspection:
    path: Path
    status: SessionFileStatus
    size: int = 0
    sha256: str | None = None
    session: SessionState | None = None
    semantic_payload: object | None = None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class MigrationMarker:
    schema_version: int
    status: str
    source_identity: str
    target_identity: str
    source_path: str
    target_path: str
    source_session_sha256: str
    target_session_sha256: str | None
    started_at: str
    completed_at: str | None
    application_version: str


@dataclass(frozen=True, slots=True)
class SessionMigrationPlan:
    decision: SessionMigrationDecision
    legacy: SessionInspection
    canonical: SessionInspection
    marker: MigrationMarker | None = None
    marker_error: str | None = None
    recovery_intents: tuple[RecoveryIntent, ...] = ()
    reason: str | None = None

    @property
    def requires_user_choice(self) -> bool:
        return self.decision in {
            SessionMigrationDecision.CHOICE_REQUIRED,
            SessionMigrationDecision.SAFE_DEFAULT_REQUIRED,
        }


class MigrationLock:
    """Exclusive small-state migration lock with conservative stale recovery."""

    def __init__(self, path: Path, *, stale_after_seconds: float = 15 * 60) -> None:
        self.path = path
        self.stale_after_seconds = stale_after_seconds
        self._held = False

    def __enter__(self) -> Self:
        self.acquire()
        return self

    def __exit__(self, _exc_type, _exc, _traceback) -> None:
        self.release()

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        for _attempt in range(2):
            try:
                descriptor = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError:
                if not self._is_stale():
                    raise RuntimeError("Another Desktop state migration is in progress.") from None
                try:
                    self.path.unlink()
                except FileNotFoundError:
                    pass
                continue
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "pid": os.getpid(),
                        "acquired_at": datetime.now(UTC).isoformat(),
                    },
                    handle,
                    sort_keys=True,
                )
                handle.flush()
                os.fsync(handle.fileno())
            self._held = True
            return
        raise RuntimeError("Could not acquire the Desktop state migration lock.")

    def release(self) -> None:
        if self._held:
            try:
                self.path.unlink()
            except FileNotFoundError:
                pass
            self._held = False

    def _is_stale(self) -> bool:
        try:
            age = time.time() - self.path.stat().st_mtime
        except OSError:
            return False
        return age >= self.stale_after_seconds


def session_path(root: Path) -> Path:
    return root / SESSION_RELATIVE_PATH


def migration_marker_path(root: Path) -> Path:
    return root / MARKER_RELATIVE_PATH


def inspect_session(path: Path) -> SessionInspection:
    """Inspect one session without mutating even corrupt input."""
    try:
        size = path.stat().st_size
        if size > MAX_SESSION_BYTES:
            raise ValueError("Desktop session exceeds the supported size limit.")
        raw = path.read_bytes()
        session = validate_session_bytes(raw)
        payload = json.loads(raw.decode("utf-8"))
        return SessionInspection(
            path=path,
            status=SessionFileStatus.VALID,
            size=len(raw),
            sha256=hashlib.sha256(raw).hexdigest(),
            session=session,
            semantic_payload=payload,
        )
    except FileNotFoundError:
        return SessionInspection(path, SessionFileStatus.ABSENT)
    except (
        OSError,
        UnicodeDecodeError,
        ValueError,
        TypeError,
        KeyError,
        json.JSONDecodeError,
    ) as exc:
        return SessionInspection(
            path,
            SessionFileStatus.CORRUPT,
            error=f"{type(exc).__name__}: {exc}",
        )


def read_migration_marker(path: Path) -> tuple[MigrationMarker | None, str | None]:
    try:
        if path.stat().st_size > MAX_MARKER_BYTES:
            return None, "marker_too_large"
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise TypeError("marker must be a JSON object")
        marker = MigrationMarker(**payload)
        _validate_marker(marker)
        return marker, None
    except FileNotFoundError:
        return None, None
    except (OSError, UnicodeDecodeError, ValueError, TypeError, json.JSONDecodeError) as exc:
        return None, f"{type(exc).__name__}: {exc}"


def plan_session_migration(locations: DesktopStateLocations) -> SessionMigrationPlan:
    """Apply the complete read-only legacy/canonical decision matrix."""
    legacy = inspect_session(session_path(locations.legacy_root))
    canonical = inspect_session(session_path(locations.canonical_root))
    marker, marker_error = read_migration_marker(migration_marker_path(locations.canonical_root))

    if marker is not None and marker.status == "completed":
        if canonical.status is SessionFileStatus.VALID:
            return SessionMigrationPlan(
                SessionMigrationDecision.USE_CANONICAL,
                legacy,
                canonical,
                marker,
                marker_error,
            )
        return _choice_plan(
            legacy,
            canonical,
            marker,
            marker_error,
            "Completed migration marker exists but canonical session is unavailable.",
        )

    if marker is not None and marker.status == "started":
        if (
            legacy.status is SessionFileStatus.VALID
            and legacy.sha256 == marker.source_session_sha256
            and canonical.status is SessionFileStatus.ABSENT
        ):
            return SessionMigrationPlan(
                SessionMigrationDecision.RESUME_MIGRATION,
                legacy,
                canonical,
                marker,
                marker_error,
            )
        return _choice_plan(
            legacy,
            canonical,
            marker,
            marker_error,
            "Interrupted migration source or target changed.",
        )

    if canonical.status is SessionFileStatus.VALID:
        if legacy.status is SessionFileStatus.ABSENT or legacy.status is SessionFileStatus.CORRUPT:
            return SessionMigrationPlan(
                SessionMigrationDecision.USE_CANONICAL,
                legacy,
                canonical,
                marker,
                marker_error,
            )
        if legacy.sha256 == canonical.sha256:
            return SessionMigrationPlan(
                SessionMigrationDecision.ADOPT_IDENTICAL,
                legacy,
                canonical,
                marker,
                marker_error,
            )
        return _choice_plan(
            legacy,
            canonical,
            marker,
            marker_error,
            (
                "Sessions are semantically equal but byte-different."
                if legacy.semantic_payload == canonical.semantic_payload
                else "Legacy and canonical sessions diverge."
            ),
        )

    if canonical.status is SessionFileStatus.CORRUPT:
        return _choice_plan(
            legacy,
            canonical,
            marker,
            marker_error,
            "Canonical session is corrupt and will not be overwritten automatically.",
        )
    if legacy.status is SessionFileStatus.VALID:
        return SessionMigrationPlan(
            SessionMigrationDecision.MIGRATE_LEGACY,
            legacy,
            canonical,
            marker,
            marker_error,
        )
    if legacy.status is SessionFileStatus.CORRUPT:
        return SessionMigrationPlan(
            SessionMigrationDecision.SAFE_DEFAULT_REQUIRED,
            legacy,
            canonical,
            marker,
            marker_error,
            (RecoveryIntent.CHOOSE_CANONICAL_SESSION, RecoveryIntent.LOCATE_EXISTING_DATA),
            "Legacy session is corrupt and was preserved unchanged.",
        )
    return SessionMigrationPlan(
        SessionMigrationDecision.CLEAN_CANONICAL,
        legacy,
        canonical,
        marker,
        marker_error,
    )


def execute_session_migration(
    plan: SessionMigrationPlan,
    locations: DesktopStateLocations,
    *,
    application_version: str,
) -> SessionMigrationPlan:
    """Copy one validated session to an absent target and atomically mark completion."""
    if plan.decision not in {
        SessionMigrationDecision.MIGRATE_LEGACY,
        SessionMigrationDecision.RESUME_MIGRATION,
    }:
        raise ValueError("The session migration plan is not executable.")
    if plan.legacy.sha256 is None:
        raise ValueError("The legacy session has no validated hash.")

    source = plan.legacy.path
    target = plan.canonical.path
    marker_path = migration_marker_path(locations.canonical_root)
    started_at = (
        plan.marker.started_at if plan.marker is not None else datetime.now(UTC).isoformat()
    )
    with MigrationLock(locations.migration_lock):
        current_source = inspect_session(source)
        if (
            current_source.status is not SessionFileStatus.VALID
            or current_source.sha256 != plan.legacy.sha256
        ):
            raise RuntimeError("Legacy session changed after migration discovery.")
        if target.exists():
            raise FileExistsError("Canonical session target already exists.")
        started = MigrationMarker(
            MIGRATION_SCHEMA_VERSION,
            "started",
            LEGACY_DESKTOP_IDENTITY,
            CANONICAL_DESKTOP_IDENTITY,
            str(source),
            str(target),
            current_source.sha256,
            None,
            started_at,
            None,
            application_version,
        )
        _write_marker(marker_path, started)
        _copy_exclusive_verified(source, target, current_source.sha256)
        installed = inspect_session(target)
        if (
            installed.status is not SessionFileStatus.VALID
            or installed.sha256 != current_source.sha256
        ):
            raise RuntimeError("Canonical session validation failed after installation.")
        completed = MigrationMarker(
            MIGRATION_SCHEMA_VERSION,
            "completed",
            LEGACY_DESKTOP_IDENTITY,
            CANONICAL_DESKTOP_IDENTITY,
            str(source),
            str(target),
            current_source.sha256,
            installed.sha256,
            started_at,
            datetime.now(UTC).isoformat(),
            application_version,
        )
        _write_marker(marker_path, completed)
    return plan_session_migration(locations)


def adopt_identical_sessions(
    plan: SessionMigrationPlan,
    locations: DesktopStateLocations,
    *,
    application_version: str,
) -> SessionMigrationPlan:
    if plan.decision is not SessionMigrationDecision.ADOPT_IDENTICAL:
        raise ValueError("Only byte-identical sessions may be adopted automatically.")
    if plan.legacy.sha256 is None or plan.canonical.sha256 != plan.legacy.sha256:
        raise ValueError("Session hashes do not match.")
    now = datetime.now(UTC).isoformat()
    marker = MigrationMarker(
        MIGRATION_SCHEMA_VERSION,
        "completed",
        LEGACY_DESKTOP_IDENTITY,
        CANONICAL_DESKTOP_IDENTITY,
        str(plan.legacy.path),
        str(plan.canonical.path),
        plan.legacy.sha256,
        plan.canonical.sha256,
        now,
        now,
        application_version,
    )
    with MigrationLock(locations.migration_lock):
        _write_marker(migration_marker_path(locations.canonical_root), marker)
    return plan_session_migration(locations)


def _choice_plan(
    legacy: SessionInspection,
    canonical: SessionInspection,
    marker: MigrationMarker | None,
    marker_error: str | None,
    reason: str,
) -> SessionMigrationPlan:
    return SessionMigrationPlan(
        SessionMigrationDecision.CHOICE_REQUIRED,
        legacy,
        canonical,
        marker,
        marker_error,
        (
            RecoveryIntent.CHOOSE_LEGACY_SESSION,
            RecoveryIntent.CHOOSE_CANONICAL_SESSION,
        ),
        reason,
    )


def _copy_exclusive_verified(source: Path, target: Path, expected_hash: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with NamedTemporaryFile(
            mode="wb",
            dir=target.parent,
            prefix=f".{target.name}.",
            suffix=".migration",
            delete=False,
        ) as temporary:
            temporary.write(source.read_bytes())
            temporary.flush()
            os.fsync(temporary.fileno())
            temporary_path = Path(temporary.name)
        staged = inspect_session(temporary_path)
        if staged.status is not SessionFileStatus.VALID or staged.sha256 != expected_hash:
            raise RuntimeError("Staged session validation failed.")
        os.link(temporary_path, target)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def _write_marker(path: Path, marker: MigrationMarker) -> None:
    _validate_marker(marker)
    _atomic_json_write(path, asdict(marker))


def _validate_marker(marker: MigrationMarker) -> None:
    if marker.schema_version != MIGRATION_SCHEMA_VERSION:
        raise ValueError("Unsupported Desktop migration marker schema.")
    if marker.status not in {"started", "completed"}:
        raise ValueError("Unsupported Desktop migration status.")
    if marker.source_identity != LEGACY_DESKTOP_IDENTITY:
        raise ValueError("Unexpected migration source identity.")
    if marker.target_identity != CANONICAL_DESKTOP_IDENTITY:
        raise ValueError("Unexpected migration target identity.")
    if marker.status == "completed" and not marker.target_session_sha256:
        raise ValueError("Completed marker requires a target hash.")


def _atomic_json_write(path: Path, payload: dict[str, object]) -> None:
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


__all__ = [
    "MARKER_RELATIVE_PATH",
    "MIGRATION_SCHEMA_VERSION",
    "SESSION_RELATIVE_PATH",
    "MigrationLock",
    "MigrationMarker",
    "SessionFileStatus",
    "SessionInspection",
    "SessionMigrationDecision",
    "SessionMigrationPlan",
    "adopt_identical_sessions",
    "execute_session_migration",
    "inspect_session",
    "migration_marker_path",
    "plan_session_migration",
    "read_migration_marker",
    "session_path",
]

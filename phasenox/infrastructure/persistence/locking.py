"""Explicit migration lock abstraction, not integrated with runtime writers."""

from __future__ import annotations

import json
import os
import socket
import uuid
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from types import TracebackType
from typing import Self


class MigrationLockError(RuntimeError):
    pass


class MigrationLockHeldError(MigrationLockError):
    pass


class MigrationLockOwnershipError(MigrationLockError):
    pass


@dataclass(frozen=True, slots=True)
class MigrationLockInfo:
    token: str
    pid: int
    hostname: str
    acquired_at: str


class MigrationLock:
    """Crash-visible exclusive sentinel lock requiring explicit acquisition."""

    def __init__(
        self,
        path: str | Path,
        *,
        token_factory: Callable[[], str] | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.path = Path(path).expanduser().resolve()
        self._token_factory = token_factory or (lambda: uuid.uuid4().hex)
        self._clock = clock or (lambda: datetime.now(UTC))
        self._info: MigrationLockInfo | None = None

    @property
    def acquired(self) -> bool:
        return self._info is not None

    def acquire(self) -> MigrationLockInfo:
        if self.acquired:
            raise MigrationLockError("migration lock is already acquired by this instance")
        if not self.path.parent.is_dir():
            raise FileNotFoundError("migration lock parent directory does not exist")

        info = MigrationLockInfo(
            token=self._token_factory(),
            pid=os.getpid(),
            hostname=socket.gethostname(),
            acquired_at=self._clock().astimezone(UTC).isoformat(),
        )
        payload = json.dumps(asdict(info), sort_keys=True, separators=(",", ":")).encode("utf-8")
        flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
        try:
            descriptor = os.open(self.path, flags, 0o600)
        except FileExistsError as exc:
            raise MigrationLockHeldError(f"migration lock already exists: {self.path}") from exc

        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
        except Exception:
            self.path.unlink(missing_ok=True)
            raise

        self._info = info
        return info

    def release(self) -> None:
        if self._info is None:
            raise MigrationLockOwnershipError("migration lock is not owned by this instance")
        current = read_migration_lock(self.path)
        if current is None or current.token != self._info.token:
            raise MigrationLockOwnershipError("migration lock ownership changed")
        self.path.unlink()
        self._info = None

    def __enter__(self) -> Self:
        self.acquire()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.release()


def read_migration_lock(path: str | Path) -> MigrationLockInfo | None:
    """Read lock ownership without acquiring or modifying the lock."""
    lock_path = Path(path)
    try:
        data = json.loads(lock_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    return MigrationLockInfo(
        token=str(data["token"]),
        pid=int(data["pid"]),
        hostname=str(data["hostname"]),
        acquired_at=str(data["acquired_at"]),
    )


__all__ = [
    "MigrationLock",
    "MigrationLockError",
    "MigrationLockHeldError",
    "MigrationLockInfo",
    "MigrationLockOwnershipError",
    "read_migration_lock",
]

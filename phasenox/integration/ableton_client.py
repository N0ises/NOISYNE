"""Separate localhost-only client for an Ableton WAV export workflow."""

from __future__ import annotations

import ctypes
import json
import os
import stat
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .ableton_bridge import (
    ABLETON_EXPORT_HELPER_CLIENT_NAME,
    DEFAULT_MAX_PAYLOAD_BYTES,
    PROTOCOL_VERSION,
)

HANDOFF_SCHEMA_VERSION = 1
HANDOFF_FILENAME = "ableton-bridge-v1.json"
CLIENT_VERSION = "1.0.0"
MAX_HANDOFF_BYTES = 8 * 1024
_ABLETON_PROCESS_PREFIX = "Ableton Live "


@dataclass(frozen=True, slots=True)
class AbletonProcess:
    pid: int
    executable_name: str


class _ProcessEntry32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", ctypes.c_ulong),
        ("cntUsage", ctypes.c_ulong),
        ("th32ProcessID", ctypes.c_ulong),
        ("th32DefaultHeapID", ctypes.c_void_p),
        ("th32ModuleID", ctypes.c_ulong),
        ("cntThreads", ctypes.c_ulong),
        ("th32ParentProcessID", ctypes.c_ulong),
        ("pcPriClassBase", ctypes.c_long),
        ("dwFlags", ctypes.c_ulong),
        ("szExeFile", ctypes.c_wchar * 260),
    ]


class AbletonClientError(RuntimeError):
    """Bounded client failure without credentials or response internals."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class AbletonBridgeHandoff:
    endpoint: str
    token: str
    export_root: Path
    created_at: datetime
    expires_at: datetime
    schema_version: int = HANDOFF_SCHEMA_VERSION

    def validate(self) -> None:
        if self.schema_version != HANDOFF_SCHEMA_VERSION:
            raise AbletonClientError(
                "unsupported_handoff", "The bridge handoff version is unsupported."
            )
        _validate_endpoint(self.endpoint)
        if len(self.token) < 32 or len(self.token) > 512:
            raise AbletonClientError("invalid_handoff", "The bridge credential is invalid.")
        if self.created_at.tzinfo is None or self.expires_at.tzinfo is None:
            raise AbletonClientError(
                "invalid_handoff", "The bridge handoff timestamps are invalid."
            )
        if self.expires_at <= datetime.now(UTC):
            raise AbletonClientError("expired_handoff", "The bridge handoff has expired.")
        _validate_root(self.export_root)


def default_handoff_path(environ: dict[str, str] | None = None) -> Path:
    values = os.environ if environ is None else environ
    local_appdata = values.get("LOCALAPPDATA")
    if not local_appdata:
        raise AbletonClientError("state_unavailable", "LOCALAPPDATA is unavailable.")
    return Path(local_appdata) / "PHASENOX" / "phasenox.desktop" / "state" / HANDOFF_FILENAME


def write_handoff(
    path: Path,
    *,
    endpoint: str,
    token: str,
    export_root: Path,
    lifetime: timedelta = timedelta(hours=8),
) -> AbletonBridgeHandoff:
    now = datetime.now(UTC)
    handoff = AbletonBridgeHandoff(
        endpoint=endpoint,
        token=token,
        export_root=Path(export_root).resolve(strict=False),
        created_at=now,
        expires_at=now + lifetime,
    )
    handoff.validate()
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    _reject_link(target.parent, "The bridge state directory is unsafe.")
    temporary = target.with_name(f".{target.name}.{os.getpid()}.tmp")
    payload = {
        "schema_version": handoff.schema_version,
        "endpoint": handoff.endpoint,
        "token": handoff.token,
        "export_root": str(handoff.export_root),
        "created_at": handoff.created_at.isoformat(),
        "expires_at": handoff.expires_at.isoformat(),
    }
    data = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    try:
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
    return handoff


def detect_running_ableton() -> tuple[AbletonProcess, ...]:
    """Return main Ableton Live processes through the read-only Windows process API."""
    if sys.platform != "win32":
        return ()
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    snapshot = kernel32.CreateToolhelp32Snapshot(0x00000002, 0)
    invalid_handle = ctypes.c_void_p(-1).value
    if snapshot == invalid_handle:
        raise AbletonClientError("process_probe_failed", "Ableton process discovery failed.")
    kernel32.Process32FirstW.argtypes = [ctypes.c_void_p, ctypes.POINTER(_ProcessEntry32W)]
    kernel32.Process32FirstW.restype = ctypes.c_long
    kernel32.Process32NextW.argtypes = [ctypes.c_void_p, ctypes.POINTER(_ProcessEntry32W)]
    kernel32.Process32NextW.restype = ctypes.c_long
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    try:
        entry = _ProcessEntry32W()
        entry.dwSize = ctypes.sizeof(_ProcessEntry32W)
        processes: list[AbletonProcess] = []
        available = bool(kernel32.Process32FirstW(snapshot, ctypes.byref(entry)))
        while available:
            name = entry.szExeFile
            if name.startswith(_ABLETON_PROCESS_PREFIX) and name.endswith(".exe"):
                processes.append(AbletonProcess(int(entry.th32ProcessID), name))
            available = bool(kernel32.Process32NextW(snapshot, ctypes.byref(entry)))
        return tuple(processes)
    finally:
        kernel32.CloseHandle(snapshot)


def read_handoff(path: Path) -> AbletonBridgeHandoff:
    target = Path(path)
    try:
        metadata = target.lstat()
    except OSError as exc:
        raise AbletonClientError(
            "handoff_unavailable", "The bridge handoff is unavailable."
        ) from exc
    if not stat.S_ISREG(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode):
        raise AbletonClientError("unsafe_handoff", "The bridge handoff is not a regular file.")
    if metadata.st_size <= 0 or metadata.st_size > MAX_HANDOFF_BYTES:
        raise AbletonClientError("invalid_handoff", "The bridge handoff size is invalid.")
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
        handoff = AbletonBridgeHandoff(
            schema_version=payload["schema_version"],
            endpoint=payload["endpoint"],
            token=payload["token"],
            export_root=Path(payload["export_root"]),
            created_at=datetime.fromisoformat(payload["created_at"]),
            expires_at=datetime.fromisoformat(payload["expires_at"]),
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise AbletonClientError("invalid_handoff", "The bridge handoff is malformed.") from exc
    handoff.validate()
    return handoff


def discard_handoff(path: Path) -> None:
    target = Path(path)
    try:
        metadata = target.lstat()
    except FileNotFoundError:
        return
    if not stat.S_ISREG(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode):
        raise AbletonClientError("unsafe_handoff", "Refusing to remove an unsafe handoff path.")
    target.unlink()


class AbletonExportClient:
    """Submit explicit Ableton WAV exports to the local PHASENOX bridge."""

    def __init__(
        self,
        handoff: AbletonBridgeHandoff,
        *,
        daw_version: str,
        timeout_seconds: float = 5.0,
    ) -> None:
        handoff.validate()
        if not daw_version.strip() or len(daw_version) > 64:
            raise ValueError("daw_version must be a non-empty bounded string.")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive.")
        self._handoff = handoff
        self._daw_version = daw_version.strip()
        self._timeout_seconds = timeout_seconds
        self._baseline: dict[Path, tuple[int, int]] = {}

    @property
    def export_root(self) -> Path:
        return self._handoff.export_root

    def handshake(self) -> dict[str, object]:
        return self._request(
            "POST",
            "/handshake",
            {
                "protocol_version": PROTOCOL_VERSION,
                "client_name": ABLETON_EXPORT_HELPER_CLIENT_NAME,
                "client_version": CLIENT_VERSION,
                "daw_version": self._daw_version,
            },
        )

    def health(self) -> dict[str, object]:
        return self._request("GET", "/health")

    def disconnect(self) -> dict[str, object]:
        return self._request("POST", "/disconnect", {})

    def submit_export(
        self,
        path: Path,
        *,
        project_name: str,
        track_name: str | None = None,
    ) -> dict[str, object]:
        unresolved = Path(path)
        try:
            _reject_link(unresolved, "The submitted export path is unsafe.")
        except FileNotFoundError as exc:
            raise AbletonClientError("path_unavailable", "The export is unavailable.") from exc
        candidate = unresolved.resolve(strict=False)
        try:
            relative_path = candidate.relative_to(self.export_root)
        except ValueError as exc:
            raise AbletonClientError(
                "unsafe_path", "The export is outside the configured root."
            ) from exc
        payload: dict[str, object] = {
            "relative_path": relative_path.as_posix(),
            "project": {"name": project_name},
        }
        if track_name:
            payload["track"] = {"name": track_name}
        return self._request("POST", "/exports", payload)

    def analysis_result(self, request_id: str) -> dict[str, object]:
        return self._request("GET", f"/results/{request_id}")

    def prime_exports(self) -> None:
        self._baseline = self._snapshot_exports()

    def changed_exports(self) -> tuple[Path, ...]:
        current = self._snapshot_exports()
        changed = tuple(
            sorted(
                (
                    path
                    for path, identity in current.items()
                    if self._baseline.get(path) != identity
                ),
                key=lambda item: item.name.casefold(),
            )
        )
        self._baseline = current
        return changed

    def wait_for_result(
        self,
        request_id: str,
        *,
        timeout_seconds: float = 120.0,
        poll_seconds: float = 0.25,
    ) -> dict[str, object]:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            result = self.analysis_result(request_id)
            if result.get("state") in {"completed", "failed"}:
                return result
            time.sleep(poll_seconds)
        raise AbletonClientError("analysis_timeout", "PHASENOX analysis did not finish in time.")

    def _snapshot_exports(self) -> dict[Path, tuple[int, int]]:
        _validate_root(self.export_root)
        exports: dict[Path, tuple[int, int]] = {}
        for candidate in self.export_root.iterdir():
            if candidate.suffix.casefold() != ".wav":
                continue
            try:
                metadata = candidate.lstat()
            except OSError:
                continue
            if stat.S_ISREG(metadata.st_mode) and not stat.S_ISLNK(metadata.st_mode):
                exports[candidate.resolve(strict=False)] = (
                    metadata.st_size,
                    metadata.st_mtime_ns,
                )
        return exports

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, object] | None = None,
    ) -> dict[str, object]:
        body = None
        if payload is not None:
            body = json.dumps(payload, separators=(",", ":")).encode()
            if len(body) > DEFAULT_MAX_PAYLOAD_BYTES:
                raise AbletonClientError("payload_too_large", "The client request is too large.")
        request = Request(
            f"{self._handoff.endpoint}{path}",
            data=body,
            method=method,
            headers={
                "Authorization": f"Bearer {self._handoff.token}",
                "Content-Type": "application/json",
            },
        )
        for attempt in range(2):
            try:
                with urlopen(request, timeout=self._timeout_seconds) as response:
                    response_payload = json.loads(response.read(DEFAULT_MAX_PAYLOAD_BYTES + 1))
                break
            except HTTPError as exc:
                try:
                    error_payload = json.loads(exc.read(DEFAULT_MAX_PAYLOAD_BYTES + 1))
                    error_code = error_payload.get("error", "bridge_error")
                except (AttributeError, json.JSONDecodeError):
                    error_code = "bridge_error"
                raise AbletonClientError(
                    str(error_code), "The PHASENOX bridge rejected the request."
                ) from exc
            except (TimeoutError, URLError, OSError) as exc:
                if attempt == 0:
                    continue
                raise AbletonClientError(
                    "bridge_unavailable", "The PHASENOX bridge is unavailable."
                ) from exc
            except json.JSONDecodeError as exc:
                raise AbletonClientError(
                    "malformed_response", "The bridge returned malformed data."
                ) from exc
        if not isinstance(response_payload, dict):
            raise AbletonClientError("malformed_response", "The bridge response is invalid.")
        return response_payload


def _validate_endpoint(endpoint: str) -> None:
    if not isinstance(endpoint, str) or len(endpoint) > 256:
        raise AbletonClientError("invalid_endpoint", "The bridge endpoint is invalid.")
    parsed = urlparse(endpoint)
    try:
        port = parsed.port
    except ValueError as exc:
        raise AbletonClientError("invalid_endpoint", "The bridge endpoint is invalid.") from exc
    if (
        parsed.scheme != "http"
        or parsed.hostname != "127.0.0.1"
        or port is None
        or parsed.path != "/v1"
        or parsed.params
        or parsed.query
        or parsed.fragment
        or parsed.username
        or parsed.password
    ):
        raise AbletonClientError("invalid_endpoint", "The bridge endpoint must be loopback-only.")


def _validate_root(path: Path) -> None:
    root = Path(path).expanduser()
    try:
        metadata = root.lstat()
    except OSError as exc:
        raise AbletonClientError(
            "path_unavailable", "The configured export root is unavailable."
        ) from exc
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or stat.S_ISLNK(metadata.st_mode)
        or bool(
            getattr(metadata, "st_file_attributes", 0)
            & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
        )
    ):
        raise AbletonClientError("unsafe_path", "The configured export root is unsafe.")


def _reject_link(path: Path, message: str) -> None:
    metadata = path.lstat()
    if stat.S_ISLNK(metadata.st_mode) or bool(
        getattr(metadata, "st_file_attributes", 0)
        & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    ):
        raise AbletonClientError("unsafe_path", message)


__all__ = [
    "CLIENT_VERSION",
    "HANDOFF_FILENAME",
    "HANDOFF_SCHEMA_VERSION",
    "AbletonBridgeHandoff",
    "AbletonClientError",
    "AbletonExportClient",
    "AbletonProcess",
    "default_handoff_path",
    "detect_running_ableton",
    "discard_handoff",
    "read_handoff",
    "write_handoff",
]

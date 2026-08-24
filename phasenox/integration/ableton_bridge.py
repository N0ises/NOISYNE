"""Authenticated loopback smoke bridge for a future Ableton-side component."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import queue
import re
import secrets
import stat
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import asdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path, PurePath, PureWindowsPath
from typing import Any, ClassVar

from .daw_analysis import DawAnalysisGateway
from .daw_bridge import (
    DawAnalysisResult,
    DawAudioExport,
    DawBridgeCapability,
    DawBridgeError,
    DawBridgeStatus,
    DawConnectionState,
    DawImportRequest,
    DawProjectIdentity,
    DawTrackIdentity,
)

PROTOCOL_VERSION = 1
ABLETON_CLIENT_NAME = "ableton-m4l"
ABLETON_EXPORT_HELPER_CLIENT_NAME = "phasenox-ableton-export-helper"
ABLETON_CLIENT_NAMES = frozenset({ABLETON_CLIENT_NAME, ABLETON_EXPORT_HELPER_CLIENT_NAME})
DEFAULT_MAX_PAYLOAD_BYTES = 64 * 1024
DEFAULT_MAX_EXPORT_BYTES = 20 * 1024**3
DEFAULT_REQUEST_TIMEOUT_SECONDS = 5.0


class _BridgeHttpServer(ThreadingHTTPServer):
    daemon_threads = True
    bridge: AbletonBridgeServer


class _BridgeRequestHandler(BaseHTTPRequestHandler):
    server: _BridgeHttpServer
    protocol_version = "HTTP/1.1"

    def setup(self) -> None:
        super().setup()
        self.connection.settimeout(self.server.bridge.request_timeout_seconds)

    def do_GET(self) -> None:
        self._dispatch("GET")

    def do_POST(self) -> None:
        self._dispatch("POST")

    def log_message(self, _format: str, *_args: object) -> None:
        return

    def _dispatch(self, method: str) -> None:
        try:
            if not self.server.bridge._is_authorized(self.headers.get("Authorization")):
                self._send(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
                return
            if method == "GET" and self.path == "/v1/health":
                self._send(HTTPStatus.OK, self.server.bridge._status_payload())
                return
            if method == "GET" and self.path.startswith("/v1/results/"):
                request_id = self.path.removeprefix("/v1/results/")
                status, response = self.server.bridge._analysis_result(request_id)
                self._send(status, response)
                return
            if method == "POST" and self.path == "/v1/handshake":
                payload = self._read_json()
                status, response = self.server.bridge._handshake(payload)
                self._send(status, response)
                return
            if method == "POST" and self.path == "/v1/exports":
                payload = self._read_json()
                status, response = self.server.bridge._submit_export(payload)
                self._send(status, response)
                return
            if method == "POST" and self.path == "/v1/disconnect":
                status, response = self.server.bridge._disconnect()
                self._send(status, response)
                return
            self._send(HTTPStatus.NOT_FOUND, {"error": "not_found"})
        except DawBridgeError as exc:
            status = {
                "payload_too_large": HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                "not_connected": HTTPStatus.CONFLICT,
                "version_mismatch": HTTPStatus.CONFLICT,
                "unsupported_audio": HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
            }.get(exc.code, HTTPStatus.BAD_REQUEST)
            self._send(status, {"error": exc.code, "message": str(exc)})
        except (ConnectionError, OSError):
            self.close_connection = True

    def _read_json(self) -> Mapping[str, Any]:
        raw_length = self.headers.get("Content-Length")
        try:
            length = int(raw_length or "")
        except ValueError as exc:
            raise DawBridgeError("invalid_length", "A valid Content-Length is required.") from exc
        if length < 0 or length > self.server.bridge.max_payload_bytes:
            raise DawBridgeError("payload_too_large", "The request payload exceeds the limit.")
        try:
            payload = json.loads(self.rfile.read(length))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise DawBridgeError("malformed_json", "The request must contain valid JSON.") from exc
        if not isinstance(payload, dict):
            raise DawBridgeError("malformed_payload", "The request must be a JSON object.")
        return payload

    def _send(self, status: HTTPStatus, payload: Mapping[str, Any]) -> None:
        body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        self.send_response(int(status))
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)


class AbletonBridgeServer:
    """A bounded PHASENOX-side handshake and WAV-export intake boundary.

    This server is not an Ableton control surface and performs no analysis on
    its request threads. A future separately shipped Ableton-side component may
    authenticate, negotiate the protocol, and enqueue a stable WAV export.
    """

    capabilities: ClassVar[tuple[DawBridgeCapability, ...]] = (
        DawBridgeCapability("health", True, "Local health and lifecycle status"),
        DawBridgeCapability("version_handshake", True, "Protocol and client version handshake"),
        DawBridgeCapability("wav_export_queue", True, "Validated stable WAV export handoff"),
        DawBridgeCapability(
            "daw_control", False, "No transport, track, device, or automation control"
        ),
    )

    def __init__(
        self,
        export_root: Path,
        *,
        token: str | None = None,
        port: int = 0,
        stable_seconds: float = 1.0,
        max_payload_bytes: int = DEFAULT_MAX_PAYLOAD_BYTES,
        max_export_bytes: int = DEFAULT_MAX_EXPORT_BYTES,
        request_timeout_seconds: float = DEFAULT_REQUEST_TIMEOUT_SECONDS,
        analysis_gateway: DawAnalysisGateway | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if not token:
            token = secrets.token_urlsafe(32)
        if len(token) < 32:
            raise ValueError("Bridge tokens must contain at least 32 characters.")
        if not 0 <= port <= 65535:
            raise ValueError("Bridge port is outside the valid range.")
        if stable_seconds < 0:
            raise ValueError("stable_seconds cannot be negative.")
        if max_payload_bytes < 1024 or max_export_bytes <= 0:
            raise ValueError("Bridge limits must be positive and bounded.")
        if request_timeout_seconds <= 0:
            raise ValueError("request_timeout_seconds must be positive.")
        expanded_root = Path(export_root).expanduser()
        self._reject_link_or_reparse(
            expanded_root,
            "Symlink and reparse-point roots are rejected.",
        )
        self._export_root = expanded_root.resolve(strict=False)
        self._token = token
        self._requested_port = port
        self._stable_seconds = stable_seconds
        self.max_payload_bytes = max_payload_bytes
        self._max_export_bytes = max_export_bytes
        self.request_timeout_seconds = request_timeout_seconds
        self._analysis_gateway = analysis_gateway
        self._clock = clock
        self._lock = threading.RLock()
        self._httpd: _BridgeHttpServer | None = None
        self._thread: threading.Thread | None = None
        self._state = DawConnectionState.STOPPED
        self._client_name: str | None = None
        self._client_version: str | None = None
        self._daw_version: str | None = None
        self._reason: str | None = None
        self._observations: dict[Path, tuple[int, int, float]] = {}
        self._accepted_ids: set[str] = set()
        self._imports: queue.Queue[DawImportRequest] = queue.Queue()

    @property
    def token(self) -> str:
        """Return the ephemeral credential for explicit local handoff."""
        return self._token

    @property
    def export_root(self) -> Path:
        return self._export_root

    def start(self) -> DawBridgeStatus:
        with self._lock:
            if self._httpd is not None:
                return self.status()
            self._validate_export_root()
            httpd = _BridgeHttpServer(("127.0.0.1", self._requested_port), _BridgeRequestHandler)
            httpd.bridge = self
            try:
                if self._analysis_gateway is not None:
                    self._analysis_gateway.start()
            except Exception:
                httpd.server_close()
                raise
            thread = threading.Thread(
                target=httpd.serve_forever,
                name="phasenox-ableton-bridge",
                daemon=True,
            )
            self._httpd = httpd
            self._thread = thread
            self._state = DawConnectionState.BRIDGE_AVAILABLE
            self._reason = "Ableton-side bridge has not completed a handshake."
            thread.start()
            return self.status()

    def stop(self) -> DawBridgeStatus:
        with self._lock:
            httpd = self._httpd
            thread = self._thread
            self._httpd = None
            self._thread = None
        if httpd is not None:
            httpd.shutdown()
            httpd.server_close()
        if thread is not None:
            thread.join(timeout=5.0)
        if self._analysis_gateway is not None:
            self._analysis_gateway.stop()
        with self._lock:
            self._state = DawConnectionState.STOPPED
            self._client_name = None
            self._client_version = None
            self._daw_version = None
            self._reason = "Bridge is stopped."
            return self.status()

    def status(self) -> DawBridgeStatus:
        with self._lock:
            endpoint = None
            if self._httpd is not None:
                endpoint = f"http://127.0.0.1:{self._httpd.server_port}/v1"
            return DawBridgeStatus(
                state=self._state,
                protocol_version=PROTOCOL_VERSION,
                endpoint=endpoint,
                client_name=self._client_name,
                client_version=self._client_version,
                daw_version=self._daw_version,
                reason=self._reason,
                queued_exports=self._imports.qsize(),
            )

    def next_import(self, timeout: float | None = None) -> DawImportRequest:
        try:
            return self._imports.get(timeout=timeout)
        except queue.Empty as exc:
            raise TimeoutError("No DAW import request became available.") from exc

    def _validate_export_root(self) -> None:
        try:
            metadata = self._export_root.lstat()
        except OSError as exc:
            raise DawBridgeError(
                "path_unavailable", "The configured export root is unavailable."
            ) from exc
        if not stat.S_ISDIR(metadata.st_mode):
            raise DawBridgeError(
                "invalid_export_root", "The configured export root is not a directory."
            )
        if stat.S_ISLNK(metadata.st_mode) or bool(
            getattr(metadata, "st_file_attributes", 0)
            & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
        ):
            raise DawBridgeError(
                "unsafe_export_root", "Symlink and reparse-point roots are rejected."
            )
        if not os.access(self._export_root, os.R_OK):
            raise DawBridgeError("path_unavailable", "The configured export root is not readable.")

    def _is_authorized(self, authorization: str | None) -> bool:
        if not authorization or not authorization.startswith("Bearer "):
            return False
        return hmac.compare_digest(authorization.removeprefix("Bearer "), self._token)

    def _status_payload(self) -> dict[str, Any]:
        status = self.status()
        payload = asdict(status)
        payload["state"] = status.state.value
        payload["capabilities"] = [asdict(capability) for capability in self.capabilities]
        return payload

    def _handshake(self, payload: Mapping[str, Any]) -> tuple[HTTPStatus, dict[str, Any]]:
        protocol = payload.get("protocol_version")
        if protocol != PROTOCOL_VERSION:
            with self._lock:
                self._state = DawConnectionState.VERSION_MISMATCH
                self._reason = f"Protocol {protocol!r} is incompatible with {PROTOCOL_VERSION}."
            raise DawBridgeError("version_mismatch", self._reason)
        client_name = self._bounded_string(payload.get("client_name"), "client_name", 64)
        if client_name not in ABLETON_CLIENT_NAMES:
            raise DawBridgeError("unsupported_client", "The client identity is not supported.")
        client_version = self._bounded_string(payload.get("client_version"), "client_version", 64)
        daw_version = self._bounded_string(payload.get("daw_version"), "daw_version", 64)
        with self._lock:
            self._client_name = client_name
            self._client_version = client_version
            self._daw_version = daw_version
            self._state = DawConnectionState.CONNECTED
            self._reason = None
        return HTTPStatus.OK, self._status_payload()

    def _disconnect(self) -> tuple[HTTPStatus, dict[str, Any]]:
        with self._lock:
            self._client_name = None
            self._client_version = None
            self._daw_version = None
            self._state = DawConnectionState.BRIDGE_AVAILABLE
            self._reason = "Ableton-side bridge disconnected."
        return HTTPStatus.OK, self._status_payload()

    def _submit_export(self, payload: Mapping[str, Any]) -> tuple[HTTPStatus, dict[str, Any]]:
        if self.status().state is not DawConnectionState.CONNECTED:
            raise DawBridgeError("not_connected", "Complete a compatible handshake first.")
        relative_path = self._bounded_string(payload.get("relative_path"), "relative_path", 1024)
        candidate = self._resolve_export(relative_path)
        metadata = candidate.stat()
        if metadata.st_size <= 0 or metadata.st_size > self._max_export_bytes:
            raise DawBridgeError("invalid_export_size", "The WAV export size is outside limits.")
        observation = (metadata.st_size, metadata.st_mtime_ns)
        now = self._clock()
        with self._lock:
            previous = self._observations.get(candidate)
            self._observations[candidate] = (
                *observation,
                now if previous is None or previous[:2] != observation else previous[2],
            )
        if (
            previous is None
            or previous[:2] != observation
            or now - previous[2] < self._stable_seconds
        ):
            return HTTPStatus.ACCEPTED, {"status": "observing", "relative_path": relative_path}
        self._validate_wav_header(candidate)
        export_id = hashlib.sha256(
            f"{relative_path}\0{metadata.st_size}\0{metadata.st_mtime_ns}".encode()
        ).hexdigest()
        with self._lock:
            if export_id in self._accepted_ids:
                return HTTPStatus.OK, {"status": "duplicate", "export_id": export_id}
        project_payload = payload.get("project") or {}
        track_payload = payload.get("track")
        if not isinstance(project_payload, dict) or (
            track_payload is not None and not isinstance(track_payload, dict)
        ):
            raise DawBridgeError(
                "malformed_identity", "Project and track identities must be objects."
            )
        project = DawProjectIdentity(
            self._bounded_string(project_payload.get("name", "Untitled"), "project.name", 256),
            self._optional_string(
                project_payload.get("persistent_id"), "project.persistent_id", 256
            ),
        )
        track = None
        if isinstance(track_payload, dict):
            raw_index = track_payload.get("index")
            if raw_index is not None and (not isinstance(raw_index, int) or raw_index < 0):
                raise DawBridgeError(
                    "invalid_track_index", "Track index must be a non-negative integer."
                )
            track = DawTrackIdentity(
                self._bounded_string(track_payload.get("name", "Unnamed"), "track.name", 256),
                raw_index,
                self._optional_string(
                    track_payload.get("persistent_id"), "track.persistent_id", 256
                ),
            )
        request = DawImportRequest(
            project,
            track,
            DawAudioExport(export_id, candidate, metadata.st_size, metadata.st_mtime_ns),
        )
        with self._lock:
            if export_id in self._accepted_ids:
                return HTTPStatus.OK, {"status": "duplicate", "export_id": export_id}
            analysis_result = None
            if self._analysis_gateway is not None:
                analysis_result = self._analysis_gateway.submit(request)
            self._accepted_ids.add(export_id)
            self._imports.put(request)
        response: dict[str, Any] = {
            "status": "queued",
            "export_id": export_id,
            "request_id": export_id,
        }
        if analysis_result is not None:
            response["analysis_state"] = analysis_result.state.value
        return HTTPStatus.ACCEPTED, response

    def _analysis_result(self, request_id: str) -> tuple[HTTPStatus, dict[str, Any]]:
        if not re.fullmatch(r"[0-9a-f]{64}", request_id):
            raise DawBridgeError("invalid_request_id", "The analysis request identity is invalid.")
        if self._analysis_gateway is None:
            raise DawBridgeError("analysis_unavailable", "DAW analysis is not enabled.")
        result = self._analysis_gateway.result(request_id)
        if result is None:
            return HTTPStatus.NOT_FOUND, {"error": "result_not_found"}
        return HTTPStatus.OK, self._analysis_payload(result)

    @staticmethod
    def _analysis_payload(result: DawAnalysisResult) -> dict[str, Any]:
        payload = asdict(result)
        payload["state"] = result.state.value
        payload["limitations"] = list(result.limitations)
        return payload

    def _resolve_export(self, relative_path: str) -> Path:
        pure = PurePath(relative_path)
        windows_path = PureWindowsPath(relative_path)
        if pure.is_absolute() or windows_path.is_absolute() or ".." in pure.parts or not pure.parts:
            raise DawBridgeError(
                "unsafe_path", "Only relative paths within the export root are accepted."
            )
        unresolved = self._export_root / pure
        current = self._export_root
        for part in pure.parts:
            current /= part
            if current.exists() or current.is_symlink():
                self._reject_link_or_reparse(
                    current,
                    "Symlink and reparse-point exports are rejected.",
                )
        candidate = unresolved.resolve(strict=False)
        if not candidate.is_relative_to(self._export_root):
            raise DawBridgeError("unsafe_path", "The export path escapes the configured root.")
        if candidate.suffix.casefold() != ".wav":
            raise DawBridgeError("unsupported_audio", "Desktop Core accepts WAV exports only.")
        try:
            metadata = candidate.lstat()
        except OSError as exc:
            raise DawBridgeError(
                "path_unavailable", "The submitted WAV export is unavailable."
            ) from exc
        if not stat.S_ISREG(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode):
            raise DawBridgeError("unsafe_path", "The submitted export must be a regular file.")
        return candidate

    @staticmethod
    def _validate_wav_header(candidate: Path) -> None:
        try:
            with candidate.open("rb") as stream:
                header = stream.read(12)
        except OSError as exc:
            raise DawBridgeError(
                "path_unavailable", "The submitted WAV export is unavailable."
            ) from exc
        if len(header) != 12 or header[:4] not in {b"RIFF", b"RF64"} or header[8:] != b"WAVE":
            raise DawBridgeError(
                "unsupported_audio", "The submitted file is not a supported WAV export."
            )

    @staticmethod
    def _reject_link_or_reparse(candidate: Path, message: str) -> None:
        try:
            metadata = candidate.lstat()
        except FileNotFoundError:
            return
        if stat.S_ISLNK(metadata.st_mode) or bool(
            getattr(metadata, "st_file_attributes", 0)
            & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
        ):
            raise DawBridgeError("unsafe_path", message)

    @staticmethod
    def _bounded_string(value: object, field: str, limit: int) -> str:
        if not isinstance(value, str) or not value.strip() or len(value) > limit:
            raise DawBridgeError("invalid_field", f"{field} must be a non-empty bounded string.")
        return value.strip()

    @classmethod
    def _optional_string(cls, value: object, field: str, limit: int) -> str | None:
        if value is None:
            return None
        return cls._bounded_string(value, field, limit)


__all__ = [
    "ABLETON_CLIENT_NAME",
    "ABLETON_CLIENT_NAMES",
    "ABLETON_EXPORT_HELPER_CLIENT_NAME",
    "DEFAULT_MAX_EXPORT_BYTES",
    "DEFAULT_MAX_PAYLOAD_BYTES",
    "DEFAULT_REQUEST_TIMEOUT_SECONDS",
    "PROTOCOL_VERSION",
    "AbletonBridgeServer",
]

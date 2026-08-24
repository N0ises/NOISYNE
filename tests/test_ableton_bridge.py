from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Iterator
from http import HTTPStatus
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from phasenox.integration.ableton_bridge import (
    ABLETON_CLIENT_NAME,
    PROTOCOL_VERSION,
    AbletonBridgeServer,
)
from phasenox.integration.daw_bridge import DawConnectionState

TOKEN = "sprint20-test-token-0123456789abcdef"


@pytest.fixture
def bridge(tmp_path: Path) -> Iterator[AbletonBridgeServer]:
    server = AbletonBridgeServer(tmp_path, token=TOKEN, stable_seconds=0)
    server.start()
    yield server
    server.stop()


def call(
    bridge: AbletonBridgeServer,
    method: str,
    path: str,
    payload: object | None = None,
    *,
    token: str = TOKEN,
) -> tuple[int, dict[str, object]]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(
        f"{bridge.status().endpoint}{path}",
        data=body,
        method=method,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    try:
        with urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read())
    except HTTPError as exc:
        return exc.code, json.loads(exc.read())


def handshake(bridge: AbletonBridgeServer) -> tuple[int, dict[str, object]]:
    return call(
        bridge,
        "POST",
        "/handshake",
        {
            "protocol_version": PROTOCOL_VERSION,
            "client_name": ABLETON_CLIENT_NAME,
            "client_version": "0.1.0-test",
            "daw_version": "11.2.7-test",
        },
    )


def test_lifecycle_is_loopback_only_and_truthful(tmp_path: Path) -> None:
    server = AbletonBridgeServer(tmp_path, token=TOKEN)
    assert server.status().state is DawConnectionState.STOPPED
    status = server.start()
    try:
        assert status.state is DawConnectionState.BRIDGE_AVAILABLE
        assert status.endpoint is not None
        assert status.endpoint.startswith("http://127.0.0.1:")
        assert "Ableton-side" in (status.reason or "")
    finally:
        assert server.stop().state is DawConnectionState.STOPPED


def test_authentication_and_handshake_state(bridge: AbletonBridgeServer) -> None:
    code, payload = call(bridge, "GET", "/health", token="x" * 32)
    assert code == HTTPStatus.UNAUTHORIZED
    assert payload["error"] == "unauthorized"

    code, payload = handshake(bridge)
    assert code == HTTPStatus.OK
    assert payload["state"] == "connected"
    assert payload["client_name"] == ABLETON_CLIENT_NAME
    assert payload["daw_version"] == "11.2.7-test"
    capabilities = {item["name"]: item["available"] for item in payload["capabilities"]}
    assert capabilities["health"] is True
    assert capabilities["wav_export_queue"] is True
    assert capabilities["daw_control"] is False


def test_payload_limit_is_enforced_before_parsing(tmp_path: Path) -> None:
    server = AbletonBridgeServer(tmp_path, token=TOKEN, max_payload_bytes=1024)
    server.start()
    try:
        code, payload = call(server, "POST", "/handshake", {"padding": "x" * 2048})
        assert code == HTTPStatus.REQUEST_ENTITY_TOO_LARGE
        assert payload["error"] == "payload_too_large"
    finally:
        server.stop()


def test_version_mismatch_never_claims_connected(bridge: AbletonBridgeServer) -> None:
    code, payload = call(
        bridge,
        "POST",
        "/handshake",
        {
            "protocol_version": 999,
            "client_name": ABLETON_CLIENT_NAME,
            "client_version": "future",
            "daw_version": "unknown",
        },
    )
    assert code == HTTPStatus.CONFLICT
    assert payload["error"] == "version_mismatch"
    assert bridge.status().state is DawConnectionState.VERSION_MISMATCH


@pytest.mark.parametrize(
    ("payload", "expected_error"),
    [
        ({}, "version_mismatch"),
        (
            {
                "protocol_version": PROTOCOL_VERSION,
                "client_name": "not-ableton",
                "client_version": "1",
                "daw_version": "1",
            },
            "unsupported_client",
        ),
    ],
)
def test_malformed_or_unsupported_handshake_is_bounded(
    bridge: AbletonBridgeServer,
    payload: dict[str, object],
    expected_error: str,
) -> None:
    code, response = call(bridge, "POST", "/handshake", payload)
    assert code in {HTTPStatus.BAD_REQUEST, HTTPStatus.CONFLICT}
    assert response["error"] == expected_error


def test_stable_wav_is_queued_once_with_identity(
    bridge: AbletonBridgeServer,
    tmp_path: Path,
) -> None:
    audio = tmp_path / "Exports" / "Mix 01.wav"
    audio.parent.mkdir()
    audio.write_bytes(b"RIFF" + b"\0" * 4 + b"WAVE" + b"\0" * 128)
    assert handshake(bridge)[0] == HTTPStatus.OK
    payload = {
        "relative_path": "Exports/Mix 01.wav",
        "project": {"name": "Disposable Set", "persistent_id": "set-1"},
        "track": {"name": "Master", "index": 0, "persistent_id": "track-1"},
    }

    code, first = call(bridge, "POST", "/exports", payload)
    assert code == HTTPStatus.ACCEPTED
    assert first["status"] == "observing"
    code, second = call(bridge, "POST", "/exports", payload)
    assert code == HTTPStatus.ACCEPTED
    assert second["status"] == "queued"

    request = bridge.next_import(timeout=1)
    assert request.audio_export.path == audio.resolve()
    assert request.project.name == "Disposable Set"
    assert request.track is not None
    assert request.track.name == "Master"
    assert request.audio_export.export_id == second["export_id"]

    code, duplicate = call(bridge, "POST", "/exports", payload)
    assert code == HTTPStatus.OK
    assert duplicate == {"status": "duplicate", "export_id": second["export_id"]}
    with pytest.raises(TimeoutError):
        bridge.next_import(timeout=0.01)


def test_incomplete_export_is_not_queued(tmp_path: Path) -> None:
    now = [10.0]
    audio = tmp_path / "render.wav"
    audio.write_bytes(b"RIFF")
    bridge = AbletonBridgeServer(
        tmp_path,
        token=TOKEN,
        stable_seconds=5,
        clock=lambda: now[0],
    )
    bridge.start()
    try:
        assert handshake(bridge)[0] == HTTPStatus.OK
        payload = {"relative_path": "render.wav", "project": {"name": "Set"}}
        assert call(bridge, "POST", "/exports", payload)[1]["status"] == "observing"
        now[0] += 2
        audio.write_bytes(b"RIFF" + b"\0" * 32)
        assert call(bridge, "POST", "/exports", payload)[1]["status"] == "observing"
        now[0] += 4
        assert call(bridge, "POST", "/exports", payload)[1]["status"] == "observing"
        with pytest.raises(TimeoutError):
            bridge.next_import(timeout=0.01)
    finally:
        bridge.stop()


def test_non_wav_content_is_rejected_after_stability_check(
    bridge: AbletonBridgeServer,
    tmp_path: Path,
) -> None:
    audio = tmp_path / "fake.wav"
    audio.write_bytes(b"not actually wave audio")
    assert handshake(bridge)[0] == HTTPStatus.OK
    payload = {"relative_path": "fake.wav", "project": {"name": "Set"}}
    assert call(bridge, "POST", "/exports", payload)[1]["status"] == "observing"
    code, response = call(bridge, "POST", "/exports", payload)
    assert code == HTTPStatus.UNSUPPORTED_MEDIA_TYPE
    assert response["error"] == "unsupported_audio"


@pytest.mark.parametrize(
    ("relative_path", "expected_error"),
    [
        ("../escape.wav", "unsafe_path"),
        ("C:/absolute.wav", "unsafe_path"),
        ("unsupported.mp3", "unsupported_audio"),
        ("missing.wav", "path_unavailable"),
    ],
)
def test_export_path_validation(
    bridge: AbletonBridgeServer,
    relative_path: str,
    expected_error: str,
) -> None:
    assert handshake(bridge)[0] == HTTPStatus.OK
    code, payload = call(
        bridge,
        "POST",
        "/exports",
        {"relative_path": relative_path, "project": {"name": "Set"}},
    )
    assert code >= 400
    assert payload["error"] == expected_error


def test_export_requires_completed_handshake(bridge: AbletonBridgeServer) -> None:
    code, payload = call(
        bridge,
        "POST",
        "/exports",
        {"relative_path": "anything.wav", "project": {"name": "Set"}},
    )
    assert code == HTTPStatus.CONFLICT
    assert payload["error"] == "not_connected"


def test_unavailable_or_unsafe_export_root_fails_without_server(tmp_path: Path) -> None:
    missing = AbletonBridgeServer(tmp_path / "missing", token=TOKEN)
    with pytest.raises(ValueError, match="unavailable"):
        missing.start()
    file_root = tmp_path / "file"
    file_root.write_text("not a folder", encoding="utf-8")
    invalid = AbletonBridgeServer(file_root, token=TOKEN)
    with pytest.raises(ValueError, match="not a directory"):
        invalid.start()


def test_bridge_can_stop_and_restart(bridge: AbletonBridgeServer) -> None:
    first_endpoint = bridge.status().endpoint
    bridge.stop()
    assert bridge.status().state is DawConnectionState.STOPPED
    second = bridge.start()
    assert second.state is DawConnectionState.BRIDGE_AVAILABLE
    assert second.endpoint is not None
    assert first_endpoint is not None


def test_import_is_lightweight_in_fresh_interpreter() -> None:
    script = """
import json
import sys
import phasenox.integration.ableton_bridge
print(json.dumps({name: name in sys.modules for name in (
    'torch', 'onnxruntime', 'chromadb', 'pyarrow', 'PySide6'
)}))
"""
    completed = subprocess.run(
        [sys.executable, "-c", script],
        check=True,
        capture_output=True,
        text=True,
    )
    assert not any(json.loads(completed.stdout).values())

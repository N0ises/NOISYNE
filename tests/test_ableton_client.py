"""Sprint 21 Ableton export helper and analysis handoff tests."""

from __future__ import annotations

import json
import socket
import subprocess
import sys
import threading
import wave
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Self
from urllib.error import URLError

import pytest

from phasenox.integration.ableton_bridge import AbletonBridgeServer
from phasenox.integration.ableton_client import (
    AbletonBridgeHandoff,
    AbletonClientError,
    AbletonExportClient,
    detect_running_ableton,
    discard_handoff,
    read_handoff,
    write_handoff,
)
from phasenox.integration.daw_analysis import DawAnalysisGateway
from phasenox.integration.daw_bridge import (
    DawAnalysisResult,
    DawAnalysisState,
    DawConnectionState,
)

TOKEN = "sprint21-test-token-0123456789abcdef"


def _write_wav(path: Path, frames: int = 4096) -> None:
    with wave.open(str(path), "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(44100)
        stream.writeframes(b"\0\0" * frames)


def _handoff(server: AbletonBridgeServer, root: Path, token: str = TOKEN) -> AbletonBridgeHandoff:
    endpoint = server.status().endpoint
    assert endpoint is not None
    now = datetime.now(UTC)
    return AbletonBridgeHandoff(
        endpoint=endpoint,
        token=token,
        export_root=root,
        created_at=now,
        expires_at=now + timedelta(hours=1),
    )


def _completed(request: object) -> DawAnalysisResult:
    export = request.audio_export  # type: ignore[attr-defined]
    return DawAnalysisResult(
        request_id=export.export_id,
        state=DawAnalysisState.COMPLETED,
        analysis_id=f"analysis-{export.export_id[:16]}",
        source=export.path.name,
        summary={"fixture": True},
    )


def test_handoff_round_trip_and_discard(tmp_path: Path) -> None:
    export_root = tmp_path / "exports"
    export_root.mkdir()
    handoff_path = tmp_path / "state" / "handoff.json"
    handoff = write_handoff(
        handoff_path,
        endpoint="http://127.0.0.1:32123/v1",
        token=TOKEN,
        export_root=export_root,
    )
    assert read_handoff(handoff_path) == handoff
    assert TOKEN not in repr(handoff_path)
    discard_handoff(handoff_path)
    assert not handoff_path.exists()
    discard_handoff(handoff_path)


@pytest.mark.parametrize(
    "endpoint",
    [
        "https://127.0.0.1:1234/v1",
        "http://0.0.0.0:1234/v1",
        "http://localhost:1234/v1",
        "http://127.0.0.1:1234/not-v1",
        "http://user:secret@127.0.0.1:1234/v1",
    ],
)
def test_handoff_rejects_noncanonical_endpoint(tmp_path: Path, endpoint: str) -> None:
    now = datetime.now(UTC)
    handoff = AbletonBridgeHandoff(
        endpoint=endpoint,
        token=TOKEN,
        export_root=tmp_path,
        created_at=now,
        expires_at=now + timedelta(hours=1),
    )
    with pytest.raises(AbletonClientError, match="loopback"):
        handoff.validate()


def test_bridge_rejects_link_root_and_link_export(tmp_path: Path) -> None:
    real_root = tmp_path / "real"
    real_root.mkdir()
    linked_root = tmp_path / "linked"
    try:
        linked_root.symlink_to(real_root, target_is_directory=True)
    except OSError:
        pytest.skip("Creating symlinks is unavailable for this Windows user.")
    with pytest.raises(ValueError, match="reparse-point roots"):
        AbletonBridgeServer(linked_root, token=TOKEN)

    target = real_root / "target.wav"
    _write_wav(target)
    linked_export = real_root / "linked.wav"
    linked_export.symlink_to(target)
    server = AbletonBridgeServer(real_root, token=TOKEN, stable_seconds=0)
    server.start()
    client = AbletonExportClient(_handoff(server, real_root), daw_version="11.2.7")
    try:
        client.handshake()
        with pytest.raises(AbletonClientError) as exc_info:
            client.submit_export(linked_export, project_name="Disposable")
        assert exc_info.value.code == "unsafe_path"
    finally:
        server.stop()


def test_expired_or_malformed_handoff_is_rejected(tmp_path: Path) -> None:
    now = datetime.now(UTC)
    expired = AbletonBridgeHandoff(
        endpoint="http://127.0.0.1:1234/v1",
        token=TOKEN,
        export_root=tmp_path,
        created_at=now - timedelta(hours=2),
        expires_at=now - timedelta(hours=1),
    )
    with pytest.raises(AbletonClientError) as exc_info:
        expired.validate()
    assert exc_info.value.code == "expired_handoff"

    malformed = tmp_path / "malformed.json"
    malformed.write_text("not json", encoding="utf-8")
    with pytest.raises(AbletonClientError) as exc_info:
        read_handoff(malformed)
    assert exc_info.value.code == "invalid_handoff"


def test_real_application_analysis_result_round_trip(tmp_path: Path) -> None:
    audio = tmp_path / "ableton-render.wav"
    _write_wav(audio)
    gateway = DawAnalysisGateway()
    server = AbletonBridgeServer(
        tmp_path,
        token=TOKEN,
        stable_seconds=0,
        analysis_gateway=gateway,
    )
    server.start()
    client = AbletonExportClient(_handoff(server, tmp_path), daw_version="11.2.7-test")
    try:
        assert client.handshake()["state"] == "connected"
        assert client.submit_export(audio, project_name="Disposable")["status"] == "observing"
        queued = client.submit_export(audio, project_name="Disposable")
        assert queued["status"] == "queued"
        result = client.wait_for_result(str(queued["request_id"]), timeout_seconds=30)
        assert result["state"] == "completed"
        assert result["source"] == audio.name
        assert result["analysis_id"]
        assert result["summary"]["descriptor_count"] >= 0  # type: ignore[index]
        assert str(tmp_path) not in json.dumps(result)
    finally:
        server.stop()


def test_analysis_failure_is_bounded(tmp_path: Path) -> None:
    audio = tmp_path / "failed.wav"
    _write_wav(audio)

    def fail(_request: object) -> DawAnalysisResult:
        raise RuntimeError(f"private path: {tmp_path}")

    server = AbletonBridgeServer(
        tmp_path,
        token=TOKEN,
        stable_seconds=0,
        analysis_gateway=DawAnalysisGateway(fail),
    )
    server.start()
    client = AbletonExportClient(_handoff(server, tmp_path), daw_version="11.2.7-test")
    try:
        client.handshake()
        client.submit_export(audio, project_name="Disposable")
        queued = client.submit_export(audio, project_name="Disposable")
        result = client.wait_for_result(str(queued["request_id"]), timeout_seconds=5)
        assert result["state"] == "failed"
        assert result["error_code"] == "analysis_failure"
        assert str(tmp_path) not in json.dumps(result)
    finally:
        server.stop()


def test_wrong_token_and_closed_bridge_map_to_safe_errors(tmp_path: Path) -> None:
    server = AbletonBridgeServer(tmp_path, token=TOKEN)
    server.start()
    wrong = AbletonExportClient(_handoff(server, tmp_path, token="x" * 32), daw_version="11.2.7")
    with pytest.raises(AbletonClientError) as exc_info:
        wrong.handshake()
    assert exc_info.value.code == "unauthorized"
    valid = AbletonExportClient(_handoff(server, tmp_path), daw_version="11.2.7")
    server.stop()
    with pytest.raises(AbletonClientError) as exc_info:
        valid.handshake()
    assert exc_info.value.code == "bridge_unavailable"


def test_disconnect_retries_bounded_transient_loopback_failures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    now = datetime.now(UTC)
    handoff = AbletonBridgeHandoff(
        endpoint="http://127.0.0.1:32123/v1",
        token=TOKEN,
        export_root=tmp_path,
        created_at=now,
        expires_at=now + timedelta(hours=1),
    )
    client = AbletonExportClient(handoff, daw_version="11.2.7")
    attempts = 0

    class Response:
        def __enter__(self) -> Self:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self, _limit: int) -> bytes:
            return b'{"state":"bridge_available"}'

    def open_request(*_args: object, **_kwargs: object) -> Response:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise URLError("transient loopback failure")
        return Response()

    monkeypatch.setattr("phasenox.integration.ableton_client.urlopen", open_request)

    assert client.disconnect() == {"state": "bridge_available"}
    assert attempts == 3


def test_client_timeout_is_bounded(tmp_path: Path) -> None:
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    release = threading.Event()

    def stall() -> None:
        connection, _address = listener.accept()
        with connection:
            release.wait(timeout=2)

    worker = threading.Thread(target=stall, daemon=True)
    worker.start()
    now = datetime.now(UTC)
    handoff = AbletonBridgeHandoff(
        endpoint=f"http://127.0.0.1:{listener.getsockname()[1]}/v1",
        token=TOKEN,
        export_root=tmp_path,
        created_at=now,
        expires_at=now + timedelta(hours=1),
    )
    client = AbletonExportClient(handoff, daw_version="11.2.7", timeout_seconds=0.05)
    try:
        with pytest.raises(AbletonClientError) as exc_info:
            client.handshake()
        assert exc_info.value.code == "bridge_unavailable"
    finally:
        release.set()
        listener.close()
        worker.join(timeout=2)


def test_watcher_ignores_baseline_and_detects_direct_wav_only(tmp_path: Path) -> None:
    existing = tmp_path / "existing.wav"
    _write_wav(existing)
    nested = tmp_path / "nested"
    nested.mkdir()
    client_handoff = AbletonBridgeHandoff(
        endpoint="http://127.0.0.1:1234/v1",
        token=TOKEN,
        export_root=tmp_path,
        created_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    client = AbletonExportClient(client_handoff, daw_version="11.2.7")
    client.prime_exports()
    assert client.changed_exports() == ()
    _write_wav(nested / "ignored.wav")
    (tmp_path / "ignored.mp3").write_bytes(b"data")
    created = tmp_path / "new.wav"
    _write_wav(created)
    assert client.changed_exports() == (created.resolve(),)
    assert client.changed_exports() == ()


def test_concurrent_duplicate_submission_queues_once(tmp_path: Path) -> None:
    audio = tmp_path / "concurrent.wav"
    _write_wav(audio)
    server = AbletonBridgeServer(
        tmp_path,
        token=TOKEN,
        stable_seconds=0,
        analysis_gateway=DawAnalysisGateway(_completed),
    )
    server.start()
    client = AbletonExportClient(_handoff(server, tmp_path), daw_version="11.2.7")
    try:
        client.handshake()
        client.submit_export(audio, project_name="Disposable")
        with ThreadPoolExecutor(max_workers=8) as pool:
            responses = list(
                pool.map(
                    lambda _index: client.submit_export(audio, project_name="Disposable"),
                    range(8),
                )
            )
        assert sum(response["status"] == "queued" for response in responses) == 1
        assert sum(response["status"] == "duplicate" for response in responses) == 7
        assert server.next_import(timeout=1).audio_export.path == audio.resolve()
        with pytest.raises(TimeoutError):
            server.next_import(timeout=0.01)
    finally:
        server.stop()


def test_disconnect_reconnect_and_bridge_restart_soak(tmp_path: Path) -> None:
    ports: list[int] = []
    gateway = DawAnalysisGateway(_completed)
    server = AbletonBridgeServer(tmp_path, token=TOKEN, analysis_gateway=gateway)
    for _index in range(10):
        status = server.start()
        assert status.endpoint is not None
        port = int(status.endpoint.split(":")[2].split("/")[0])
        ports.append(port)
        client = AbletonExportClient(_handoff(server, tmp_path), daw_version="11.2.7")
        assert client.handshake()["state"] == "connected"
        assert client.disconnect()["state"] == "bridge_available"
        server.stop()
        assert server.status().state is DawConnectionState.STOPPED
        with socket.socket() as probe:
            assert probe.connect_ex(("127.0.0.1", port)) != 0
    assert len(ports) == 10


def test_disconnect_and_shutdown_wait_for_active_analysis(tmp_path: Path) -> None:
    audio = tmp_path / "active.wav"
    second_audio = tmp_path / "second.wav"
    _write_wav(audio)
    _write_wav(second_audio, frames=2048)
    entered = threading.Event()
    release = threading.Event()

    def blocking(request: object) -> DawAnalysisResult:
        entered.set()
        assert release.wait(timeout=10)
        return _completed(request)

    gateway = DawAnalysisGateway(blocking)
    server = AbletonBridgeServer(
        tmp_path,
        token=TOKEN,
        stable_seconds=0,
        analysis_gateway=gateway,
    )
    server.start()
    client = AbletonExportClient(_handoff(server, tmp_path), daw_version="11.2.7")
    client.handshake()
    client.submit_export(audio, project_name="Disposable")
    queued = client.submit_export(audio, project_name="Disposable")
    request_id = str(queued["request_id"])
    assert entered.wait(timeout=2)
    client.submit_export(second_audio, project_name="Disposable")
    second_queued = client.submit_export(second_audio, project_name="Disposable")
    second_request_id = str(second_queued["request_id"])
    assert client.disconnect()["state"] == "bridge_available"

    shutdown = threading.Thread(target=server.stop, daemon=True)
    shutdown.start()
    shutdown.join(timeout=0.1)
    assert shutdown.is_alive()
    release.set()
    shutdown.join(timeout=5)
    assert not shutdown.is_alive()
    assert server.status().state is DawConnectionState.STOPPED
    result = gateway.result(request_id)
    assert result is not None
    assert result.state is DawAnalysisState.COMPLETED
    second_result = gateway.result(second_request_id)
    assert second_result is not None
    assert second_result.state is DawAnalysisState.COMPLETED


def test_client_and_gateway_imports_remain_lightweight() -> None:
    script = """
import json
import sys
import phasenox.integration.ableton_client
import phasenox.integration.daw_analysis
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


def test_process_probe_returns_only_main_ableton_processes() -> None:
    processes = detect_running_ableton()
    assert all(item.pid > 0 for item in processes)
    assert all(item.executable_name.startswith("Ableton Live ") for item in processes)
    assert all("Scanner" not in item.executable_name for item in processes)
    assert all("Index" not in item.executable_name for item in processes)

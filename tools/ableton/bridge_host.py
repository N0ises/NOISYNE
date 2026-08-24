"""Run the PHASENOX-side Ableton export bridge for explicit local use."""

from __future__ import annotations

import argparse
import json
import signal
import threading
from pathlib import Path

from phasenox.integration.ableton_bridge import AbletonBridgeServer
from phasenox.integration.ableton_client import (
    AbletonClientError,
    default_handoff_path,
    discard_handoff,
    read_handoff,
    write_handoff,
)
from phasenox.integration.daw_analysis import DawAnalysisGateway


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the local PHASENOX Ableton export bridge.")
    parser.add_argument("--export-root", type=Path, required=True)
    parser.add_argument("--handoff", type=Path, default=None)
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--stable-seconds", type=float, default=1.0)
    return parser


def main() -> int:
    args = _parser().parse_args()
    handoff_path = args.handoff or default_handoff_path()
    bridge = AbletonBridgeServer(
        args.export_root,
        port=args.port,
        stable_seconds=args.stable_seconds,
        analysis_gateway=DawAnalysisGateway(),
    )
    stop_event = threading.Event()

    def request_stop(_signum: int, _frame: object) -> None:
        stop_event.set()

    signal.signal(signal.SIGINT, request_stop)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, request_stop)

    status = bridge.start()
    if status.endpoint is None:
        raise RuntimeError("Bridge started without a loopback endpoint.")
    write_handoff(
        handoff_path,
        endpoint=status.endpoint,
        token=bridge.token,
        export_root=bridge.export_root,
    )
    print(
        json.dumps(
            {
                "state": status.state.value,
                "endpoint": status.endpoint,
                "handoff": str(handoff_path),
                "export_root": str(bridge.export_root),
            },
            sort_keys=True,
        ),
        flush=True,
    )
    try:
        stop_event.wait()
    finally:
        bridge.stop()
        try:
            current = read_handoff(handoff_path)
        except AbletonClientError:
            current = None
        if current is not None and current.token == bridge.token:
            discard_handoff(handoff_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

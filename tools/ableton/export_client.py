"""Watch one explicit Ableton export folder and submit changed WAV files."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from phasenox.integration.ableton_client import (
    AbletonClientError,
    AbletonExportClient,
    default_handoff_path,
    read_handoff,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the PHASENOX Ableton export helper.")
    parser.add_argument("--daw-version", required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--track", default=None)
    parser.add_argument("--handoff", type=Path, default=None)
    parser.add_argument("--poll-seconds", type=float, default=0.5)
    parser.add_argument("--include-existing", action="store_true")
    parser.add_argument("--once", action="store_true")
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.poll_seconds < 0.1:
        raise SystemExit("--poll-seconds must be at least 0.1")
    client = AbletonExportClient(
        read_handoff(args.handoff or default_handoff_path()),
        daw_version=args.daw_version,
    )
    handshake = client.handshake()
    print(
        json.dumps(
            {
                "state": handshake.get("state"),
                "client": handshake.get("client_name"),
                "daw_version": handshake.get("daw_version"),
            },
            sort_keys=True,
        ),
        flush=True,
    )
    if not args.include_existing:
        client.prime_exports()
    pending: set[Path] = set(client.changed_exports() if args.include_existing else ())
    completed = 0
    try:
        while True:
            pending.update(client.changed_exports())
            for path in tuple(sorted(pending, key=lambda item: item.name.casefold())):
                try:
                    response = client.submit_export(
                        path,
                        project_name=args.project,
                        track_name=args.track,
                    )
                except AbletonClientError as exc:
                    if exc.code in {"path_unavailable", "unsupported_audio"}:
                        pending.discard(path)
                    print(json.dumps({"state": "error", "code": exc.code}), flush=True)
                    continue
                state = response.get("status")
                if state == "observing":
                    continue
                pending.discard(path)
                request_id = response.get("request_id") or response.get("export_id")
                if state == "queued" and isinstance(request_id, str):
                    result = client.wait_for_result(request_id)
                    print(json.dumps(result, sort_keys=True), flush=True)
                else:
                    print(json.dumps(response, sort_keys=True), flush=True)
                completed += 1
                if args.once and completed >= 1:
                    return 0
            time.sleep(args.poll_seconds)
    except KeyboardInterrupt:
        return 0
    finally:
        try:
            client.disconnect()
        except AbletonClientError:
            pass


if __name__ == "__main__":
    raise SystemExit(main())

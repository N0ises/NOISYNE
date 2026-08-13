"""Optional local-only desktop performance probe.

The probe deliberately uses a deterministic adapter and never imports the V1
backend.  It measures desktop construction/render overhead; it does not claim
to measure model, DSP, RAG, or provider latency.
"""

from __future__ import annotations

import argparse
import gc
import json
import os
import subprocess
import sys
import time
import tracemalloc
from dataclasses import asdict, dataclass

from .app import build_main_window, create_application
from .branding import default_product_metadata
from .contracts import SettingsSnapshot
from .presentation_state import NAVIGATION_ORDER
from .presentation_store import PresentationStore
from .state import ApplicationStateStore


@dataclass(frozen=True, slots=True)
class DesktopPerformanceReport:
    application_creation_ms: float
    main_window_construction_ms: float
    initial_render_ms: float
    offscreen_ready_ms: float
    mean_current_page_render_ms: float
    navigation_cycle_ms: float
    navigation_python_growth_bytes: int
    navigation_python_peak_bytes: int
    page_count: int
    subscriber_count: int
    cold_process_ms: float | None = None


class _ProbeAdapter:
    """Minimum construction-time adapter surface; no backend code is loaded."""

    def product_metadata(self):
        return default_product_metadata()

    def settings_snapshot(self) -> SettingsSnapshot:
        return SettingsSnapshot("performance-probe", "deterministic local probe", (), False)


def _milliseconds(start: float, end: float) -> float:
    return round((end - start) * 1000.0, 3)


def collect_desktop_metrics(
    *, render_iterations: int = 20, navigation_cycles: int = 10
) -> DesktopPerformanceReport:
    """Collect deterministic UI-only timings and bounded allocation growth."""
    if render_iterations < 1 or navigation_cycles < 1:
        raise ValueError("Performance probe iteration counts must be positive.")

    adapter = _ProbeAdapter()
    application_start = time.perf_counter()
    application = create_application(adapter.product_metadata())
    application_end = time.perf_counter()

    store = PresentationStore()
    construction_start = time.perf_counter()
    window = build_main_window(adapter, ApplicationStateStore(), store)
    construction_end = time.perf_counter()

    render_start = time.perf_counter()
    window._page_host.render_current(store.state)
    render_end = time.perf_counter()

    ready_start = time.perf_counter()
    window.show()
    application.processEvents()
    ready_end = time.perf_counter()

    repeated_render_start = time.perf_counter()
    for _ in range(render_iterations):
        window._page_host.render_current(store.state)
    repeated_render_end = time.perf_counter()

    tracemalloc.start()
    gc.collect()
    allocation_start = tracemalloc.get_traced_memory()[0]
    navigation_start = time.perf_counter()
    for _ in range(navigation_cycles):
        for page in NAVIGATION_ORDER:
            store.navigate(page)
    application.processEvents()
    navigation_end = time.perf_counter()
    gc.collect()
    allocation_end, allocation_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    report = DesktopPerformanceReport(
        application_creation_ms=_milliseconds(application_start, application_end),
        main_window_construction_ms=_milliseconds(construction_start, construction_end),
        initial_render_ms=_milliseconds(render_start, render_end),
        offscreen_ready_ms=_milliseconds(ready_start, ready_end),
        mean_current_page_render_ms=(
            _milliseconds(repeated_render_start, repeated_render_end) / render_iterations
        ),
        navigation_cycle_ms=(_milliseconds(navigation_start, navigation_end) / navigation_cycles),
        navigation_python_growth_bytes=max(0, allocation_end - allocation_start),
        navigation_python_peak_bytes=allocation_peak,
        page_count=len(window._page_host._pages),
        subscriber_count=len(store._subscribers),
    )
    window.close()
    window.deleteLater()
    application.processEvents()
    return report


def collect_cold_process_metrics() -> DesktopPerformanceReport:
    """Measure a cold-ish Python/Qt process around the deterministic child probe."""
    environment = os.environ.copy()
    environment.setdefault("QT_QPA_PLATFORM", "offscreen")
    started = time.perf_counter()
    completed = subprocess.run(
        [sys.executable, "-m", "brain.ui.performance_probe", "--child"],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    )
    finished = time.perf_counter()
    payload = json.loads(completed.stdout.strip().splitlines()[-1])
    payload["cold_process_ms"] = _milliseconds(started, finished)
    return DesktopPerformanceReport(**payload)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run local desktop UI performance probes.")
    parser.add_argument(
        "--cold-process",
        action="store_true",
        help="Include Python/Qt startup by running the deterministic probe in a child process.",
    )
    parser.add_argument("--child", action="store_true", help=argparse.SUPPRESS)
    return parser


def main(argv: list[str] | None = None) -> int:
    options = _parser().parse_args(argv)
    report = (
        collect_cold_process_metrics()
        if options.cold_process and not options.child
        else collect_desktop_metrics()
    )
    print(json.dumps(asdict(report), indent=None if options.child else 2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

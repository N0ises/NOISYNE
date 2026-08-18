from __future__ import annotations

import threading
import time
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass
from math import fsum
from statistics import mean, median
from typing import Any

from ._common import PERFORMANCE_SCHEMA_VERSION, _require_identifier
from .contracts import (
    DeviceType,
    LatencyStatistics,
    MemoryMeasurement,
    PerformanceBenchmarkResult,
    PerformanceEnvironment,
    PerformanceWorkload,
    Precision,
    RawLatencySample,
)


def _percentile(sorted_values: list[float], percentile: float) -> float:
    if not sorted_values:
        raise ValueError("percentile requires at least one value")
    if percentile <= 0.0:
        return sorted_values[0]
    if percentile >= 1.0:
        return sorted_values[-1]
    index = percentile * (len(sorted_values) - 1)
    lower = int(index)
    upper = lower + 1
    if upper >= len(sorted_values):
        return sorted_values[-1]
    weight = index - lower
    return sorted_values[lower] * (1.0 - weight) + sorted_values[upper] * weight


@dataclass(frozen=True, slots=True)
class BenchmarkMethod:
    """Reproducible benchmark methodology identity and parameters."""

    method_version: str = PERFORMANCE_SCHEMA_VERSION
    warmup_iterations: int = 3
    timed_iterations: int = 10

    def __post_init__(self) -> None:
        _require_identifier(self.method_version, "method_version")
        if not isinstance(self.warmup_iterations, int) or self.warmup_iterations < 0:
            raise ValueError("warmup_iterations must be a non-negative integer")
        if not isinstance(self.timed_iterations, int) or self.timed_iterations < 1:
            raise ValueError("timed_iterations must be a positive integer")


def measure_latency(
    callable: Callable[..., Any],
    *args: Any,
    warmup_iterations: int = 3,
    timed_iterations: int = 10,
    **kwargs: Any,
) -> list[RawLatencySample]:
    """Return raw latency samples from repeated execution of ``callable``.

    Samples are tagged by phase: "cold", "warmup", or "timed".  The first call
    is always recorded as cold; subsequent calls follow the declared warmup and
    timed counts.
    """
    samples: list[RawLatencySample] = []
    timer = time.perf_counter

    # Cold call: first execution is always measured separately.
    start = timer()
    callable(*args, **kwargs)
    samples.append(RawLatencySample(phase="cold", elapsed_seconds=timer() - start))

    for iteration in range(warmup_iterations):
        start = timer()
        callable(*args, **kwargs)
        samples.append(RawLatencySample(phase="warmup", elapsed_seconds=timer() - start))

    for iteration in range(timed_iterations):
        start = timer()
        callable(*args, **kwargs)
        samples.append(RawLatencySample(phase="timed", elapsed_seconds=timer() - start))

    return samples


def aggregate_timed_samples(samples: list[RawLatencySample]) -> LatencyStatistics:
    """Aggregate only ``timed`` phase samples into statistics."""
    timed = [sample.elapsed_seconds for sample in samples if sample.phase == "timed"]
    if not timed:
        raise ValueError("no timed samples to aggregate")
    sorted_timed = sorted(timed)
    count = len(sorted_timed)
    p95 = _percentile(sorted_timed, 0.95) if count >= 2 else None
    return LatencyStatistics(
        mean_seconds=mean(sorted_timed),
        median_seconds=median(sorted_timed),
        min_seconds=sorted_timed[0],
        max_seconds=sorted_timed[-1],
        p95_seconds=p95,
        sample_count=count,
    )


@dataclass
class _MemoryPeak:
    ram_bytes: int | None
    gpu_allocated_bytes: int | None
    gpu_reserved_bytes: int | None


@contextmanager
def _memory_sampler(
    device: DeviceType,
    has_psutil: bool,
    has_torch: bool,
):
    """Context manager that records peak process RAM and GPU memory while running."""
    peak = _MemoryPeak(None, None, None)
    stop_event = threading.Event()
    psutil = None
    torch = None

    if has_psutil:
        psutil = __import__("psutil")
    if has_torch:
        torch = __import__("torch")

    def sample() -> None:
        process = psutil.Process() if psutil is not None else None
        while not stop_event.is_set():
            if process is not None:
                try:
                    rss = int(process.memory_info().rss)
                    if peak.ram_bytes is None or rss > peak.ram_bytes:
                        peak.ram_bytes = rss
                except Exception:  # noqa: BLE001, S110
                    pass
            if torch is not None and device is DeviceType.CUDA:
                try:
                    if torch.cuda.is_available():
                        allocated = int(torch.cuda.memory_allocated())
                        reserved = int(torch.cuda.memory_reserved())
                        if peak.gpu_allocated_bytes is None or allocated > peak.gpu_allocated_bytes:
                            peak.gpu_allocated_bytes = allocated
                        if peak.gpu_reserved_bytes is None or reserved > peak.gpu_reserved_bytes:
                            peak.gpu_reserved_bytes = reserved
                except Exception:  # noqa: BLE001, S110
                    pass
            time.sleep(0.05)

    sampler = threading.Thread(target=sample, daemon=True)
    sampler.start()
    try:
        yield peak
    finally:
        stop_event.set()
        sampler.join(timeout=1.0)


def _has_psutil() -> bool:
    try:
        __import__("psutil")
        return True
    except Exception:  # noqa: BLE001
        return False


def _has_torch() -> bool:
    try:
        __import__("torch")
        return True
    except Exception:  # noqa: BLE001
        return False


def benchmark_callable(
    *,
    benchmark_id: str,
    workload: PerformanceWorkload,
    runtime_identity: str,
    device: DeviceType,
    precision: Precision,
    environment: PerformanceEnvironment,
    method: BenchmarkMethod,
    callable: Callable[[], Any],
) -> PerformanceBenchmarkResult:
    """Benchmark a no-argument ``callable`` and return a transport-safe result."""
    _require_identifier(benchmark_id, "benchmark_id")
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    has_psutil = _has_psutil()
    has_torch = _has_torch()

    with _memory_sampler(device, has_psutil, has_torch) as peak:
        samples = measure_latency(
            callable,
            warmup_iterations=method.warmup_iterations,
            timed_iterations=method.timed_iterations,
        )

    cold_samples = [s for s in samples if s.phase == "cold"]
    cold_latency = cold_samples[0].elapsed_seconds if cold_samples else None

    try:
        warm_statistics = aggregate_timed_samples(samples)
    except ValueError:
        warm_statistics = None

    throughput: float | None = None
    if warm_statistics is not None and warm_statistics.median_seconds > 0.0:
        throughput = 1.0 / warm_statistics.median_seconds

    limitations: list[str] = []
    if not has_psutil:
        limitations.append("psutil unavailable; RAM peak measurement disabled")
    if not has_torch:
        limitations.append("torch unavailable; GPU memory measurement disabled")

    return PerformanceBenchmarkResult(
        benchmark_id=benchmark_id,
        workload_id=workload.workload_id,
        runtime_identity=runtime_identity,
        device=device,
        precision=precision,
        environment=environment,
        warmup_iterations=method.warmup_iterations,
        timed_iterations=method.timed_iterations,
        startup_load_time_seconds=None,
        cold_latency_seconds=cold_latency,
        warm_statistics=warm_statistics,
        throughput_per_second=throughput,
        peak_memory=MemoryMeasurement(
            ram_bytes=peak.ram_bytes,
            gpu_allocated_bytes=peak.gpu_allocated_bytes,
            gpu_reserved_bytes=peak.gpu_reserved_bytes,
        ),
        limitations=limitations,
        timestamp_iso=timestamp,
        raw_samples=samples,
    )


def sum_latency_seconds(samples: list[RawLatencySample]) -> float:
    """Sum finite elapsed seconds; used for deterministic aggregate throughput."""
    return fsum(sample.elapsed_seconds for sample in samples if sample.phase == "timed")


__all__ = [
    "BenchmarkMethod",
    "aggregate_timed_samples",
    "benchmark_callable",
    "measure_latency",
    "sum_latency_seconds",
]

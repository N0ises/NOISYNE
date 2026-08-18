from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .benchmark import BenchmarkMethod, benchmark_callable
from .contracts import (
    DeviceType,
    EquivalenceKind,
    PerformanceProfile,
    Precision,
    RuntimeBackend,
    RuntimeCandidate,
)
from .environment import capture_environment
from .fixture_model import build_fixture_runtimes
from .runtime import check_runtime_availability, evaluate_equivalence, select_runtime
from .workloads import build_workload_callables


def _build_fixture_candidates(environment, workload, cache_dir: Path) -> list[RuntimeCandidate]:
    pytorch_fn, onnx_fn, _ = build_fixture_runtimes(str(cache_dir))
    candidates: list[RuntimeCandidate] = []

    pytorch_compat = check_runtime_availability(
        "pytorch_cpu_fp32",
        RuntimeBackend.PYTORCH,
        DeviceType.CPU,
        Precision.FP32,
    )
    onnx_compat = check_runtime_availability(
        "onnxruntime_cpu_fp32",
        RuntimeBackend.ONNX_RUNTIME,
        DeviceType.CPU,
        Precision.FP32,
    )

    fixture_input = np.random.randn(1, 64).astype(np.float32)

    if pytorch_compat.state.value == "available":
        assert pytorch_fn is not None
        benchmark = benchmark_callable(
            benchmark_id=f"fixture_{workload.workload_id}_pytorch_cpu_fp32",
            workload=workload,
            runtime_identity="pytorch_cpu_fp32",
            device=DeviceType.CPU,
            precision=Precision.FP32,
            environment=environment,
            method=BenchmarkMethod(warmup_iterations=2, timed_iterations=5),
            callable=lambda: pytorch_fn(fixture_input),
        )
        candidates.append(
            RuntimeCandidate(
                runtime_identity="pytorch_cpu_fp32",
                backend=RuntimeBackend.PYTORCH,
                device=DeviceType.CPU,
                precision=Precision.FP32,
                compatibility=pytorch_compat,
                equivalence=None,
                benchmark=benchmark,
                is_canonical=True,
            )
        )

    canonical_fn = pytorch_fn if pytorch_fn is not None else onnx_fn
    if onnx_compat.state.value == "available" and canonical_fn is not None and onnx_fn is not None:
        equivalence = evaluate_equivalence(
            canonical_callable=lambda: canonical_fn(fixture_input),
            candidate_callable=lambda: onnx_fn(fixture_input),
            fixture_input=fixture_input,
            canonical_identity="pytorch_cpu_fp32",
            candidate_identity="onnxruntime_cpu_fp32",
            policy=EquivalenceKind.ABSOLUTE_TOLERANCE,
            tolerance_value=1e-4,
        )
        benchmark = benchmark_callable(
            benchmark_id=f"fixture_{workload.workload_id}_onnxruntime_cpu_fp32",
            workload=workload,
            runtime_identity="onnxruntime_cpu_fp32",
            device=DeviceType.CPU,
            precision=Precision.FP32,
            environment=environment,
            method=BenchmarkMethod(warmup_iterations=2, timed_iterations=5),
            callable=lambda: onnx_fn(fixture_input),
        )
        candidates.append(
            RuntimeCandidate(
                runtime_identity="onnxruntime_cpu_fp32",
                backend=RuntimeBackend.ONNX_RUNTIME,
                device=DeviceType.CPU,
                precision=Precision.FP32,
                compatibility=onnx_compat,
                equivalence=equivalence,
                benchmark=benchmark,
                is_canonical=False,
            )
        )

    return candidates


def _run_benchmarks(
    workload_ids: list[str] | None,
    include_fixture: bool,
    cache_dir: Path,
) -> dict[str, Any]:
    environment = capture_environment()
    method = BenchmarkMethod(warmup_iterations=2, timed_iterations=5)
    workload_callables = build_workload_callables()

    results: dict[str, Any] = {
        "environment": environment.to_dict(),
        "workload_benchmarks": [],
        "fixture_benchmarks": [],
        "selections": [],
    }

    for workload_id, (workload, callable) in workload_callables.items():
        if workload_ids is not None and workload_id not in workload_ids:
            continue
        benchmark = benchmark_callable(
            benchmark_id=f"{workload_id}_reference_runtime",
            workload=workload,
            runtime_identity="reference_numpy",
            device=DeviceType.CPU,
            precision=Precision.FP32,
            environment=environment,
            method=method,
            callable=callable,
        )
        results["workload_benchmarks"].append(benchmark.to_dict())

    if include_fixture:
        workload = next(iter(workload_callables.values()))[0]
        candidates = _build_fixture_candidates(environment, workload, cache_dir)
        results["fixture_benchmarks"] = [
            c.benchmark.to_dict() if c.benchmark else None for c in candidates
        ]
        if candidates:
            from .contracts import RuntimeSelectionPolicy

            policy = RuntimeSelectionPolicy(
                policy_id="sprint14_cli",
                profile=PerformanceProfile.BALANCED,
                require_equivalence=True,
                preferred_device=DeviceType.CPU,
                fallback_to_canonical=True,
                prohibited_precisions=[Precision.FP16, Precision.BF16, Precision.INT8],
            )
            canonical = next((c for c in candidates if c.is_canonical), None)
            selection = select_runtime(candidates, policy, canonical)
            results["selections"].append(selection.to_dict())

    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="NØISYNE V2 Sprint 14 performance benchmark")
    parser.add_argument(
        "--workloads",
        nargs="+",
        help="Workload IDs to benchmark (default: all short workloads)",
    )
    parser.add_argument(
        "--no-fixture",
        action="store_true",
        help="Skip the tiny PyTorch/ONNX fixture model benchmark",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path(".noisyne_performance_cache"),
        help="Directory for cached ONNX exports",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output JSON file (default: stdout)",
    )
    args = parser.parse_args(argv)

    results = _run_benchmarks(
        workload_ids=args.workloads,
        include_fixture=not args.no_fixture,
        cache_dir=args.cache_dir,
    )

    json_bytes = json.dumps(results, sort_keys=True, ensure_ascii=False).encode("utf-8")
    if args.output:
        args.output.write_bytes(json_bytes)
    else:
        sys.stdout.write(json_bytes.decode("utf-8"))
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    import numpy as np

    raise SystemExit(main())

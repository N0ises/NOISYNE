from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np

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
from .fixture_model import build_fixture_runtimes_by_device
from .runtime import check_runtime_availability, evaluate_equivalence, select_runtime
from .workloads import build_workload_callables


def _build_fixture_candidates(environment, workload, cache_dir: Path) -> list[RuntimeCandidate]:
    runtimes = build_fixture_runtimes_by_device(str(cache_dir))
    candidates: list[RuntimeCandidate] = []

    fixture_input = np.random.randn(1, 64).astype(np.float32)
    canonical_fn: Callable[[], np.ndarray] | None = None
    canonical_identity: str | None = None

    cpu_compat = check_runtime_availability(
        "pytorch_cpu_fp32",
        RuntimeBackend.PYTORCH,
        DeviceType.CPU,
        Precision.FP32,
    )
    cpu_runtime = runtimes.get("cpu")
    pytorch_cpu_fn = cpu_runtime[0] if cpu_runtime else None
    onnx_cpu_fn = cpu_runtime[1] if cpu_runtime else None

    if cpu_compat.state.value == "available" and pytorch_cpu_fn is not None:
        canonical_fn = pytorch_cpu_fn
        canonical_identity = "pytorch_cpu_fp32"
        benchmark = benchmark_callable(
            benchmark_id=f"fixture_{workload.workload_id}_pytorch_cpu_fp32",
            workload=workload,
            runtime_identity="pytorch_cpu_fp32",
            device=DeviceType.CPU,
            precision=Precision.FP32,
            environment=environment,
            method=BenchmarkMethod(warmup_iterations=2, timed_iterations=5),
            callable=lambda: pytorch_cpu_fn(fixture_input),
        )
        candidates.append(
            RuntimeCandidate(
                runtime_identity="pytorch_cpu_fp32",
                backend=RuntimeBackend.PYTORCH,
                device=DeviceType.CPU,
                precision=Precision.FP32,
                compatibility=cpu_compat,
                equivalence=None,
                benchmark=benchmark,
                is_canonical=True,
            )
        )

    onnx_cpu_compat = check_runtime_availability(
        "onnxruntime_cpu_fp32",
        RuntimeBackend.ONNX_RUNTIME,
        DeviceType.CPU,
        Precision.FP32,
    )
    if (
        onnx_cpu_compat.state.value == "available"
        and canonical_fn is not None
        and onnx_cpu_fn is not None
    ):
        equivalence = evaluate_equivalence(
            canonical_callable=canonical_fn,
            candidate_callable=onnx_cpu_fn,
            fixture_input=fixture_input,
            canonical_identity=canonical_identity,
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
            callable=lambda: onnx_cpu_fn(fixture_input),
        )
        candidates.append(
            RuntimeCandidate(
                runtime_identity="onnxruntime_cpu_fp32",
                backend=RuntimeBackend.ONNX_RUNTIME,
                device=DeviceType.CPU,
                precision=Precision.FP32,
                compatibility=onnx_cpu_compat,
                equivalence=equivalence,
                benchmark=benchmark,
                is_canonical=False,
            )
        )

    cuda_runtime = runtimes.get("cuda")
    pytorch_cuda_fn = cuda_runtime[0] if cuda_runtime else None
    onnx_cuda_fn = cuda_runtime[1] if cuda_runtime else None
    onnx_cuda_session = cuda_runtime[2] if cuda_runtime else None

    if pytorch_cuda_fn is not None:
        pytorch_cuda_compat = check_runtime_availability(
            "pytorch_cuda_fp32",
            RuntimeBackend.PYTORCH,
            DeviceType.CUDA,
            Precision.FP32,
        )
        if pytorch_cuda_compat.state.value == "available":
            cuda_canonical_fn = canonical_fn if canonical_fn is not None else pytorch_cuda_fn
            cuda_canonical_identity = canonical_identity or "pytorch_cuda_fp32"
            equivalence = None
            if canonical_fn is not None:
                equivalence = evaluate_equivalence(
                    canonical_callable=cuda_canonical_fn,
                    candidate_callable=pytorch_cuda_fn,
                    fixture_input=fixture_input,
                    canonical_identity=cuda_canonical_identity,
                    candidate_identity="pytorch_cuda_fp32",
                    policy=EquivalenceKind.ABSOLUTE_TOLERANCE,
                    tolerance_value=1e-4,
                )
            benchmark = benchmark_callable(
                benchmark_id=f"fixture_{workload.workload_id}_pytorch_cuda_fp32",
                workload=workload,
                runtime_identity="pytorch_cuda_fp32",
                device=DeviceType.CUDA,
                precision=Precision.FP32,
                environment=environment,
                method=BenchmarkMethod(warmup_iterations=2, timed_iterations=5),
                callable=lambda: pytorch_cuda_fn(fixture_input),
            )
            candidates.append(
                RuntimeCandidate(
                    runtime_identity="pytorch_cuda_fp32",
                    backend=RuntimeBackend.PYTORCH,
                    device=DeviceType.CUDA,
                    precision=Precision.FP32,
                    compatibility=pytorch_cuda_compat,
                    equivalence=equivalence,
                    benchmark=benchmark,
                    is_canonical=False,
                )
            )

    if onnx_cuda_fn is not None and onnx_cuda_session is not None:
        active_providers = onnx_cuda_session.get_providers()
        provider_is_cuda = "CUDAExecutionProvider" in active_providers
        runtime_identity = (
            "onnxruntime_cuda_fp32"
            if provider_is_cuda
            else "onnxruntime_cuda_advertised_cpu_fallback"
        )
        onnx_cuda_compat = check_runtime_availability(
            runtime_identity,
            RuntimeBackend.ONNX_RUNTIME,
            DeviceType.CUDA if provider_is_cuda else DeviceType.CPU,
            Precision.FP32,
        )
        if onnx_cuda_compat.state.value == "available":
            equivalence = None
            if canonical_fn is not None:
                equivalence = evaluate_equivalence(
                    canonical_callable=canonical_fn,
                    candidate_callable=onnx_cuda_fn,
                    fixture_input=fixture_input,
                    canonical_identity=canonical_identity or "unknown",
                    candidate_identity=runtime_identity,
                    policy=EquivalenceKind.ABSOLUTE_TOLERANCE,
                    tolerance_value=1e-4,
                )
            benchmark = benchmark_callable(
                benchmark_id=f"fixture_{workload.workload_id}_{runtime_identity}",
                workload=workload,
                runtime_identity=runtime_identity,
                device=DeviceType.CUDA if provider_is_cuda else DeviceType.CPU,
                precision=Precision.FP32,
                environment=environment,
                method=BenchmarkMethod(warmup_iterations=2, timed_iterations=5),
                callable=lambda: onnx_cuda_fn(fixture_input),
            )
            candidates.append(
                RuntimeCandidate(
                    runtime_identity=runtime_identity,
                    backend=RuntimeBackend.ONNX_RUNTIME,
                    device=DeviceType.CUDA if provider_is_cuda else DeviceType.CPU,
                    precision=Precision.FP32,
                    compatibility=onnx_cuda_compat,
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
    parser = argparse.ArgumentParser(description="PHASENOX V2 Sprint 14 performance benchmark")
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
    raise SystemExit(main())

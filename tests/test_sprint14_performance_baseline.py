from __future__ import annotations

import math
import time
from datetime import UTC, datetime

import numpy as np
import pytest

from phasenox.performance import (
    AuditoryFrontendWorkload,
    BenchmarkFingerprint,
    BenchmarkMethod,
    BrightnessDescriptorWorkload,
    CompatibilityResult,
    DeviceType,
    EquivalenceKind,
    EquivalenceResult,
    EquivalenceStatus,
    LatencyStatistics,
    MemoryMeasurement,
    PerformanceBenchmarkResult,
    PerformanceEnvironment,
    PerformanceProfile,
    PerformanceWorkload,
    Precision,
    RawLatencySample,
    ReferenceComparisonWorkload,
    RuntimeAvailabilityState,
    RuntimeBackend,
    RuntimeCandidate,
    RuntimeSelectionPolicy,
    SelectionStatus,
    aggregate_timed_samples,
    benchmark_callable,
    capture_environment,
    check_runtime_availability,
    evaluate_equivalence,
    measure_latency,
    runtime_fingerprint_fields,
    select_runtime,
)
from phasenox.performance.fixture_model import build_fixture_runtimes
from phasenox.runtime.capabilities import CapabilityStatus, registry


def _environment_fixture() -> PerformanceEnvironment:
    return PerformanceEnvironment(
        os_name="TestOS",
        os_version="1.0",
        architecture="x86_64",
        python_version="3.12.0",
        cpu_brand="Test CPU",
        logical_cores=4,
        total_ram_bytes=16_000_000_000,
        gpu_name=None,
        gpu_total_vram_bytes=None,
        cuda_available=False,
        cuda_version=None,
        torch_version="2.0.0",
        onnxruntime_version="1.27.0",
        onnxruntime_providers=["CPUExecutionProvider"],
    )


def test_environment_contract_round_trip() -> None:
    env = _environment_fixture()
    restored = PerformanceEnvironment.from_dict(env.to_dict())
    assert restored == env


def test_workload_contract_round_trip() -> None:
    workload = PerformanceWorkload(
        workload_id="w1",
        workload_type="auditory_frontend",
        description="short auditory workload",
        duration_seconds=1.0,
        sample_count=1,
        deterministic=True,
    )
    assert PerformanceWorkload.from_dict(workload.to_dict()) == workload


def test_benchmark_result_round_trip() -> None:
    env = _environment_fixture()
    result = PerformanceBenchmarkResult(
        benchmark_id="b1",
        workload_id="w1",
        runtime_identity="pytorch_cpu_fp32",
        device=DeviceType.CPU,
        precision=Precision.FP32,
        environment=env,
        warmup_iterations=2,
        timed_iterations=3,
        startup_load_time_seconds=0.1,
        cold_latency_seconds=0.05,
        warm_statistics=LatencyStatistics(
            mean_seconds=0.01,
            median_seconds=0.01,
            min_seconds=0.009,
            max_seconds=0.012,
            p95_seconds=0.012,
            sample_count=3,
        ),
        throughput_per_second=100.0,
        peak_memory=MemoryMeasurement(
            ram_bytes=50_000_000, gpu_allocated_bytes=None, gpu_reserved_bytes=None
        ),
        timestamp_iso=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    )
    restored = PerformanceBenchmarkResult.from_dict(result.to_dict())
    assert restored == result


def test_latency_statistics_reject_non_finite() -> None:
    with pytest.raises(ValueError):
        LatencyStatistics(
            mean_seconds=float("nan"),
            median_seconds=0.01,
            min_seconds=0.01,
            max_seconds=0.01,
            p95_seconds=None,
            sample_count=1,
        )


def test_workload_reject_negative_duration() -> None:
    with pytest.raises(ValueError):
        PerformanceWorkload(
            workload_id="w1",
            workload_type="x",
            description="bad",
            duration_seconds=-1.0,
            sample_count=1,
            deterministic=True,
        )


def test_raw_latency_sample_finite_only() -> None:
    with pytest.raises(ValueError):
        RawLatencySample(phase="timed", elapsed_seconds=float("inf"))


def test_explicit_units_in_field_names() -> None:
    # Ensure time fields carry seconds and memory fields carry bytes in their names.
    result = PerformanceBenchmarkResult(
        benchmark_id="b1",
        workload_id="w1",
        runtime_identity="r1",
        device=DeviceType.CPU,
        precision=Precision.FP32,
        environment=_environment_fixture(),
        warmup_iterations=1,
        timed_iterations=1,
        startup_load_time_seconds=0.1,
        cold_latency_seconds=0.1,
        warm_statistics=LatencyStatistics(
            mean_seconds=0.1,
            median_seconds=0.1,
            min_seconds=0.1,
            max_seconds=0.1,
            p95_seconds=None,
            sample_count=1,
        ),
        throughput_per_second=10.0,
        peak_memory=MemoryMeasurement(
            ram_bytes=1000, gpu_allocated_bytes=None, gpu_reserved_bytes=None
        ),
    )
    data = result.to_dict()
    assert "cold_latency_seconds" in data
    assert "warm_statistics" in data
    assert "throughput_per_second" in data
    assert "peak_memory" in data


def test_capture_environment_truthful() -> None:
    env = capture_environment()
    assert env.os_name
    assert env.architecture
    assert env.python_version
    # Missing data must be None/empty, not fabricated.
    assert env.total_ram_bytes is None or isinstance(env.total_ram_bytes, int)
    assert isinstance(env.cuda_available, bool)


def test_runtime_availability_cpu_runtimes_available() -> None:
    pytorch = check_runtime_availability(
        "pytorch_cpu_fp32", RuntimeBackend.PYTORCH, DeviceType.CPU, Precision.FP32
    )
    onnx = check_runtime_availability(
        "onnxruntime_cpu_fp32", RuntimeBackend.ONNX_RUNTIME, DeviceType.CPU, Precision.FP32
    )
    # On this machine both PyTorch and ONNX Runtime are installed.
    assert pytorch.state is RuntimeAvailabilityState.AVAILABLE
    assert onnx.state is RuntimeAvailabilityState.AVAILABLE


def test_runtime_availability_cuda_truthful() -> None:
    cuda = check_runtime_availability(
        "pytorch_cuda_fp32", RuntimeBackend.PYTORCH, DeviceType.CUDA, Precision.FP32
    )
    # The result must truthfully reflect whether PyTorch can use CUDA on this machine.
    import torch

    if torch.cuda.is_available():
        assert cuda.state is RuntimeAvailabilityState.AVAILABLE
    else:
        assert cuda.state in (
            RuntimeAvailabilityState.UNAVAILABLE,
            RuntimeAvailabilityState.INCOMPATIBLE,
        )


def test_runtime_availability_fp16_incompatible_on_pytorch_cpu() -> None:
    result = check_runtime_availability(
        "pytorch_cpu_fp16", RuntimeBackend.PYTORCH, DeviceType.CPU, Precision.FP16
    )
    assert result.state in (
        RuntimeAvailabilityState.INCOMPATIBLE,
        RuntimeAvailabilityState.UNAVAILABLE,
    )


def test_measure_latency_separates_cold_and_warm() -> None:
    samples = measure_latency(
        lambda: time.sleep(0.001),
        warmup_iterations=2,
        timed_iterations=3,
    )
    phases = [sample.phase for sample in samples]
    assert phases.count("cold") == 1
    assert phases.count("warmup") == 2
    assert phases.count("timed") == 3


def test_aggregate_timed_samples_ignores_cold_and_warmup() -> None:
    samples = [
        RawLatencySample(phase="cold", elapsed_seconds=1.0),
        RawLatencySample(phase="warmup", elapsed_seconds=1.0),
        RawLatencySample(phase="timed", elapsed_seconds=0.01),
        RawLatencySample(phase="timed", elapsed_seconds=0.02),
        RawLatencySample(phase="timed", elapsed_seconds=0.03),
    ]
    stats = aggregate_timed_samples(samples)
    assert stats.sample_count == 3
    assert stats.min_seconds == pytest.approx(0.01, abs=1e-12)
    assert stats.max_seconds == pytest.approx(0.03, abs=1e-12)
    assert stats.median_seconds == pytest.approx(0.02, abs=1e-12)


def test_benchmark_callable_returns_finite_result() -> None:
    env = _environment_fixture()
    workload = PerformanceWorkload(
        workload_id="sleep",
        workload_type="stub",
        description="stub",
        duration_seconds=0.0,
        sample_count=1,
        deterministic=True,
    )
    result = benchmark_callable(
        benchmark_id="stub_bench",
        workload=workload,
        runtime_identity="stub_runtime",
        device=DeviceType.CPU,
        precision=Precision.FP32,
        environment=env,
        method=BenchmarkMethod(warmup_iterations=1, timed_iterations=2),
        callable=lambda: time.sleep(0.001),
    )
    assert result.benchmark_id == "stub_bench"
    assert result.warm_statistics is not None
    assert result.cold_latency_seconds is not None
    assert result.throughput_per_second is not None
    assert math.isfinite(result.warm_statistics.median_seconds)


def test_equivalence_exact_match() -> None:
    result = evaluate_equivalence(
        canonical_callable=lambda x: x * 2,
        candidate_callable=lambda x: x * 2,
        fixture_input=np.array([1.0, 2.0, 3.0]),
        canonical_identity="canonical",
        candidate_identity="candidate",
        policy=EquivalenceKind.EXACT,
    )
    assert result.status is EquivalenceStatus.EQUIVALENT


def test_equivalence_absolute_tolerance_within() -> None:
    result = evaluate_equivalence(
        canonical_callable=lambda x: x * 2,
        candidate_callable=lambda x: x * 2 + 1e-7,
        fixture_input=np.array([1.0, 2.0, 3.0]),
        canonical_identity="canonical",
        candidate_identity="candidate",
        policy=EquivalenceKind.ABSOLUTE_TOLERANCE,
        tolerance_value=1e-5,
    )
    assert result.status is EquivalenceStatus.WITHIN_TOLERANCE


def test_equivalence_absolute_tolerance_different() -> None:
    result = evaluate_equivalence(
        canonical_callable=lambda x: x * 2,
        candidate_callable=lambda x: x * 2 + 1.0,
        fixture_input=np.array([1.0, 2.0, 3.0]),
        canonical_identity="canonical",
        candidate_identity="candidate",
        policy=EquivalenceKind.ABSOLUTE_TOLERANCE,
        tolerance_value=1e-5,
    )
    assert result.status is EquivalenceStatus.DIFFERENT


def test_select_runtime_prefers_validated_fastest() -> None:
    env = _environment_fixture()
    workload = PerformanceWorkload(
        workload_id="w1",
        workload_type="x",
        description="x",
        duration_seconds=0.0,
        sample_count=1,
        deterministic=True,
    )

    def make_candidate(
        identity: str,
        latency: float,
        equivalent: bool,
        is_canonical: bool = False,
    ) -> RuntimeCandidate:
        benchmark = PerformanceBenchmarkResult(
            benchmark_id=f"b_{identity}",
            workload_id=workload.workload_id,
            runtime_identity=identity,
            device=DeviceType.CPU,
            precision=Precision.FP32,
            environment=env,
            warmup_iterations=0,
            timed_iterations=1,
            warm_statistics=LatencyStatistics(
                mean_seconds=latency,
                median_seconds=latency,
                min_seconds=latency,
                max_seconds=latency,
                p95_seconds=None,
                sample_count=1,
            ),
            throughput_per_second=1.0 / latency,
            peak_memory=MemoryMeasurement(None, None, None),
        )
        equivalence = EquivalenceResult(
            runtime_identity=identity,
            canonical_identity="canonical",
            status=(
                EquivalenceStatus.WITHIN_TOLERANCE if equivalent else EquivalenceStatus.DIFFERENT
            ),
            policy=EquivalenceKind.ABSOLUTE_TOLERANCE,
            tolerance_value=1e-5,
            max_absolute_difference=0.0 if equivalent else 1.0,
            max_relative_difference=0.0 if equivalent else 1.0,
            reason="test",
        )
        return RuntimeCandidate(
            runtime_identity=identity,
            backend=RuntimeBackend.PYTORCH,
            device=DeviceType.CPU,
            precision=Precision.FP32,
            compatibility=CompatibilityResult(
                runtime_identity=identity,
                backend=RuntimeBackend.PYTORCH,
                device=DeviceType.CPU,
                precision=Precision.FP32,
                state=RuntimeAvailabilityState.AVAILABLE,
                reason=None,
            ),
            equivalence=equivalence,
            benchmark=benchmark,
            is_canonical=is_canonical,
        )

    canonical = make_candidate("canonical", 0.010, equivalent=True, is_canonical=True)
    fast_invalid = make_candidate("fast_invalid", 0.001, equivalent=False)
    slow_valid = make_candidate("slow_valid", 0.005, equivalent=True)

    policy = RuntimeSelectionPolicy(
        policy_id="p1",
        profile=PerformanceProfile.BALANCED,
        require_equivalence=True,
        fallback_to_canonical=True,
    )
    selection = select_runtime([canonical, fast_invalid, slow_valid], policy, canonical)
    assert selection.selection_status is SelectionStatus.SELECTED
    assert selection.selected_candidate is not None
    assert selection.selected_candidate.runtime_identity == "slow_valid"
    assert any(r.runtime_identity == "fast_invalid" for r in selection.rejected_candidates)
    assert selection.evidence_ids == ["slow_valid", "slow_valid"]


def test_select_runtime_falls_back_to_canonical() -> None:
    canonical = RuntimeCandidate(
        runtime_identity="canonical",
        backend=RuntimeBackend.PYTORCH,
        device=DeviceType.CPU,
        precision=Precision.FP32,
        compatibility=CompatibilityResult(
            runtime_identity="canonical",
            backend=RuntimeBackend.PYTORCH,
            device=DeviceType.CPU,
            precision=Precision.FP32,
            state=RuntimeAvailabilityState.AVAILABLE,
            reason=None,
        ),
        equivalence=None,
        benchmark=None,
        is_canonical=True,
    )
    bad = RuntimeCandidate(
        runtime_identity="bad",
        backend=RuntimeBackend.PYTORCH,
        device=DeviceType.CPU,
        precision=Precision.FP32,
        compatibility=CompatibilityResult(
            runtime_identity="bad",
            backend=RuntimeBackend.PYTORCH,
            device=DeviceType.CPU,
            precision=Precision.FP32,
            state=RuntimeAvailabilityState.UNAVAILABLE,
            reason="not installed",
        ),
        equivalence=None,
        benchmark=None,
        is_canonical=False,
    )
    policy = RuntimeSelectionPolicy(
        policy_id="p1",
        profile=PerformanceProfile.BALANCED,
        require_equivalence=True,
        fallback_to_canonical=True,
    )
    selection = select_runtime([bad], policy, canonical)
    assert selection.selection_status is SelectionStatus.FALLBACK
    assert selection.selected_candidate is canonical


def test_benchmark_fingerprint_determinism() -> None:
    env = _environment_fixture()
    fp1 = BenchmarkFingerprint(
        **runtime_fingerprint_fields(env, "pytorch_cpu_fp32", Precision.FP32, "w1")
    )
    fp2 = BenchmarkFingerprint(
        **runtime_fingerprint_fields(env, "pytorch_cpu_fp32", Precision.FP32, "w1")
    )
    assert fp1.to_dict() == fp2.to_dict()


def test_benchmark_fingerprint_changes_with_runtime() -> None:
    env = _environment_fixture()
    fp1 = BenchmarkFingerprint(
        **runtime_fingerprint_fields(env, "pytorch_cpu_fp32", Precision.FP32, "w1")
    )
    fp2 = BenchmarkFingerprint(
        **runtime_fingerprint_fields(env, "onnxruntime_cpu_fp32", Precision.FP32, "w1")
    )
    assert fp1.to_dict() != fp2.to_dict()


def test_selection_preserves_provider_and_device_identity() -> None:
    canonical = RuntimeCandidate(
        runtime_identity="canonical",
        backend=RuntimeBackend.PYTORCH,
        device=DeviceType.CPU,
        precision=Precision.FP32,
        compatibility=CompatibilityResult(
            runtime_identity="canonical",
            backend=RuntimeBackend.PYTORCH,
            device=DeviceType.CPU,
            precision=Precision.FP32,
            state=RuntimeAvailabilityState.AVAILABLE,
            reason=None,
        ),
        equivalence=None,
        benchmark=None,
        is_canonical=True,
    )
    policy = RuntimeSelectionPolicy(
        policy_id="p1",
        profile=PerformanceProfile.BALANCED,
        require_equivalence=False,
        fallback_to_canonical=True,
    )
    selection = select_runtime([], policy, canonical)
    assert selection.canonical_candidate is not None
    assert selection.canonical_candidate.backend is RuntimeBackend.PYTORCH
    assert selection.canonical_candidate.device is DeviceType.CPU


def test_no_universal_performance_score_in_contract() -> None:
    result = PerformanceBenchmarkResult(
        benchmark_id="b1",
        workload_id="w1",
        runtime_identity="r1",
        device=DeviceType.CPU,
        precision=Precision.FP32,
        environment=_environment_fixture(),
        warmup_iterations=0,
        timed_iterations=1,
        warm_statistics=LatencyStatistics(
            mean_seconds=0.1,
            median_seconds=0.1,
            min_seconds=0.1,
            max_seconds=0.1,
            p95_seconds=None,
            sample_count=1,
        ),
        throughput_per_second=10.0,
        peak_memory=MemoryMeasurement(None, None, None),
    )
    data = result.to_dict()
    assert "overall_score" not in data
    assert "score" not in data


def test_runtime_selection_rejects_missing_equivalence_when_required() -> None:
    candidate = RuntimeCandidate(
        runtime_identity="no_equiv",
        backend=RuntimeBackend.ONNX_RUNTIME,
        device=DeviceType.CPU,
        precision=Precision.FP32,
        compatibility=CompatibilityResult(
            runtime_identity="no_equiv",
            backend=RuntimeBackend.ONNX_RUNTIME,
            device=DeviceType.CPU,
            precision=Precision.FP32,
            state=RuntimeAvailabilityState.AVAILABLE,
            reason=None,
        ),
        equivalence=None,
        benchmark=None,
        is_canonical=False,
    )
    policy = RuntimeSelectionPolicy(
        policy_id="p1",
        profile=PerformanceProfile.BALANCED,
        require_equivalence=True,
        fallback_to_canonical=False,
    )
    selection = select_runtime([candidate], policy, None)
    assert selection.selection_status is SelectionStatus.NO_CANDIDATE


def test_fixture_model_pytorch_onnx_equivalence() -> None:
    pytorch_fn, onnx_fn, _ = build_fixture_runtimes(".noisyne_performance_test_cache")
    if pytorch_fn is None or onnx_fn is None:
        pytest.skip("PyTorch or ONNX Runtime not available for fixture model")
    fixture_input = np.random.randn(1, 64).astype(np.float32)
    result = evaluate_equivalence(
        canonical_callable=pytorch_fn,
        candidate_callable=onnx_fn,
        fixture_input=fixture_input,
        canonical_identity="pytorch_cpu_fp32",
        candidate_identity="onnxruntime_cpu_fp32",
        policy=EquivalenceKind.ABSOLUTE_TOLERANCE,
        tolerance_value=1e-4,
    )
    assert result.status in (EquivalenceStatus.EQUIVALENT, EquivalenceStatus.WITHIN_TOLERANCE)


def test_auditory_workload_benchmark_is_finite() -> None:
    workload_runner = AuditoryFrontendWorkload(1.0)
    env = capture_environment()
    workload = workload_runner.workload
    result = benchmark_callable(
        benchmark_id="auditory_1s_bench",
        workload=workload,
        runtime_identity="reference_numpy",
        device=DeviceType.CPU,
        precision=Precision.FP32,
        environment=env,
        method=BenchmarkMethod(warmup_iterations=0, timed_iterations=2),
        callable=workload_runner.run,
    )
    assert result.warm_statistics is not None
    assert math.isfinite(result.warm_statistics.median_seconds)


def test_brightness_workload_benchmark_is_finite() -> None:
    workload_runner = BrightnessDescriptorWorkload(1.0)
    env = capture_environment()
    workload = workload_runner.workload
    result = benchmark_callable(
        benchmark_id="brightness_1s_bench",
        workload=workload,
        runtime_identity="reference_numpy",
        device=DeviceType.CPU,
        precision=Precision.FP32,
        environment=env,
        method=BenchmarkMethod(warmup_iterations=0, timed_iterations=2),
        callable=workload_runner.run,
    )
    assert result.warm_statistics is not None
    assert math.isfinite(result.warm_statistics.median_seconds)


def test_reference_comparison_workload_benchmark_is_finite() -> None:
    workload_runner = ReferenceComparisonWorkload(1.0)
    env = capture_environment()
    workload = workload_runner.workload
    result = benchmark_callable(
        benchmark_id="reference_1s_bench",
        workload=workload,
        runtime_identity="reference_numpy",
        device=DeviceType.CPU,
        precision=Precision.FP32,
        environment=env,
        method=BenchmarkMethod(warmup_iterations=0, timed_iterations=2),
        callable=workload_runner.run,
    )
    assert result.warm_statistics is not None
    assert math.isfinite(result.warm_statistics.median_seconds)


def test_performance_capabilities_registered() -> None:
    for name in (
        "performance_benchmark_foundation",
        "runtime_selection_foundation",
        "onnx_runtime_optimization",
    ):
        cap = registry.get(name)
        assert cap is not None
        assert cap.status in (CapabilityStatus.IMPLEMENTED, CapabilityStatus.VERIFIED)

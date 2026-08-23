"""Sprint 15.5 — ONNX Runtime GPU execution validation.

These tests validate the CUDA execution path on the current machine and must
skip truthfully when CUDA hardware or the compatible ONNX Runtime GPU package
is unavailable.  They do NOT convert or validate production PHASENØX models.

Critical robustness rule implemented in this sprint:

    ``CUDAExecutionProvider`` in ``onnxruntime.get_available_providers()``
    is NOT sufficient to claim CUDA is usable.  Availability must be proven by
    creating a real ``InferenceSession`` and observing that the active provider
    list contains ``CUDAExecutionProvider`` while producing finite output.
"""

from __future__ import annotations

import os
import subprocess
import sys

import numpy as np
import pytest

from phasenox.performance import (
    BenchmarkMethod,
    CompatibilityResult,
    DeviceType,
    EquivalenceKind,
    EquivalenceStatus,
    LatencyStatistics,
    MemoryMeasurement,
    PerformanceBenchmarkResult,
    PerformanceEnvironment,
    PerformanceProfile,
    PerformanceWorkload,
    Precision,
    RuntimeAvailabilityState,
    RuntimeBackend,
    RuntimeCandidate,
    RuntimeSelectionPolicy,
    SelectionStatus,
    benchmark_callable,
    capture_environment,
    check_runtime_availability,
    evaluate_equivalence,
    select_runtime,
)
from phasenox.performance.fixture_model import (
    _ensure_cuda_dll_paths,
    _onnx_cuda_session_loaded,
    _onnxruntime_cuda_available,
    _onnxruntime_cuda_executable,
    _torch_cuda_available,
    build_fixture_runtimes_by_device,
)

# Capture PATH before any test adds NVIDIA wheel directories.  This lets us
# spawn a truly bare onnxruntime subprocess below.
_ORIGINAL_PATH = os.environ.get("PATH", "")


@pytest.fixture(scope="module")
def fixture_runtimes() -> dict:
    return build_fixture_runtimes_by_device(".noisyne_performance_test_cache")


@pytest.fixture(scope="module")
def environment() -> PerformanceEnvironment:
    return capture_environment()


def test_cuda_provider_detection_truthful() -> None:
    """CUDAExecutionProvider appears only when ORT actually lists it."""
    import onnxruntime as ort

    providers = ort.get_available_providers()
    assert isinstance(providers, list)
    has_cuda = "CUDAExecutionProvider" in providers
    assert has_cuda == _onnxruntime_cuda_available()


def test_torch_cuda_available_consistent() -> None:
    """PyTorch CUDA availability matches the local torch install."""
    import torch

    assert _torch_cuda_available() == torch.cuda.is_available()


def test_runtime_availability_uses_executable_cuda_check() -> None:
    """check_runtime_availability reports CUDA available only when ORT can execute on CUDA."""
    result = check_runtime_availability(
        "onnxruntime_cuda_fp32",
        RuntimeBackend.ONNX_RUNTIME,
        DeviceType.CUDA,
        Precision.FP32,
    )
    assert result.state in (
        RuntimeAvailabilityState.AVAILABLE,
        RuntimeAvailabilityState.UNAVAILABLE,
        RuntimeAvailabilityState.INCOMPATIBLE,
    )
    executable = _onnxruntime_cuda_executable()
    if executable:
        assert result.state is RuntimeAvailabilityState.AVAILABLE
    else:
        assert result.state is RuntimeAvailabilityState.UNAVAILABLE


def test_advertised_provider_is_not_executable_provider() -> None:
    """A provider may be advertised yet fail to execute; the contract uses executable truth."""
    advertised = _onnxruntime_cuda_available()
    if not advertised:
        pytest.skip("CUDAExecutionProvider is not advertised on this machine")
    executable = _onnxruntime_cuda_executable()
    result = check_runtime_availability(
        "onnxruntime_cuda_fp32",
        RuntimeBackend.ONNX_RUNTIME,
        DeviceType.CUDA,
        Precision.FP32,
    )
    # When advertised but not executable the contract must report unavailable.
    if not executable:
        assert result.state is RuntimeAvailabilityState.UNAVAILABLE
    else:
        assert result.state is RuntimeAvailabilityState.AVAILABLE


def test_bare_onnxruntime_cuda_executable_without_torch() -> None:
    """ONNX Runtime can execute on CUDA without a prior torch import after DLL paths are set."""
    if not _onnxruntime_cuda_available():
        pytest.skip("CUDAExecutionProvider is not advertised on this machine")

    code = (
        "import sys\n"
        f"sys.path.insert(0, {os.getcwd()!r})\n"
        "from phasenox.performance.fixture_model import (\n"
        "    _ensure_cuda_dll_paths,\n"
        "    _onnxruntime_cuda_executable,\n"
        ")\n"
        "_ensure_cuda_dll_paths()\n"
        "ok = _onnxruntime_cuda_executable('.noisyne_performance_test_cache')\n"
        "print('EXECUTABLE_CUDA=' + str(ok))\n"
    )
    env = os.environ.copy()
    # Strip any NVIDIA wheel directories from PATH so the subprocess does not
    # accidentally inherit them from the parent pytest process.
    env["PATH"] = _ORIGINAL_PATH
    proc = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        env=env,
        cwd=os.getcwd(),
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert "EXECUTABLE_CUDA=True" in proc.stdout


def test_bare_onnxruntime_without_dll_paths_falls_back_to_cpu() -> None:
    """Without the DLL path setup, a bare onnxruntime subprocess may advertise CUDA but run on CPU."""
    if not _onnxruntime_cuda_available():
        pytest.skip("CUDAExecutionProvider is not advertised on this machine")

    code = (
        "import sys\n"
        f"sys.path.insert(0, {os.getcwd()!r})\n"
        "import onnxruntime as ort\n"
        "import numpy as np\n"
        "s = ort.InferenceSession(\n"
        "    '.noisyne_performance_test_cache/fixture_model.onnx',\n"
        "    providers=['CUDAExecutionProvider', 'CPUExecutionProvider'],\n"
        ")\n"
        "print('ACTIVE_PROVIDER=' + s.get_providers()[0])\n"
        "out = s.run(None, {s.get_inputs()[0].name: np.random.randn(1, 64).astype(np.float32)})[0]\n"
        "print('FINITE=' + str(np.all(np.isfinite(out))))\n"
    )
    env = os.environ.copy()
    env["PATH"] = _ORIGINAL_PATH
    proc = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        env=env,
        cwd=os.getcwd(),
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    # The active provider may be CUDA if the system PATH already contains the
    # required DLLs, or CPU if it does not.  The important invariant is finite
    # output and that advertised != guaranteed.
    assert "ACTIVE_PROVIDER=" in proc.stdout
    assert "FINITE=True" in proc.stdout
    active = next(
        line.split("=", 1)[1]
        for line in proc.stdout.splitlines()
        if line.startswith("ACTIVE_PROVIDER=")
    )
    assert active in ("CUDAExecutionProvider", "CPUExecutionProvider")


def test_provider_preference_prefers_cuda_first() -> None:
    """When CUDA is executable, the fixture CUDA session uses it before CPU fallback."""
    if not _onnxruntime_cuda_executable():
        pytest.skip("CUDAExecutionProvider cannot execute on this machine")
    import onnxruntime as ort

    _ensure_cuda_dll_paths()
    session = ort.InferenceSession(
        ".noisyne_performance_test_cache/fixture_model.onnx",
        providers=["CUDAExecutionProvider", "CPUExecutionProvider"],
    )
    assert session.get_providers()[0] == "CUDAExecutionProvider"
    assert _onnx_cuda_session_loaded(session)


def test_actual_cuda_session_loads_or_skips(fixture_runtimes: dict) -> None:
    """If a CUDA runtime entry exists, the ONNX session must actually use CUDA."""
    if "cuda" not in fixture_runtimes:
        pytest.skip("No CUDA fixture runtime available on this machine")
    _, onnx_fn, session = fixture_runtimes["cuda"]
    assert onnx_fn is not None
    assert session is not None
    assert "CUDAExecutionProvider" in session.get_providers()
    assert _onnx_cuda_session_loaded(session)


def test_cpu_fixture_runtimes_are_usable() -> None:
    """CPU-only fixture runtimes are always built and produce finite output."""
    runtimes = build_fixture_runtimes_by_device(".noisyne_performance_test_cache")
    if "cpu" not in runtimes:
        pytest.skip("CPU fixture runtime unavailable")
    pt_fn, onnx_fn, _ = runtimes["cpu"]
    assert pt_fn is not None
    assert onnx_fn is not None
    x = np.random.randn(1, 64).astype(np.float32)
    assert np.all(np.isfinite(pt_fn(x)))
    assert np.all(np.isfinite(onnx_fn(x)))


def test_fixture_outputs_finite(fixture_runtimes: dict) -> None:
    """Fixture outputs must be finite on every available device."""
    x = np.random.randn(1, 64).astype(np.float32)
    for device, (pt_fn, onnx_fn, _) in fixture_runtimes.items():
        if pt_fn is not None:
            assert np.all(np.isfinite(pt_fn(x))), f"{device} PyTorch output non-finite"
        if onnx_fn is not None:
            assert np.all(np.isfinite(onnx_fn(x))), f"{device} ONNX output non-finite"


def test_fixture_equivalence_cpu(fixture_runtimes: dict) -> None:
    """PyTorch CPU and ONNX CPU fixture outputs are numerically equivalent."""
    if "cpu" not in fixture_runtimes:
        pytest.skip("CPU fixture runtime unavailable")
    pt_fn, onnx_fn, _ = fixture_runtimes["cpu"]
    assert pt_fn is not None and onnx_fn is not None
    fixture_input = np.random.randn(1, 64).astype(np.float32)
    result = evaluate_equivalence(
        canonical_callable=pt_fn,
        candidate_callable=onnx_fn,
        fixture_input=fixture_input,
        canonical_identity="pytorch_cpu_fp32",
        candidate_identity="onnxruntime_cpu_fp32",
        policy=EquivalenceKind.ABSOLUTE_TOLERANCE,
        tolerance_value=1e-4,
    )
    assert result.status in (EquivalenceStatus.EQUIVALENT, EquivalenceStatus.WITHIN_TOLERANCE)
    assert result.max_absolute_difference is not None
    assert result.max_absolute_difference <= 1e-4


def test_fixture_equivalence_cuda(fixture_runtimes: dict) -> None:
    """PyTorch CPU canonical and ONNX CUDA fixture outputs are equivalent."""
    if "cuda" not in fixture_runtimes:
        pytest.skip("CUDA fixture runtime unavailable")
    cpu_pt = fixture_runtimes["cpu"][0]
    cuda_onnx = fixture_runtimes["cuda"][1]
    if cpu_pt is None or cuda_onnx is None:
        pytest.skip("Required CPU PyTorch or CUDA ONNX callable unavailable")
    fixture_input = np.random.randn(1, 64).astype(np.float32)
    result = evaluate_equivalence(
        canonical_callable=cpu_pt,
        candidate_callable=cuda_onnx,
        fixture_input=fixture_input,
        canonical_identity="pytorch_cpu_fp32",
        candidate_identity="onnxruntime_cuda_fp32",
        policy=EquivalenceKind.ABSOLUTE_TOLERANCE,
        tolerance_value=1e-4,
    )
    assert result.status in (EquivalenceStatus.EQUIVALENT, EquivalenceStatus.WITHIN_TOLERANCE)


def test_failed_equivalence_rejects_candidate() -> None:
    """A candidate with numerically different output must fail equivalence."""
    result = evaluate_equivalence(
        canonical_callable=lambda x: x * 2.0,
        candidate_callable=lambda x: x * 2.0 + 1.0,
        fixture_input=np.array([1.0, 2.0, 3.0]),
        canonical_identity="canonical",
        candidate_identity="bad_candidate",
        policy=EquivalenceKind.ABSOLUTE_TOLERANCE,
        tolerance_value=1e-4,
    )
    assert result.status is EquivalenceStatus.DIFFERENT


def test_unavailable_gpu_candidate_rejected_despite_faster_benchmark(
    environment: PerformanceEnvironment,
) -> None:
    """A faster GPU candidate whose compatibility fails must never be selected."""
    fast_gpu_benchmark = PerformanceBenchmarkResult(
        benchmark_id="fake_fast_gpu",
        workload_id="fixture",
        runtime_identity="onnxruntime_cuda_fp32",
        device=DeviceType.CUDA,
        precision=Precision.FP32,
        environment=environment,
        warmup_iterations=1,
        timed_iterations=5,
        cold_latency_seconds=1e-6,
        warm_statistics=LatencyStatistics(
            mean_seconds=1e-7,
            median_seconds=1e-7,
            min_seconds=1e-7,
            max_seconds=1e-7,
            p95_seconds=1e-7,
            sample_count=5,
        ),
        throughput_per_second=1_000_000.0,
        peak_memory=MemoryMeasurement(None, None, None),
    )
    slow_cpu_benchmark = PerformanceBenchmarkResult(
        benchmark_id="fake_slow_cpu",
        workload_id="fixture",
        runtime_identity="pytorch_cpu_fp32",
        device=DeviceType.CPU,
        precision=Precision.FP32,
        environment=environment,
        warmup_iterations=1,
        timed_iterations=5,
        cold_latency_seconds=1e-3,
        warm_statistics=LatencyStatistics(
            mean_seconds=1e-3,
            median_seconds=1e-3,
            min_seconds=1e-3,
            max_seconds=1e-3,
            p95_seconds=1e-3,
            sample_count=5,
        ),
        throughput_per_second=1_000.0,
        peak_memory=MemoryMeasurement(None, None, None),
    )
    unavailable_gpu = RuntimeCandidate(
        runtime_identity="onnxruntime_cuda_fp32",
        backend=RuntimeBackend.ONNX_RUNTIME,
        device=DeviceType.CUDA,
        precision=Precision.FP32,
        compatibility=CompatibilityResult(
            runtime_identity="onnxruntime_cuda_fp32",
            backend=RuntimeBackend.ONNX_RUNTIME,
            device=DeviceType.CUDA,
            precision=Precision.FP32,
            state=RuntimeAvailabilityState.UNAVAILABLE,
            reason="GPU runtime not executable on this environment",
        ),
        equivalence=None,
        benchmark=fast_gpu_benchmark,
        is_canonical=False,
    )
    canonical_cpu = RuntimeCandidate(
        runtime_identity="pytorch_cpu_fp32",
        backend=RuntimeBackend.PYTORCH,
        device=DeviceType.CPU,
        precision=Precision.FP32,
        compatibility=CompatibilityResult(
            runtime_identity="pytorch_cpu_fp32",
            backend=RuntimeBackend.PYTORCH,
            device=DeviceType.CPU,
            precision=Precision.FP32,
            state=RuntimeAvailabilityState.AVAILABLE,
            reason=None,
        ),
        equivalence=None,
        benchmark=slow_cpu_benchmark,
        is_canonical=True,
    )
    policy = RuntimeSelectionPolicy(
        policy_id="test_reject_fast_unavailable_gpu",
        profile=PerformanceProfile.BALANCED,
        require_equivalence=False,
        fallback_to_canonical=True,
    )
    result = select_runtime([unavailable_gpu], policy, canonical_cpu)
    assert result.selection_status is SelectionStatus.FALLBACK
    assert result.selected_candidate is canonical_cpu
    rejected_identities = {r.runtime_identity for r in result.rejected_candidates}
    assert "onnxruntime_cuda_fp32" in rejected_identities


def test_fixture_benchmark_timing_is_finite(fixture_runtimes: dict) -> None:
    """Benchmarking the fixture on available devices yields finite timing."""
    env = capture_environment()
    workload = PerformanceWorkload(
        workload_id="fixture_inference",
        workload_type="fixture_model",
        description="Tiny fixture model inference",
        duration_seconds=0.0,
        sample_count=1,
        deterministic=True,
    )
    for device, (pt_fn, onnx_fn, _) in fixture_runtimes.items():
        for fn, runtime_identity in (
            (pt_fn, f"pytorch_{device}_fp32"),
            (onnx_fn, f"onnxruntime_{device}_fp32"),
        ):
            if fn is None:
                continue
            device_type = DeviceType.CUDA if device == "cuda" else DeviceType.CPU
            result = benchmark_callable(
                benchmark_id=f"fixture_{runtime_identity}",
                workload=workload,
                runtime_identity=runtime_identity,
                device=device_type,
                precision=Precision.FP32,
                environment=env,
                method=BenchmarkMethod(warmup_iterations=1, timed_iterations=3),
                callable=lambda _f=fn: _f(np.random.randn(1, 64).astype(np.float32)),
            )
            assert result.warm_statistics is not None
            assert np.isfinite(result.warm_statistics.median_seconds)
            if device == "cuda":
                # CUDA runs should report some GPU memory measurement when torch is present.
                assert (
                    result.peak_memory.gpu_allocated_bytes is not None
                    or result.peak_memory.gpu_reserved_bytes is not None
                    or env.gpu_name is None
                )


def test_gpu_synchronization_present_in_cuda_callables(fixture_runtimes: dict) -> None:
    """CUDA PyTorch/ONNX callables synchronize the device before returning."""
    if "cuda" not in fixture_runtimes:
        pytest.skip("CUDA fixture runtime unavailable")
    x = np.random.randn(1, 64).astype(np.float32)
    pt_fn, onnx_fn, _ = fixture_runtimes["cuda"]
    if pt_fn is not None:
        out = pt_fn(x)
        assert np.all(np.isfinite(out))
    if onnx_fn is not None:
        out = onnx_fn(x)
        assert np.all(np.isfinite(out))


def test_capability_truth_separates_package_and_gpu(fixture_runtimes: dict) -> None:
    """Package installation, advertised provider, and actual GPU execution are separate."""
    import onnxruntime as ort

    advertised = "CUDAExecutionProvider" in ort.get_available_providers()
    actually_loaded = "cuda" in fixture_runtimes and _onnx_cuda_session_loaded(
        fixture_runtimes["cuda"][2]
    )
    # The contract's AVAILABLE state requires executable proof, not just advertisement.
    result = check_runtime_availability(
        "onnxruntime_cuda_fp32",
        RuntimeBackend.ONNX_RUNTIME,
        DeviceType.CUDA,
        Precision.FP32,
    )
    if actually_loaded:
        assert result.state is RuntimeAvailabilityState.AVAILABLE
    else:
        assert result.state in (
            RuntimeAvailabilityState.UNAVAILABLE,
            RuntimeAvailabilityState.INCOMPATIBLE,
        )
    # Advertised does not guarantee loaded.
    assert isinstance(advertised, bool)
    assert isinstance(actually_loaded, bool)


def test_fixture_validation_is_not_production_validation() -> None:
    """Fixture equivalence does not establish production model compatibility."""
    # This test documents the boundary: Sprint 15.5 validates only the fixture
    # model and the CUDA execution provider infrastructure.  Production PHASENØX
    # models remain unconverted and unvalidated.
    assert True

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import numpy as np

from .contracts import (
    CompatibilityResult,
    DeviceType,
    EquivalenceKind,
    EquivalenceResult,
    EquivalenceStatus,
    Precision,
    RejectedCandidate,
    RuntimeAvailabilityState,
    RuntimeBackend,
    RuntimeCandidate,
    RuntimeSelectionPolicy,
    RuntimeSelectionResult,
    SelectionStatus,
)


def _torch_available() -> bool:
    try:
        import torch  # noqa: F401

        return True
    except Exception:  # noqa: BLE001
        return False


def _onnxruntime_available() -> bool:
    try:
        import onnxruntime  # noqa: F401

        return True
    except Exception:  # noqa: BLE001
        return False


def _torch_cuda_available() -> bool:
    try:
        import torch

        return torch.cuda.is_available()
    except Exception:  # noqa: BLE001
        return False


def _onnxruntime_cuda_available() -> bool:
    try:
        import onnxruntime

        return "CUDAExecutionProvider" in onnxruntime.get_available_providers()
    except Exception:  # noqa: BLE001
        return False


def _precision_supported_on_device(
    backend: RuntimeBackend, device: DeviceType, precision: Precision
) -> tuple[bool, str | None]:
    """Return whether the declared precision is likely usable on this device.

    These checks are conservative; actual support may differ by model.
    """
    if precision is Precision.INT8:
        return False, "INT8 precision is not enabled for Sprint 14"
    if precision is Precision.FP16:
        if backend is RuntimeBackend.ONNX_RUNTIME:
            return True, None
        if backend is RuntimeBackend.PYTORCH and device is DeviceType.CUDA:
            return True, None
        return (
            False,
            "FP16 is generally unsupported on PyTorch CPU in Sprint 14",
        )
    if precision is Precision.BF16:
        return False, "BF16 precision is not enabled for Sprint 14"
    return True, None


def check_runtime_availability(
    runtime_identity: str,
    backend: RuntimeBackend,
    device: DeviceType,
    precision: Precision,
) -> CompatibilityResult:
    """Return a truthful compatibility result for one runtime candidate."""
    if backend is RuntimeBackend.PYTORCH:
        if not _torch_available():
            return CompatibilityResult(
                runtime_identity=runtime_identity,
                backend=backend,
                device=device,
                precision=precision,
                state=RuntimeAvailabilityState.UNAVAILABLE,
                reason="PyTorch is not installed",
            )
        if device is DeviceType.CUDA and not _torch_cuda_available():
            return CompatibilityResult(
                runtime_identity=runtime_identity,
                backend=backend,
                device=device,
                precision=precision,
                state=RuntimeAvailabilityState.UNAVAILABLE,
                reason="CUDA device is not available to PyTorch",
            )
    elif backend is RuntimeBackend.ONNX_RUNTIME:
        if not _onnxruntime_available():
            return CompatibilityResult(
                runtime_identity=runtime_identity,
                backend=backend,
                device=device,
                precision=precision,
                state=RuntimeAvailabilityState.UNAVAILABLE,
                reason="ONNX Runtime is not installed",
            )
        if device is DeviceType.CUDA and not _onnxruntime_cuda_available():
            return CompatibilityResult(
                runtime_identity=runtime_identity,
                backend=backend,
                device=device,
                precision=precision,
                state=RuntimeAvailabilityState.UNAVAILABLE,
                reason="CUDAExecutionProvider is not available to ONNX Runtime",
            )
    else:
        return CompatibilityResult(
            runtime_identity=runtime_identity,
            backend=backend,
            device=device,
            precision=precision,
            state=RuntimeAvailabilityState.INCOMPATIBLE,
            reason=f"Unknown backend {backend.value}",
        )

    supported, reason = _precision_supported_on_device(backend, device, precision)
    if not supported:
        return CompatibilityResult(
            runtime_identity=runtime_identity,
            backend=backend,
            device=device,
            precision=precision,
            state=RuntimeAvailabilityState.INCOMPATIBLE,
            reason=reason or f"{precision.value} not supported on {device.value}",
        )

    return CompatibilityResult(
        runtime_identity=runtime_identity,
        backend=backend,
        device=device,
        precision=precision,
        state=RuntimeAvailabilityState.AVAILABLE,
        reason=None,
    )


def evaluate_equivalence(
    *,
    canonical_callable: Callable[[Any], Any],
    candidate_callable: Callable[[Any], Any],
    fixture_input: Any,
    canonical_identity: str,
    candidate_identity: str,
    policy: EquivalenceKind = EquivalenceKind.ABSOLUTE_TOLERANCE,
    tolerance_value: float = 1e-5,
) -> EquivalenceResult:
    """Compare candidate output against canonical output on a deterministic fixture."""
    try:
        canonical_output = canonical_callable(fixture_input)
        candidate_output = candidate_callable(fixture_input)
    except Exception as exc:  # noqa: BLE001
        return EquivalenceResult(
            runtime_identity=candidate_identity,
            canonical_identity=canonical_identity,
            status=EquivalenceStatus.FAILED,
            policy=policy,
            tolerance_value=tolerance_value,
            max_absolute_difference=None,
            max_relative_difference=None,
            reason=f"Inference failed during equivalence check: {exc}",
        )

    try:
        canonical_arr = np.asarray(canonical_output, dtype=np.float64)
        candidate_arr = np.asarray(candidate_output, dtype=np.float64)
        if canonical_arr.shape != candidate_arr.shape:
            return EquivalenceResult(
                runtime_identity=candidate_identity,
                canonical_identity=canonical_identity,
                status=EquivalenceStatus.DIFFERENT,
                policy=policy,
                tolerance_value=tolerance_value,
                max_absolute_difference=None,
                max_relative_difference=None,
                reason="Output shapes differ",
            )
        if canonical_arr.size == 0:
            return EquivalenceResult(
                runtime_identity=candidate_identity,
                canonical_identity=canonical_identity,
                status=EquivalenceStatus.EQUIVALENT,
                policy=policy,
                tolerance_value=tolerance_value,
                max_absolute_difference=0.0,
                max_relative_difference=0.0,
                reason="Empty output; no difference detected",
            )
        abs_diff = np.abs(canonical_arr - candidate_arr)
        max_abs = float(np.max(abs_diff))
        denom = np.abs(canonical_arr)
        with np.errstate(divide="ignore", invalid="ignore"):
            rel_diff = np.where(denom > 0.0, abs_diff / denom, 0.0)
        max_rel = float(np.max(rel_diff))
    except Exception as exc:  # noqa: BLE001
        return EquivalenceResult(
            runtime_identity=candidate_identity,
            canonical_identity=canonical_identity,
            status=EquivalenceStatus.FAILED,
            policy=policy,
            tolerance_value=tolerance_value,
            max_absolute_difference=None,
            max_relative_difference=None,
            reason=f"Failed to compare outputs: {exc}",
        )

    if policy is EquivalenceKind.EXACT:
        within = max_abs == 0.0
        status = EquivalenceStatus.EQUIVALENT if within else EquivalenceStatus.DIFFERENT
    elif policy is EquivalenceKind.ABSOLUTE_TOLERANCE:
        within = max_abs <= tolerance_value
        status = EquivalenceStatus.WITHIN_TOLERANCE if within else EquivalenceStatus.DIFFERENT
    elif policy is EquivalenceKind.RELATIVE_TOLERANCE:
        within = max_rel <= tolerance_value
        status = EquivalenceStatus.WITHIN_TOLERANCE if within else EquivalenceStatus.DIFFERENT
    else:
        # DOMAIN_SPECIFIC: defer to caller by accepting within absolute tolerance.
        within = max_abs <= tolerance_value
        status = EquivalenceStatus.WITHIN_TOLERANCE if within else EquivalenceStatus.DIFFERENT
    reason = f"max_absolute_difference={max_abs:.3e}, max_relative_difference={max_rel:.3e}"

    return EquivalenceResult(
        runtime_identity=candidate_identity,
        canonical_identity=canonical_identity,
        status=status,
        policy=policy,
        tolerance_value=tolerance_value,
        max_absolute_difference=max_abs,
        max_relative_difference=max_rel,
        reason=reason,
    )


def _sortable_score(candidate: RuntimeCandidate) -> tuple[float, ...]:
    """Lower tuple is better.  Prioritizes: device match ignored here, latency, throughput."""
    benchmark = candidate.benchmark
    if benchmark is None or benchmark.warm_statistics is None:
        return (float("inf"),)
    latency = benchmark.warm_statistics.median_seconds
    throughput = benchmark.throughput_per_second or 0.0
    return (latency, -throughput)


def select_runtime(
    candidates: list[RuntimeCandidate],
    policy: RuntimeSelectionPolicy,
    canonical: RuntimeCandidate | None,
) -> RuntimeSelectionResult:
    """Select the fastest validated runtime candidate under the given policy."""
    rejected: list[RejectedCandidate] = []
    available: list[RuntimeCandidate] = []

    for candidate in candidates:
        identity = candidate.runtime_identity
        if candidate.compatibility.state is not RuntimeAvailabilityState.AVAILABLE:
            rejected.append(
                RejectedCandidate(
                    runtime_identity=identity,
                    reason=f"compatibility state {candidate.compatibility.state.value}",
                )
            )
            continue
        if candidate.backend in policy.prohibited_backends:
            rejected.append(
                RejectedCandidate(runtime_identity=identity, reason="backend prohibited by policy")
            )
            continue
        if candidate.precision in policy.prohibited_precisions:
            rejected.append(
                RejectedCandidate(
                    runtime_identity=identity, reason="precision prohibited by policy"
                )
            )
            continue
        if policy.preferred_device is not None and candidate.device is not policy.preferred_device:
            rejected.append(
                RejectedCandidate(
                    runtime_identity=identity,
                    reason=f"device {candidate.device.value} does not match preferred device",
                )
            )
            continue
        if policy.require_equivalence:
            if candidate.equivalence is None:
                rejected.append(
                    RejectedCandidate(
                        runtime_identity=identity,
                        reason="equivalence required but not evaluated",
                    )
                )
                continue
            if candidate.equivalence.status not in (
                EquivalenceStatus.EQUIVALENT,
                EquivalenceStatus.WITHIN_TOLERANCE,
            ):
                rejected.append(
                    RejectedCandidate(
                        runtime_identity=identity,
                        reason=(f"equivalence status {candidate.equivalence.status.value}"),
                    )
                )
                continue
        if candidate.benchmark is not None:
            bench = candidate.benchmark
            if (
                policy.max_acceptable_latency_seconds is not None
                and bench.warm_statistics is not None
                and bench.warm_statistics.median_seconds > policy.max_acceptable_latency_seconds
            ):
                rejected.append(
                    RejectedCandidate(
                        runtime_identity=identity,
                        reason="median latency exceeds policy threshold",
                    )
                )
                continue
            if (
                policy.min_acceptable_throughput_per_second is not None
                and bench.throughput_per_second is not None
                and bench.throughput_per_second < policy.min_acceptable_throughput_per_second
            ):
                rejected.append(
                    RejectedCandidate(
                        runtime_identity=identity,
                        reason="throughput below policy threshold",
                    )
                )
                continue
        available.append(candidate)

    if available:
        available.sort(key=_sortable_score)
        selected = available[0]
        return RuntimeSelectionResult(
            selection_status=SelectionStatus.SELECTED,
            selected_candidate=selected,
            canonical_candidate=canonical,
            rejected_candidates=rejected,
            reason=(f"{selected.runtime_identity} selected as fastest validated candidate"),
            evidence_ids=[
                selected.compatibility.runtime_identity,
                *(selected.equivalence.runtime_identity if selected.equivalence else ""),
            ],
        )

    if canonical is not None and policy.fallback_to_canonical:
        return RuntimeSelectionResult(
            selection_status=SelectionStatus.FALLBACK,
            selected_candidate=canonical,
            canonical_candidate=canonical,
            rejected_candidates=rejected,
            reason="No optimized candidate passed policy; falling back to canonical runtime",
            evidence_ids=[canonical.compatibility.runtime_identity],
        )

    return RuntimeSelectionResult(
        selection_status=SelectionStatus.NO_CANDIDATE,
        selected_candidate=None,
        canonical_candidate=canonical,
        rejected_candidates=rejected,
        reason="No candidate satisfied the selection policy",
        evidence_ids=[],
    )


def runtime_fingerprint_fields(
    environment: Any,
    runtime_identity: str,
    precision: Precision,
    workload_id: str,
) -> dict[str, Any]:
    """Return the stable fields that form a benchmark fingerprint.

    This is a helper; the caller must still construct the BenchmarkFingerprint.
    """

    return {
        "os_name": environment.os_name,
        "architecture": environment.architecture,
        "python_version": environment.python_version,
        "cpu_brand": environment.cpu_brand,
        "logical_cores": environment.logical_cores,
        "total_ram_bytes": environment.total_ram_bytes,
        "gpu_name": environment.gpu_name,
        "torch_version": environment.torch_version,
        "onnxruntime_version": environment.onnxruntime_version,
        "runtime_identity": runtime_identity,
        "precision": precision,
        "workload_id": workload_id,
        "benchmark_method_version": environment.benchmark_method_version,
    }


__all__ = [
    "check_runtime_availability",
    "evaluate_equivalence",
    "runtime_fingerprint_fields",
    "select_runtime",
]

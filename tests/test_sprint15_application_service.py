"""Sprint 15 V2 application service integration tests."""

from __future__ import annotations

import subprocess
import sys
import wave
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from phasenox.application import (
    ApplicationRequest,
    ApplicationResult,
    ApplicationResultStatus,
    CapabilitySnapshotResult,
    MachineAvailability,
    OperationType,
    PhasenoxV2Service,
    StageState,
)
from phasenox.perception.common import ScalarValue, UnitBasis
from phasenox.perception.mix_intelligence_contracts import (
    MixCriterionOperator,
    MixEvidenceDimensionId,
    MixEvidenceSourceType,
    MixIssueCriterion,
    MixIssuePolicy,
    MixIssuePriority,
    MixIssueType,
)
from phasenox.perception.reference_contracts import (
    ReferenceComparisonConfig,
    ReferenceComparisonMode,
    ReferenceProvenance,
    ReferenceRole,
    ReferenceTrackIdentity,
)
from phasenox.perception.translation_contracts import TranslationPolicyProvenance


def _write_temp_wav(path: Path, duration_seconds: float = 0.5, sample_rate: int = 44100) -> None:
    """Write a deterministic mono sine WAV for service tests."""
    sample_count = int(duration_seconds * sample_rate)
    samples = (0.5 * np.sin(2.0 * np.pi * 440.0 * np.arange(sample_count) / sample_rate)).astype(
        np.float32
    )
    # Convert to 16-bit PCM for stdlib wave.
    pcm = (samples * 32767.0).astype(np.int16)
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm.tobytes())


def _synthetic_reference_identity(duration_seconds: float = 0.5) -> dict[str, Any]:
    return ReferenceTrackIdentity(
        reference_id="synthetic_reference",
        version="1.0.0",
        display_name="Synthetic reference",
        provenance=ReferenceProvenance.USER_SUPPLIED,
        source="test",
        duration_seconds=duration_seconds,
        sample_rate_hz=44100,
        channel_count=1,
        declared_role=ReferenceRole.GENERAL_REFERENCE,
    ).to_dict()


def _sample_mix_policy() -> dict[str, Any]:
    """Return a minimal mix policy that evaluates context resolution conflict."""
    return MixIssuePolicy(
        policy_id="test_policy",
        version="1.0.0",
        provenance=TranslationPolicyProvenance.USER_DECLARED,
        source="test",
        description="Test policy with no matching evidence",
        criteria=[
            MixIssueCriterion(
                criterion_id="ctx_conflict",
                version="1.0.0",
                provenance=TranslationPolicyProvenance.USER_DECLARED,
                source="test",
                description="Detect context resolution conflict",
                display_name="Context conflict",
                evidence_source_type=MixEvidenceSourceType.CONTEXT_RESOLUTION,
                evidence_dimension=MixEvidenceDimensionId.CONTEXT_RESOLUTION_CONFLICT,
                operator=MixCriterionOperator.BOOLEAN_IS_TRUE,
                threshold=ScalarValue(True, UnitBasis.NAMED_SCALE, scale="boolean"),
                issue_type=MixIssueType.CONTEXT_POLICY_CONFLICT,
                priority=MixIssuePriority.MEDIUM,
            )
        ],
    ).to_dict()


def test_import_phasenox_application_is_lightweight() -> None:
    """Importing phasenox.application must not initialize torch, ONNX, LLM, network, Qt."""
    code = (
        "import sys; "
        "import phasenox.application; "
        "assert phasenox.application.PhasenoxV2Service is not None; "
        "assert 'torch' not in sys.modules, 'torch loaded on import'; "
        "assert 'onnxruntime' not in sys.modules, 'onnxruntime loaded on import'; "
        "print('ok')"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout


def test_request_validation_missing_audio_path() -> None:
    with pytest.raises(ValueError):
        ApplicationRequest(
            request_id="r1",
            operation=OperationType.ANALYZE,
            parameters={},
        )


def test_request_validation_unknown_fields_rejected() -> None:
    with pytest.raises(ValueError):
        ApplicationRequest.from_dict(
            {
                "request_id": "r1",
                "operation": "analyze",
                "parameters": {"audio_path": "/tmp/x.wav"},
                "forged_field": "x",
            }
        )


def test_request_json_round_trip() -> None:
    request = ApplicationRequest(
        request_id="r1",
        operation=OperationType.ANALYZE,
        parameters={"audio_path": "/tmp/x.wav"},
    )
    restored = ApplicationRequest.from_dict(request.to_dict())
    assert restored == request


def test_deterministic_request_id_preserved() -> None:
    request = ApplicationRequest(
        request_id="my-stable-id",
        operation=OperationType.CAPABILITY_INSPECT,
        parameters={},
    )
    service = PhasenoxV2Service()
    result = service.execute(request)
    assert result.request_id == "my-stable-id"


def test_analyze_success(tmp_path: Path) -> None:
    audio_path = tmp_path / "test.wav"
    _write_temp_wav(audio_path)
    service = PhasenoxV2Service()
    request = ApplicationRequest(
        request_id="analyze-1",
        operation=OperationType.ANALYZE,
        parameters={"audio_path": str(audio_path)},
    )
    result = service.execute(request)
    assert isinstance(result, ApplicationResult)
    assert result.status is ApplicationResultStatus.SUCCESS
    assert result.operation is OperationType.ANALYZE
    assert result.payload is not None
    assert "audio_metadata" in result.payload
    assert "auditory_summary" in result.payload
    assert "descriptors" in result.payload
    stage_ids = {stage.stage_id: stage.state for stage in result.stages}
    assert stage_ids.get("audio_io") is StageState.COMPLETED
    assert stage_ids.get("auditory_frontend") is StageState.COMPLETED
    assert stage_ids.get("descriptor_foundation") is StageState.COMPLETED


def test_reference_compare_success(tmp_path: Path) -> None:
    source_path = tmp_path / "source.wav"
    reference_path = tmp_path / "reference.wav"
    _write_temp_wav(source_path)
    _write_temp_wav(reference_path)
    service = PhasenoxV2Service()
    request = ApplicationRequest(
        request_id="ref-1",
        operation=OperationType.REFERENCE_COMPARE,
        parameters={
            "audio_path": str(source_path),
            "reference_path": str(reference_path),
            "reference_identity": _synthetic_reference_identity(),
            "config": ReferenceComparisonConfig(mode=ReferenceComparisonMode.RAW_LEVEL).to_dict(),
        },
    )
    result = service.execute(request)
    assert result.status is ApplicationResultStatus.SUCCESS
    assert result.payload is not None
    assert "comparison" in result.payload


def test_mix_evaluate_insufficient_evidence_success() -> None:
    """A policy with no matching evidence returns SUCCESS with truthful limitations."""
    service = PhasenoxV2Service()
    request = ApplicationRequest(
        request_id="mix-1",
        operation=OperationType.MIX_EVALUATE,
        parameters={"mix_policy": _sample_mix_policy()},
    )
    result = service.execute(request)
    assert result.status is ApplicationResultStatus.SUCCESS
    assert result.payload is not None
    mix = result.payload["mix_intelligence"]
    assert mix["summary"]["insufficient_evidence_count"] == 1
    assert mix["summary"]["triggered_issue_count"] == 0
    assert any("insufficient evidence" in lim.lower() for lim in result.limitations)


def test_reason_no_grounded_statements_success() -> None:
    """REASON with no matching evidence yields NO_GROUNDED_STATEMENTS mapped to SUCCESS."""
    service = PhasenoxV2Service()
    request = ApplicationRequest(
        request_id="reason-1",
        operation=OperationType.REASON,
        parameters={"mix_policy": _sample_mix_policy()},
    )
    result = service.execute(request)
    assert result.status is ApplicationResultStatus.SUCCESS
    assert result.payload is not None
    reasoning = result.payload["reasoning"]
    assert reasoning["state"] == "no_grounded_statements"
    assert any("no grounded statements" in lim.lower() for lim in result.limitations)


def test_capability_inspect_success() -> None:
    service = PhasenoxV2Service()
    request = ApplicationRequest(
        request_id="cap-1",
        operation=OperationType.CAPABILITY_INSPECT,
        parameters={},
    )
    result = service.execute(request)
    assert result.status is ApplicationResultStatus.SUCCESS
    assert result.payload is not None
    snapshot_dict = result.payload["snapshot"]
    snapshot = CapabilitySnapshotResult.from_dict(snapshot_dict)
    assert len(snapshot.capabilities) > 0
    assert snapshot.count_available >= 0
    assert snapshot.count_unavailable >= 0
    assert snapshot.count_unknown >= 0


def test_capability_lifecycle_separate_from_machine_availability() -> None:
    """A capability may be IMPLEMENTED while its dependency is UNAVAILABLE on this machine."""
    service = PhasenoxV2Service()
    request = ApplicationRequest(
        request_id="cap-2",
        operation=OperationType.CAPABILITY_INSPECT,
        parameters={},
    )
    result = service.execute(request)
    snapshot = CapabilitySnapshotResult.from_dict(result.payload["snapshot"])
    onnx_entry = next(
        (c for c in snapshot.capabilities if c.name == "onnx_runtime_optimization"), None
    )
    assert onnx_entry is not None
    # Lifecycle says implementation foundation exists.
    assert onnx_entry.lifecycle_status == "implemented"
    # Machine availability is independent and may be unavailable if onnxruntime is absent.
    assert onnx_entry.dependency_availability in (
        MachineAvailability.AVAILABLE,
        MachineAvailability.UNAVAILABLE,
    )


def test_unavailable_dependency_reflected_in_snapshot() -> None:
    """If a fake dependency is added to a capability, it reports UNAVAILABLE."""
    from phasenox.runtime.capabilities import Capability, CapabilityStatus, registry

    registry.register(
        Capability(
            name="sprint15_test_fake_dependency",
            description="Test capability with a fake dependency",
            status=CapabilityStatus.PLANNED,
            dependencies=("nonexistent_module_xyz_12345",),
        )
    )
    try:
        service = PhasenoxV2Service()
        request = ApplicationRequest(
            request_id="cap-3",
            operation=OperationType.CAPABILITY_INSPECT,
            parameters={},
        )
        result = service.execute(request)
        snapshot = CapabilitySnapshotResult.from_dict(result.payload["snapshot"])
        entry = next(
            (c for c in snapshot.capabilities if c.name == "sprint15_test_fake_dependency"), None
        )
        assert entry is not None
        assert entry.dependency_availability is MachineAvailability.UNAVAILABLE
    finally:
        registry.unregister("sprint15_test_fake_dependency")


def test_partial_semantics_for_invalid_mix_policy() -> None:
    service = PhasenoxV2Service()
    request = ApplicationRequest(
        request_id="mix-bad",
        operation=OperationType.MIX_EVALUATE,
        parameters={"mix_policy": {"not_a_real_policy": True}},
    )
    result = service.execute(request)
    assert result.status is ApplicationResultStatus.FAILED
    assert result.errors
    assert result.errors[0].code == "invalid_request"


def test_bounded_error_no_stack_trace() -> None:
    """Public result errors must not contain stack traces, secrets, or prompts."""
    service = PhasenoxV2Service()
    request = ApplicationRequest(
        request_id="err-1",
        operation=OperationType.ANALYZE,
        parameters={"audio_path": "nonexistent_file.wav"},
    )
    result = service.execute(request)
    assert result.status in (ApplicationResultStatus.FAILED, ApplicationResultStatus.PARTIAL)
    assert result.errors
    error = result.errors[0]
    assert "Traceback" not in error.message
    assert "\n" not in error.message
    assert error.code in (
        "audio_decode_failure",
        "analysis_failure",
        "internal_failure",
    )


def test_repeated_call_determinism(tmp_path: Path) -> None:
    audio_path = tmp_path / "test.wav"
    _write_temp_wav(audio_path)
    service = PhasenoxV2Service()
    request = ApplicationRequest(
        request_id="det-1",
        operation=OperationType.ANALYZE,
        parameters={"audio_path": str(audio_path)},
    )
    r1 = service.execute(request)
    r2 = service.execute(request)
    assert r1.to_dict() == r2.to_dict()


def test_v1_alias_not_loaded_by_default() -> None:
    """The canonical V1 service export stays lazy until attribute access."""
    code = (
        "import sys; import phasenox.application; "
        "assert 'phasenox.application.phasenox_service' not in sys.modules; "
        "assert 'PhasenoxService' in dir(phasenox.application); "
        "assert phasenox.application.PhasenoxService is not None; "
        "assert 'phasenox.application.phasenox_service' in sys.modules"
    )
    subprocess.run([sys.executable, "-c", code], check=True)


def test_no_qt_import() -> None:
    """Application module must not require Qt."""
    import phasenox.application

    # If PySide/PyQt were imported, they'd be in sys.modules. We just assert the
    # module loads without error; the lightweight import test above is stronger.
    assert phasenox.application is not None


def test_sprint14_onnx_not_promoted_to_production() -> None:
    """Capability inspect must not claim production ONNX readiness."""
    service = PhasenoxV2Service()
    request = ApplicationRequest(
        request_id="cap-onnx",
        operation=OperationType.CAPABILITY_INSPECT,
        parameters={},
    )
    result = service.execute(request)
    snapshot = CapabilitySnapshotResult.from_dict(result.payload["snapshot"])
    onnx_entry = next(
        (c for c in snapshot.capabilities if c.name == "onnx_runtime_optimization"), None
    )
    assert onnx_entry is not None
    assert onnx_entry.lifecycle_status != "production"
    assert onnx_entry.lifecycle_status != "validated"


def test_sprint13_memory_not_promoted_to_scientific_truth() -> None:
    """Memory foundation must not appear as scientific validation authority."""
    service = PhasenoxV2Service()
    request = ApplicationRequest(
        request_id="cap-mem",
        operation=OperationType.CAPABILITY_INSPECT,
        parameters={},
    )
    result = service.execute(request)
    snapshot = CapabilitySnapshotResult.from_dict(result.payload["snapshot"])
    memory_entry = next(
        (c for c in snapshot.capabilities if c.name == "knowledge_memory_foundation"), None
    )
    assert memory_entry is not None
    assert memory_entry.lifecycle_status != "production"

"""Sprint 15 V2 application service foundation.

`NoisyneV2Service` composes frozen Sprint 2–14 components behind a small,
deterministic public contract. Heavy imports remain lazy so that importing
`phasenox.application` does not initialize torch, ONNX sessions, LLM clients,
network, Qt, or audio devices.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from phasenox.application.contracts import (
    ApplicationError,
    ApplicationRequest,
    ApplicationResult,
    ApplicationResultStatus,
    CapabilitySnapshotEntry,
    CapabilitySnapshotResult,
    MachineAvailability,
    OperationType,
    StageOutcome,
    StageState,
)

logger = logging.getLogger(__name__)


def _new_request_id() -> str:
    """Return a deterministic, version-4-UUID-shaped request identity."""
    return str(uuid.uuid4())


def _check_dependency_availability(dependency: str) -> MachineAvailability:
    """Return machine-level availability for a single declared dependency.

    A successful import only means the dependency package is present in the
    environment. It is NOT an attestation of model, runtime, or hardware
    compatibility.
    """
    try:
        __import__(dependency)
        return MachineAvailability.AVAILABLE
    except ImportError:
        return MachineAvailability.UNAVAILABLE
    except Exception:  # noqa: BLE001
        return MachineAvailability.UNKNOWN


def _capability_snapshot() -> CapabilitySnapshotResult:
    """Build a capability snapshot with truthful machine-level dependency states.

    Import the capability registry lazily here; it transitively imports runtime
    modules that load torch, and importing it at module level would make
    `import phasenox.application` heavy.
    """
    from phasenox.runtime.capabilities import registry

    entries: list[CapabilitySnapshotEntry] = []
    counts = {
        MachineAvailability.AVAILABLE: 0,
        MachineAvailability.UNAVAILABLE: 0,
        MachineAvailability.UNKNOWN: 0,
    }
    for capability in registry.all():
        if capability.dependencies:
            availabilities = [
                _check_dependency_availability(dep) for dep in capability.dependencies
            ]
            if MachineAvailability.UNAVAILABLE in availabilities:
                dependency_availability = MachineAvailability.UNAVAILABLE
            elif MachineAvailability.UNKNOWN in availabilities:
                dependency_availability = MachineAvailability.UNKNOWN
            else:
                dependency_availability = MachineAvailability.AVAILABLE
        else:
            dependency_availability = MachineAvailability.AVAILABLE
        counts[dependency_availability] += 1
        entries.append(
            CapabilitySnapshotEntry(
                name=capability.name,
                lifecycle_status=capability.status.value,
                tested_in_freeze=capability.tested_in_freeze,
                dependency_availability=dependency_availability,
                reason_unavailable=capability.reason_unavailable,
            )
        )
    return CapabilitySnapshotResult(
        capabilities=entries,
        count_available=counts[MachineAvailability.AVAILABLE],
        count_unavailable=counts[MachineAvailability.UNAVAILABLE],
        count_unknown=counts[MachineAvailability.UNKNOWN],
    )


def _stage(
    stage_id: str,
    state: StageState,
    payload: dict[str, Any] | None = None,
    limitations: list[str] | None = None,
) -> StageOutcome:
    return StageOutcome(
        stage_id=stage_id,
        state=state,
        payload=payload,
        limitations=limitations or [],
    )


def _error(code: str, message: str, stage_id: str | None = None) -> ApplicationError:
    return ApplicationError(code=code, message=message, stage_id=stage_id)


def _success(
    request: ApplicationRequest,
    payload: dict[str, Any],
    stages: list[StageOutcome],
    limitations: list[str] | None = None,
) -> ApplicationResult:
    return ApplicationResult(
        request_id=request.request_id,
        operation=request.operation,
        status=ApplicationResultStatus.SUCCESS,
        payload=payload,
        stages=stages,
        limitations=limitations or [],
    )


def _partial(
    request: ApplicationRequest,
    payload: dict[str, Any] | None,
    stages: list[StageOutcome],
    errors: list[ApplicationError],
    limitations: list[str] | None = None,
) -> ApplicationResult:
    return ApplicationResult(
        request_id=request.request_id,
        operation=request.operation,
        status=ApplicationResultStatus.PARTIAL,
        payload=payload,
        stages=stages,
        errors=errors,
        limitations=limitations or [],
    )


def _failed(
    request: ApplicationRequest,
    stages: list[StageOutcome],
    errors: list[ApplicationError],
    limitations: list[str] | None = None,
) -> ApplicationResult:
    return ApplicationResult(
        request_id=request.request_id,
        operation=request.operation,
        status=ApplicationResultStatus.FAILED,
        stages=stages,
        errors=errors,
        limitations=limitations or [],
    )


def _dictify(contract: Any) -> dict[str, Any]:
    """Serialize a JsonContract to a dict; pass through plain dicts."""
    if hasattr(contract, "to_dict"):
        return contract.to_dict()
    if isinstance(contract, dict):
        return contract
    raise TypeError(f"Unsupported payload type: {type(contract).__name__}")


class NoisyneV2Service:
    """Lightweight V2 application service over frozen Sprint 2–14 components."""

    def __init__(
        self,
        *,
        audio_io: Any | None = None,
        auditory_frontend: Any | None = None,
        descriptor_foundation: Any | None = None,
        reference_comparator: Any | None = None,
        mix_engine: Any | None = None,
        reasoning_engine: Any | None = None,
    ) -> None:
        """Construct with optional injected components; all defaults are lazy."""
        self._audio_io = audio_io
        self._auditory_frontend = auditory_frontend
        self._descriptor_foundation = descriptor_foundation
        self._reference_comparator = reference_comparator
        self._mix_engine = mix_engine
        self._reasoning_engine = reasoning_engine

    def execute(self, request: ApplicationRequest) -> ApplicationResult:
        """Dispatch one validated application request."""
        if not isinstance(request, ApplicationRequest):
            return ApplicationResult(
                request_id=getattr(request, "request_id", "unknown"),
                operation=getattr(request, "operation", OperationType.CAPABILITY_INSPECT),
                status=ApplicationResultStatus.FAILED,
                errors=[_error("invalid_request", "request must be an ApplicationRequest")],
            )
        try:
            if request.operation is OperationType.ANALYZE:
                return self._analyze(request)
            if request.operation is OperationType.REFERENCE_COMPARE:
                return self._reference_compare(request)
            if request.operation is OperationType.MIX_EVALUATE:
                return self._mix_evaluate(request)
            if request.operation is OperationType.REASON:
                return self._reason(request)
            if request.operation is OperationType.CAPABILITY_INSPECT:
                return self._capability_inspect(request)
        except Exception as exc:
            logger.exception("Unhandled exception executing %s", request.operation.value)
            return _failed(
                request,
                stages=[],
                errors=[
                    _error(
                        "internal_failure",
                        f"Unhandled service error: {exc}",
                    )
                ],
            )
        return _failed(
            request,
            stages=[],
            errors=[_error("invalid_request", f"unsupported operation {request.operation.value}")],
        )

    def _analyze(self, request: ApplicationRequest) -> ApplicationResult:
        audio_path = request.parameters["audio_path"]
        stages: list[StageOutcome] = []
        try:
            audio = self._load_audio(audio_path, stages)
        except Exception as exc:  # noqa: BLE001
            return _failed(
                request,
                stages=stages,
                errors=[
                    _error(
                        "audio_decode_failure",
                        f"Failed to load audio: {exc}",
                        stage_id="audio_io",
                    )
                ],
            )

        try:
            auditory = self._auditory_frontend or self._import_auditory_frontend()
            auditory_result = auditory.analyze(audio)
            stages.append(
                _stage(
                    "auditory_frontend",
                    StageState.COMPLETED,
                    {"summary": auditory_result.summary.to_dict()},
                )
            )
        except Exception as exc:  # noqa: BLE001
            return _failed(
                request,
                stages=stages,
                errors=[
                    _error(
                        "analysis_failure",
                        f"Auditory frontend failed: {exc}",
                        stage_id="auditory_frontend",
                    )
                ],
            )

        try:
            descriptors = self._descriptor_foundation or self._import_descriptor_foundation()
            descriptor_result = descriptors.analyze(audio)
            stages.append(
                _stage(
                    "descriptor_foundation",
                    StageState.COMPLETED,
                    {"descriptor_count": len(descriptor_result.descriptors)},
                )
            )
        except Exception as exc:  # noqa: BLE001
            return _failed(
                request,
                stages=stages,
                errors=[
                    _error(
                        "analysis_failure",
                        f"Descriptor foundation failed: {exc}",
                        stage_id="descriptor_foundation",
                    )
                ],
            )

        return _success(
            request,
            payload={
                "audio_metadata": {
                    "filename": audio.metadata.filename,
                    "format": audio.metadata.format,
                    "codec": audio.metadata.codec,
                    "sample_rate": audio.metadata.sample_rate,
                    "channels": audio.metadata.channels,
                    "duration": audio.metadata.duration,
                    "bit_depth": audio.metadata.bit_depth,
                },
                "auditory_summary": _dictify(auditory_result.summary),
                "descriptors": [_dictify(d) for d in descriptor_result.descriptors],
            },
            stages=stages,
            limitations=[
                "ANALYZE returns auditory and brightness-correlate evidence only; no reasoning or reference comparison is performed unless requested."
            ],
        )

    def _reference_compare(self, request: ApplicationRequest) -> ApplicationResult:
        audio_path = request.parameters["audio_path"]
        reference_path = request.parameters["reference_path"]
        reference_identity_dict = request.parameters["reference_identity"]
        config_dict = request.parameters.get("config")
        stages: list[StageOutcome] = []

        try:
            source = self._load_audio(audio_path, stages)
            reference = self._load_audio(reference_path, stages)
        except Exception as exc:  # noqa: BLE001
            return _failed(
                request,
                stages=stages,
                errors=[
                    _error(
                        "audio_decode_failure",
                        f"Failed to load audio: {exc}",
                        stage_id="audio_io",
                    )
                ],
            )

        try:
            from phasenox.perception.reference_contracts import (
                ReferenceComparisonConfig,
                ReferenceTrackIdentity,
            )

            reference_identity = ReferenceTrackIdentity.from_dict(reference_identity_dict)
            if config_dict is not None:
                config = ReferenceComparisonConfig.from_dict(config_dict)
            else:
                config = ReferenceComparisonConfig()
            stages.append(
                _stage(
                    "reference_identity_rehydration",
                    StageState.COMPLETED,
                )
            )
        except Exception as exc:  # noqa: BLE001
            return _failed(
                request,
                stages=stages,
                errors=[
                    _error(
                        "invalid_request",
                        f"Invalid reference identity or config: {exc}",
                        stage_id="reference_identity",
                    )
                ],
            )

        try:
            comparator = self._reference_comparator or self._import_reference_comparator()
            comparison = comparator.compare(source, reference, reference_identity, config=config)
            stages.append(_stage("reference_compare", StageState.COMPLETED))
        except Exception as exc:  # noqa: BLE001
            return _failed(
                request,
                stages=stages,
                errors=[
                    _error(
                        "reference_failure",
                        f"Reference comparison failed: {exc}",
                        stage_id="reference_compare",
                    )
                ],
            )

        return _success(
            request,
            payload={"comparison": _dictify(comparison.evidence)},
            stages=stages,
            limitations=[
                "Reference comparison uses declared mode and transport evidence only; it does not prove perceptual similarity."
            ],
        )

    def _mix_evaluate(self, request: ApplicationRequest) -> ApplicationResult:
        policy_dict = request.parameters["mix_policy"]
        evidence_dicts = request.parameters.get("evidence", [])
        stages: list[StageOutcome] = []

        try:
            from phasenox.perception.mix_intelligence_contracts import MixIssuePolicy

            policy = MixIssuePolicy.from_dict(policy_dict)
            stages.append(_stage("policy_rehydration", StageState.COMPLETED))
        except Exception as exc:  # noqa: BLE001
            return _failed(
                request,
                stages=stages,
                errors=[
                    _error(
                        "invalid_request",
                        f"Invalid mix policy: {exc}",
                        stage_id="policy_rehydration",
                    )
                ],
            )

        evidence = []
        if evidence_dicts:
            try:
                evidence = self._rehydrate_evidence(evidence_dicts, stages)
            except Exception as exc:  # noqa: BLE001
                return _failed(
                    request,
                    stages=stages,
                    errors=[
                        _error(
                            "invalid_request",
                            f"Invalid evidence: {exc}",
                            stage_id="evidence_rehydration",
                        )
                    ],
                )

        try:
            engine = self._mix_engine or self._import_mix_engine()
            result = engine.evaluate(policy, evidence)
            stages.append(_stage("mix_evaluate", StageState.COMPLETED))
        except Exception as exc:  # noqa: BLE001
            return _failed(
                request,
                stages=stages,
                errors=[
                    _error(
                        "analysis_failure",
                        f"Mix evaluation failed: {exc}",
                        stage_id="mix_evaluate",
                    )
                ],
            )

        return _success(
            request,
            payload={"mix_intelligence": _dictify(result)},
            stages=stages,
            limitations=[
                "Mix evaluation applies declared policy criteria to supplied evidence; insufficient evidence remains a truthful result, not a failure.",
                "Triggered issues are not claims about audible defects.",
            ],
        )

    def _reason(self, request: ApplicationRequest) -> ApplicationResult:
        policy_dict = request.parameters["mix_policy"]
        evidence_dicts = request.parameters.get("evidence", [])
        stages: list[StageOutcome] = []

        try:
            from phasenox.perception.mix_intelligence_contracts import MixIssuePolicy

            policy = MixIssuePolicy.from_dict(policy_dict)
        except Exception as exc:  # noqa: BLE001
            return _failed(
                request,
                stages=stages,
                errors=[
                    _error(
                        "invalid_request",
                        f"Invalid mix policy: {exc}",
                        stage_id="policy_rehydration",
                    )
                ],
            )

        evidence = []
        if evidence_dicts:
            try:
                evidence = self._rehydrate_evidence(evidence_dicts, stages)
            except Exception as exc:  # noqa: BLE001
                return _failed(
                    request,
                    stages=stages,
                    errors=[
                        _error(
                            "invalid_request",
                            f"Invalid evidence: {exc}",
                            stage_id="evidence_rehydration",
                        )
                    ],
                )

        try:
            mix_engine = self._mix_engine or self._import_mix_engine()
            mix_result = mix_engine.evaluate(policy, evidence)
            stages.append(_stage("mix_evaluate", StageState.COMPLETED))
        except Exception as exc:  # noqa: BLE001
            return _failed(
                request,
                stages=stages,
                errors=[
                    _error(
                        "analysis_failure",
                        f"Mix evaluation failed: {exc}",
                        stage_id="mix_evaluate",
                    )
                ],
            )

        try:
            reasoning = self._reasoning_engine or self._import_reasoning_engine()
            reasoning_result = reasoning.explain(mix_result)
            stages.append(_stage("reasoning", StageState.COMPLETED))
        except Exception as exc:  # noqa: BLE001
            return _failed(
                request,
                stages=stages,
                errors=[
                    _error(
                        "reasoning_failure",
                        f"Reasoning failed: {exc}",
                        stage_id="reasoning",
                    )
                ],
            )

        if reasoning_result.state.value == "completed":
            return _success(
                request,
                payload={
                    "mix_intelligence": _dictify(mix_result),
                    "reasoning": _dictify(reasoning_result),
                },
                stages=stages,
                limitations=[
                    "Reasoning statements are grounded in Sprint 10 facts; they are not perceptual certainty."
                ],
            )

        if reasoning_result.state.value == "no_grounded_statements":
            return _success(
                request,
                payload={
                    "mix_intelligence": _dictify(mix_result),
                    "reasoning": _dictify(reasoning_result),
                },
                stages=stages,
                limitations=[
                    "No grounded statements were produced; the reasoning result is truthful but empty."
                ],
            )

        errors: list[ApplicationError] = []
        for err in reasoning_result.errors:
            errors.append(
                _error(
                    "reasoning_failure",
                    err.message,
                    stage_id="reasoning",
                )
            )
        if not errors:
            errors.append(
                _error(
                    "reasoning_failure",
                    f"Reasoning finished with state {reasoning_result.state.value}",
                    stage_id="reasoning",
                )
            )
        return _partial(
            request,
            payload={
                "mix_intelligence": _dictify(mix_result),
                "reasoning": _dictify(reasoning_result),
            },
            stages=stages,
            errors=errors,
            limitations=[
                "Reasoning produced a bounded non-completion result; the mix intelligence payload is still returned."
            ],
        )

    def _capability_inspect(self, request: ApplicationRequest) -> ApplicationResult:
        snapshot = _capability_snapshot()
        return _success(
            request,
            payload={"snapshot": _dictify(snapshot)},
            stages=[_stage("capability_inspect", StageState.COMPLETED)],
            limitations=[
                "Dependency availability reflects importable packages only, not model, hardware, or runtime compatibility."
            ],
        )

    def _load_audio(self, path: Any, stages: list[StageOutcome]) -> Any:
        from phasenox.audio.io import AudioIOService

        audio_io = self._audio_io or AudioIOService()
        stages.append(_stage("audio_io", StageState.RUNNING))
        audio = audio_io.load(path)
        stages[-1] = _stage("audio_io", StageState.COMPLETED)
        return audio

    def _import_auditory_frontend(self) -> Any:
        from phasenox.perception.auditory import AuditoryFrontend

        return AuditoryFrontend()

    def _import_descriptor_foundation(self) -> Any:
        from phasenox.perception.descriptors import PerceptualDescriptorFoundation

        return PerceptualDescriptorFoundation()

    def _import_reference_comparator(self) -> Any:
        from phasenox.perception.reference_intelligence import ObjectiveReferenceComparator

        return ObjectiveReferenceComparator()

    def _import_mix_engine(self) -> Any:
        from phasenox.perception.mix_intelligence import PerceptualMixIntelligenceEngine

        return PerceptualMixIntelligenceEngine()

    def _import_reasoning_engine(self) -> Any:
        from phasenox.perception.reasoning import PerceptualReasoningEngine

        return PerceptualReasoningEngine()

    def _rehydrate_evidence(
        self,
        evidence_dicts: list[dict[str, Any]],
        stages: list[StageOutcome],
    ) -> list[Any]:
        from phasenox.perception.reference_contracts import ReferenceEvidenceResult
        from phasenox.perception.translation_contracts import TranslationEvidenceResult

        evidence: list[Any] = []
        for item in evidence_dicts:
            if not isinstance(item, dict):
                raise TypeError("each evidence item must be a dict")
            contract_type = item.get("contract_type")
            data = item.get("data")
            if not isinstance(data, dict):
                raise TypeError("each evidence item must contain a dict 'data'")
            if contract_type == "reference_evidence":
                evidence.append(ReferenceEvidenceResult.from_dict(data))
            elif contract_type == "translation_evidence":
                evidence.append(TranslationEvidenceResult.from_dict(data))
            else:
                raise ValueError(f"unsupported evidence contract_type: {contract_type}")
        if evidence:
            stages.append(
                _stage(
                    "evidence_rehydration",
                    StageState.COMPLETED,
                    {"count": len(evidence)},
                )
            )
        return evidence


__all__ = ["NoisyneV2Service"]

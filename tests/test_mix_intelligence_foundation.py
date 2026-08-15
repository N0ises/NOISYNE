from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from noisyne.audio.io.models import AudioData, AudioMetadata
from noisyne.perception import (
    ConfidenceBasis,
    ContextClaim,
    ContextDimension,
    ContextPolicySelectionResult,
    ContextPolicySelectionStatus,
    ContextProvenance,
    ContextResolutionResult,
    ContextResolutionStatus,
    MixCriterionOperator,
    MixEvaluationState,
    MixEvidenceDimensionId,
    MixEvidenceSourceType,
    MixIntelligenceResult,
    MixIntelligenceSummary,
    MixIssuePolicy,
    MixIssuePriority,
    MixIssueType,
    PlaybackProfileReference,
    ReferenceComparisonConfig,
    ReferenceComparisonMode,
    ReferenceProvenance,
    ReferenceTrackIdentity,
    RelativeMaskingPairContext,
    ResolvedContextDimension,
    ScalarValue,
    TransferAcousticScope,
    TransferChannelTopology,
    TransferGainBasis,
    TransferKind,
    TransferPhaseBasis,
    TransferProvenance,
    TranslationEvidenceDimensionId,
    TranslationPolicyProvenance,
    TranslationRiskComparison,
    TranslationRiskCriterion,
    TranslationRiskPolicy,
    UnitBasis,
)
from noisyne.perception.masking import SimultaneousMaskingFoundation
from noisyne.perception.mix_intelligence import PerceptualMixIntelligenceEngine
from noisyne.perception.mix_intelligence_contracts import MixIssueCriterion
from noisyne.perception.reference_intelligence import ObjectiveReferenceComparator
from noisyne.perception.transfer import ImpulseResponseTransfer
from noisyne.perception.transfer_contracts import PlaybackTransferProfile
from noisyne.perception.translation import TranslationEvidenceAnalyzer, TranslationRiskEvaluator
from noisyne.runtime.capabilities import CapabilityStatus, registry

ROOT = Path(__file__).resolve().parents[1]


def _audio(samples: np.ndarray, sample_rate: int = 48_000) -> AudioData:
    values = np.asarray(samples, dtype=np.float64)
    channels = values.shape[1] if values.ndim == 2 else 1
    return AudioData(
        samples=values,
        metadata=AudioMetadata(
            path=Path("mix-intelligence-fixture.wav"),
            filename="mix-intelligence-fixture.wav",
            extension=".wav",
            format="wav",
            codec=None,
            sample_rate=sample_rate,
            channels=channels,
            duration=len(values) / sample_rate,
            bit_depth=24,
            file_size=values.nbytes,
        ),
    )


def _tone(amplitude: float = 0.2, frequency_hz: float = 1000.0) -> np.ndarray:
    time = np.arange(4096, dtype=np.float64) / 48_000.0
    return amplitude * np.sin(2.0 * np.pi * frequency_hz * time)


def _reference_result(
    reference_gain: float = 0.5,
    *,
    mode: ReferenceComparisonMode = ReferenceComparisonMode.RAW_LEVEL,
    reference_id: str = "fixture.reference",
):
    source = _audio(_tone())
    reference = _audio(source.samples * reference_gain)
    identity = ReferenceTrackIdentity(
        reference_id=reference_id,
        version="1.0.0",
        display_name="Fixture reference",
        provenance=ReferenceProvenance.PROJECT_SUPPLIED,
        source="Sprint 10 analytical fixture",
        duration_seconds=reference.metadata.duration,
        sample_rate_hz=reference.metadata.sample_rate,
        channel_count=reference.metadata.channels,
    )
    return (
        ObjectiveReferenceComparator()
        .compare(
            source,
            reference,
            identity,
            config=ReferenceComparisonConfig(mode=mode),
            source_id="fixture.source",
        )
        .evidence
    )


def _criterion(
    criterion_id: str = "reference-energy",
    *,
    source_type: MixEvidenceSourceType = MixEvidenceSourceType.REFERENCE_EVIDENCE,
    dimension: MixEvidenceDimensionId = (
        MixEvidenceDimensionId.REFERENCE_PROGRAMME_ENERGY_DELTA_DB
    ),
    operator: MixCriterionOperator = MixCriterionOperator.ABSOLUTE_GREATER_THAN,
    threshold: ScalarValue | None = None,
    issue_type: MixIssueType = MixIssueType.REFERENCE_DEVIATION,
    priority: MixIssuePriority = MixIssuePriority.MEDIUM,
    priority_rank: int | None = None,
    evidence_identity: str | None = None,
) -> MixIssueCriterion:
    return MixIssueCriterion(
        criterion_id=criterion_id,
        version="1.0.0",
        provenance=TranslationPolicyProvenance.PROJECT_DECLARED,
        source="Fixture project policy",
        description="Explicit analytical criterion; no universal interpretation.",
        display_name=f"Declared criterion {criterion_id} exceeded",
        evidence_source_type=source_type,
        evidence_dimension=dimension,
        evidence_identity=evidence_identity,
        operator=operator,
        threshold=threshold or ScalarValue(3.0, UnitBasis.DECLARED_UNIT, unit="dB"),
        issue_type=issue_type,
        priority=priority,
        priority_rank=priority_rank,
    )


def _policy(*criteria: MixIssueCriterion) -> MixIssuePolicy:
    return MixIssuePolicy(
        policy_id="fixture.mix-policy",
        version="1.0.0",
        provenance=TranslationPolicyProvenance.PROJECT_DECLARED,
        source="Fixture project policy",
        description="Caller-defined Sprint 10 fixture policy.",
        criteria=list(criteria),
    )


def _boolean_threshold(value: bool, scale: str) -> ScalarValue:
    return ScalarValue(value, UnitBasis.NAMED_SCALE, scale=scale)


def _transfer_profile() -> PlaybackTransferProfile:
    return PlaybackTransferProfile(
        transfer_id="fixture.transfer",
        version="1.0.0",
        profile_reference=PlaybackProfileReference("fixture.playback", "1.0.0"),
        provenance=TransferProvenance.ENGINEERING_APPROXIMATION,
        evidence_source="Sprint 10 fixture",
        evidence_version="1.0.0",
        transfer_kind=TransferKind.IMPULSE_RESPONSE,
        gain_basis=TransferGainBasis.DIGITAL_AMPLITUDE_RATIO,
        phase_basis=TransferPhaseBasis.IMPULSE_RESPONSE_CONTAINS_PHASE,
        acoustic_scope=TransferAcousticScope.ENGINEERING_TEST_FIXTURE,
        channel_topology=TransferChannelTopology.CHANNEL_INDEPENDENT_SHARED,
        measurement_conditions="Analytical single-tap fixture",
        normalization_reference="Digital amplitude ratio",
        time_origin_alignment="Tap zero at source sample zero",
        sample_rate_hz=48_000,
    )


def _translation_evidence(gain: float):
    taps = np.array([[gain]], dtype=np.float64)
    taps.setflags(write=False)
    transfer = ImpulseResponseTransfer(_transfer_profile(), taps)
    return TranslationEvidenceAnalyzer().analyze(_audio(_tone()), transfer).evidence


def _translation_policy_result(exceeded: bool):
    evidence = _translation_evidence(0.5)
    threshold = -3.0 if exceeded else -10.0
    criterion = TranslationRiskCriterion(
        criterion_id="translation.energy.floor",
        criterion_version="1.0.0",
        evidence_dimension_id=TranslationEvidenceDimensionId.PROGRAMME_ENERGY_DELTA_DB,
        comparison=TranslationRiskComparison.LESS_THAN,
        threshold=ScalarValue(threshold, UnitBasis.DECLARED_UNIT, unit="dB"),
        direction_semantics="Exact signed energy comparison.",
        provenance=TranslationPolicyProvenance.PROJECT_DECLARED,
        source="Fixture translation policy",
        description="Declared translation energy criterion.",
    )
    policy = TranslationRiskPolicy(
        policy_id="fixture.translation-policy",
        version="1.0.0",
        provenance=TranslationPolicyProvenance.PROJECT_DECLARED,
        source="Fixture translation policy",
        description="Explicit translation fixture policy.",
        criteria=[criterion],
    )
    return TranslationRiskEvaluator().evaluate(evidence, policy)


def _context_conflict() -> ContextResolutionResult:
    claims = [
        ContextClaim(
            claim_id="genre.a",
            context_dimension=ContextDimension.GENRE,
            value="example-a",
            provenance=ContextProvenance.PROJECT_DECLARED,
            source="Fixture project",
        ),
        ContextClaim(
            claim_id="genre.b",
            context_dimension=ContextDimension.GENRE,
            value="example-b",
            provenance=ContextProvenance.PROJECT_DECLARED,
            source="Fixture project",
        ),
    ]
    return ContextResolutionResult(
        status=ContextResolutionStatus.CONFLICT,
        dimensions=[
            ResolvedContextDimension(
                context_dimension=ContextDimension.GENRE,
                status=ContextResolutionStatus.CONFLICT,
                values=["example-a", "example-b"],
                claims=claims,
            )
        ],
    )


def _ambiguous_selection() -> ContextPolicySelectionResult:
    claim = ContextClaim(
        claim_id="delivery.fixture",
        context_dimension=ContextDimension.DELIVERY_TARGET,
        value="fixture-delivery",
        provenance=ContextProvenance.PROJECT_DECLARED,
        source="Fixture project",
    )
    resolution = ContextResolutionResult(
        status=ContextResolutionStatus.RESOLVED,
        dimensions=[
            ResolvedContextDimension(
                context_dimension=ContextDimension.DELIVERY_TARGET,
                status=ContextResolutionStatus.RESOLVED,
                values=["fixture-delivery"],
                claims=[claim],
            )
        ],
    )
    return ContextPolicySelectionResult(
        status=ContextPolicySelectionStatus.AMBIGUOUS,
        resolution=resolution,
        matched_binding_ids=["binding.a", "binding.b"],
        reason="Two explicit bindings matched.",
    )


def test_reference_energy_criterion_triggers_with_objective_exceedance() -> None:
    result = PerceptualMixIntelligenceEngine().evaluate(
        _policy(_criterion()), [_reference_result()]
    )

    assert result.summary.triggered_issue_count == 1
    issue = result.issues[0]
    assert issue.evidence_value.value == pytest.approx(6.020599913279624)
    assert issue.exceedance.value == pytest.approx(3.020599913279624)
    assert issue.criterion.priority is MixIssuePriority.MEDIUM
    assert issue.confidence.score is None
    assert issue.confidence.basis is ConfidenceBasis.UNKNOWN


def test_reference_energy_larger_threshold_does_not_trigger() -> None:
    criterion = _criterion(threshold=ScalarValue(10.0, UnitBasis.DECLARED_UNIT, unit="dB"))
    result = PerceptualMixIntelligenceEngine().evaluate(_policy(criterion), [_reference_result()])

    assert result.issues == []
    assert result.summary.not_triggered_count == 1


@pytest.mark.parametrize(
    ("operator", "expected"),
    [
        (MixCriterionOperator.GREATER_THAN, False),
        (MixCriterionOperator.GREATER_THAN_OR_EQUAL, True),
    ],
)
def test_numeric_equality_semantics(operator: MixCriterionOperator, expected: bool) -> None:
    evidence = _reference_result(reference_gain=0.5)
    actual = evidence.programme_energy.signed_delta.value
    criterion = _criterion(
        operator=operator,
        threshold=ScalarValue(actual, UnitBasis.DECLARED_UNIT, unit="dB"),
    )
    result = PerceptualMixIntelligenceEngine().evaluate(_policy(criterion), [evidence])
    assert bool(result.issues) is expected


def test_unit_mismatch_is_rejected_without_conversion() -> None:
    criterion = _criterion(threshold=ScalarValue(3.0, UnitBasis.DECLARED_UNIT, unit="Hz"))
    with pytest.raises(ValueError, match="unit/scale"):
        PerceptualMixIntelligenceEngine().evaluate(_policy(criterion), [_reference_result()])


@pytest.mark.parametrize("exceeded", [True, False])
def test_translation_policy_boolean_is_not_probability(exceeded: bool) -> None:
    translation = _translation_policy_result(exceeded)
    criterion = _criterion(
        "translation-policy-boolean",
        source_type=MixEvidenceSourceType.TRANSLATION_POLICY_RESULT,
        dimension=MixEvidenceDimensionId.TRANSLATION_DECLARED_POLICY_THRESHOLD_EXCEEDED,
        operator=MixCriterionOperator.BOOLEAN_IS_TRUE,
        threshold=_boolean_threshold(True, "declared_policy_threshold_exceeded"),
        issue_type=MixIssueType.TRANSLATION_POLICY_EXCEEDED,
    )
    result = PerceptualMixIntelligenceEngine().evaluate(_policy(criterion), [translation])

    assert bool(result.issues) is exceeded
    if exceeded:
        assert result.issues[0].exceedance is None


def test_translation_objective_evidence_adapter_reuses_signed_delta() -> None:
    criterion = _criterion(
        "translation-energy",
        source_type=MixEvidenceSourceType.TRANSLATION_EVIDENCE,
        dimension=MixEvidenceDimensionId.TRANSLATION_PROGRAMME_ENERGY_DELTA_DB,
        issue_type=MixIssueType.LEVEL_CONDITION,
    )
    result = PerceptualMixIntelligenceEngine().evaluate(
        _policy(criterion), [_translation_evidence(0.5)]
    )
    assert result.issues[0].evidence_value.value == pytest.approx(-6.020599913279624)
    assert result.issues[0].exceedance.value == pytest.approx(3.020599913279624)


def test_missing_evidence_records_insufficient_evidence() -> None:
    result = PerceptualMixIntelligenceEngine().evaluate(_policy(_criterion()), [])
    assert result.issues == []
    assert result.evaluations[0].state is MixEvaluationState.INSUFFICIENT_EVIDENCE
    assert result.summary.insufficient_evidence_count == 1


def test_shape_only_skipped_energy_is_not_substituted_with_zero() -> None:
    result = PerceptualMixIntelligenceEngine().evaluate(
        _policy(_criterion()),
        [_reference_result(mode=ReferenceComparisonMode.SHAPE_ONLY)],
    )
    assert result.issues == []
    assert result.evaluations[0].state is MixEvaluationState.INSUFFICIENT_EVIDENCE


def test_context_resolution_conflict_emits_configuration_issue_only() -> None:
    criterion = _criterion(
        "context-conflict",
        source_type=MixEvidenceSourceType.CONTEXT_RESOLUTION,
        dimension=MixEvidenceDimensionId.CONTEXT_RESOLUTION_CONFLICT,
        operator=MixCriterionOperator.BOOLEAN_IS_TRUE,
        threshold=_boolean_threshold(True, "context_resolution_conflict"),
        issue_type=MixIssueType.CONTEXT_POLICY_CONFLICT,
        priority=MixIssuePriority.HIGH,
    )
    result = PerceptualMixIntelligenceEngine().evaluate(_policy(criterion), [_context_conflict()])
    assert result.issues[0].criterion.issue_type is MixIssueType.CONTEXT_POLICY_CONFLICT


def test_ambiguous_context_policy_selection_can_emit_explicit_workflow_issue() -> None:
    criterion = _criterion(
        "context-ambiguous",
        source_type=MixEvidenceSourceType.CONTEXT_POLICY_SELECTION,
        dimension=MixEvidenceDimensionId.CONTEXT_POLICY_SELECTION_AMBIGUOUS,
        operator=MixCriterionOperator.BOOLEAN_IS_TRUE,
        threshold=_boolean_threshold(True, "context_policy_selection_ambiguous"),
        issue_type=MixIssueType.CONTEXT_POLICY_CONFLICT,
    )
    result = PerceptualMixIntelligenceEngine().evaluate(
        _policy(criterion), [_ambiguous_selection()]
    )
    assert result.summary.triggered_issue_count == 1


def test_masking_adapter_uses_declared_pair_maximum_relative_margin_only() -> None:
    target = _tone(amplitude=0.1)
    masking = SimultaneousMaskingFoundation().analyze_pair(
        _audio(target * 2.0),
        _audio(target),
        context=RelativeMaskingPairContext(
            gain_relationship_reference="shared-gain-fixture",
            alignment_reference="sample-zero-fixture",
            masker_source_id="masker",
            target_source_id="target",
        ),
    )
    criterion = _criterion(
        "masking-relative-margin",
        source_type=MixEvidenceSourceType.MASKING_RELATIVE_MARGIN,
        dimension=MixEvidenceDimensionId.MASKING_MAXIMUM_RELATIVE_EXCITATION_MARGIN_DB,
        operator=MixCriterionOperator.GREATER_THAN,
        issue_type=MixIssueType.MASKING_RELATIVE_MARGIN,
    )
    result = PerceptualMixIntelligenceEngine().evaluate(_policy(criterion), [masking])
    assert result.issues[0].evidence_value.value == pytest.approx(6.020599913279624)


def test_declared_priority_and_stable_criterion_tie_break_control_order() -> None:
    criteria = (
        _criterion("criterion-c", priority=MixIssuePriority.HIGH),
        _criterion("criterion-b", priority=MixIssuePriority.MEDIUM),
        _criterion("criterion-a", priority=MixIssuePriority.HIGH),
    )
    result = PerceptualMixIntelligenceEngine().evaluate(_policy(*criteria), [_reference_result()])
    assert [item.criterion.criterion_id for item in result.issues] == [
        "criterion-a",
        "criterion-c",
        "criterion-b",
    ]


def test_policy_rank_breaks_same_priority_before_criterion_id() -> None:
    result = PerceptualMixIntelligenceEngine().evaluate(
        _policy(
            _criterion("criterion-a", priority=MixIssuePriority.HIGH, priority_rank=2),
            _criterion("criterion-z", priority=MixIssuePriority.HIGH, priority_rank=1),
        ),
        [_reference_result()],
    )
    assert [item.criterion.criterion_id for item in result.issues] == [
        "criterion-z",
        "criterion-a",
    ]


def test_no_triggered_issues_is_a_valid_result() -> None:
    criterion = _criterion(threshold=ScalarValue(100.0, UnitBasis.DECLARED_UNIT, unit="dB"))
    result = PerceptualMixIntelligenceEngine().evaluate(_policy(criterion), [_reference_result()])
    assert result.issues == []
    assert result.summary.triggered_issue_count == 0


def test_duplicate_criterion_ids_are_rejected() -> None:
    with pytest.raises(ValueError, match="unique criterion_id"):
        _policy(_criterion(), _criterion())


def test_multiple_unspecified_evidence_identities_record_conflict() -> None:
    result = PerceptualMixIntelligenceEngine().evaluate(
        _policy(_criterion()),
        [
            _reference_result(reference_id="reference-a"),
            _reference_result(reference_id="reference-b"),
        ],
    )
    assert result.evaluations[0].state is MixEvaluationState.CONFLICT
    assert result.summary.conflict_count == 1


def test_same_canonical_evidence_identity_with_different_values_is_rejected() -> None:
    with pytest.raises(ValueError, match="conflicting supplied evidence"):
        PerceptualMixIntelligenceEngine().evaluate(
            _policy(_criterion()),
            [_reference_result(0.5), _reference_result(0.25)],
        )


def test_forged_issue_criterion_identity_is_rejected() -> None:
    result = PerceptualMixIntelligenceEngine().evaluate(
        _policy(_criterion()), [_reference_result()]
    )
    forged_criterion = replace(result.issues[0].criterion, criterion_id="forged")
    with pytest.raises(ValueError, match="issue_id must be deterministically derived"):
        replace(
            result.issues[0],
            criterion=forged_criterion,
            title=forged_criterion.display_name,
            issue_id="mix_issue.000000000000000000000000",
        )


def test_forged_summary_counts_are_rejected() -> None:
    result = PerceptualMixIntelligenceEngine().evaluate(
        _policy(_criterion()), [_reference_result()]
    )
    forged = MixIntelligenceSummary(1, 0, 1, 0, 0)
    with pytest.raises(ValueError, match="summary counts"):
        replace(result, summary=forged)


def test_json_round_trip_and_forged_from_dict_validation() -> None:
    result = PerceptualMixIntelligenceEngine().evaluate(
        _policy(_criterion()), [_reference_result()]
    )
    payload = result.to_dict()
    assert MixIntelligenceResult.from_dict(payload) == result
    assert json.loads(json.dumps(payload, allow_nan=False)) == payload

    payload["summary"]["triggered_issue_count"] = 0
    payload["summary"]["not_triggered_count"] = 1
    with pytest.raises(ValueError, match="summary counts"):
        MixIntelligenceResult.from_dict(payload)


def test_repeated_evaluation_is_deterministic() -> None:
    policy = _policy(_criterion())
    evidence = [_reference_result()]
    engine = PerceptualMixIntelligenceEngine()
    assert engine.evaluate(policy, evidence) == engine.evaluate(policy, evidence)


def test_transport_has_no_aggregate_score_or_recommendation_fields() -> None:
    result = PerceptualMixIntelligenceEngine().evaluate(
        _policy(_criterion()), [_reference_result()]
    )
    payload = result.to_dict()

    def field_names(value: object) -> set[str]:
        if isinstance(value, dict):
            return set(value) | set().union(*(field_names(item) for item in value.values()))
        if isinstance(value, list):
            return set().union(*(field_names(item) for item in value), set())
        return set()

    names = field_names(payload)
    for prohibited in (
        "mix_score",
        "quality_score",
        "professional_score",
        "readiness_score",
        "recommendation",
    ):
        assert prohibited not in names


def test_precomputed_evaluator_import_is_lightweight() -> None:
    program = (
        "import sys; "
        f"sys.path.insert(0, {str(ROOT)!r}); "
        "import noisyne.perception.mix_intelligence; "
        "assert 'numpy' not in sys.modules; assert 'torch' not in sys.modules; "
        "assert 'noisyne.perception.auditory' not in sys.modules; "
        "assert 'noisyne.perception.masking' not in sys.modules"
    )
    completed = subprocess.run(
        [sys.executable, "-I", "-c", program],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr


def test_capability_truth_is_narrow() -> None:
    assert (
        registry.get("perceptual_mix_intelligence_foundation").status
        is CapabilityStatus.IMPLEMENTED
    )
    assert registry.get("mix_policy_evaluation").status is CapabilityStatus.IMPLEMENTED
    for prohibited in (
        "automatic_mix_engine",
        "mix_quality_ai",
        "professional_mix_scoring",
        "autonomous_mixing",
        "mastering_recommendation",
    ):
        assert registry.get(prohibited) is None

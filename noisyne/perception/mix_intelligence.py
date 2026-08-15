from __future__ import annotations

from dataclasses import dataclass

from .common import (
    Confidence,
    ConfidenceBasis,
    MethodMetadata,
    ResultStatus,
    ScalarValue,
    UnitBasis,
)
from .context_contracts import (
    ContextPolicySelectionResult,
    ContextPolicySelectionStatus,
    ContextResolutionResult,
    ContextResolutionStatus,
)
from .mix_intelligence_contracts import (
    MIX_INTELLIGENCE_METHOD_ID,
    MIX_INTELLIGENCE_METHOD_VERSION,
    MixCriterionEvaluation,
    MixEvaluationState,
    MixEvidenceDimensionId,
    MixEvidenceSourceType,
    MixIntelligenceResult,
    MixIntelligenceSummary,
    MixIssue,
    MixIssueCriterion,
    MixIssuePolicy,
    _criterion_triggered,
    _expected_exceedance,
    _same_unit,
    mix_issue_id,
    mix_issue_sort_key,
)
from .reference_contracts import ReferenceEvidenceResult
from .translation_contracts import (
    PolicyConditionedTranslationRiskResult,
    TranslationEvidenceResult,
)


@dataclass(frozen=True, slots=True)
class _ResolvedEvidence:
    source_type: MixEvidenceSourceType
    dimension: MixEvidenceDimensionId
    identity: str
    state: ResultStatus
    value: ScalarValue | None
    method: MethodMetadata
    references: tuple[str, ...]
    reason: str | None = None


class PerceptualMixIntelligenceEngine:
    """Evaluate declared criteria against existing evidence without signal analysis."""

    def evaluate(self, policy: MixIssuePolicy, evidence: list[object]) -> MixIntelligenceResult:
        if not isinstance(policy, MixIssuePolicy):
            raise TypeError("policy must be a MixIssuePolicy")
        if not isinstance(evidence, list):
            raise TypeError("evidence must be a list")
        resolved = _resolve_evidence(evidence)

        evaluations: list[MixCriterionEvaluation] = []
        issues: list[MixIssue] = []
        for criterion in policy.criteria:
            candidates = [
                item
                for item in resolved
                if item.source_type is criterion.evidence_source_type
                and item.dimension is criterion.evidence_dimension
                and (
                    criterion.evidence_identity is None
                    or item.identity == criterion.evidence_identity
                )
            ]
            if not candidates:
                evaluations.append(
                    _non_computed_evaluation(
                        criterion,
                        MixEvaluationState.INSUFFICIENT_EVIDENCE,
                        "No supplied evidence matched the declared source, dimension, and identity.",
                    )
                )
                continue
            if len(candidates) > 1:
                evaluations.append(
                    _non_computed_evaluation(
                        criterion,
                        MixEvaluationState.CONFLICT,
                        "Multiple distinct evidence identities match this criterion; none was selected.",
                    )
                )
                continue

            actual = candidates[0]
            if actual.state is not ResultStatus.COMPUTED or actual.value is None:
                reason = actual.reason or (
                    f"Evidence state {actual.state.value} does not provide a criterion value."
                )
                evaluations.append(
                    MixCriterionEvaluation(
                        criterion_id=criterion.criterion_id,
                        criterion_version=criterion.version,
                        state=MixEvaluationState.INSUFFICIENT_EVIDENCE,
                        evidence_source_type=criterion.evidence_source_type,
                        evidence_dimension=criterion.evidence_dimension,
                        reason=reason,
                        evidence_identity=actual.identity,
                        evidence_state=actual.state,
                        evidence_method=actual.method,
                    )
                )
                continue
            if not _same_unit(actual.value, criterion.threshold):
                raise ValueError(
                    f"criterion {criterion.criterion_id} threshold unit/scale does not match evidence"
                )

            triggered = _criterion_triggered(actual.value, criterion.operator, criterion.threshold)
            state = MixEvaluationState.TRIGGERED if triggered else MixEvaluationState.NOT_TRIGGERED
            evaluations.append(
                MixCriterionEvaluation(
                    criterion_id=criterion.criterion_id,
                    criterion_version=criterion.version,
                    state=state,
                    evidence_source_type=criterion.evidence_source_type,
                    evidence_dimension=criterion.evidence_dimension,
                    reason=(
                        "Supplied evidence satisfies the declared criterion."
                        if triggered
                        else "Supplied evidence does not satisfy the declared criterion."
                    ),
                    evidence_identity=actual.identity,
                    evidence_value=actual.value,
                    evidence_state=actual.state,
                    evidence_method=actual.method,
                )
            )
            if triggered:
                issues.append(_issue(policy, criterion, actual))

        issues.sort(key=mix_issue_sort_key)
        counts = {state: 0 for state in MixEvaluationState}
        for evaluation in evaluations:
            counts[evaluation.state] += 1
        summary = MixIntelligenceSummary(
            evaluated_criterion_count=len(evaluations),
            triggered_issue_count=counts[MixEvaluationState.TRIGGERED],
            not_triggered_count=counts[MixEvaluationState.NOT_TRIGGERED],
            insufficient_evidence_count=counts[MixEvaluationState.INSUFFICIENT_EVIDENCE],
            conflict_count=counts[MixEvaluationState.CONFLICT],
        )
        return MixIntelligenceResult(
            policy=policy,
            method=_method(),
            evaluations=evaluations,
            issues=issues,
            summary=summary,
            confidence=Confidence(
                score=None,
                basis=ConfidenceBasis.UNKNOWN,
                reason=(
                    "Criterion evaluation is deterministic; perceptual importance is not validated."
                ),
            ),
            assumptions=["Every threshold and priority is supplied by the identified policy."],
            limitations=[
                "A triggered issue is not an audible defect, mix failure, or recommendation.",
                "Independent issues are not aggregated into a quality or readiness score.",
            ],
        )


def _issue(
    policy: MixIssuePolicy,
    criterion: MixIssueCriterion,
    actual: _ResolvedEvidence,
) -> MixIssue:
    return MixIssue(
        issue_id=mix_issue_id(policy.policy_id, policy.version, criterion, actual.identity),
        policy_id=policy.policy_id,
        policy_version=policy.version,
        criterion=criterion,
        state=MixEvaluationState.TRIGGERED,
        title=criterion.display_name,
        evidence_identity=actual.identity,
        evidence_value=actual.value,
        evidence_method=actual.method,
        exceedance=_expected_exceedance(actual.value, criterion.operator, criterion.threshold),
        confidence=Confidence(
            score=None,
            basis=ConfidenceBasis.UNKNOWN,
            reason=(
                "Criterion evaluation is deterministic; audibility and perceptual severity are "
                "not validated."
            ),
        ),
        evidence_references=list(actual.references),
        assumptions=list(criterion.assumptions),
        limitations=[
            "Priority is declared by policy and is not inferred from exceedance magnitude.",
            *criterion.limitations,
        ],
    )


def _non_computed_evaluation(
    criterion: MixIssueCriterion, state: MixEvaluationState, reason: str
) -> MixCriterionEvaluation:
    return MixCriterionEvaluation(
        criterion_id=criterion.criterion_id,
        criterion_version=criterion.version,
        state=state,
        evidence_source_type=criterion.evidence_source_type,
        evidence_dimension=criterion.evidence_dimension,
        reason=reason,
    )


def _resolve_evidence(values: list[object]) -> list[_ResolvedEvidence]:
    resolved: list[_ResolvedEvidence] = []
    for value in values:
        if isinstance(value, ReferenceEvidenceResult):
            resolved.extend(_reference_evidence(value))
        elif isinstance(value, PolicyConditionedTranslationRiskResult):
            resolved.extend(_translation_policy_evidence(value))
        elif isinstance(value, TranslationEvidenceResult):
            resolved.extend(_translation_evidence(value))
        elif isinstance(value, ContextPolicySelectionResult):
            resolved.extend(_context_selection_evidence(value))
        elif isinstance(value, ContextResolutionResult):
            resolved.extend(_context_resolution_evidence(value))
        elif _is_masking_runtime(value):
            resolved.extend(_masking_evidence(value))
        else:
            raise TypeError(f"unsupported mix evidence type: {type(value).__name__}")

    by_key: dict[tuple[MixEvidenceSourceType, MixEvidenceDimensionId, str], _ResolvedEvidence] = {}
    for item in resolved:
        key = (item.source_type, item.dimension, item.identity)
        previous = by_key.get(key)
        if previous is not None and previous != item:
            raise ValueError("conflicting supplied evidence has the same canonical identity")
        by_key[key] = item
    return list(by_key.values())


def _reference_evidence(result: ReferenceEvidenceResult) -> list[_ResolvedEvidence]:
    reference = result.comparison.reference
    identity = f"reference:{reference.reference_id}@{reference.version}"
    source_type = MixEvidenceSourceType.REFERENCE_EVIDENCE
    values = [
        _measurement_evidence(
            source_type,
            MixEvidenceDimensionId.REFERENCE_BRIGHTNESS_CENTROID_DELTA_HZ,
            identity,
            result.brightness.state.status,
            result.brightness.signed_delta,
            result.brightness.method,
            f"{result.brightness.evidence_id}@{result.brightness.method.version}",
            result.brightness.state.reason,
        ),
        _measurement_evidence(
            source_type,
            MixEvidenceDimensionId.REFERENCE_PROGRAMME_ENERGY_DELTA_DB,
            identity,
            result.programme_energy.state.status,
            result.programme_energy.signed_delta,
            result.programme_energy.method,
            f"{result.programme_energy.evidence_id}@{result.programme_energy.method.version}",
            result.programme_energy.state.reason,
        ),
        _measurement_evidence(
            source_type,
            MixEvidenceDimensionId.REFERENCE_SAMPLE_PEAK_DELTA_ABSOLUTE,
            identity,
            result.sample_peak.state.status,
            result.sample_peak.signed_delta,
            result.sample_peak.method,
            f"{result.sample_peak.evidence_id}@{result.sample_peak.method.version}",
            result.sample_peak.state.reason,
        ),
    ]
    summary = result.erb_power_distribution
    erb_value = (
        ScalarValue(summary.maximum_absolute_delta_db, UnitBasis.DECLARED_UNIT, unit="dB")
        if summary.state.status is ResultStatus.COMPUTED
        else None
    )
    values.append(
        _measurement_evidence(
            source_type,
            MixEvidenceDimensionId.REFERENCE_ERB_BAND_MAXIMUM_ABSOLUTE_DELTA_DB,
            identity,
            summary.state.status,
            erb_value,
            summary.method,
            f"{summary.method.method_id}@{summary.method.version}",
            summary.state.reason,
        )
    )
    return values


def _translation_evidence(result: TranslationEvidenceResult) -> list[_ResolvedEvidence]:
    profile = result.comparison.target_profile
    transfer = result.comparison.transfer.profile
    identity = (
        f"translation:{profile.profile_id}@{profile.version}:"
        f"{transfer.transfer_id}@{transfer.version}"
    )
    source_type = MixEvidenceSourceType.TRANSLATION_EVIDENCE
    values = [
        _measurement_evidence(
            source_type,
            MixEvidenceDimensionId.TRANSLATION_BRIGHTNESS_CENTROID_SHIFT_HZ,
            identity,
            result.brightness_centroid.state.status,
            result.brightness_centroid.signed_delta,
            result.brightness_centroid.method,
            result.brightness_centroid.evidence_id,
            result.brightness_centroid.state.reason,
        ),
        _measurement_evidence(
            source_type,
            MixEvidenceDimensionId.TRANSLATION_PROGRAMME_ENERGY_DELTA_DB,
            identity,
            result.programme_energy.state.status,
            result.programme_energy.signed_delta,
            result.programme_energy.method,
            result.programme_energy.evidence_id,
            result.programme_energy.state.reason,
        ),
    ]
    summary = result.erb_power_distribution
    values.append(
        _measurement_evidence(
            source_type,
            MixEvidenceDimensionId.TRANSLATION_ERB_BAND_MAXIMUM_ABSOLUTE_DELTA_DB,
            identity,
            summary.state.status,
            (
                ScalarValue(summary.maximum_absolute_delta_db, UnitBasis.DECLARED_UNIT, unit="dB")
                if summary.state.status is ResultStatus.COMPUTED
                else None
            ),
            summary.method,
            f"{summary.method.method_id}@{summary.method.version}",
            summary.state.reason,
        )
    )
    values.append(
        _measurement_evidence(
            source_type,
            MixEvidenceDimensionId.TRANSLATION_TRANSFERRED_PEAK_ABSOLUTE,
            identity,
            ResultStatus.COMPUTED,
            ScalarValue(
                result.nominal_full_scale.transferred_peak_absolute,
                UnitBasis.DECLARED_UNIT,
                unit="digital_sample_amplitude",
            ),
            result.comparison.transfer_method,
            f"{result.comparison.transfer_method.method_id}@{result.comparison.transfer_method.version}",
        )
    )
    return values


def _translation_policy_evidence(
    result: PolicyConditionedTranslationRiskResult,
) -> list[_ResolvedEvidence]:
    policy = result.policy
    criteria = {item.criterion_id: item for item in policy.criteria}
    method = result.translation.method
    if method is None:
        raise ValueError("computed translation policy evidence requires method identity")
    resolved = []
    for dimension in result.translation.dimensions:
        criterion = criteria.get(dimension.dimension_id)
        if criterion is None:
            raise ValueError("translation policy result dimension lacks its policy criterion")
        identity = (
            f"translation_policy:{policy.policy_id}@{policy.version}:"
            f"{criterion.criterion_id}@{criterion.criterion_version}"
        )
        resolved.append(
            _measurement_evidence(
                MixEvidenceSourceType.TRANSLATION_POLICY_RESULT,
                MixEvidenceDimensionId.TRANSLATION_DECLARED_POLICY_THRESHOLD_EXCEEDED,
                identity,
                dimension.state.status,
                dimension.risk,
                method,
                identity,
                dimension.state.reason,
            )
        )
    return resolved


def _context_resolution_evidence(result: ContextResolutionResult) -> list[_ResolvedEvidence]:
    method = MethodMetadata(result.method_id, result.method_version)
    identity = f"context_resolution:{result.method_id}@{result.method_version}"
    return [
        _measurement_evidence(
            MixEvidenceSourceType.CONTEXT_RESOLUTION,
            MixEvidenceDimensionId.CONTEXT_RESOLUTION_CONFLICT,
            identity,
            ResultStatus.COMPUTED,
            ScalarValue(
                result.status is ContextResolutionStatus.CONFLICT,
                UnitBasis.NAMED_SCALE,
                scale="context_resolution_conflict",
            ),
            method,
            identity,
        )
    ]


def _context_selection_evidence(
    result: ContextPolicySelectionResult,
) -> list[_ResolvedEvidence]:
    method = MethodMetadata(result.method_id, result.method_version)
    identity = f"context_policy_selection:{result.method_id}@{result.method_version}"
    source_type = MixEvidenceSourceType.CONTEXT_POLICY_SELECTION
    return [
        _measurement_evidence(
            source_type,
            MixEvidenceDimensionId.CONTEXT_POLICY_SELECTION_CONFLICT,
            identity,
            ResultStatus.COMPUTED,
            ScalarValue(
                result.status is ContextPolicySelectionStatus.CONFLICT,
                UnitBasis.NAMED_SCALE,
                scale="context_policy_selection_conflict",
            ),
            method,
            identity,
        ),
        _measurement_evidence(
            source_type,
            MixEvidenceDimensionId.CONTEXT_POLICY_SELECTION_AMBIGUOUS,
            identity,
            ResultStatus.COMPUTED,
            ScalarValue(
                result.status is ContextPolicySelectionStatus.AMBIGUOUS,
                UnitBasis.NAMED_SCALE,
                scale="context_policy_selection_ambiguous",
            ),
            method,
            identity,
        ),
    ]


def _is_masking_runtime(value: object) -> bool:
    value_type = type(value)
    return (
        value_type.__module__ == "noisyne.perception.masking"
        and value_type.__name__ == "RelativeMaskingFoundationResult"
    )


def _masking_evidence(result: object) -> list[_ResolvedEvidence]:
    context = result.context
    masking = result.frequency_masking
    method = masking.method
    if method is None:
        raise ValueError("relative masking evidence requires method identity")
    identity = (
        f"masking_pair:{context.masker_source_id or 'undeclared_masker'}:"
        f"{context.target_source_id or 'undeclared_target'}:"
        f"{context.gain_relationship_reference}:{context.alignment_reference}"
    )
    value = None
    if masking.state.status is ResultStatus.COMPUTED:
        defined = result.margin_defined
        if not bool(defined.any()):
            raise ValueError("computed masking evidence requires a defined relative margin")
        value = ScalarValue(
            float(result.relative_excitation_margin_db[defined].max()),
            UnitBasis.DECLARED_UNIT,
            unit="dB",
        )
    return [
        _measurement_evidence(
            MixEvidenceSourceType.MASKING_RELATIVE_MARGIN,
            MixEvidenceDimensionId.MASKING_MAXIMUM_RELATIVE_EXCITATION_MARGIN_DB,
            identity,
            masking.state.status,
            value,
            method,
            f"{method.method_id}@{method.version}",
            masking.state.reason,
        )
    ]


def _measurement_evidence(
    source_type: MixEvidenceSourceType,
    dimension: MixEvidenceDimensionId,
    identity: str,
    state: ResultStatus,
    value: ScalarValue | None,
    method: MethodMetadata,
    reference: str,
    reason: str | None = None,
) -> _ResolvedEvidence:
    if state is ResultStatus.COMPUTED and value is None:
        raise ValueError("computed adapter evidence requires a value")
    if state is not ResultStatus.COMPUTED and value is not None:
        raise ValueError("non-computed adapter evidence must not carry a value")
    return _ResolvedEvidence(
        source_type=source_type,
        dimension=dimension,
        identity=identity,
        state=state,
        value=value,
        method=method,
        references=(reference,),
        reason=reason,
    )


def _method() -> MethodMetadata:
    return MethodMetadata(
        MIX_INTELLIGENCE_METHOD_ID,
        MIX_INTELLIGENCE_METHOD_VERSION,
        "Deterministic evaluation of explicit policy criteria over precomputed evidence.",
    )


__all__ = ["PerceptualMixIntelligenceEngine"]

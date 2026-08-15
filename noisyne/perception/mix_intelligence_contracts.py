from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from enum import Enum

from ._serialization import JsonContract
from .common import (
    Confidence,
    ConfidenceBasis,
    MethodMetadata,
    ResultStatus,
    ScalarValue,
    _require_identifier,
    _require_non_negative_integer,
)
from .translation_contracts import TranslationPolicyProvenance

MIX_INTELLIGENCE_METHOD_ID = "noisyne.perceptual_mix_intelligence_foundation"
MIX_INTELLIGENCE_METHOD_VERSION = "1.0.0"
MIX_INTELLIGENCE_SCHEMA_VERSION = "1.0.0"


class MixIssuePriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MixIssueType(str, Enum):
    REFERENCE_DEVIATION = "reference_deviation"
    TRANSLATION_POLICY_EXCEEDED = "translation_policy_exceeded"
    MASKING_RELATIVE_MARGIN = "masking_relative_margin"
    CONTEXT_POLICY_CONFLICT = "context_policy_conflict"
    LEVEL_CONDITION = "level_condition"
    SPECTRAL_CONDITION = "spectral_condition"


class MixEvidenceSourceType(str, Enum):
    REFERENCE_EVIDENCE = "reference_evidence"
    TRANSLATION_EVIDENCE = "translation_evidence"
    TRANSLATION_POLICY_RESULT = "translation_policy_result"
    CONTEXT_RESOLUTION = "context_resolution"
    CONTEXT_POLICY_SELECTION = "context_policy_selection"
    MASKING_RELATIVE_MARGIN = "masking_relative_margin"


class MixEvidenceDimensionId(str, Enum):
    REFERENCE_BRIGHTNESS_CENTROID_DELTA_HZ = "reference.brightness_centroid_delta_hz"
    REFERENCE_PROGRAMME_ENERGY_DELTA_DB = "reference.programme_energy_delta_db"
    REFERENCE_ERB_BAND_MAXIMUM_ABSOLUTE_DELTA_DB = "reference.erb_band_maximum_absolute_delta_db"
    REFERENCE_SAMPLE_PEAK_DELTA_ABSOLUTE = "reference.sample_peak_delta_absolute"
    TRANSLATION_BRIGHTNESS_CENTROID_SHIFT_HZ = "translation.brightness_centroid_shift_hz"
    TRANSLATION_PROGRAMME_ENERGY_DELTA_DB = "translation.programme_energy_delta_db"
    TRANSLATION_ERB_BAND_MAXIMUM_ABSOLUTE_DELTA_DB = (
        "translation.erb_band_maximum_absolute_delta_db"
    )
    TRANSLATION_TRANSFERRED_PEAK_ABSOLUTE = "translation.transferred_peak_absolute"
    TRANSLATION_DECLARED_POLICY_THRESHOLD_EXCEEDED = (
        "translation_policy.declared_policy_threshold_exceeded"
    )
    CONTEXT_RESOLUTION_CONFLICT = "context.resolution_conflict"
    CONTEXT_POLICY_SELECTION_CONFLICT = "context.policy_selection_conflict"
    CONTEXT_POLICY_SELECTION_AMBIGUOUS = "context.policy_selection_ambiguous"
    MASKING_MAXIMUM_RELATIVE_EXCITATION_MARGIN_DB = "masking.maximum_relative_excitation_margin_db"


class MixCriterionOperator(str, Enum):
    GREATER_THAN = "greater_than"
    GREATER_THAN_OR_EQUAL = "greater_than_or_equal"
    LESS_THAN = "less_than"
    LESS_THAN_OR_EQUAL = "less_than_or_equal"
    ABSOLUTE_GREATER_THAN = "absolute_greater_than"
    ABSOLUTE_GREATER_THAN_OR_EQUAL = "absolute_greater_than_or_equal"
    BOOLEAN_IS_TRUE = "boolean_is_true"
    BOOLEAN_IS_FALSE = "boolean_is_false"


class MixEvaluationState(str, Enum):
    TRIGGERED = "triggered"
    NOT_TRIGGERED = "not_triggered"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    CONFLICT = "conflict"


_BOOLEAN_OPERATORS = {
    MixCriterionOperator.BOOLEAN_IS_TRUE,
    MixCriterionOperator.BOOLEAN_IS_FALSE,
}
_ABSOLUTE_OPERATORS = {
    MixCriterionOperator.ABSOLUTE_GREATER_THAN,
    MixCriterionOperator.ABSOLUTE_GREATER_THAN_OR_EQUAL,
}
_PRIORITY_ORDER = {
    MixIssuePriority.LOW: 0,
    MixIssuePriority.MEDIUM: 1,
    MixIssuePriority.HIGH: 2,
    MixIssuePriority.CRITICAL: 3,
}


def _validate_strings(values: list[str], field_name: str) -> None:
    if not isinstance(values, list):
        raise TypeError(f"{field_name} must be a list")
    for value in values:
        _require_identifier(value, field_name)


def _same_unit(left: ScalarValue, right: ScalarValue) -> bool:
    return (
        left.unit_basis is right.unit_basis
        and left.unit == right.unit
        and left.scale == right.scale
        and left.normalized == right.normalized
    )


@dataclass(frozen=True, slots=True)
class MixIssueCriterion(JsonContract):
    criterion_id: str
    version: str
    provenance: TranslationPolicyProvenance
    source: str
    description: str
    display_name: str
    evidence_source_type: MixEvidenceSourceType
    evidence_dimension: MixEvidenceDimensionId
    operator: MixCriterionOperator
    threshold: ScalarValue
    issue_type: MixIssueType
    priority: MixIssuePriority
    evidence_identity: str | None = None
    priority_rank: int | None = None
    assumptions: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        for field_name in (
            "criterion_id",
            "version",
            "source",
            "description",
            "display_name",
        ):
            _require_identifier(getattr(self, field_name), field_name)
        if not isinstance(self.provenance, TranslationPolicyProvenance):
            raise TypeError("provenance must be a TranslationPolicyProvenance")
        if not isinstance(self.evidence_source_type, MixEvidenceSourceType):
            raise TypeError("evidence_source_type must be a MixEvidenceSourceType")
        if not isinstance(self.evidence_dimension, MixEvidenceDimensionId):
            raise TypeError("evidence_dimension must be a MixEvidenceDimensionId")
        if not isinstance(self.operator, MixCriterionOperator):
            raise TypeError("operator must be a MixCriterionOperator")
        if not isinstance(self.threshold, ScalarValue):
            raise TypeError("threshold must be a ScalarValue")
        if not isinstance(self.issue_type, MixIssueType):
            raise TypeError("issue_type must be a MixIssueType")
        if not isinstance(self.priority, MixIssuePriority):
            raise TypeError("priority must be a MixIssuePriority")
        if self.evidence_identity is not None:
            _require_identifier(self.evidence_identity, "evidence_identity")
        if self.priority_rank is not None:
            _require_non_negative_integer(self.priority_rank, "priority_rank")

        if self.operator in _BOOLEAN_OPERATORS:
            expected = self.operator is MixCriterionOperator.BOOLEAN_IS_TRUE
            if type(self.threshold.value) is not bool or self.threshold.value is not expected:
                raise ValueError("boolean operator threshold must contain its exact boolean target")
        elif isinstance(self.threshold.value, bool) or not isinstance(
            self.threshold.value, int | float
        ):
            raise TypeError("numeric mix criteria require a numeric threshold")
        if self.operator in _ABSOLUTE_OPERATORS and float(self.threshold.value) < 0.0:
            raise ValueError("absolute comparison thresholds must be non-negative")
        _validate_evidence_dimension_scope(self.evidence_source_type, self.evidence_dimension)
        _validate_issue_type_scope(self.evidence_source_type, self.issue_type)
        _validate_strings(self.assumptions, "assumptions")
        _validate_strings(self.limitations, "limitations")


@dataclass(frozen=True, slots=True)
class MixIssuePolicy(JsonContract):
    policy_id: str
    version: str
    provenance: TranslationPolicyProvenance
    source: str
    description: str
    criteria: list[MixIssueCriterion]
    assumptions: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        for field_name in ("policy_id", "version", "source", "description"):
            _require_identifier(getattr(self, field_name), field_name)
        if not isinstance(self.provenance, TranslationPolicyProvenance):
            raise TypeError("provenance must be a TranslationPolicyProvenance")
        if not isinstance(self.criteria, list) or not self.criteria:
            raise ValueError("mix issue policy requires at least one criterion")
        if any(not isinstance(item, MixIssueCriterion) for item in self.criteria):
            raise TypeError("criteria must contain MixIssueCriterion values")
        identifiers = [item.criterion_id for item in self.criteria]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("criteria must use unique criterion_id values")
        if any(item.provenance is not self.provenance for item in self.criteria):
            raise ValueError("criterion provenance must match policy provenance")
        _validate_strings(self.assumptions, "assumptions")
        _validate_strings(self.limitations, "limitations")


@dataclass(frozen=True, slots=True)
class MixCriterionEvaluation(JsonContract):
    criterion_id: str
    criterion_version: str
    state: MixEvaluationState
    evidence_source_type: MixEvidenceSourceType
    evidence_dimension: MixEvidenceDimensionId
    reason: str
    evidence_identity: str | None = None
    evidence_value: ScalarValue | None = None
    evidence_state: ResultStatus | None = None
    evidence_method: MethodMetadata | None = None

    def __post_init__(self) -> None:
        for field_name in ("criterion_id", "criterion_version", "reason"):
            _require_identifier(getattr(self, field_name), field_name)
        if not isinstance(self.state, MixEvaluationState):
            raise TypeError("state must be a MixEvaluationState")
        if not isinstance(self.evidence_source_type, MixEvidenceSourceType):
            raise TypeError("evidence_source_type must be a MixEvidenceSourceType")
        if not isinstance(self.evidence_dimension, MixEvidenceDimensionId):
            raise TypeError("evidence_dimension must be a MixEvidenceDimensionId")
        if self.evidence_identity is not None:
            _require_identifier(self.evidence_identity, "evidence_identity")
        if self.evidence_state is not None and not isinstance(self.evidence_state, ResultStatus):
            raise TypeError("evidence_state must be a ResultStatus")
        computed = self.state in (
            MixEvaluationState.TRIGGERED,
            MixEvaluationState.NOT_TRIGGERED,
        )
        if computed:
            if (
                self.evidence_identity is None
                or not isinstance(self.evidence_value, ScalarValue)
                or self.evidence_state is not ResultStatus.COMPUTED
                or not isinstance(self.evidence_method, MethodMetadata)
            ):
                raise ValueError("computed criterion evaluation requires identified evidence")
        elif self.evidence_value is not None:
            raise ValueError("non-computed criterion evaluation must not carry an evidence value")


@dataclass(frozen=True, slots=True)
class MixIssue(JsonContract):
    issue_id: str
    policy_id: str
    policy_version: str
    criterion: MixIssueCriterion
    state: MixEvaluationState
    title: str
    evidence_identity: str
    evidence_value: ScalarValue
    evidence_method: MethodMetadata
    exceedance: ScalarValue | None
    confidence: Confidence
    evidence_references: list[str]
    assumptions: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        for field_name in (
            "issue_id",
            "policy_id",
            "policy_version",
            "title",
            "evidence_identity",
        ):
            _require_identifier(getattr(self, field_name), field_name)
        if not isinstance(self.criterion, MixIssueCriterion):
            raise TypeError("criterion must be a MixIssueCriterion")
        if self.state is not MixEvaluationState.TRIGGERED:
            raise ValueError("transported mix issues must be triggered")
        if self.title != self.criterion.display_name:
            raise ValueError("issue title must match its originating criterion")
        if not isinstance(self.evidence_value, ScalarValue):
            raise TypeError("evidence_value must be a ScalarValue")
        if not isinstance(self.evidence_method, MethodMetadata):
            raise TypeError("evidence_method must be MethodMetadata")
        if not isinstance(self.confidence, Confidence):
            raise TypeError("confidence must be Confidence")
        if (
            self.confidence.score is not None
            or self.confidence.basis is not ConfidenceBasis.UNKNOWN
        ):
            raise ValueError("mix issue confidence must remain unscored with unknown basis")
        expected_id = mix_issue_id(
            self.policy_id,
            self.policy_version,
            self.criterion,
            self.evidence_identity,
        )
        if self.issue_id != expected_id:
            raise ValueError("issue_id must be deterministically derived from policy and evidence")
        if not _same_unit(self.evidence_value, self.criterion.threshold):
            raise ValueError("issue evidence unit/scale must match criterion threshold")
        if not _criterion_triggered(
            self.evidence_value, self.criterion.operator, self.criterion.threshold
        ):
            raise ValueError("triggered issue evidence does not satisfy its criterion")
        expected_exceedance = _expected_exceedance(
            self.evidence_value, self.criterion.operator, self.criterion.threshold
        )
        if self.exceedance != expected_exceedance:
            raise ValueError("issue exceedance must exactly match criterion arithmetic")
        if not isinstance(self.evidence_references, list) or not self.evidence_references:
            raise ValueError("triggered issue requires evidence references")
        _validate_strings(self.evidence_references, "evidence_references")
        _validate_strings(self.assumptions, "assumptions")
        _validate_strings(self.limitations, "limitations")


@dataclass(frozen=True, slots=True)
class MixIntelligenceSummary(JsonContract):
    evaluated_criterion_count: int
    triggered_issue_count: int
    not_triggered_count: int
    insufficient_evidence_count: int
    conflict_count: int

    def __post_init__(self) -> None:
        for field_name in (
            "evaluated_criterion_count",
            "triggered_issue_count",
            "not_triggered_count",
            "insufficient_evidence_count",
            "conflict_count",
        ):
            _require_non_negative_integer(getattr(self, field_name), field_name)
        if self.evaluated_criterion_count != (
            self.triggered_issue_count
            + self.not_triggered_count
            + self.insufficient_evidence_count
            + self.conflict_count
        ):
            raise ValueError("evaluation summary counts must sum to evaluated_criterion_count")


@dataclass(frozen=True, slots=True)
class MixIntelligenceResult(JsonContract):
    policy: MixIssuePolicy
    method: MethodMetadata
    evaluations: list[MixCriterionEvaluation]
    issues: list[MixIssue]
    summary: MixIntelligenceSummary
    confidence: Confidence
    assumptions: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    schema_version: str = MIX_INTELLIGENCE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.policy, MixIssuePolicy):
            raise TypeError("policy must be a MixIssuePolicy")
        if not isinstance(self.method, MethodMetadata):
            raise TypeError("method must be MethodMetadata")
        if (
            self.method.method_id != MIX_INTELLIGENCE_METHOD_ID
            or self.method.version != MIX_INTELLIGENCE_METHOD_VERSION
        ):
            raise ValueError("unsupported mix intelligence method identity")
        if not isinstance(self.evaluations, list) or any(
            not isinstance(item, MixCriterionEvaluation) for item in self.evaluations
        ):
            raise TypeError("evaluations must contain MixCriterionEvaluation values")
        if not isinstance(self.issues, list) or any(
            not isinstance(item, MixIssue) for item in self.issues
        ):
            raise TypeError("issues must contain MixIssue values")
        if not isinstance(self.summary, MixIntelligenceSummary):
            raise TypeError("summary must be a MixIntelligenceSummary")
        if not isinstance(self.confidence, Confidence):
            raise TypeError("confidence must be Confidence")
        if (
            self.confidence.score is not None
            or self.confidence.basis is not ConfidenceBasis.UNKNOWN
        ):
            raise ValueError("mix intelligence confidence must remain unscored with unknown basis")
        _require_identifier(self.schema_version, "schema_version")

        expected_criteria = [(item.criterion_id, item.version) for item in self.policy.criteria]
        actual_criteria = [(item.criterion_id, item.criterion_version) for item in self.evaluations]
        if actual_criteria != expected_criteria:
            raise ValueError("evaluations must exactly match policy criteria in policy order")
        for criterion, evaluation in zip(self.policy.criteria, self.evaluations, strict=True):
            if (
                evaluation.evidence_source_type is not criterion.evidence_source_type
                or evaluation.evidence_dimension is not criterion.evidence_dimension
            ):
                raise ValueError("evaluation evidence target must match its policy criterion")
        issue_ids = [item.issue_id for item in self.issues]
        if len(issue_ids) != len(set(issue_ids)):
            raise ValueError("issues must use unique issue_id values")
        expected_issue_criteria = {
            item.criterion_id
            for item in self.evaluations
            if item.state is MixEvaluationState.TRIGGERED
        }
        if {item.criterion.criterion_id for item in self.issues} != expected_issue_criteria:
            raise ValueError("issues must correspond exactly to triggered evaluations")
        policy_by_id = {item.criterion_id: item for item in self.policy.criteria}
        evaluation_by_id = {item.criterion_id: item for item in self.evaluations}
        for issue in self.issues:
            if (
                issue.policy_id != self.policy.policy_id
                or issue.policy_version != self.policy.version
            ):
                raise ValueError("issue policy identity must match result policy")
            if issue.criterion != policy_by_id.get(issue.criterion.criterion_id):
                raise ValueError("issue criterion must exactly match its policy criterion")
            evaluation = evaluation_by_id[issue.criterion.criterion_id]
            if (
                evaluation.state is not MixEvaluationState.TRIGGERED
                or evaluation.evidence_identity != issue.evidence_identity
                or evaluation.evidence_value != issue.evidence_value
                or evaluation.evidence_method != issue.evidence_method
            ):
                raise ValueError("issue evidence must exactly match its triggered evaluation")
        if self.issues != sorted(self.issues, key=mix_issue_sort_key):
            raise ValueError("issues must use deterministic declared-priority ordering")

        counts = {state: 0 for state in MixEvaluationState}
        for evaluation in self.evaluations:
            counts[evaluation.state] += 1
        expected_summary = MixIntelligenceSummary(
            evaluated_criterion_count=len(self.evaluations),
            triggered_issue_count=counts[MixEvaluationState.TRIGGERED],
            not_triggered_count=counts[MixEvaluationState.NOT_TRIGGERED],
            insufficient_evidence_count=counts[MixEvaluationState.INSUFFICIENT_EVIDENCE],
            conflict_count=counts[MixEvaluationState.CONFLICT],
        )
        if self.summary != expected_summary or self.summary.triggered_issue_count != len(
            self.issues
        ):
            raise ValueError("summary counts must exactly match evaluations and issues")
        _validate_strings(self.assumptions, "assumptions")
        _validate_strings(self.limitations, "limitations")


def mix_issue_id(
    policy_id: str,
    policy_version: str,
    criterion: MixIssueCriterion,
    evidence_identity: str,
) -> str:
    material = (
        f"{policy_id}\x1f{policy_version}\x1f{criterion.criterion_id}\x1f"
        f"{criterion.version}\x1f{evidence_identity}"
    ).encode()
    return f"mix_issue.{hashlib.sha256(material).hexdigest()[:24]}"


def mix_issue_sort_key(issue: MixIssue) -> tuple[int, int, str]:
    rank = issue.criterion.priority_rank
    return (
        -_PRIORITY_ORDER[issue.criterion.priority],
        rank if rank is not None else 2**31 - 1,
        issue.criterion.criterion_id,
    )


def _criterion_triggered(
    actual: ScalarValue, operator: MixCriterionOperator, threshold: ScalarValue
) -> bool:
    if operator in _BOOLEAN_OPERATORS:
        if type(actual.value) is not bool:
            raise TypeError("boolean mix criterion requires boolean evidence")
        return actual.value is threshold.value
    if isinstance(actual.value, bool) or not isinstance(actual.value, int | float):
        raise TypeError("numeric mix criterion requires numeric evidence")
    value = float(actual.value)
    limit = float(threshold.value)
    if operator is MixCriterionOperator.GREATER_THAN:
        return value > limit
    if operator is MixCriterionOperator.GREATER_THAN_OR_EQUAL:
        return value >= limit
    if operator is MixCriterionOperator.LESS_THAN:
        return value < limit
    if operator is MixCriterionOperator.LESS_THAN_OR_EQUAL:
        return value <= limit
    if operator is MixCriterionOperator.ABSOLUTE_GREATER_THAN:
        return abs(value) > limit
    if operator is MixCriterionOperator.ABSOLUTE_GREATER_THAN_OR_EQUAL:
        return abs(value) >= limit
    raise ValueError(f"unsupported mix criterion operator: {operator!r}")


def _expected_exceedance(
    actual: ScalarValue, operator: MixCriterionOperator, threshold: ScalarValue
) -> ScalarValue | None:
    if operator in _BOOLEAN_OPERATORS:
        return None
    value = float(actual.value)
    limit = float(threshold.value)
    if operator in (
        MixCriterionOperator.GREATER_THAN,
        MixCriterionOperator.GREATER_THAN_OR_EQUAL,
    ):
        amount = value - limit
    elif operator in (
        MixCriterionOperator.LESS_THAN,
        MixCriterionOperator.LESS_THAN_OR_EQUAL,
    ):
        amount = limit - value
    else:
        amount = abs(value) - limit
    return ScalarValue(
        amount,
        actual.unit_basis,
        unit=actual.unit,
        scale=actual.scale,
        normalized=False,
    )


def _validate_issue_type_scope(
    source_type: MixEvidenceSourceType, issue_type: MixIssueType
) -> None:
    allowed = {
        MixEvidenceSourceType.REFERENCE_EVIDENCE: {
            MixIssueType.REFERENCE_DEVIATION,
            MixIssueType.LEVEL_CONDITION,
            MixIssueType.SPECTRAL_CONDITION,
        },
        MixEvidenceSourceType.TRANSLATION_EVIDENCE: {
            MixIssueType.LEVEL_CONDITION,
            MixIssueType.SPECTRAL_CONDITION,
        },
        MixEvidenceSourceType.TRANSLATION_POLICY_RESULT: {MixIssueType.TRANSLATION_POLICY_EXCEEDED},
        MixEvidenceSourceType.CONTEXT_RESOLUTION: {MixIssueType.CONTEXT_POLICY_CONFLICT},
        MixEvidenceSourceType.CONTEXT_POLICY_SELECTION: {MixIssueType.CONTEXT_POLICY_CONFLICT},
        MixEvidenceSourceType.MASKING_RELATIVE_MARGIN: {MixIssueType.MASKING_RELATIVE_MARGIN},
    }
    if issue_type not in allowed[source_type]:
        raise ValueError("issue_type is not valid for its evidence source type")


def _validate_evidence_dimension_scope(
    source_type: MixEvidenceSourceType, dimension: MixEvidenceDimensionId
) -> None:
    allowed = {
        MixEvidenceSourceType.REFERENCE_EVIDENCE: {
            MixEvidenceDimensionId.REFERENCE_BRIGHTNESS_CENTROID_DELTA_HZ,
            MixEvidenceDimensionId.REFERENCE_PROGRAMME_ENERGY_DELTA_DB,
            MixEvidenceDimensionId.REFERENCE_ERB_BAND_MAXIMUM_ABSOLUTE_DELTA_DB,
            MixEvidenceDimensionId.REFERENCE_SAMPLE_PEAK_DELTA_ABSOLUTE,
        },
        MixEvidenceSourceType.TRANSLATION_EVIDENCE: {
            MixEvidenceDimensionId.TRANSLATION_BRIGHTNESS_CENTROID_SHIFT_HZ,
            MixEvidenceDimensionId.TRANSLATION_PROGRAMME_ENERGY_DELTA_DB,
            MixEvidenceDimensionId.TRANSLATION_ERB_BAND_MAXIMUM_ABSOLUTE_DELTA_DB,
            MixEvidenceDimensionId.TRANSLATION_TRANSFERRED_PEAK_ABSOLUTE,
        },
        MixEvidenceSourceType.TRANSLATION_POLICY_RESULT: {
            MixEvidenceDimensionId.TRANSLATION_DECLARED_POLICY_THRESHOLD_EXCEEDED
        },
        MixEvidenceSourceType.CONTEXT_RESOLUTION: {
            MixEvidenceDimensionId.CONTEXT_RESOLUTION_CONFLICT
        },
        MixEvidenceSourceType.CONTEXT_POLICY_SELECTION: {
            MixEvidenceDimensionId.CONTEXT_POLICY_SELECTION_CONFLICT,
            MixEvidenceDimensionId.CONTEXT_POLICY_SELECTION_AMBIGUOUS,
        },
        MixEvidenceSourceType.MASKING_RELATIVE_MARGIN: {
            MixEvidenceDimensionId.MASKING_MAXIMUM_RELATIVE_EXCITATION_MARGIN_DB
        },
    }
    if dimension not in allowed[source_type]:
        raise ValueError("evidence_dimension is not valid for its evidence source type")


__all__ = [
    "MIX_INTELLIGENCE_METHOD_ID",
    "MIX_INTELLIGENCE_METHOD_VERSION",
    "MIX_INTELLIGENCE_SCHEMA_VERSION",
    "MixCriterionEvaluation",
    "MixCriterionOperator",
    "MixEvaluationState",
    "MixEvidenceDimensionId",
    "MixEvidenceSourceType",
    "MixIntelligenceResult",
    "MixIntelligenceSummary",
    "MixIssue",
    "MixIssuePolicy",
    "MixIssuePriority",
    "MixIssueType",
]

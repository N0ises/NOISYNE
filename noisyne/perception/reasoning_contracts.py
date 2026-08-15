from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol, runtime_checkable

from ._serialization import JsonContract
from .common import (
    Confidence,
    ConfidenceBasis,
    MethodMetadata,
    ScalarValue,
    _require_identifier,
    _require_non_negative_integer,
)
from .mix_intelligence_contracts import (
    MixCriterionOperator,
    MixEvidenceDimensionId,
    MixIssueType,
)

PERCEPTUAL_REASONING_METHOD_ID = "noisyne.grounded_perceptual_reasoning_foundation"
PERCEPTUAL_REASONING_METHOD_VERSION = "1.0.0"
PERCEPTUAL_REASONING_SCHEMA_VERSION = "1.0.0"


class ReasoningStatementKind(str, Enum):
    OBSERVATION = "observation"
    POLICY_INTERPRETATION = "policy_interpretation"
    LIMITATION = "limitation"
    REVIEW_SUGGESTION = "review_suggestion"


class ReasoningGroundingStatus(str, Enum):
    GROUNDED = "grounded"
    REJECTED_UNSUPPORTED = "rejected_unsupported"
    REJECTED_CONTRADICTED = "rejected_contradicted"


class GroundingFactType(str, Enum):
    POLICY_IDENTITY = "policy_identity"
    SUMMARY_COUNT = "summary_count"
    CONFIDENCE_SEMANTICS = "confidence_semantics"
    ISSUE_TYPE = "issue_type"
    ISSUE_TITLE = "issue_title"
    PRIORITY = "priority"
    EVIDENCE_IDENTITY = "evidence_identity"
    EVIDENCE_DIMENSION = "evidence_dimension"
    EVIDENCE_VALUE = "evidence_value"
    CRITERION_IDENTITY = "criterion_identity"
    THRESHOLD = "threshold"
    OPERATOR = "operator"
    EXCEEDANCE = "exceedance"
    TRIGGERED = "triggered"
    ASSUMPTION = "assumption"
    LIMITATION = "limitation"


class ReasoningProviderType(str, Enum):
    DETERMINISTIC_TEMPLATE = "deterministic_template"
    STRUCTURED_MODEL = "structured_model"


class ReasoningProviderAvailability(str, Enum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


class PerceptualReasoningState(str, Enum):
    COMPLETED = "completed"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    TIMEOUT = "timeout"
    INVALID_PROVIDER_RESPONSE = "invalid_provider_response"
    GROUNDING_REJECTED = "grounding_rejected"
    NO_GROUNDED_STATEMENTS = "no_grounded_statements"


class ReasoningErrorCode(str, Enum):
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    TIMEOUT = "timeout"
    INVALID_PROVIDER_RESPONSE = "invalid_provider_response"
    GROUNDING_REJECTED = "grounding_rejected"
    NO_GROUNDED_STATEMENTS = "no_grounded_statements"


@dataclass(frozen=True, slots=True)
class GroundingFact(JsonContract):
    fact_id: str
    fact_type: GroundingFactType
    value: ScalarValue
    source_contract: str
    source_identity: str
    issue_id: str | None = None
    criterion_id: str | None = None

    def __post_init__(self) -> None:
        for field_name in (
            "fact_id",
            "source_contract",
            "source_identity",
        ):
            _require_identifier(getattr(self, field_name), field_name)
        if not isinstance(self.fact_type, GroundingFactType):
            raise TypeError("fact_type must be a GroundingFactType")
        if not isinstance(self.value, ScalarValue):
            raise TypeError("fact value must be a ScalarValue")
        if (self.issue_id is None) is not (self.criterion_id is None):
            raise ValueError("fact issue_id and criterion_id must be supplied together")
        if self.issue_id is not None:
            _require_identifier(self.issue_id, "issue_id")
            _require_identifier(self.criterion_id, "criterion_id")


@dataclass(frozen=True, slots=True)
class ReasoningEvidenceReference(JsonContract):
    fact_id: str
    source_contract: str
    source_identity: str
    issue_id: str
    criterion_id: str

    def __post_init__(self) -> None:
        for field_name in (
            "fact_id",
            "source_contract",
            "source_identity",
            "issue_id",
            "criterion_id",
        ):
            _require_identifier(getattr(self, field_name), field_name)


@dataclass(frozen=True, slots=True)
class ReasoningProviderIdentity(JsonContract):
    provider_id: str
    provider_type: ReasoningProviderType
    provider_version: str
    structured_output_supported: bool
    availability: ReasoningProviderAvailability
    model_id: str | None = None
    model_version: str | None = None
    endpoint_type: str | None = None
    unavailable_reason: str | None = None

    def __post_init__(self) -> None:
        _require_identifier(self.provider_id, "provider_id")
        _require_identifier(self.provider_version, "provider_version")
        if not isinstance(self.provider_type, ReasoningProviderType):
            raise TypeError("provider_type must be a ReasoningProviderType")
        if type(self.structured_output_supported) is not bool:
            raise TypeError("structured_output_supported must be a bool")
        if not isinstance(self.availability, ReasoningProviderAvailability):
            raise TypeError("availability must be a ReasoningProviderAvailability")
        for field_name in ("model_id", "model_version", "endpoint_type"):
            value = getattr(self, field_name)
            if value is not None:
                _require_identifier(value, field_name)
        if self.availability is ReasoningProviderAvailability.UNAVAILABLE:
            _require_identifier(self.unavailable_reason, "unavailable_reason")
        elif self.unavailable_reason is not None:
            raise ValueError("available provider must not carry unavailable_reason")
        if self.provider_type is ReasoningProviderType.STRUCTURED_MODEL:
            if self.model_id is None or self.endpoint_type is None:
                raise ValueError("structured model provider requires model_id and endpoint_type")
        elif any(
            value is not None for value in (self.model_id, self.model_version, self.endpoint_type)
        ):
            raise ValueError("deterministic provider must not claim model or endpoint identity")


@dataclass(frozen=True, slots=True)
class ReasoningRequest(JsonContract):
    request_id: str
    source_policy_id: str
    source_policy_version: str
    issue_ids: list[str]
    allowed_facts: list[GroundingFact]

    def __post_init__(self) -> None:
        for field_name in ("request_id", "source_policy_id", "source_policy_version"):
            _require_identifier(getattr(self, field_name), field_name)
        _validate_string_list(self.issue_ids, "issue_ids")
        if len(self.issue_ids) != len(set(self.issue_ids)):
            raise ValueError("reasoning request issue_ids must be unique")
        if not isinstance(self.allowed_facts, list) or any(
            not isinstance(item, GroundingFact) for item in self.allowed_facts
        ):
            raise TypeError("allowed_facts must contain GroundingFact values")
        fact_ids = [item.fact_id for item in self.allowed_facts]
        if len(fact_ids) != len(set(fact_ids)):
            raise ValueError("reasoning request facts must use unique fact IDs")
        if any(
            item.issue_id is not None and item.issue_id not in self.issue_ids
            for item in self.allowed_facts
        ):
            raise ValueError("reasoning request facts must belong to declared issues")


@dataclass(frozen=True, slots=True)
class ProviderReasoningStatement(JsonContract):
    kind: ReasoningStatementKind
    template_id: str
    fact_ids: list[str]
    issue_id: str
    criterion_id: str
    text: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.kind, ReasoningStatementKind):
            raise TypeError("kind must be a ReasoningStatementKind")
        for field_name in ("template_id", "issue_id", "criterion_id"):
            _require_identifier(getattr(self, field_name), field_name)
        _validate_string_list(self.fact_ids, "fact_ids")
        if not self.fact_ids or len(self.fact_ids) != len(set(self.fact_ids)):
            raise ValueError("provider statement fact_ids must be non-empty and unique")
        if self.text is not None:
            _require_identifier(self.text, "text")


@dataclass(frozen=True, slots=True)
class ProviderReasoningResponse(JsonContract):
    statements: list[ProviderReasoningStatement]

    def __post_init__(self) -> None:
        if not isinstance(self.statements, list) or any(
            not isinstance(item, ProviderReasoningStatement) for item in self.statements
        ):
            raise TypeError("statements must contain ProviderReasoningStatement values")


@runtime_checkable
class PerceptualReasoningProvider(Protocol):
    @property
    def identity(self) -> ReasoningProviderIdentity: ...

    def generate(self, request: ReasoningRequest) -> ProviderReasoningResponse: ...


@dataclass(frozen=True, slots=True)
class ReasoningStatement(JsonContract):
    statement_id: str
    kind: ReasoningStatementKind
    text: str
    grounding_status: ReasoningGroundingStatus
    template_id: str
    issue_id: str
    criterion_id: str
    evidence_references: list[ReasoningEvidenceReference]
    source_facts: list[GroundingFact]
    assumptions: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        for field_name in (
            "statement_id",
            "text",
            "template_id",
            "issue_id",
            "criterion_id",
        ):
            _require_identifier(getattr(self, field_name), field_name)
        if not isinstance(self.kind, ReasoningStatementKind):
            raise TypeError("kind must be a ReasoningStatementKind")
        if self.grounding_status is not ReasoningGroundingStatus.GROUNDED:
            raise ValueError("accepted reasoning transport may contain only grounded statements")
        if (
            not isinstance(self.evidence_references, list)
            or not self.evidence_references
            or any(
                not isinstance(item, ReasoningEvidenceReference)
                for item in self.evidence_references
            )
        ):
            raise ValueError("grounded statement requires evidence references")
        if (
            not isinstance(self.source_facts, list)
            or not self.source_facts
            or any(not isinstance(item, GroundingFact) for item in self.source_facts)
        ):
            raise ValueError("grounded statement requires source facts")
        reference_ids = [item.fact_id for item in self.evidence_references]
        fact_ids = [item.fact_id for item in self.source_facts]
        if reference_ids != fact_ids or len(fact_ids) != len(set(fact_ids)):
            raise ValueError("statement evidence references must exactly match unique source facts")
        for reference, fact in zip(self.evidence_references, self.source_facts, strict=True):
            if (
                reference.source_contract != fact.source_contract
                or reference.source_identity != fact.source_identity
                or reference.issue_id != self.issue_id
                or reference.criterion_id != self.criterion_id
                or fact.issue_id != self.issue_id
                or fact.criterion_id != self.criterion_id
            ):
                raise ValueError("statement grounding must match its issue and criterion")
        if self.text != render_reasoning_statement(
            self.kind,
            self.template_id,
            self.source_facts,
        ):
            raise ValueError("statement text must match deterministic canonical rendering")
        _validate_string_list(self.assumptions, "assumptions")
        _validate_string_list(self.limitations, "limitations")


@dataclass(frozen=True, slots=True)
class PerceptualReasoningSummary(JsonContract):
    provider_statement_count: int
    grounded_statement_count: int
    rejected_statement_count: int

    def __post_init__(self) -> None:
        for field_name in (
            "provider_statement_count",
            "grounded_statement_count",
            "rejected_statement_count",
        ):
            _require_non_negative_integer(getattr(self, field_name), field_name)
        if self.provider_statement_count != (
            self.grounded_statement_count + self.rejected_statement_count
        ):
            raise ValueError("reasoning summary counts must balance")


@dataclass(frozen=True, slots=True)
class ReasoningError(JsonContract):
    code: ReasoningErrorCode
    safe_message: str

    def __post_init__(self) -> None:
        if not isinstance(self.code, ReasoningErrorCode):
            raise TypeError("code must be a ReasoningErrorCode")
        _require_identifier(self.safe_message, "safe_message")


@dataclass(frozen=True, slots=True)
class PerceptualReasoningResult(JsonContract):
    request_id: str
    state: PerceptualReasoningState
    provider: ReasoningProviderIdentity
    source_policy_id: str
    source_policy_version: str
    method: MethodMetadata
    facts: list[GroundingFact]
    statements: list[ReasoningStatement]
    summary: PerceptualReasoningSummary
    errors: list[ReasoningError]
    confidence: Confidence
    assumptions: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    schema_version: str = PERCEPTUAL_REASONING_SCHEMA_VERSION

    def __post_init__(self) -> None:
        for field_name in (
            "request_id",
            "source_policy_id",
            "source_policy_version",
            "schema_version",
        ):
            _require_identifier(getattr(self, field_name), field_name)
        if not isinstance(self.state, PerceptualReasoningState):
            raise TypeError("state must be a PerceptualReasoningState")
        if not isinstance(self.provider, ReasoningProviderIdentity):
            raise TypeError("provider must be a ReasoningProviderIdentity")
        if not isinstance(self.method, MethodMetadata):
            raise TypeError("method must be MethodMetadata")
        if (
            self.method.method_id != PERCEPTUAL_REASONING_METHOD_ID
            or self.method.version != PERCEPTUAL_REASONING_METHOD_VERSION
        ):
            raise ValueError("unsupported perceptual reasoning method identity")
        if not isinstance(self.facts, list) or any(
            not isinstance(item, GroundingFact) for item in self.facts
        ):
            raise TypeError("facts must contain GroundingFact values")
        fact_by_id = {item.fact_id: item for item in self.facts}
        if len(fact_by_id) != len(self.facts):
            raise ValueError("reasoning result facts must use unique fact IDs")
        if not isinstance(self.statements, list) or any(
            not isinstance(item, ReasoningStatement) for item in self.statements
        ):
            raise TypeError("statements must contain ReasoningStatement values")
        statement_ids = [item.statement_id for item in self.statements]
        if len(statement_ids) != len(set(statement_ids)):
            raise ValueError("reasoning statements must use unique statement IDs")
        for statement in self.statements:
            expected_id = reasoning_statement_id(
                self.provider.provider_id,
                statement.issue_id,
                statement.kind,
                statement.template_id,
                [item.fact_id for item in statement.source_facts],
            )
            if statement.statement_id != expected_id:
                raise ValueError("statement_id must be deterministically derived")
            for fact in statement.source_facts:
                if fact_by_id.get(fact.fact_id) != fact:
                    raise ValueError("statement source fact must exactly match result fact")
        if not isinstance(self.summary, PerceptualReasoningSummary):
            raise TypeError("summary must be a PerceptualReasoningSummary")
        if self.summary.grounded_statement_count != len(self.statements):
            raise ValueError("reasoning summary must match accepted statements")
        if not isinstance(self.errors, list) or any(
            not isinstance(item, ReasoningError) for item in self.errors
        ):
            raise TypeError("errors must contain ReasoningError values")
        if self.state is PerceptualReasoningState.COMPLETED:
            if not self.statements or self.errors:
                raise ValueError("completed reasoning requires statements and no errors")
        elif self.statements:
            raise ValueError("non-completed reasoning must not contain accepted statements")
        elif not self.errors:
            raise ValueError("non-completed reasoning requires a structured error")
        if not isinstance(self.confidence, Confidence):
            raise TypeError("confidence must be Confidence")
        if (
            self.confidence.score is not None
            or self.confidence.basis is not ConfidenceBasis.UNKNOWN
        ):
            raise ValueError("reasoning confidence must remain unscored with unknown basis")
        _validate_string_list(self.assumptions, "assumptions")
        _validate_string_list(self.limitations, "limitations")


def reasoning_statement_id(
    provider_id: str,
    issue_id: str,
    kind: ReasoningStatementKind,
    template_id: str,
    fact_ids: list[str],
) -> str:
    material = "\x1f".join(
        (provider_id, issue_id, kind.value, template_id, *sorted(fact_ids))
    ).encode()
    return f"reasoning_statement.{hashlib.sha256(material).hexdigest()[:24]}"


def render_reasoning_statement(
    kind: ReasoningStatementKind,
    template_id: str,
    facts: list[GroundingFact],
) -> str:
    fact_types = {item.fact_type for item in facts}
    if len(fact_types) != len(facts):
        raise ValueError("canonical statement facts must use unique fact types")
    if kind is ReasoningStatementKind.OBSERVATION:
        if template_id != "observation.scalar" or fact_types != {
            GroundingFactType.EVIDENCE_DIMENSION,
            GroundingFactType.EVIDENCE_VALUE,
        }:
            raise ValueError("observation template requires exact evidence facts")
        dimension = MixEvidenceDimensionId(
            str(_fact_by_type(facts, GroundingFactType.EVIDENCE_DIMENSION).value.value)
        )
        actual = _fact_by_type(facts, GroundingFactType.EVIDENCE_VALUE).value
        return f"{_DIMENSION_LABELS[dimension]} is {_format_scalar(actual, signed=True)}."
    if kind is ReasoningStatementKind.POLICY_INTERPRETATION:
        if template_id != "policy.declared_criterion_triggered" or fact_types != {
            GroundingFactType.EVIDENCE_VALUE,
            GroundingFactType.THRESHOLD,
            GroundingFactType.OPERATOR,
            GroundingFactType.TRIGGERED,
        }:
            raise ValueError("policy template requires exact criterion facts")
        threshold = _fact_by_type(facts, GroundingFactType.THRESHOLD).value
        operator = MixCriterionOperator(
            str(_fact_by_type(facts, GroundingFactType.OPERATOR).value.value)
        )
        triggered = _fact_by_type(facts, GroundingFactType.TRIGGERED).value.value
        if triggered is not True:
            raise ValueError("policy interpretation requires triggered fact")
        return (
            f"The declared criterion requires {_OPERATOR_PHRASES[operator]} "
            f"{_format_scalar(threshold)}; the supplied evidence satisfied it and the criterion "
            "was triggered."
        )
    issue_type = MixIssueType(str(_fact_by_type(facts, GroundingFactType.ISSUE_TYPE).value.value))
    if kind is ReasoningStatementKind.LIMITATION:
        if template_id != f"limitation.{issue_type.value}" or fact_types != {
            GroundingFactType.ISSUE_TYPE
        }:
            raise ValueError("limitation template requires exact issue-type fact")
        return _LIMITATIONS[issue_type]
    if kind is ReasoningStatementKind.REVIEW_SUGGESTION:
        if template_id != f"review.{issue_type.value}" or fact_types != {
            GroundingFactType.ISSUE_TYPE
        }:
            raise ValueError("review template requires exact issue-type fact")
        return _REVIEW_SUGGESTIONS[issue_type]
    raise ValueError("unsupported reasoning statement kind")


def _fact_by_type(facts: list[GroundingFact], fact_type: GroundingFactType) -> GroundingFact:
    matches = [item for item in facts if item.fact_type is fact_type]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one {fact_type.value} fact")
    return matches[0]


def _format_scalar(value: ScalarValue, *, signed: bool = False) -> str:
    raw = value.value
    if type(raw) is bool:
        rendered = "true" if raw else "false"
    elif isinstance(raw, int | float):
        rendered = f"{float(raw):+.2f}" if signed else f"{float(raw):.2f}"
    else:
        rendered = str(raw)
    return f"{rendered} {value.unit}" if value.unit else rendered


_DIMENSION_LABELS = {
    MixEvidenceDimensionId.REFERENCE_BRIGHTNESS_CENTROID_DELTA_HZ: (
        "Reference brightness-centroid delta"
    ),
    MixEvidenceDimensionId.REFERENCE_PROGRAMME_ENERGY_DELTA_DB: (
        "Reference programme energy delta"
    ),
    MixEvidenceDimensionId.REFERENCE_ERB_BAND_MAXIMUM_ABSOLUTE_DELTA_DB: (
        "Reference ERB-band maximum absolute delta"
    ),
    MixEvidenceDimensionId.REFERENCE_SAMPLE_PEAK_DELTA_ABSOLUTE: (
        "Reference sample-peak absolute delta"
    ),
    MixEvidenceDimensionId.TRANSLATION_BRIGHTNESS_CENTROID_SHIFT_HZ: (
        "Translation brightness-centroid shift"
    ),
    MixEvidenceDimensionId.TRANSLATION_PROGRAMME_ENERGY_DELTA_DB: (
        "Translation programme energy delta"
    ),
    MixEvidenceDimensionId.TRANSLATION_ERB_BAND_MAXIMUM_ABSOLUTE_DELTA_DB: (
        "Translation ERB-band maximum absolute delta"
    ),
    MixEvidenceDimensionId.TRANSLATION_TRANSFERRED_PEAK_ABSOLUTE: (
        "Transferred sample-peak magnitude"
    ),
    MixEvidenceDimensionId.TRANSLATION_DECLARED_POLICY_THRESHOLD_EXCEEDED: (
        "Declared translation policy threshold exceeded"
    ),
    MixEvidenceDimensionId.CONTEXT_RESOLUTION_CONFLICT: "Context resolution conflict",
    MixEvidenceDimensionId.CONTEXT_POLICY_SELECTION_CONFLICT: ("Context policy-selection conflict"),
    MixEvidenceDimensionId.CONTEXT_POLICY_SELECTION_AMBIGUOUS: (
        "Context policy selection ambiguous"
    ),
    MixEvidenceDimensionId.MASKING_MAXIMUM_RELATIVE_EXCITATION_MARGIN_DB: (
        "Maximum relative excitation margin"
    ),
}

_OPERATOR_PHRASES = {
    MixCriterionOperator.GREATER_THAN: "greater than",
    MixCriterionOperator.GREATER_THAN_OR_EQUAL: "greater than or equal to",
    MixCriterionOperator.LESS_THAN: "less than",
    MixCriterionOperator.LESS_THAN_OR_EQUAL: "less than or equal to",
    MixCriterionOperator.ABSOLUTE_GREATER_THAN: "absolute value greater than",
    MixCriterionOperator.ABSOLUTE_GREATER_THAN_OR_EQUAL: (
        "absolute value greater than or equal to"
    ),
    MixCriterionOperator.BOOLEAN_IS_TRUE: "the boolean value true",
    MixCriterionOperator.BOOLEAN_IS_FALSE: "the boolean value false",
}

_LIMITATIONS = {
    MixIssueType.REFERENCE_DEVIATION: (
        "Reference deviation does not establish quality loss or perceptual preference."
    ),
    MixIssueType.TRANSLATION_POLICY_EXCEEDED: (
        "A declared translation-policy outcome is not a probability of translation failure."
    ),
    MixIssueType.MASKING_RELATIVE_MARGIN: (
        "Relative excitation-margin evidence does not establish audibility or inaudibility."
    ),
    MixIssueType.CONTEXT_POLICY_CONFLICT: (
        "This is a workflow or configuration conflict, not an audio-quality finding."
    ),
    MixIssueType.LEVEL_CONDITION: (
        "A declared level condition does not establish perceived loudness quality."
    ),
    MixIssueType.SPECTRAL_CONDITION: (
        "A declared spectral condition does not establish a subjective timbral defect."
    ),
}

_REVIEW_SUGGESTIONS = {
    MixIssueType.REFERENCE_DEVIATION: "Review the declared reference relationship.",
    MixIssueType.TRANSLATION_POLICY_EXCEEDED: (
        "Review the declared translation criterion and its evidence."
    ),
    MixIssueType.MASKING_RELATIVE_MARGIN: (
        "Review the declared masker-target relationship and relative-margin criterion."
    ),
    MixIssueType.CONTEXT_POLICY_CONFLICT: (
        "Resolve the conflicting or ambiguous context declarations before interpretation."
    ),
    MixIssueType.LEVEL_CONDITION: "Review the declared level criterion and its evidence.",
    MixIssueType.SPECTRAL_CONDITION: "Review the declared spectral criterion and its evidence.",
}


def _validate_string_list(values: list[str], field_name: str) -> None:
    if not isinstance(values, list):
        raise TypeError(f"{field_name} must be a list")
    for value in values:
        _require_identifier(value, field_name)


__all__ = [
    "PERCEPTUAL_REASONING_METHOD_ID",
    "PERCEPTUAL_REASONING_METHOD_VERSION",
    "PERCEPTUAL_REASONING_SCHEMA_VERSION",
    "GroundingFact",
    "GroundingFactType",
    "PerceptualReasoningProvider",
    "PerceptualReasoningResult",
    "PerceptualReasoningState",
    "PerceptualReasoningSummary",
    "ProviderReasoningResponse",
    "ProviderReasoningStatement",
    "ReasoningError",
    "ReasoningErrorCode",
    "ReasoningEvidenceReference",
    "ReasoningGroundingStatus",
    "ReasoningProviderAvailability",
    "ReasoningProviderIdentity",
    "ReasoningProviderType",
    "ReasoningRequest",
    "ReasoningStatement",
    "ReasoningStatementKind",
    "render_reasoning_statement",
]
